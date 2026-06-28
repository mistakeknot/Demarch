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
