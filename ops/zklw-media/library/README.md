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

## Known gaps

- `recyclarr.yml` lives only on grey and is not mirrored in this repo. The
  `AI Upscale` custom format was created via the API, so a future recyclarr run
  with `delete_old_custom_formats: true` would remove it until it is mirrored.
- Curtis's *Shifty* (2025) has no clean TVDB entry; TVDB carries an umbrella
  "Adam Curtis Films" series that would overlap the Radarr entries.
