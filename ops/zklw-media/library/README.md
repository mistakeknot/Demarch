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
| `archival_unknown.py` | Scopes the `Unknown` quality allowance to `Archival-Best` and routes the archival filmographies onto it. |
| `size_efficiency.py` | Sets `preferredSize` and lowers the `minSize` floors so efficient encodes are expressible. |
| `freeleech_format.py` | Creates the Freeleech / Halfleech custom formats and scores them on both profiles. |
| `crossseed_assess.py` | Read-only: measures cross-seed overlap between trackers and reports a verdict. |
| `crossseed_setup.py` | Deploys cross-seed on grey and runs bounded search passes. |
| `jarmusch_dupes.py` | Pauses torrents jarmusch is seeding that grey also seeds. |
| `kg_review_force.py` | Clears KG adoption rows stranded on advisory rejections. |

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
- **`preferredSize` must not exceed `maxSize`.** Sonarr accepts the PUT and
  returns success, then silently drops the value, leaving it null. Setting 400
  MB/min against `Bluray-2160p Remux`'s 250 cap looked like it applied and had
  not. Always re-read the definition after writing it.
- **Sonarr queue rows are per-episode.** A season pack shows one row per episode
  it satisfies. 23 rows / 12 downloads is normal, not duplication.

## Size efficiency: the caps were only half the policy

The 250 MB/min caps stop bloat. Nothing expressed the other half — *preferring*
the efficient release — and the `minSize` floors were actively rejecting it.

Measured before the fix, by interactive search:

| title | release rejected as too small | floor demanded |
|---|---|---|
| Dune | 9.5 GB / 12.7 GB 2160p x265 DV HDR | 15.4 GB |
| Blade Runner 2049 | 9.9 GB / 11.3 GB 2160p DV HDR | 16.3 GB |
| Arrival | 8.0 GB 2160p x265 HDR (Tigole) | 11.6 GB |
| Midsommar | 11.2 GB 2160p x265 HDR | 14.6 GB |

A 155-minute *Dune* at 9.5 GB is 63 MB/min; the floor demanded 102. Those are
exactly the releases a size-conscious library wants, and every one was refused.

**The floors cannot go to zero.** The same searches turned up a 1.71 GB "2160p
UHD BluRay" of *Hereditary* — 13.8 MB/min, not a 4K source in any meaningful
sense. So the floors sit at roughly half the credible-encode bitrate: low enough
to admit a good HEVC encode, high enough that sub-2 GB "2160p" still fails.
After the change, 38 sub-15GB 2160p releases became acceptable across seven test
titles while 108 were still rejected as too small.

**`preferredSize` is the positive half**, and it had been null on every HD tier.
Both arrs rank releases *within* a quality tier by proximity to it, so it is what
actually chooses between a 15 GB and a 30 GB encode of the same film. Left null,
nothing preferred the smaller and the biggest release under the cap tended to
win. The values sit at a good-encode bitrate rather than at the cap — 130 MB/min
(~17 Mbps) for 2160p, 60 for Bluray-1080p — with remux tiers deliberately set
near the cap, since preferring a "small" untouched-video release is meaningless.

Changing quality definitions does **not** retroactively re-grab: RSS surfaces
only newly-posted releases, and the back catalogue is re-evaluated only by an
explicit search. Verified after applying — across 370 movies holding a file,
zero changed file and zero changed profile, with both queues empty.

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

## Freeleech scoring

On HDBits a freeleech grab costs no download credit and a halfleech grab costs
half, so preferring them is the best per-grab ratio lever short of cross-seeding.
Prowlarr passes tracker flags through as `indexerFlags` and both arrs score them
via `IndexerFlagSpecification`.

Measured over ~1600 releases: HDBits returned 59 freeleech and **79 halfleech**;
TorrentLeech 295 freeleech of 619; **Karagarga zero — KG reports no flags at
all**, so this lever does not apply there. Its Prowlarr `freeleech` field is a
search *filter*, not a flag reporter.

Halfleech is scored too, at half the weight, precisely because HDBits carries
more of it than freeleech. Scoring only full freeleech would capture under half
the benefit.

