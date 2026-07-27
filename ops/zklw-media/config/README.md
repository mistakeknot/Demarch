# grey media-server config — repo-owned

Config for grey's media stack now lives here rather than only on the box.

Before this, `recyclarr.yml` existed solely at
`/home/mk/grey-media/config/recyclarr/` with API keys in plaintext, and it
described a topology that no longer exists. Running it would have silently
reverted the quality policy: the DV/HDR scoring, the AI-upscale guard, and the
`Best-Available` profile were all applied through the API and none were in
recyclarr's config.

## Layout

```
recyclarr/
  recyclarr.yml    the config. GENERATED from live state -- see below
  generate.py      regenerates recyclarr.yml by reading Radarr/Sonarr
  sync-to-grey.sh  bootstrap-env | deploy | preview | sync | regenerate
```

## Usage

```bash
./recyclarr/sync-to-grey.sh bootstrap-env   # once: write recyclarr.env on grey (0600)
./recyclarr/sync-to-grey.sh deploy          # push this repo's config to grey
./recyclarr/sync-to-grey.sh preview         # dry run -- ALWAYS read this first
./recyclarr/sync-to-grey.sh sync            # apply
./recyclarr/sync-to-grey.sh regenerate      # re-derive YAML after an API-side change
```

## Why the config is generated, not hand-written

`recyclarr.yml` is produced by `generate.py` reading the live instances. A
quality profile is a ~15-entry ordered ladder per instance; transcribing that by
hand is how drift starts, and drift here is invisible until a sync quietly
rewrites a profile. Generating it means `preview` reporting "no changes" is
proof the repo matches the box.

After changing a profile through the API, run `regenerate` and commit the diff.

## Secrets

`recyclarr.yml` carries `!env_var RADARR_API_KEY` / `!env_var SONARR_API_KEY`,
never literal keys. `bootstrap-env` extracts them from each service's own
`config.xml` **server-side** and writes `recyclarr.env` (0600, uid 1001) on
grey; the container reads it via `--env-file`. No key passes through argv, shell
history, or this repository.

## Things that will bite

- **Run the container as uid 1001.** Files are owned by `mk` (1001:1001) and the
  image defaults to a different uid, which then cannot read its own cached TRaSH
  checkout. The failure surfaces as a bare `Access to the path ... is denied`
  that says nothing about permissions.
- **Instance names must be unique ACROSS services, not within them.** The old
  config had `main` and `uhd` under both `radarr:` and `sonarr:` and simply
  refused to load with `Duplicate Instances`.
- **`delete_old_custom_formats: false` does NOT stop deletions** in this version.
  A custom format that recyclarr previously synced and that is no longer in the
  config gets deleted regardless. What actually protects the `AI Upscale` format
  is that recyclarr never created it, so it is not tracked at all — the flag
  reads like a safety net it is not.
- **`quality_definition` is deliberately absent.** Including it applies TRaSH's
  size recommendations, which would overwrite the 250 MB/min `maxSize` caps that
  keep 50-80GB remuxes out. Sizes stay API-managed by
  `../library/consolidate_library.py`.
- **The SDR penalty is deliberately absent.** TRaSH scores SDR at -2000. Both
  profiles cascade to archival SD material where SDR is not a defect but the
  only source that ever existed, and against `min_format_score: 0` that penalty
  would reject every such release.

## What the sync removed, intentionally

The first repo-owned sync deleted `Remux Tier 01/02/03` and `SDR` from both
instances. Those were scored only on `UHD-Remux`, which the consolidation left
vestigial. Verified afterwards against the API: `Best-Available` keeps DV/HDR at
1500, `AI Upscale` at -10000, all five size caps at 250 MB/min, and no 2160p
remux tier allowed.
