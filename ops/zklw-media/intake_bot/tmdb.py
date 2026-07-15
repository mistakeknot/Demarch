"""Minimal TMDB search client (stdlib urllib only).

We hit TMDB directly for candidate generation rather than Seerr's search proxy
so the resolver owns the candidate list it feeds to the LLM ranker. Dispatch
still goes through Seerr by tmdbId, so dedup/quota/permissions are unaffected.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

from .models import Candidate, MediaType

_BASE = "https://api.themoviedb.org/3"


class TMDBError(RuntimeError):
    pass


def _get(path: str, api_key: str, **params) -> dict:
    params["api_key"] = api_key
    url = f"{_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # network, json, http — all surface the same way
        raise TMDBError(f"TMDB request failed: {e}") from e


def _to_candidate(row: dict) -> Optional[Candidate]:
    mt = row.get("media_type")
    if mt == "movie" or ("title" in row and mt is None):
        title = row.get("title") or row.get("original_title") or ""
        date = row.get("release_date") or ""
        media_type = MediaType.MOVIE
    elif mt == "tv" or ("name" in row and mt is None):
        title = row.get("name") or row.get("original_name") or ""
        date = row.get("first_air_date") or ""
        media_type = MediaType.TV
    else:
        return None  # person, collection, etc. — not requestable media
    if not title:
        return None
    year = int(date[:4]) if date[:4].isdigit() else None
    return Candidate(
        tmdb_id=int(row["id"]),
        title=title,
        year=year,
        media_type=media_type,
        overview=row.get("overview", "") or "",
        popularity=float(row.get("popularity", 0.0) or 0.0),
    )


def search(
    query: str, api_key: str, *, year: Optional[int] = None, limit: int = 8
) -> list[Candidate]:
    """Multi-search TMDB; return up to `limit` movie/TV candidates, most
    popular first. `year` is a soft filter applied after the fetch."""
    data = _get(
        "/search/multi",
        api_key,
        query=query,
        include_adult="false",
        language="en-US",
        page=1,
    )
    cands: list[Candidate] = []
    for row in data.get("results", []):
        c = _to_candidate(row)
        if c:
            cands.append(c)
    if year is not None:
        exact = [c for c in cands if c.year == year]
        if exact:
            cands = exact
    cands.sort(key=lambda c: c.popularity, reverse=True)
    return cands[:limit]


# Watch-provider names that TMDB reports for the buy/rent storefronts we nudge
# toward. TMDB spells Apple's storefront "Apple TV" (formerly "Apple iTunes");
# both are matched so the check survives their rename. Comparison is casefolded
# and substring-based, so "YouTube" matches "YouTube (Movies)" etc.
def _provider_names(block: dict) -> set[str]:
    """Collect provider display names from a region block across the buy/rent/
    flatrate offer types. We care about buy+rent (purchasable); flatrate is
    included so a caller can tell 'it's on a sub you have' apart if it wants."""
    names: set[str] = set()
    for offer in ("buy", "rent", "flatrate"):
        for p in block.get(offer, []) or []:
            name = (p.get("provider_name") or "").strip()
            if name:
                names.add(name)
    return names


def purchasable_on(
    tmdb_id: int,
    media_type: str,
    api_key: str,
    *,
    region: str,
    providers: frozenset[str],
) -> list[str]:
    """Return the subset of `providers` that can buy/rent this title in `region`,
    per TMDB's watch/providers endpoint. Empty list = not purchasable there (or
    unknown). Best-effort: any TMDB error returns [] so the caller proceeds with
    the normal download flow — a provider lookup must never block a request.

    `providers` is matched casefolded + substring, so "Apple TV" matches TMDB's
    "Apple TV" and the legacy "Apple iTunes"; "YouTube" matches "YouTube (Movies)".
    """
    if not providers:
        return []
    kind = "tv" if media_type == "tv" else "movie"
    try:
        data = _get(f"/{kind}/{tmdb_id}/watch/providers", api_key)
    except TMDBError:
        return []
    block = (data.get("results") or {}).get(region) or {}
    available = _provider_names(block)
    if not available:
        return []
    avail_cf = [a.casefold() for a in available]
    hits: list[str] = []
    for want in providers:
        wcf = want.casefold()
        # "Apple TV" should also catch the legacy "Apple iTunes" storefront.
        needles = [wcf]
        if wcf.startswith("apple"):
            needles.append("apple itunes")
        if any(n in a for a in avail_cf for n in needles):
            hits.append(want)
    return hits