`Freeleech +100`, `Halfleech +50`. Both sit above the x265 nudge so the cheaper
of two equal releases wins, and both sit far below the 1500 on DV/HDR10+/HDR so
**ratio can never outrank picture quality** — this is a tie-breaker, not a
preference for worse video. Verified across nine like-for-like pairs: at
identical tier and identical video formats the freeleech release scored exactly
+100 higher, including one case (*Hereditary* INTERNAL 2160p) where the two rows
are the same release, 150 against 50.

The flag enums differ between services and must never be shared:

| | Freeleech | Halfleech | Freeleech75 | Freeleech25 |
|---|---|---|---|---|
| Radarr | 1 | 2 | 256 | 512 |
| Sonarr | 1 | 2 | 32 | 64 |

## Cross-seed: deployed, and my own assessment was wrong

Cross-seeding needs the same **file**, not the same film. I first estimated the
opportunity by sampling 22 torrents per tracker and size-matching across
trackers via Prowlarr, which gave HDBits 8/22 (36%) and Karagarga 2/22 (9%),
with most HDBits matches landing on TorrentLeech. I wrote that up as "the
pairing is HDBits ↔ TorrentLeech, not Karagarga."

**Running the actual tool disproved that.** A bounded 12-search pass found
**9 cross seeds**, of which **Karagarga supplied 6 and TorrentLeech 2** — the
reverse of the prediction, at a far higher hit rate (9 from 12 searched, against
a predicted ~36%).

The estimate was wrong for two reasons worth remembering. It sampled the
*seeding stock* — torrents already loaded — whereas cross-seed searches the
*library*, 709 items, a different and much larger population. And it matched on
cleaned-up names plus approximate size, whereas cross-seed matches on actual
file structure. A name-and-size proxy is fine for deciding whether to bother
looking; it is not fine for predicting what a real matcher will find. The
lesson: when a tool exists that answers the question directly, a sampling proxy
is a reason to run the tool, not a substitute for its verdict.

Deployed via `crossseed_setup.py`. First run injected 8 torrents totalling
**47.96 GB of new seeding stock for zero additional disk**, hardlinked into
`/data/cross-seeds` and tagged `cross-seed` so qbit-manage governs them like any
other torrent.

Safety properties, in the order they matter:

- **No two-IP violation.** Cross-seeding creates a NEW infohash on a DIFFERENT
  tracker, seeded only from grey. The rule is about one infohash on two
  machines — a real and separate problem here, see below, but an orthogonal one.
- **`matchMode: safe`** requires file sizes to line up exactly. Approximate
  matching was good enough to assess; it is not good enough to announce.
- **`skipRecheck: false`** so qBittorrent hashes the data before announcing.
  Announcing data you cannot serve is how a tracker learns to distrust you.
- **`delay: 30`** paces searches. The point of ratio work is protecting standing
  on these trackers.
- Searches are **bounded by `--search-limit`**. An unbounded pass over 709
  torrents × 3 indexers is ~2000 queries; do not run one casually.

`config.js` holds the Prowlarr key and qBittorrent credentials, so it is
generated on grey and written 0600. It is not in this repo.

Two traps hit during deployment: the config directory must be owned by uid 1001
or cross-seed fails with `attempt to write a readonly database` (its SQLite
store, not the config) — the same uid trap recyclarr has. And an earlier
half-finished install had left `cross-seed.db` owned by root since 25 Jul,
failing silently.

## Two machines hold the same torrents — but only 6 are announcing

`crossseed_assess.py` led somewhere unrelated to cross-seed. jarmusch is still
up, still running `qbittorrent-nox`, and holds 513 torrents. Comparing
infohashes against grey's 463:

    432 infohashes are loaded on BOTH machines.

That number reads like a catastrophe and is not. Enumerating the actual states
(via `jarmusch_dupes.py`, once a credential was available) gives:

| | count |
|---|---|
| duplicates in `stoppedUP` — paused, not announcing | **426** |
| duplicates actually announcing — the real exposure | **6** |
| unique to jarmusch, left alone | 81 (14 seeding) |

So the migration *was* done properly: the originals were stopped, and six leaked
through. The standing rule — never seed one infohash from two IPs — is being
violated by six torrents, not by four hundred.

Worth keeping as a method note: the infohash intersection was cheap and proved
*presence*, but presence is not exposure. The states needed a credentialed
query, and the gap between "432 shared" and "6 announcing" is the whole
difference between an emergency and a chore. Don't report the cheap number as
though it were the expensive one.

