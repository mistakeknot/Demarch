# HDBits curation gate

Replaces grey's qBittorrent RSS auto-download rule with a jawncite-backed
admission decision. Bead `sylveste-p9ox.4`.

## Why the regex rule had to go

The RSS rule matched on title regex and grabbed 24 torrents at roughly a 67%
slop rate — Tubi, Fawesome and FoundTV rips plus a wall of no-name 2026
AMZN/Netflix filler. It could not have done better: **an RSS rule sees only the
release name**, and no regex over release names distinguishes a Bruno Dumont
from a Tubi original. Fixing it needed an external judgment about the film,
which is what jawncite provides.

Both qBittorrent RSS master switches (`rss_processing_enabled`,
`rss_auto_downloading_enabled`) stay **false**. The gate pushes torrents
directly; a regex rule racing it over the same feed would reintroduce the slop.

## Decision order

1. **free-ad-tier → REJECT.** An override, checked first. Tubi / Fawesome /
   FoundTV / Plex / Roku / Crackle / Xumo / Pluto / Redbox / VMX. No later
   signal can rescue one — acclaim is irrelevant if the provenance is a free
   ad-supported catalogue.
2. **no imdbid → REJECT.** Nothing to ask jawncite about. Rare: the Prowlarr
   feed carried an `imdbid` on 50 of 50 sampled articles.
3. **acclaim → ADMIT.** `entity_acclaim.score >= 0.5` or membership in ≥1
   canonical list.
4. **pedigree (director, then studio) → ADMIT.**
5. otherwise **REJECT** as `no_signal`.

## Pedigree is the primary path, not a fallback

This surprised me and is worth stating plainly. Of the films the old racer
grabbed that were actually worth keeping — Body Snatchers (1993, Ferrara), Hors
Satan (2011, Dumont), Mank (2020, Fincher) — **none appear in TSPDT 2026, Sight
& Sound 2022 or the Criterion Collection.** Canonical lists skew hard to
pre-2000. An acclaim-only gate rejects all three.

So the creator allowlist carries the design, and it is derived from jawncite's
own canon rather than hand-curated: *if you made something the canon
recognises, your next film is worth grabbing before anyone has written about
it.* `build-pedigree.ts` resolves every canon film above score 1.0 to its
directors **and screenwriters** via Wikidata (keyless, no account) — currently
**1,619 creators from 1,504 of 1,559 canon films**, plus a short manual list for
people whose work is clearly worth grabbing but who have not yet charted.

**Writers count, and leaving them out was a real gap.** L'Orphéline avec en plus
un bras en moins (2012) has a director with no canon feature, but was co-written
by Roland Topor — who has two films in the corpus (*Fantastic Planet* in
Criterion, *The Tenant* in TSPDT). Adding P58 alongside P57 admits it on its own
merits rather than by hand-adding a name. The correction cost almost nothing in
precision: the allowlist roughly doubled but admissions rose by exactly one in
each replay set.

A related accident worth keeping: Wikidata has no English *label* for Topor
(only arz/fa/he/ja/ru/zh), so the SPARQL label service returns the bare q-id
`Q550806`. Matching on that id is what linked Fantastic Planet to L'Orphéline —
**name-matching would have missed him entirely.** The gate prints such matches as
`wikidata:Q550806` rather than pretending an id is a name.

The allowlist grows automatically as jawncite ingests more lists.

## Results

Replayed against the 24 torrents the regex rule actually grabbed, with IMDb ids
resolved by asking Prowlarr rather than by hand:

| | regex rule | gate |
|---|---|---|
| admitted | 24 / 24 | **5 / 24** |
| free-ad-tier admitted | 3 | **0** |

Against a live 50-article feed sample: **9 / 50 admitted**, 0 free-ad-tier.
Admits included Rohmer's *Le rayon vert* (acclaim), Ferrara's *Body Snatchers*
and Dumont's *Hors Satan* (pedigree); rejects included Piranha 3DD, Wrong Turn,
Balls of Fury, Big Stan, Mortal Kombat II and Bullet to the Head.

## Usage

```bash
npm install
bash scripts/link-dev.sh                      # dedupe drizzle-orm across the linked repos
export JAWNCITE_DATABASE_URL="$(bash ~/projects/jawncite/scripts/devdb.sh url)"
npm run pedigree                              # derive the director allowlist (slow: ~1500 Wikidata lookups, cached)
npm run replay                                # judge both fixtures, assert
npm run gate -- --fixture fixtures/hdbits-feed-50.json
```

## Live operation

```bash
npm run gate                      # poll the live feed, report, push NOTHING
npm run gate -- --push            # actually grab the admitted releases
npm run gate -- --fixture fixtures/hdbits-feed-50.json --offline
```

**Pushing is opt-in.** Without `--push` the gate is a report and nothing else —
the same arm/disarm discipline the ratio scripts use. An outward-facing act
against a private tracker should never be the default behaviour of running a
command to see what it thinks. `--push` also refuses to run from a fixture,
since that would grab against stale data.

Three guards fire before anything is added:

1. **`assertRssDisarmed()`** — refuses to push if either qBittorrent RSS master
   switch is on. The old regex rule racing this gate over the same feed would
   reintroduce exactly the slop the gate exists to stop.
2. **Already-present check** — admitted releases already in the client are
   skipped rather than re-added.
3. **Category *and* tag `ratio-race`** — so the existing qbit-manage priority-0
   group governs the torrent, carrying the 14-day HnR floor and `cleanup:false`.
   Grabbing outside that group would put a private-tracker torrent under no
   retention policy at all.

### Deployment

The gate must run **on grey**: it reads the Prowlarr API key and the qBittorrent
password from `/home/mk/grey-media/config/...` at call time, so the secrets never
become arguments. It also needs `JAWNCITE_DATABASE_URL` pointing at the shared
Neon project — which means deployment is naturally sequenced *after* the Neon
apply (bead `sylveste-p9ox.6`). grey needs Node ≥20 and an `npm install` of this
directory plus the two linked packages.
