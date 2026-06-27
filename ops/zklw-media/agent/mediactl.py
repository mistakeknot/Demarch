#!/usr/bin/env python3
"""
mediactl — a thin, read-mostly control surface over the zklw media stack
for an LLM ops agent (Claude Code / Hermes) to drive.

Design intent
-------------
The *arr stack already does the deterministic grab loop. This tool is the
AGENT'S hands for the fuzzy ops around it: diagnose a stuck request, fix a
mislabeled import, audit the library, summarize what's new. It deliberately
does NOT initiate downloads or talk to your tracker — acquisition decisions
stay with you via Jellyseerr/Radarr. The agent observes and repairs; it does
not acquire.

Config
------
Reads API keys from env (or ~/.config/zklw-media/agent.env):
    RADARR_URL,   RADARR_API_KEY
    SONARR_URL,   SONARR_API_KEY
    JELLYFIN_URL, JELLYFIN_API_KEY
    QBIT_URL,     QBIT_USER, QBIT_PASS

Each *arr API key: Settings → General → API Key in its web UI.
Jellyfin key:      Dashboard → API Keys.

Usage
-----
    ./mediactl.py queue            # what's downloading / stuck, with reasons
    ./mediactl.py movie "Dune"     # status of a title across Radarr + Jellyfin
    ./mediactl.py audit            # library hygiene: missing files, dupes
    ./mediactl.py recent           # what landed recently (Jellyfin)
    ./mediactl.py health           # are all services reachable

Everything prints JSON so the agent can reason over structured output.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# --- config loading -----------------------------------------------------


def _load_env() -> None:
    cfg = Path.home() / ".config" / "zklw-media" / "agent.env"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _get(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        sys.exit(f"missing config: {name} (set env or ~/.config/zklw-media/agent.env)")
    return val


# --- tiny HTTP helper (stdlib only, no pip deps) ------------------------


def _req(
    url: str,
    headers: dict | None = None,
    data: bytes | None = None,
    method: str = "GET",
) -> dict | list:
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode()
            return json.loads(body) if body else {}
    except Exception as e:  # noqa: BLE001 - agent wants the message, not a crash
        return {"_error": str(e), "_url": url}


def _arr(base_env: str, key_env: str, path: str) -> dict | list:
    base = _get(base_env).rstrip("/")
    key = _get(key_env)
    return _req(f"{base}/api/v3/{path}", headers={"X-Api-Key": key})


# --- commands -----------------------------------------------------------


def cmd_health(_args: list[str]) -> None:
    """Are all services reachable from this host?"""
    out = {}
    for name, url_env, key_env in [
        ("radarr", "RADARR_URL", "RADARR_API_KEY"),
        ("sonarr", "SONARR_URL", "SONARR_API_KEY"),
    ]:
        if os.environ.get(url_env):
            r = _arr(url_env, key_env, "system/status")
            out[name] = "error" if "_error" in r else r.get("version", "ok")
    if os.environ.get("JELLYFIN_URL"):
        j = _req(
            f"{_get('JELLYFIN_URL').rstrip('/')}/System/Info",
            headers={"X-Emby-Token": _get("JELLYFIN_API_KEY")},
        )
        out["jellyfin"] = "error" if "_error" in j else j.get("Version", "ok")
    print(json.dumps(out, indent=2))


def cmd_queue(_args: list[str]) -> None:
    """Active downloads + WHY anything is stuck (the #1 agent question)."""
    q = _arr("RADARR_URL", "RADARR_API_KEY", "queue?pageSize=100&includeMovie=true")
    records = q.get("records", []) if isinstance(q, dict) else []
    summary = []
    for rec in records:
        movie = (rec.get("movie") or {}).get("title", "?")
        summary.append(
            {
                "movie": movie,
                "status": rec.get("status"),
                "trackedStatus": rec.get("trackedDownloadStatus"),
                "state": rec.get("trackedDownloadState"),
                "progress_pct": round(
                    100 * (1 - (rec.get("sizeleft", 0) / (rec.get("size", 1) or 1))), 1
                ),
                # messages explain stalls: "no files found", "import blocked", etc.
                "messages": [m.get("messages") for m in rec.get("statusMessages", [])],
            }
        )
    print(json.dumps({"count": len(summary), "queue": summary}, indent=2))


def cmd_movie(args: list[str]) -> None:
    """Status of a title across Radarr (acquisition) and the library."""
    if not args:
        sys.exit("usage: mediactl movie <title>")
    term = " ".join(args)
    movies = _arr("RADARR_URL", "RADARR_API_KEY", "movie")
    hits = [
        m
        for m in (movies if isinstance(movies, list) else [])
        if term.lower() in (m.get("title", "").lower())
    ]
    out = [
        {
            "title": m.get("title"),
            "year": m.get("year"),
            "hasFile": m.get("hasFile"),
            "monitored": m.get("monitored"),
            "path": m.get("path"),
            "sizeOnDisk_GB": round(m.get("sizeOnDisk", 0) / 1e9, 2),
            "quality": (
                ((m.get("movieFile") or {}).get("quality") or {}).get("quality") or {}
            ).get("name"),
        }
        for m in hits
    ]
    print(json.dumps({"matches": len(out), "movies": out}, indent=2))


def cmd_audit(_args: list[str]) -> None:
    """Library hygiene: monitored-but-missing, and duplicate titles."""
    movies = _arr("RADARR_URL", "RADARR_API_KEY", "movie")
    movies = movies if isinstance(movies, list) else []
    missing = [
        {"title": m["title"], "year": m.get("year")}
        for m in movies
        if m.get("monitored") and not m.get("hasFile")
    ]
    seen: dict[str, int] = {}
    for m in movies:
        seen[m.get("title", "?")] = seen.get(m.get("title", "?"), 0) + 1
    dupes = {t: n for t, n in seen.items() if n > 1}
    print(
        json.dumps(
            {
                "total_movies": len(movies),
                "monitored_missing": missing[:50],
                "monitored_missing_count": len(missing),
                "duplicate_titles": dupes,
            },
            indent=2,
        )
    )


def cmd_recent(_args: list[str]) -> None:
    """What recently landed (Jellyfin recently-added)."""
    base = _get("JELLYFIN_URL").rstrip("/")
    key = _get("JELLYFIN_API_KEY")
    items = _req(
        f"{base}/Items/Latest?"
        + urllib.parse.urlencode({"IncludeItemTypes": "Movie", "Limit": 25}),
        headers={"X-Emby-Token": key},
    )
    out = [
        {"name": i.get("Name"), "year": i.get("ProductionYear")}
        for i in (items if isinstance(items, list) else [])
    ]
    print(json.dumps({"recent": out}, indent=2))


COMMANDS = {
    "health": cmd_health,
    "queue": cmd_queue,
    "movie": cmd_movie,
    "audit": cmd_audit,
    "recent": cmd_recent,
}


def main() -> None:
    _load_env()
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("commands:", ", ".join(COMMANDS))
        sys.exit(0 if len(sys.argv) < 2 else 2)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
