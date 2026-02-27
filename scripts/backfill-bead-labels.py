#!/usr/bin/env python3
"""
Backfill theme and module labels onto beads based on title/description heuristics.

Label taxonomy (two dimensions):

MODULE labels (mod:<name>) — which pillar/subproject:
  mod:clavain, mod:intercore, mod:intermute, mod:autarch, mod:intercom,
  mod:interspect, mod:interverse, mod:interflux, mod:interkasten,
  mod:interlock, mod:intermap, mod:interpath, mod:interwatch,
  mod:interject, mod:intermem, mod:interbase, mod:intercache,
  mod:interform, mod:interline, mod:interpeer, mod:intersearch,
  mod:interpub, mod:interphase, mod:interdev, mod:interserve,
  mod:interdoc, mod:intership, mod:internext, mod:intertest,
  mod:interslack, mod:interlens, mod:intermux, mod:interfluence,
  mod:intersynth, mod:intercraft, mod:demarch, mod:tldrs

THEME labels (theme:<name>) — what kind of work:
  theme:tech-debt, theme:performance, theme:security, theme:ux,
  theme:observability, theme:dx, theme:infra, theme:docs,
  theme:testing, theme:architecture, theme:coordination,
  theme:research

Rules:
- Module is inferred from [module] prefix in title, or keyword matches in title+description
- Theme is inferred from keyword patterns in title+description
- Labels are additive (never removes existing labels)
- Idempotent (skips beads that already have the label)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Module detection
# ---------------------------------------------------------------------------

# Canonical bracket prefixes -> module label
BRACKET_MAP: dict[str, str] = {
    "clavain": "mod:clavain",
    "intercore": "mod:intercore",
    "intermute": "mod:intermute",
    "autarch": "mod:autarch",
    "intercom": "mod:intercom",
    "interspect": "mod:interspect",
    "interverse": "mod:interverse",
    "interflux": "mod:interflux",
    "interkasten": "mod:interkasten",
    "interlock": "mod:interlock",
    "intermap": "mod:intermap",
    "interpath": "mod:interpath",
    "interwatch": "mod:interwatch",
    "interject": "mod:interject",
    "intermem": "mod:intermem",
    "interbase": "mod:interbase",
    "intercache": "mod:intercache",
    "interform": "mod:interform",
    "interline": "mod:interline",
    "interpeer": "mod:interpeer",
    "intersearch": "mod:intersearch",
    "interpub": "mod:interpub",
    "interphase": "mod:interphase",
    "interdev": "mod:interdev",
    "interserve": "mod:interserve",
    "interdoc": "mod:interdoc",
    "intership": "mod:intership",
    "internext": "mod:internext",
    "intertest": "mod:intertest",
    "interslack": "mod:interslack",
    "interlens": "mod:interlens",
    "intermux": "mod:intermux",
    "interfluence": "mod:interfluence",
    "intersynth": "mod:intersynth",
    "intercraft": "mod:intercraft",
    "tldrs": "mod:tldrs",
    "tldr-swinton": "mod:tldrs",
    "flux-drive": "mod:interflux",
    "flux-drive-spec": "mod:interflux",
    "coldwine": "mod:autarch",
    "gurgeh": "mod:autarch",
    "bigend": "mod:autarch",
    "pollard": "mod:autarch",
    "recovered-doc": None,  # skip, not a module
    "recovered": None,
    "roadmap-recovery": None,
    "vision": None,  # skip, too ambiguous
}

# Keyword patterns in title/description -> module label
# Order matters: first match wins for ambiguous cases
MODULE_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bclavain\b", re.I), "mod:clavain"),
    (re.compile(r"\bintercore\b", re.I), "mod:intercore"),
    (re.compile(r"\bintermute\b", re.I), "mod:intermute"),
    (re.compile(r"\bautarch\b", re.I), "mod:autarch"),
    (re.compile(r"\bcoldwine\b", re.I), "mod:autarch"),
    (re.compile(r"\bgurgeh\b", re.I), "mod:autarch"),
    (re.compile(r"\bbigend\b", re.I), "mod:autarch"),
    (re.compile(r"\bpollard\b", re.I), "mod:autarch"),
    (re.compile(r"\bintercom\b", re.I), "mod:intercom"),
    (re.compile(r"\binterspect\b", re.I), "mod:interspect"),
    (re.compile(r"\binterverse\b", re.I), "mod:interverse"),
    (re.compile(r"\binterflux\b", re.I), "mod:interflux"),
    (re.compile(r"\bflux-drive\b", re.I), "mod:interflux"),
    (re.compile(r"\binterkasten\b", re.I), "mod:interkasten"),
    (re.compile(r"\binterlock\b", re.I), "mod:interlock"),
    (re.compile(r"\bintermap\b", re.I), "mod:intermap"),
    (re.compile(r"\binterpath\b", re.I), "mod:interpath"),
    (re.compile(r"\binterwatch\b", re.I), "mod:interwatch"),
    (re.compile(r"\binterject\b", re.I), "mod:interject"),
    (re.compile(r"\bintermem\b", re.I), "mod:intermem"),
    (re.compile(r"\binterbase\b", re.I), "mod:interbase"),
    (re.compile(r"\bintercache\b", re.I), "mod:intercache"),
    (re.compile(r"\binterform\b", re.I), "mod:interform"),
    (re.compile(r"\binterline\b", re.I), "mod:interline"),
    (re.compile(r"\binterpeer\b", re.I), "mod:interpeer"),
    (re.compile(r"\bintersearch\b", re.I), "mod:intersearch"),
    (re.compile(r"\binterpub\b", re.I), "mod:interpub"),
    (re.compile(r"\binterphase\b", re.I), "mod:interphase"),
    (re.compile(r"\binterdev\b", re.I), "mod:interdev"),
    (re.compile(r"\binterserve\b", re.I), "mod:interserve"),
    (re.compile(r"\binterdoc\b", re.I), "mod:interdoc"),
    (re.compile(r"\bintership\b", re.I), "mod:intership"),
    (re.compile(r"\binternext\b", re.I), "mod:internext"),
    (re.compile(r"\bintertest\b", re.I), "mod:intertest"),
    (re.compile(r"\binterslack\b", re.I), "mod:interslack"),
    (re.compile(r"\binterlens\b", re.I), "mod:interlens"),
    (re.compile(r"\bintermux\b", re.I), "mod:intermux"),
    (re.compile(r"\binterfluence\b", re.I), "mod:interfluence"),
    (re.compile(r"\bintersynth\b", re.I), "mod:intersynth"),
    (re.compile(r"\bintercraft\b", re.I), "mod:intercraft"),
    (re.compile(r"\btldrs\b", re.I), "mod:tldrs"),
    (re.compile(r"\btldr-swinton\b", re.I), "mod:tldrs"),
    (re.compile(r"\bIronClaw\b", re.I), "mod:intercom"),
    (re.compile(r"\bbeads\b", re.I), "mod:demarch"),
    (re.compile(r"\bmonorepo\b", re.I), "mod:demarch"),
    (re.compile(r"\binstall\.sh\b", re.I), "mod:demarch"),
    (re.compile(r"\bic publish\b", re.I), "mod:demarch"),
]

# ---------------------------------------------------------------------------
# Theme detection
# ---------------------------------------------------------------------------

THEME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # tech-debt
    (re.compile(r"\btech.?debt\b|\brefactor\b|\bcleanup\b|\bdeprecate\b|\blegacy\b|\bdead code\b|\bshellcheck\b|\bharden\b", re.I), "theme:tech-debt"),
    # performance
    (re.compile(r"\bperf\b|\bperformance\b|\boptimi[sz]\b|\blatency\b|\bthroughput\b|\bbottleneck\b|\bcache\b|\bpre-filter\b|\btoken.?effici\b", re.I), "theme:performance"),
    # security
    (re.compile(r"\bsecur\b|\bsecret.?scan\b|\bcredential\b|\bauth\b|\btrust\b|\bpermission\b|\baccess.?control\b|\bsandbox\b|\bgitleaks\b|\bwaiver\b", re.I), "theme:security"),
    # ux
    (re.compile(r"\bux\b|\bonboarding\b|\btui\b|\bdashboard\b|\bsidebar\b|\bui\b|\bdisplay\b|\bvisual\b|\bprogressive.?disclos\b", re.I), "theme:ux"),
    # observability
    (re.compile(r"\bobservab\b|\blogging\b|\btrac(?:e|ing)\b|\bmetric\b|\bmonitor\b|\btelemetry\b|\bheartbeat\b|\bdiagnostic\b", re.I), "theme:observability"),
    # dx (developer experience)
    (re.compile(r"\bdeveloper.?exp\b|\bdx\b|\bcli\b|\bskill\b|\bhook\b|\bplugin\b|\bscaffold\b|\btemplate\b|\bboilerplate\b|\bsetup\b|\binstall\b", re.I), "theme:dx"),
    # infra
    (re.compile(r"\bci\b|\bcd\b|\bbuild\b|\bdeploy\b|\bgithub.?action\b|\bdependabot\b|\bworkflow\b|\brelease\b|\bpipeline\b|\bsystemd\b", re.I), "theme:infra"),
    # docs
    (re.compile(r"\bdoc(?:s|umentation)\b|\bagents\.md\b|\bclaude\.md\b|\breadme\b|\bguide\b|\bchangelog\b", re.I), "theme:docs"),
    # testing
    (re.compile(r"\btest\b|\btdd\b|\bcoverage\b|\bregression\b|\bsmoke.?test\b|\bintegration.?test\b|\bunit.?test\b|\bbenchmark\b", re.I), "theme:testing"),
    # architecture
    (re.compile(r"\barchitect\b|\bmodule.?boundar\b|\bdecompos\b|\bmigrat(?:e|ion)\b|\breplatform\b|\bschema\b|\bkernel\b|\bevent.?sourc\b", re.I), "theme:architecture"),
    # coordination (multi-agent)
    (re.compile(r"\bcoordinat\b|\bmulti.?agent\b|\borch(?:estrat|estr)\b|\bdispatch\b|\breservation\b|\bclaiming\b|\bbroadcast\b|\bmessag(?:e|ing)\b|\bagent.?mail\b", re.I), "theme:coordination"),
    # research
    (re.compile(r"\bresearch\b|\bbrainstorm\b|\bexplor\b|\bprototype\b|\bspike\b|\bpoc\b|\bexperiment\b", re.I), "theme:research"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BRACKET_RE = re.compile(r"\[([a-z][a-z0-9_-]*)\]", re.I)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def get_existing_labels(issue_id: str) -> set[str]:
    r = run(["bd", "sql", "--json", f'select label from labels where issue_id = "{issue_id}"'])
    if r.returncode != 0:
        return set()
    try:
        rows = json.loads(r.stdout or "[]")
        return {row["label"] for row in rows}
    except Exception:
        return set()


def add_label(issue_id: str, label: str, dry_run: bool) -> bool:
    if dry_run:
        return True
    r = run(["bd", "label", "add", issue_id, label])
    return r.returncode == 0


def bulk_insert_labels(pairs: list[tuple[str, str]], dry_run: bool, batch_size: int = 50) -> tuple[int, int]:
    """Insert labels via direct SQL in batches. Returns (ok, failed)."""
    if dry_run:
        return len(pairs), 0
    ok = 0
    failed = 0
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i + batch_size]
        values = ", ".join(f'("{eid}", "{lab}")' for eid, lab in batch)
        query = f"insert ignore into labels (issue_id, label) values {values}"
        r = run(["bd", "sql", query])
        if r.returncode == 0:
            ok += len(batch)
        else:
            # Fall back to individual inserts
            for eid, lab in batch:
                r2 = run(["bd", "label", "add", eid, lab])
                if r2.returncode == 0:
                    ok += 1
                else:
                    failed += 1
    return ok, failed


def detect_modules(title: str, description: str) -> set[str]:
    modules: set[str] = set()
    # 1) Bracket prefixes in title
    for m in BRACKET_RE.finditer(title):
        bracket = m.group(1).lower()
        if bracket in BRACKET_MAP:
            label = BRACKET_MAP[bracket]
            if label:
                modules.add(label)
    # 2) Keyword matches in title + description
    text = f"{title} {description}"
    for pattern, label in MODULE_KEYWORDS:
        if pattern.search(text):
            modules.add(label)
    return modules


def detect_themes(title: str, description: str) -> set[str]:
    themes: set[str] = set()
    text = f"{title} {description}"
    for pattern, label in THEME_PATTERNS:
        if pattern.search(text):
            themes.add(label)
    return themes


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill theme and module labels onto beads.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    parser.add_argument("--limit", type=int, default=0, help="Limit to N beads (0=all)")
    parser.add_argument("--status", default="all", choices=["all", "open", "closed"], help="Filter by status")
    args = parser.parse_args()

    # Fetch all beads
    query = 'select id, title, description, status from issues'
    if args.status == "open":
        query += ' where status in ("open", "in_progress")'
    elif args.status == "closed":
        query += ' where status = "closed"'
    if args.limit:
        query += f" limit {args.limit}"

    r = run(["bd", "sql", "--json", query])
    if r.returncode != 0:
        print(f"error: bd sql failed: {r.stderr}", file=sys.stderr)
        return 1

    beads = json.loads(r.stdout or "[]")
    print(f"Processing {len(beads)} beads...")

    # Fetch all existing labels in one query
    print("Loading existing labels...")
    r_labels = run(["bd", "sql", "--json", "select issue_id, label from labels"])
    existing_map: dict[str, set[str]] = {}
    if r_labels.returncode == 0:
        for row in json.loads(r_labels.stdout or "[]"):
            existing_map.setdefault(row["issue_id"], set()).add(row["label"])
    print(f"Loaded {sum(len(v) for v in existing_map.values())} existing labels across {len(existing_map)} beads")

    stats = {"checked": 0, "labeled": 0, "labels_added": 0, "skipped": 0, "failed": 0}
    module_counts: dict[str, int] = {}
    theme_counts: dict[str, int] = {}
    all_pairs: list[tuple[str, str]] = []

    for bead in beads:
        bead_id = bead["id"]
        title = bead.get("title", "")
        desc = bead.get("description", "")
        stats["checked"] += 1

        new_modules = detect_modules(title, desc)
        new_themes = detect_themes(title, desc)
        new_labels = new_modules | new_themes

        if not new_labels:
            stats["skipped"] += 1
            continue

        existing = existing_map.get(bead_id, set())
        to_add = new_labels - existing

        if not to_add:
            stats["skipped"] += 1
            continue

        stats["labeled"] += 1
        for label in sorted(to_add):
            all_pairs.append((bead_id, label))
            prefix = "would_add" if args.dry_run else "add"
            print(f"  {prefix} {bead_id} <- {label}")
            if label.startswith("mod:"):
                module_counts[label] = module_counts.get(label, 0) + 1
            elif label.startswith("theme:"):
                theme_counts[label] = theme_counts.get(label, 0) + 1

    # Bulk insert
    if all_pairs:
        ok_count, fail_count = bulk_insert_labels(all_pairs, args.dry_run)
        stats["labels_added"] = ok_count
        stats["failed"] = fail_count
    else:
        stats["labels_added"] = 0

    print(f"\n--- Summary ---")
    print(f"Checked:      {stats['checked']}")
    print(f"Beads labeled: {stats['labeled']}")
    print(f"Labels added:  {stats['labels_added']}")
    print(f"Skipped:       {stats['skipped']}")
    print(f"Failed:        {stats['failed']}")
    print(f"Dry run:       {args.dry_run}")

    if module_counts:
        print(f"\nModule distribution:")
        for label, cnt in sorted(module_counts.items(), key=lambda x: -x[1]):
            print(f"  {label}: {cnt}")

    if theme_counts:
        print(f"\nTheme distribution:")
        for label, cnt in sorted(theme_counts.items(), key=lambda x: -x[1]):
            print(f"  {label}: {cnt}")

    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
