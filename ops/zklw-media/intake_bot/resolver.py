"""The resolver — the two-tier brain.

Tier 1 (deterministic, free): parse an explicit "Title (Year)" or a clean
title, search TMDB, and if there's one unambiguous strong hit, resolve it with
NO LLM call. This handles the common case ("add Dune Part Two 2024").

Tier 2 (LLM ranker, only when needed): for vague text ("that movie with the
spinning top", "the new villeneuve sci-fi"), pre-fetch TMDB candidates and ask
Claude Haiku to PICK from that fixed list via structured output. The LLM is a
ranker over a closed set, never a free-text searcher — no tool loops, bounded
cost, and it can never invent a tmdbId that doesn't exist.
"""

from __future__ import annotations

import re

from . import tmdb
from .config import Config
from .models import Candidate, MediaType, Request, Resolution

# "The Matrix (1999)" / "dune part two 2024" → (title, year)
_YEAR_PAREN = re.compile(r"^\s*(.+?)\s*\((\d{4})\)\s*$")
_YEAR_TRAIL = re.compile(r"^\s*(.+?)\s+(\d{4})\s*$")
# Leading verbs people type that aren't part of the title.
_PREFIX = re.compile(
    r"^\s*(please\s+)?(add|get|download|grab|request|want|find)\b" r"[:,\s]+",
    re.IGNORECASE,
)


def _strip_prefix(text: str) -> str:
    return _PREFIX.sub("", text).strip()


def _parse_title_year(text: str) -> tuple[str, int | None]:
    m = _YEAR_PAREN.match(text)
    if m:
        return m.group(1).strip(), int(m.group(2))
    m = _YEAR_TRAIL.match(text)
    if m:
        return m.group(1).strip(), int(m.group(2))
    return text.strip(), None


def _looks_specific(text: str, has_year: bool) -> bool:
    """Heuristic: is this a clean title we can trust the fast-path on?
    A trailing year, or a short title with no vague-pointer words."""
    if has_year:
        return True
    vague = (
        "that",
        "the one",
        "movie with",
        "show about",
        "whatshisname",
        "something",
        "new ",
        "latest",
        "remember",
    )
    low = text.lower()
    if any(v in low for v in vague):
        return False
    return len(text.split()) <= 6


async def resolve(req: Request, cfg: Config) -> Resolution:
    """Resolve a request to a single Candidate (or explain why it couldn't)."""
    cleaned = _strip_prefix(req.text)
    if not cleaned:
        return Resolution(req, None, "none", note="empty request")

    title, year = _parse_title_year(cleaned)

    try:
        candidates = tmdb.search(title, cfg.tmdb_api_key, year=year)
    except tmdb.TMDBError as e:
        return Resolution(req, None, "none", note=f"search failed: {e}")

    if not candidates:
        return Resolution(req, None, "none", note=f"no TMDB match for “{title}”.")

    # --- Tier 1: deterministic fast-path -------------------------------
    specific = _looks_specific(cleaned, year is not None)
    if specific and _is_strong_single(candidates):
        return Resolution(req, candidates[0], "exact", alternatives=candidates[1:4])

    # --- Tier 2: LLM ranker over the fixed candidate set ---------------
    if cfg.llm_enabled and len(candidates) > 1:
        picked = await _llm_rank(req.text, candidates, cfg)
        if picked is not None:
            return Resolution(
                req,
                picked,
                "llm",
                alternatives=[c for c in candidates if c.tmdb_id != picked.tmdb_id][:4],
            )

    # --- Could not confidently resolve → return alternatives for the
    #     adapter to present as a numbered choice list.
    return Resolution(
        req,
        None,
        "ambiguous",
        alternatives=candidates[:5],
        note="multiple matches — reply with a number to pick.",
    )


def _is_strong_single(candidates: list[Candidate]) -> bool:
    """One clearly-dominant hit: either a single result, or the top result is
    much more popular than the runner-up."""
    if len(candidates) == 1:
        return True
    top, second = candidates[0], candidates[1]
    return top.popularity >= 8.0 and top.popularity >= 2.5 * max(second.popularity, 0.1)


async def _llm_rank(
    user_text: str, candidates: list[Candidate], cfg: Config
) -> Candidate | None:
    """Ask Claude to pick the tmdbId that best matches the user's intent.
    Structured output over a closed candidate set. Lazy-imports anthropic so
    the module structure-checks without the dep installed."""
    try:
        import anthropic  # noqa: WPS433 (intentional lazy import)
    except ImportError:
        return None  # degrade gracefully to the ambiguous path

    listing = "\n".join(
        f"- tmdb_id={c.tmdb_id} | {c.label()} | {c.media_type.value} | "
        f"{c.overview[:160]}"
        for c in candidates
    )
    tool = {
        "name": "pick_title",
        "description": "Pick the single candidate that best matches the request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tmdb_id": {
                    "type": "integer",
                    "description": "tmdb_id of the best match, or 0 if none fit.",
                },
                "reason": {"type": "string"},
            },
            "required": ["tmdb_id"],
        },
    }
    client = anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)
    try:
        resp = await client.messages.create(
            model=cfg.llm_model,
            max_tokens=256,
            tools=[tool],
            tool_choice={"type": "tool", "name": "pick_title"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "A user asked for a movie/show. Pick the ONE candidate from "
                        "the list that best matches their request. Only choose from "
                        "the listed tmdb_id values; if none fit, return 0.\n\n"
                        f"User request: {user_text!r}\n\nCandidates:\n{listing}"
                    ),
                }
            ],
        )
    except Exception:
        return None  # any API failure → fall back to ambiguous path

    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            picked_id = block.input.get("tmdb_id", 0)
            for c in candidates:
                if c.tmdb_id == picked_id:
                    return c
    return None
