#!/usr/bin/env python3
"""bd create dup detector.

Reads candidate title (and optional description) on argv/stdin, scores
similarity against all open beads, and emits top-K candidates if any
exceed the warning threshold.

Signal stack (per sylveste-a4oj.9.3 / KF-02 + POLY-5):
  - TF-IDF cosine over title+description (semantic-ish; rare tokens carry
    more weight than common ones, so distinctive identifiers like
    "GIT_INDEX_FILE" or "session-freshness" boost similarity even when
    surface phrasing differs)
  - Label overlap (Jaccard)
  - Recency decay: 1 / log(days_since_updated + 2)
  - 3-gram exact (POLY-5's bird-homing tertiary): boosts when the candidate
    contains a 3+ word phrase that also appears in an existing bead

Composite score: weighted sum; threshold-gated.

Usage:
  python3 lib-bd-dup-check.py --title "<t>" [--description "<d>"]
                              [--labels a,b,c] [--threshold 0.55] [--top 5]
                              [--db <path>]

Exit codes:
  0 — no dup candidates above threshold
  1 — dup candidates printed (caller decides whether to proceed)
  2 — error (bd unavailable, etc.)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass


WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
DEFAULT_THRESHOLD = 0.30
DEFAULT_TOP = 5


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text or "")]


def trigrams(tokens: list[str]) -> set[tuple[str, str, str]]:
    return {(tokens[i], tokens[i + 1], tokens[i + 2]) for i in range(len(tokens) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def days_since(iso_ts: str | None) -> float:
    if not iso_ts:
        return 365.0
    try:
        # bd timestamps look like "2026-05-04T12:34:56Z" or with offset
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 86400.0)
    except Exception:
        return 365.0


def recency_weight(days: float) -> float:
    """Saturating recency in [0, 1.0]. 1.0 for same-day, ~0.5 at ~5 days, ~0.27 at ~50 days."""
    return min(1.0, 1.0 / math.log(days + 2.0, math.e))


@dataclass
class Bead:
    id: str
    title: str
    description: str
    labels: list[str]
    updated: str | None
    status: str

    @property
    def text_tokens(self) -> list[str]:
        return tokenize(f"{self.title} {self.description}")


def fetch_open_beads(db_path: str | None = None) -> list[Bead]:
    """Run `bd list --status open --limit 0 --json` and parse the array.

    bd's --json output is a JSON array followed by a footer line. We use
    raw_decode to consume just the array."""
    cmd = ["bd"]
    if db_path:
        cmd += ["--db", db_path]
    # Include in_progress + blocked + deferred — anything not closed is a
    # potential dup target. A bead that's actively being worked on is the
    # likeliest dup of a freshly-filed identical bead.
    cmd += ["list", "--status", "open,in_progress,blocked,deferred", "--limit", "0", "--json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"bd-dup-check: bd unavailable ({e})", file=sys.stderr)
        return []

    decoder = json.JSONDecoder()
    text = out.lstrip()
    try:
        arr, _ = decoder.raw_decode(text)
    except json.JSONDecodeError as e:
        print(f"bd-dup-check: failed to parse bd output ({e})", file=sys.stderr)
        return []
    if not isinstance(arr, list):
        return []

    beads: list[Bead] = []
    for o in arr:
        if not isinstance(o, dict):
            continue
        beads.append(Bead(
            id=o.get("id", ""),
            title=o.get("title", ""),
            description=o.get("description", "") or "",
            labels=o.get("labels", []) or [],
            updated=o.get("updated_at") or o.get("updated") or o.get("created_at"),
            status=o.get("status", "open"),
        ))
    return beads


def build_idf(corpus: list[list[str]]) -> dict[str, float]:
    """idf(t) = log(N / (1 + df(t)))"""
    n = len(corpus) or 1
    df: Counter[str] = Counter()
    for tokens in corpus:
        for t in set(tokens):
            df[t] += 1
    return {t: math.log(n / (1 + dft)) for t, dft in df.items()}


def tfidf_vec(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    if not tf:
        return {}
    max_tf = max(tf.values())
    return {
        t: (0.5 + 0.5 * c / max_tf) * idf.get(t, 0.0)
        for t, c in tf.items()
    }


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0.0) for k in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return (dot / (na * nb)) if (na and nb) else 0.0


def score_against(
    cand_title_tokens: list[str],
    cand_full_tokens: list[str],
    cand_trigrams: set,
    cand_labels: set[str],
    bead: Bead,
    idf_full: dict[str, float],
    idf_title: dict[str, float],
    cand_vec_full: dict[str, float],
    cand_vec_title: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """Return composite score and component breakdown.

    Two cosine signals: title-only (high precision for rename dups) and
    title+description (broader semantic). Title-only carries more weight
    because long descriptions dilute the headline-concept similarity.
    """
    bead_title_tokens = tokenize(bead.title)
    bead_full_tokens = bead.text_tokens
    bead_vec_full = tfidf_vec(bead_full_tokens, idf_full)
    bead_vec_title = tfidf_vec(bead_title_tokens, idf_title)

    cos_title = cosine(cand_vec_title, bead_vec_title)
    cos_full = cosine(cand_vec_full, bead_vec_full)
    tri = jaccard(cand_trigrams, trigrams(bead_full_tokens))
    lab = jaccard(cand_labels, set(bead.labels))
    rec = recency_weight(days_since(bead.updated))

    # Title cosine carries the most weight because it captures the
    # headline-concept overlap without dilution from long descriptions.
    # Full-text cosine catches deeper semantic overlap when titles diverge.
    similarity = (
        0.45 * cos_title +
        0.25 * cos_full +
        0.20 * tri +
        0.10 * lab
    )
    # Recency multiplier saturates at 1.0; stale-bead similarities are
    # attenuated to avoid surfacing year-old dups for a brand-new bead that
    # happens to share vocabulary.
    composite = similarity * (0.4 + 0.6 * rec)
    return composite, {
        "cosine_title": cos_title,
        "cosine_full": cos_full,
        "trigram": tri,
        "label": lab,
        "recency": rec,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="bd create dup detector")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--labels", default="", help="comma-separated")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--top", type=int, default=DEFAULT_TOP)
    p.add_argument("--db", default=None)
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON output")
    args = p.parse_args()

    beads = fetch_open_beads(args.db)
    if not beads:
        if args.json:
            print(json.dumps({"candidates": [], "reason": "no_open_beads"}))
        return 0

    cand_full_tokens = tokenize(f"{args.title} {args.description}")
    cand_title_tokens = tokenize(args.title)
    cand_trigrams = trigrams(cand_full_tokens)
    cand_labels = set(filter(None, [s.strip() for s in args.labels.split(",")]))

    # Build separate IDFs for full text and title-only over candidate + beads.
    # Title IDF gives titular-rare tokens the weight they deserve.
    corpus_full = [cand_full_tokens] + [b.text_tokens for b in beads]
    corpus_title = [cand_title_tokens] + [tokenize(b.title) for b in beads]
    idf_full = build_idf(corpus_full)
    idf_title = build_idf(corpus_title)
    cand_vec_full = tfidf_vec(cand_full_tokens, idf_full)
    cand_vec_title = tfidf_vec(cand_title_tokens, idf_title)

    scored = []
    for b in beads:
        composite, parts = score_against(
            cand_title_tokens, cand_full_tokens, cand_trigrams, cand_labels,
            b, idf_full, idf_title, cand_vec_full, cand_vec_title,
        )
        scored.append((composite, parts, b))
    scored.sort(key=lambda x: x[0], reverse=True)

    candidates = [
        {
            "id": b.id,
            "title": b.title,
            "score": round(composite, 3),
            "components": {k: round(v, 3) for k, v in parts.items()},
        }
        for composite, parts, b in scored[: args.top]
        if composite >= args.threshold
    ]

    if args.json:
        print(json.dumps({"candidates": candidates, "threshold": args.threshold}, indent=2))
        return 1 if candidates else 0

    if not candidates:
        return 0

    print(f"\n⚠  Possible duplicate(s) of an open bead (threshold={args.threshold}):", file=sys.stderr)
    for c in candidates:
        comps = c["components"]
        print(
            f"  {c['id']}  score={c['score']:.2f}  "
            f"(cos_t={comps['cosine_title']:.2f} cos_f={comps['cosine_full']:.2f} "
            f"tri={comps['trigram']:.2f} lab={comps['label']:.2f} rec={comps['recency']:.2f})\n"
            f"    {c['title'][:90]}",
            file=sys.stderr,
        )
    print("", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
