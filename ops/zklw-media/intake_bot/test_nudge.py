"""No-dep smoke tests for the scarcity nudge (Apple TV / YouTube availability).

Run: python3 -m unittest intake_bot.test_nudge   (from ops/zklw-media/)
     or  python3 intake_bot/test_nudge.py

Mocks tmdb._get so no network/API key is needed — mirrors the README's
"mock TMDB + mock Seerr _post" convention. Covers the provider-match logic,
the disable switch, region scoping, and graceful degradation on TMDB errors.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from . import tmdb
from .config import _csv_set_default
from .models import Candidate, MediaType, Request, Resolution
from . import pipeline


def _providers_payload(region: str, *, buy=None, rent=None, flatrate=None) -> dict:
    block = {}
    if buy:
        block["buy"] = [{"provider_name": n} for n in buy]
    if rent:
        block["rent"] = [{"provider_name": n} for n in rent]
    if flatrate:
        block["flatrate"] = [{"provider_name": n} for n in flatrate]
    return {"id": 1, "results": {region: block}}


APPLE_YT = frozenset({"Apple TV", "YouTube"})


class PurchasableOnTests(unittest.TestCase):
    def test_matches_apple_tv_buy(self):
        payload = _providers_payload("US", buy=["Apple TV", "Amazon Video"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, ["Apple TV"])

    def test_matches_legacy_apple_itunes(self):
        # TMDB's older spelling of the Apple storefront must still match "Apple TV".
        payload = _providers_payload("US", rent=["Apple iTunes"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, ["Apple TV"])

    def test_matches_youtube_movies_substring(self):
        payload = _providers_payload("US", buy=["YouTube (Movies)"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, ["YouTube"])

    def test_flatrate_only_still_counts_as_available(self):
        # A title on a flatrate sub (e.g. Apple TV+) is reported; the caller can
        # nudge "it's on a sub you may have" — we include flatrate deliberately.
        payload = _providers_payload("US", flatrate=["Apple TV"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, ["Apple TV"])

    def test_not_available_returns_empty(self):
        payload = _providers_payload("US", buy=["Amazon Video", "Google Play Movies"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, [])

    def test_region_scoping(self):
        # Providers live under US, but we ask for GB → nothing.
        payload = _providers_payload("US", buy=["Apple TV"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="GB", providers=APPLE_YT
            )
        self.assertEqual(hits, [])

    def test_tmdb_error_degrades_to_empty(self):
        with mock.patch.object(tmdb, "_get", side_effect=tmdb.TMDBError("boom")):
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=APPLE_YT
            )
        self.assertEqual(hits, [])

    def test_empty_providers_short_circuits(self):
        # No providers configured => no lookup at all (function returns []).
        with mock.patch.object(tmdb, "_get") as m:
            hits = tmdb.purchasable_on(
                603, "movie", "k", region="US", providers=frozenset()
            )
        self.assertEqual(hits, [])
        m.assert_not_called()

    def test_tv_uses_tv_endpoint(self):
        payload = _providers_payload("US", buy=["Apple TV"])
        with mock.patch.object(tmdb, "_get", return_value=payload) as m:
            tmdb.purchasable_on(1399, "tv", "k", region="US", providers=APPLE_YT)
        path = m.call_args.args[0]
        self.assertIn("/tv/1399/watch/providers", path)


class ConfigDefaultTests(unittest.TestCase):
    def test_unset_uses_default(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            s = _csv_set_default("NUDGE_PROVIDERS", "Apple TV,YouTube")
        self.assertEqual(s, frozenset({"Apple TV", "YouTube"}))

    def test_explicit_empty_disables(self):
        with mock.patch.dict("os.environ", {"NUDGE_PROVIDERS": ""}, clear=True):
            s = _csv_set_default("NUDGE_PROVIDERS", "Apple TV,YouTube")
        self.assertEqual(s, frozenset())

    def test_explicit_override(self):
        with mock.patch.dict("os.environ", {"NUDGE_PROVIDERS": "Netflix"}, clear=True):
            s = _csv_set_default("NUDGE_PROVIDERS", "Apple TV,YouTube")
        self.assertEqual(s, frozenset({"Netflix"}))


class _FakeCfg:
    """Minimal stand-in for Config — only the fields the nudge touches."""

    def __init__(self, providers=APPLE_YT, region="US"):
        self.nudge_providers = providers
        self.watch_region = region
        self.tmdb_api_key = "k"

    @property
    def nudge_enabled(self) -> bool:
        return bool(self.nudge_providers)


def _resolution(resolved=True) -> Resolution:
    c = Candidate(tmdb_id=603, title="The Matrix", year=1999, media_type=MediaType.MOVIE)
    return Resolution(
        request=Request(
            channel=None, user="u", text="the matrix 1999", reply=None
        ),
        candidate=c if resolved else None,
        confidence="exact" if resolved else "ambiguous",
    )


class PipelineNudgeTests(unittest.TestCase):
    def test_nudge_text_when_purchasable(self):
        payload = _providers_payload("US", buy=["Apple TV"], rent=["YouTube (Movies)"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            txt = pipeline._scarcity_nudge(_resolution(), _FakeCfg())
        self.assertIn("Apple TV or YouTube", txt)
        self.assertIn("The Matrix (1999)", txt)
        self.assertTrue(txt.endswith("\n\n"))

    def test_no_nudge_when_not_purchasable(self):
        payload = _providers_payload("US", buy=["Amazon Video"])
        with mock.patch.object(tmdb, "_get", return_value=payload):
            txt = pipeline._scarcity_nudge(_resolution(), _FakeCfg())
        self.assertEqual(txt, "")

    def test_no_nudge_when_disabled(self):
        with mock.patch.object(tmdb, "_get") as m:
            txt = pipeline._scarcity_nudge(_resolution(), _FakeCfg(providers=frozenset()))
        self.assertEqual(txt, "")
        m.assert_not_called()

    def test_no_nudge_without_candidate(self):
        txt = pipeline._scarcity_nudge(_resolution(resolved=False), _FakeCfg())
        self.assertEqual(txt, "")

    def test_human_join(self):
        self.assertEqual(pipeline._human_join([]), "")
        self.assertEqual(pipeline._human_join(["Apple TV"]), "Apple TV")
        self.assertEqual(
            pipeline._human_join(["Apple TV", "YouTube"]), "Apple TV or YouTube"
        )


if __name__ == "__main__":
    unittest.main()
