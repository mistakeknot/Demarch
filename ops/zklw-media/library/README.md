# Library curation — auteur filmographies

Tooling for adding complete director filmographies to grey and keeping the
quality selection honest. Everything here runs **on grey** and reads each
service's API key from its own config at call time, so no secret is ever passed
as an argument. Every script is dry-run by default; `--apply` is opt-in.

## Scripts

| script | what it does |
|---|---|
| `auteur_import.py` | Creates the `Archival-Best` quality profile and one TMDb Person import list per director. `--prune-unreleased` drops films that do not exist yet. |
| `curtis_series.py` | Adds Adam Curtis's multi-part BBC serials to Sonarr and retunes his features off profiles they can never satisfy. |
| `auteur_search.py` | Issues searches for the imported titles only, in paced batches. |
| `seerr_quality.py` | Points Seerr's default Radarr/Sonarr at the unified profile. |
| `fix_bad_grabs.py` | Removes wrong-series and AI-upscale grabs, and installs guards against both. |
| `consolidate_library.py` | Collapses the 4K/non-4K split into one `Best-Available` library and sets the size caps. |
| `purge_4k_dupes.py` | Deletes files orphaned by the consolidation, with live safety preconditions. |
| `audit_settings.py` | Read-only dump of every lever governing quality/size/ratio, including the ones invisible from the quality profiles. |
| `tracker_health.py` | Read-only census of the seeding stock by tracker, with announce status. |
| `apply_audit_fixes.py` | Applies the 2026-07-27 audit fixes in their required dependency order. |

## grey's config is repo-owned

**`recyclarr.yml` now lives in this repo** at `../config/recyclarr/`, deployed
with `sync-to-grey.sh`. It previously existed only on grey, with API keys in
plaintext, describing a topology that no longer exists — so running it would
have silently reverted the quality policy below. See `../config/README.md`,
which also records the traps (run the container as uid 1001; instance names must
be unique across services; `delete_old_custom_formats: false` does not actually
prevent deletions).

Anything changed through the API must be followed by `sync-to-grey.sh
regenerate` so the repo does not drift from the box.

## One profile: Best-Available

The library ran a 4K/non-4K split until the two collapsed into one. The 4K
Radarr used a profile that fell back to 1080p, which let 1080p releases *satisfy*
4K requests — so the 4K shelf was both nearly empty and not actually 4K.

`Best-Available` is the single profile now, expressing "best available, but not
massive 4K Blu-ray rips":

- **excludes Remux-2160p** — 50-80GB untouched disc streams. A *Mad Max* remux is
  50.1GB against 17.2GB for the 2160p encode.
- **tops out at Bluray-2160p / WEB 2160p** — real 4K at ~15-30GB.
- **cascades to SDTV**, so Kiarostami's DVD-era shorts and Curtis's 1980s BBC
  films still resolve. Nothing else would ever grab them: that material has no HD
  source and never will.
- **boosts DV / HDR10+ / HDR at +1500.** On an OLED these are far more visible
  than the last 20 Mbps of bitrate.
- **rejects AI upscales at -10000**, and caps five tiers at 250 MB/min (~33 Mbps).
  Both guards now exist on **Sonarr as well as Radarr**; the consolidation
  originally applied them to Radarr only, leaving TV uncapped and unguarded
  against the same fake-4K releases.
- **stops upgrading at `cutoffFormatScore` 1550.** It was 10000, against a
  ceiling of 1500+1500+1500+50 that no real release reaches — so every title sat
  permanently below cutoff and both arrs hunted upgrades forever. 1550 means
  "correct quality, plus any HDR flavour". Archival SD still cannot reach it and
  will keep searching, which is inherent to scoring HDR on material that has
  none; the quality cutoff still bounds what actually gets grabbed.

It carries **no SDR penalty** on purpose. TRaSH scores SDR at -2000; on a 1984
broadcast SDR is not a defect but the only thing that ever existed, and against
`minFormatScore: 0` that penalty would reject every archival release.

`Archival-Best` still exists and is declared in the recyclarr config, but nothing
uses it now — `Best-Available` cascades just as far.

## Things that bit, so they do not bite again

- **Build quality profiles from the live `/qualityprofile/schema`.** WEB tiers
  are *groups* (`WEB 1080p` = WEBDL + WEBRip) with no `quality` key. Treating a
  group as a plain quality disables every WEB release, silently and without
  error — which would have excluded the main source for Curtis's work.
- **TMDb `status: announced` does not mean "unreleased".** It also means "no
  release date recorded", which is common for obscure shorts. Pruning on status
  alone deleted Aster's *The Strange Thing About the Johnsons* and Villeneuve's
  *Next Floor*. The prune now also requires a future year.