`jarmusch_dupes.py` pauses only the announcing duplicates, leaves the 81 unique
torrents alone, and pauses rather than deletes so resuming undoes it. Grey is
the right survivor: it already seeds all 432, it is connectable where jarmusch
is firewalled with near-zero upload, and qbit-manage governs its share limits.

Two gotchas: the 1Password item `qbit-jarmusch` has an **empty username field**,
and jarmusch's `qBittorrent.conf` has no `WebUI\Username`, so qBittorrent is on
its default `admin` — the script falls back to that. And jarmusch sets no
`MaxAuthenticationFailCount`, so qBittorrent's default of 5 failures / 1 hour
ban applies; do not brute-force it.

## The KG adoption review queue

The queue read as 240 folders needing review. Bucketed against what was actually
on disk, it was almost entirely phantom:

| | count |
|---|---|
| empty — `kg_restore.sh` had not reached them yet | 213 |
| had video, restore still in progress | 12 |
| **genuinely reviewable** | **15** |

`kg_adopt` records `no-video-items` when it runs against a folder mid-transfer,
and the nightly prunes those once the dir completes — so most of the "queue" is
a snapshot of work not yet done, not work that failed. **Count the queue against
disk before treating its size as a backlog.**

Working the real 15 produced imports of 230 → 244, every one hardlinked
(`nlink=2`), so the library grew by fourteen films and zero bytes.

Three failure modes, each needing a different fix:

- **Stale `no-video-items` (10).** Recorded once while the folder was empty and
  never retried. Pruning the row and re-running `kg_adopt.py import` cleared
  them — the nightly's own logic, just run on demand.
- **Advisory rejections (4).** `kg_adopt` bails on ANY rejection, which strands
  files over `Unknown Movie` (Radarr cannot parse a title from a KG filename —
  irrelevant when we supply the movieId) and `No audio tracks detected`
  (*Khabarda* (1931) is a Georgian **silent** film; the rule met content it was
  never written for). `kg_review_force.py` overrides exactly those two and
  nothing else.
- **Case-collision same-path (1).** Radarr compares paths case-insensitively, so
  `/data/Movies/Top Knot Detective (2017)` and `/data/movies/Top Knot Detective
  (2017)` looked identical and it refused with `Source and destination can't be
  the same`. `kg_fix_samepath.py` already exists for this and hardlinks the file
  in directly.

Recovering a movieId for a stranded row needs care: `kg_adopt` omits it when
recording a `rejected` row, so `kg_review_force.py` merges the progress log with
the report's `review_from_import`, then falls back to matching the folder name
against Radarr's library. That fallback allows **±2 years** — KG folder years,
release filenames and TMDb routinely disagree (*Je, tu, il, elle* is variously
1974, 1975 and 1976). The exact normalised title match is what makes it safe,
not the year window, and an ambiguous match is refused rather than guessed.

One genuine manual case remains: *Roar* (1981) exists only as `cd1`/`cd2`, and
Radarr cannot represent one movie as two files.

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

## Duplicates in Jellyfin: three causes, only one of them obvious

Users reported "a ton of duplicates". There were three independent causes, and
counting by *name* would have found the symptom but misattributed all three.
Counting by **inode** separated them:

| cause | tiles |
|---|---|
| Jellyfin scanned both `/data/movies` and `/data/Movies` | 277 |
| 209 loose video files sitting unfoldered in the Radarr root | 209 |
| 38 release-named *torrent folders* also in the Radarr root | 38 |

**The seeding tree was a library path.** `/data/Movies` (capital M) is the KG
seeding tree; `/data/movies` is the Radarr root. `kg_adopt` hardlinks between
them — one inode, two names, zero extra disk, exactly as designed. But Jellyfin
scanned both and has no cross-path dedup, so every adopted film rendered twice.

Removing the path took **two** changes, not one. Editing `options.xml` is not
enough: Jellyfin also stores each media path as a `.mblink` file in the library
folder, and the scan keeps following it. `Movies.mblink` had to go too.

**The loose files could not simply be moved.** All 209 were actively seeded by
qBittorrent *from that exact path* — moving them would have broken 209 torrents
across three private trackers at once. The order that works:

