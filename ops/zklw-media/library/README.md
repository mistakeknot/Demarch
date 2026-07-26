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
| `seerr_quality.py` | Points Seerr's default (non-4K) Radarr/Sonarr at a 4K-remux-first profile. |
| `fix_bad_grabs.py` | Removes wrong-series and AI-upscale grabs, and installs guards against both. |

## Why two quality profiles

`UHD-Remux` (recyclarr-managed) bottoms out at WEB 1080p. That is correct for
directors whose work exists on Blu-ray, and wrong for archival material: none of
Kiarostami's early shorts or Curtis's 1980s BBC films have an HD source and they
never will, so that profile would reject every release that exists.

`Archival-Best` allows SDTV/DVD/576p through Remux-2160p with upgrades still
enabled — take whatever exists now, climb if something better appears. It
carries **no custom formats** on purpose: UHD-Remux applies a -2000 SDR penalty,
and on a 1984 broadcast SDR is not a defect, it is the only thing that ever
existed.

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