- **Never take Sonarr's top search hit for this catalogue.** `Pandora's Box`
  returns a 2016 true-crime series first; `The Living Dead` returns
  *The Walking Dead*. tvdbIds in `curtis_series.py` are pinned and confirmed.
- **Sonarr fuzzy-matches across near-identical titles.** Curtis's *The Living
  Dead* (1995) happily accepted *The Living and the Dead* (2016) — same network,
  same 3-episode S01. Guarded by a tag-scoped release profile.
- **A 2160p label is not a 2160p source.** `Prisoners.2013.2160p.AI.Upscale`
  is a 1080p master upscaled and relabelled with DV/HDR10+. It satisfies a
  2160p-first profile while being worse than the honest 1080p remux. Guarded by
  the `AI Upscale` custom format at -10000.
- **Radarr caches import-list payloads.** After deleting a movie, neither
  `ImportListSync` nor re-saving the list will re-add it; add it back explicitly
  by tmdbId.
- **Sonarr queue rows are per-episode.** A season pack shows one row per episode
  it satisfies. 23 rows / 12 downloads is normal, not duplication.

## Indexer topology, and the rule that keeps it safe

Prowlarr does not push every indexer to every app — it filters by **tag**. The
private trackers carry tag `1` (`trackers`), Usenet carries tag `2`, and each
app entry lists the tags it accepts.

This is how the trackers went missing. Tag `1` was only ever granted to
`Radarr4K` / `Sonarr4K`, so when the 4K consolidation retired those instances,
HDBits and Karagarga silently went with them. The live arrs ran Usenet-only for
weeks; Karagarga logged 89 queries and **zero grabs, ever**. Nothing in either
service reports this — Radarr does not know it used to have indexers, and
Prowlarr does not know its apps can no longer see them. The signature to watch
for is queries climbing while grabs stay at zero.

**Before granting an app tag `1`, confirm that app will not delete torrents.**
Radarr's qBittorrent client shipped with `removeCompletedDownloads=True`, which
removes a torrent from the client after import — cutting seeding short against
HDBits' 14-day and Karagarga's 30-day minimums. qbit-manage is the only
component allowed to delete torrents (every `share_limits` group is
`cleanup: false`). Enabling trackers on an app that removes downloads is the one
ordering that produces real hit-and-run exposure.

Karagarga syncs to **Radarr only, and cannot be made to sync to Sonarr.** This
was tested rather than assumed. Karagarga has exactly three sections — Movies
(2000), Audio (3000), Books (7000). There is no TV category on the tracker, so
`tvSearchParams` is empty and there is nothing to map. Three wiring attempts
were made against Sonarr, adding KG directly as a Torznab indexer through
Prowlarr's per-indexer endpoint; Sonarr's own validation rejected all three:

| attempt | Sonarr's response |
|---|---|
| no category filter | `Either 'Categories' or 'Anime Categories' must be provided` |
| TV category 5000 | `No RSS feed query available` |
| Movies category 2000, RSS on | `No RSS feed query available` |

The only remaining route would be forking KG's Cardigann definition to declare
its Movies category as TV. Do not. Karagarga files everything — including
documentary serials — under Movies, so that mapping would present films to
Sonarr as series. Archival coverage is not lost: Radarr searches KG, and that
is where KG's material correctly lands.

## Unknown quality, and why it lives only on Archival-Best

Karagarga names frequently carry no quality tag at all — `Man ham mitounam AKA
So Can I 1975 Iran [So.Can.I]` — so Radarr parses them as quality `Unknown`,
which every profile excluded. The majority of KG results were rejected with
"Unknown is not wanted in profile", precisely for the material where KG is the
only source that exists.

`Unknown` is Radarr's catch-all for anything unparseable, so allowing it on
Best-Available would let untagged junk satisfy a mainstream title that is merely
waiting for a proper WEB-DL. It is therefore scoped: **`Archival-Best` is now
exactly `Best-Available` plus `Unknown`**, and only the archival directors'
file-less titles sit on it.

Three properties make this safe:

- **`Unknown` ranks lowest** in Radarr's quality ordering, so a parseable
  release still wins whenever one exists. Unknown is a fallback, never a
  preference.
- **Radarr caps `Unknown` at 100 MB/min**, and `AI Upscale` still scores -10000.
- **Only file-less movies moved.** A title that already has a file was left on
  Best-Available, so nothing already satisfied could be re-evaluated downward.

Membership is declarative: the two archival import lists apply an `archival`
tag. Note that **Radarr applies an import list's tags only when it ADDS a
movie** — a list sync will not retroactively tag titles imported earlier, so
`archival_unknown.py` resolves both filmographies through Seerr's person
endpoint (the one TMDb credential already running here) and tags the matches.

Measured before and after: *So Can I* went from all 3 KG releases rejected to
all 3 acceptable, *Orderly or Disorderly?* from 0 acceptable to 2, *The
Traveler* from 2 to 4 — while Best-Available titles still reject Unknown.

## Reading `stalledUP` correctly

A census of the 461 migrated torrents showed 455 "stalled", which looks alarming
and is not. `stalledUP` means *seeding, no peers currently downloading* — the
normal resting state for a seedbox. The real health signal is the tracker
announce: 328/332 HDBits and 118/125 Karagarga announces are `working`. Only 9
leechers existed across the whole HDBits catalogue, which is simply what an
older arthouse library looks like.

The corollary matters for ratio planning: passive seeding of an old catalogue
will not move ratio. The levers that do are fresh grabs, freeleech preference,
and cross-seeding the same file to a second tracker.

## Known gaps

- **The `Unknown` fix covers two directors, but the problem is wider.** The
  behavioural control turned up non-Curtis/Kiarostami arthouse titles hitting
  the same rejection on Best-Available — *Je Tu Il Elle* (1974), *Roar* (1981),
  *Out of the Way!* (1931). They are correctly excluded today, but they are
  archival by nature. Widening membership needs a rule, not a longer hardcoded
  list. Tracked as `sylveste-op85`.
- Curtis's *Shifty* (2025) has no clean TVDB entry; TVDB carries an umbrella
  "Adam Curtis Films" series that would overlap the Radarr entries.
- `preferredSize` is unset on every HD tier, and the `minSize` floors reject
  efficient encodes (`Bluray-2160p min=102 MB/min` refuses a good 8-10GB x265 4K
  as *too small*). The caps stop bloat; the floors block efficiency.
  Tracked as `sylveste-3g1t`.