1. `loose_adopt.py add` / `import` — hardlink each file into a proper movie
   folder via `importMode=copy` against `copyUsingHardlinks`. Zero bytes copied;
   the path qBittorrent knows is untouched.
2. `loose_adopt.py relocate` — only then, `setLocation` the torrent to
   `/data/torrents/movies`. `/data` is one filesystem, so this is a `rename(2)`:
   the inode survives, the library's hardlink stays valid, the root gets clean.

Doing those in the other order strands the library. The relocate guard is by
inode, and deliberately stricter than "is this the registered movieFile": a
loose file nobody has matched is currently the *only* way its film appears in
Jellyfin, so it is held rather than quietly moved out of view.

Result: **978 → 639 Jellyfin entries, surplus duplicate tiles 179 → 5.**
The 62 torrents still in the root are held for manual matching (`sylveste-n5gl`);
the remaining 5 tiles are `/data/movies-4k` pairs (`sylveste-ixxu`).

### Not all duplicates were free

The hardlink duplicates cost nothing. The torrent-folder ones are **real second
copies** — `Fruitvale Station` exists as inode 600998462 (the torrent) and inode
59213107 (the KG restore), byte-identical at 7,038,422,589 bytes each. The KG
restore re-downloaded material the box already had. Quantifying that is
`sylveste-a2pn`.

### A caution this run earned

`kg_orphan_adopt.py` originally picked the largest video in a KG folder as the
feature. That is wrong often enough to matter: the folder `No Data Plan (2019)`
also contains `At.Land.1944.720p.x264.mkv`, which is bigger and is a *different
film with its own folder*. Radarr's parser does not rescue you — given the
folder as context it reports **both** files as "No Data Plan". The fix is to let
the filename decide and only break ties by size.

It mis-filed one title before that fix (`Fantasma.2006` imported as *Barren
Illusion*); repaired by de-registering the file and re-importing the correct
`BARREN_ILLUSIONS.avi`. Worth remembering that "biggest file in the folder" is a
proxy, and proxies are what keep going wrong here.

## The Vampire Lestat: a metadata split, not a broken request

A request for *The Vampire Lestat* silently failed for one user — no error, and
no row in Seerr's request table. The cause is upstream: TMDb carries it as a
standalone series (id 323411) with **`tvdbId: null`**, while TVDB never split it
and tracks it as **Interview With The Vampire season 3** (7 episodes).

Seerr speaks TMDb to users and TVDB to Sonarr. With no TVDB id, that translation
has no output and the request dies at submit — which is why nothing was logged.

The scene is split the same way: HDBits ships `Interview.with.the.Vampire.S03`,
TorrentLeech ships both that *and* `The Vampire Lestat S01E0x`. Only the S03
naming can ever match Sonarr, so the `The Vampire Lestat S01` releases are
invisible to it no matter what is configured.

Fix: monitor the existing series and search season 3. Nothing to add, nothing to
map. Until TMDb gains the TVDB link, users must request *Interview with the
Vampire* — the Lestat entry cannot be made to work from this side.

## Transcoding: why this box buffers, and what was done

Users reported buffering even on 1080p. Bandwidth was ruled out first, by
measurement rather than assumption: **545–578 Mb/s up, 874 Mb/s down** on a
1 Gbps NIC, no per-user or server bitrate limits, Tailscale direct rather than
DERP-relayed, qBittorrent uploading 0.00 MB/s, load average 0.12. A 1080p stream
needs 8–20 Mb/s, so the uplink supports 30–60 of them.

Two hardware facts set the ceiling, and neither is fixable in software:

* **No GPU.** The Ryzen 7 3700X has no integrated graphics and the only display
  adapter is an ASPEED BMC. `HardwareAccelerationType: none` is not a
  misconfiguration — it is the only available value. Every transcode is
  software.
* **No SSD.** Four spinning 14.6 TB disks; `/` (md2) and `/data` (md3) are RAID5
  across *the same four spindles*. Media reads, transcode scratch, the KG rsync
  and seeding all contend, with RAID5's read-modify-write penalty on top.

### What actually triggers a transcode

Measured across 641 films via Jellyfin's own `MediaStreams`, not inferred:

