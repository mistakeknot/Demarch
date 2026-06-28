"""Dispatch — hand a resolved candidate to Seerr's request API.

We go through Seerr (POST /api/v1/request), NOT straight to Radarr, on purpose:
Seerr already does request dedup, per-user quotas, and permission checks. We
attribute the request to the admin key; per-user quota attribution can be added
later by mapping channel users → Seerr userIds.

stdlib urllib only — no third-party HTTP dep for this hot path.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import Config
from .models import MediaType, Reply, Resolution


def _post(url: str, api_key: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"message": raw[:300]}
        return e.code, parsed
    except Exception as e:  # noqa: BLE001 — network/timeout surface uniformly
        return 0, {"message": str(e)}


def _format_alternatives(res: Resolution) -> str:
    if not res.alternatives:
        return ""
    lines = [f"  {i+1}. {c.label()}" for i, c in enumerate(res.alternatives)]
    return "\n".join(lines)


async def dispatch(res: Resolution, cfg: Config) -> Reply:
    """Send a resolved request to Seerr; build the channel-facing Reply."""
    if not res.resolved or res.candidate is None:
        if res.alternatives:
            alts = _format_alternatives(res)
            return Reply(
                False,
                f"🤔 Not sure which one you meant:\n{alts}\n"
                f"Reply with the number, or add the year.",
            )
        return Reply(False, f"❌ Couldn't find that. {res.note}".strip())

    c = res.candidate
    # Seerr request payload. TV requests want season info; for a first cut we
    # request all seasons ("all"). Movie requests just need the mediaId.
    payload: dict = {
        "mediaType": c.media_type.value,
        "mediaId": c.tmdb_id,
    }
    if c.media_type == MediaType.TV:
        payload["seasons"] = "all"

    url = cfg.seerr_url.rstrip("/") + "/api/v1/request"
    status, data = _post(url, cfg.seerr_api_key, payload)

    if status in (200, 201):
        return Reply(True, f"✅ Added **{c.label()}** — Radarr is on it.")
    if status == 409:
        # Seerr's dedup: already requested or already available.
        return Reply(True, f"👍 **{c.label()}** is already requested/available.")
    msg = data.get("message") or data.get("error") or f"HTTP {status}"
    return Reply(False, f"⚠️ Seerr rejected **{c.label()}**: {msg}")