| | count | |
|---|---|---|
| image subs only — subtitles on forces a **video burn-in** | 89 | 14% |
| image **and** text — burn-in avoidable, a text track already exists | 115 | 18% |
| text subs only — free overlay | 293 | 46% |
| no subtitles | 144 | 22% |
| no Samsung-compatible audio track at all | 122 | 19% |
| video codec Samsung cannot decode | 7 | 1% |

Video codec is *not* the problem. Subtitles are. Image subtitles (PGS/VOBSUB)
are pictures, so the only way to show them is to re-encode the video with them
painted on — which is why "buffering on 1080p" is really "buffering whenever
subtitles are on", and why resolution was a red herring.

### Applied

* `tmpfs` at `/transcodes`, 12 GB, and `TranscodingTempPath` pointed at it.
  Moving scratch to `/` would have achieved nothing — md2 and md3 are the same
  spindles. RAM is the only genuinely faster target.
* `EncoderPreset: veryfast` — a CPU-only encoder has to stay ahead of playback.
* `EnableThrottling: true` and `EnableSegmentDeletion: true` — stop ffmpeg
  racing ahead, and stop segments accumulating in a fixed-size tmpfs.
* **Bazarr**, wired to both arrs (SignalR connected), English profile as the
  default for movies and series. External `.srt` files are text, so the client
  renders them for free — this is the only lever that reaches the 89
  image-only films without re-encoding anything.

A trap worth recording: `encoding.xml` stores unset options as self-closing
`<EncoderPreset xsi:nil="true" />`. A naive `<tag>…</tag>` regex misses that
form, appends a *second* element, and Jellyfin then reads the first (nil) one
and silently discards the change. Handle both forms.

## Removing a library path does not remove its items

Worth its own heading, because it is the opposite of the intuition and it cost
this estate a week of believing the duplicates were fixed when they were not.

After `/data/Movies` was taken out of the Movies library on 2026-07-28 — from
`options.xml` *and* the `.mblink`, both of which are required — a full scan was
run and reported success:

    Scan Media Library   Completed after 0 minute(s) and 11 seconds

and 333 films were still double-listed. Rescanning again changed nothing,
because rescanning **cannot** change it. Jellyfin's validation walks the paths
a library currently declares and removes DB children it fails to find beneath
them. Take a path away and its items are not "missing" — they are *unreachable
by the validator*. They stay in `BaseItems`, keep joining into every query the
UI runs, and render forever. The 11-second runtime is the tell: the scan was
not skipping work, it was doing all the work it believed it had.

There is no supported "forget these" API. `DELETE /Items/{id}` deletes the
media from disk, which here would unlink hardlinks that 124 seeding torrents
depend on. So the rows must go directly — `purge_jellyfin_orphans.py`.

Two things make that safe, and one makes it dangerous.

Safe: every foreign key into `BaseItems` is `ON DELETE CASCADE`, including
`BaseItems.ParentId → BaseItems.Id`, so one `DELETE` also clears `UserData`,
`MediaStreamInfos`, `Chapters`, `AncestorIds`, images and people maps — as long
as you remember `PRAGMA foreign_keys = ON`, which SQLite leaves **off** by
default. And nothing of value was attached: 0 of the 1032 orphan rows carried a
play position, a played flag or a favourite.

Dangerous — and this is the part to actually remember:

    where Path like '/data/Movies%'   ->  1712 rows   WRONG, matches both dirs
    where Path glob '/data/Movies*'   ->  1032 rows   correct

SQLite's `LIKE` is case-insensitive for ASCII. On a box whose entire problem is
two directories differing only in case, the obvious cleanup statement silently
unions them and deletes the real library alongside the orphans. `GLOB` is
case-sensitive and is the only correct operator here. The same trap had already
produced a wrong reading earlier in the session — a check for at-risk watch
state reported "3 rows on each side" when it was the same 3 lower-case rows
counted twice.

### Not solved by any of the above

`EncoderPreset` and tmpfs make transcodes survivable; they do not make them
stop. The only fix that eliminates them is a client that can play the files:
an Apple TV 4K or Nvidia Shield direct-plays HEVC, DTS and TrueHD, and renders
PGS natively without burn-in. That is one ~€150 device against a server
migration — and Hetzner cannot sell the alternative, because its capacity line
(SX, all AMD, no iGPU) and its QuickSync line (EX, Intel Core) do not overlap.
Tracked as `sylveste-3f8x`.
