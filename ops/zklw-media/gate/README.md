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

So the director allowlist carries the design, and it is derived from jawncite's
own canon rather than hand-curated: *if you directed something the canon
recognises, your next film is worth grabbing before anyone has written about
it.* `build-pedigree.ts` resolves every canon film above score 1.0 to its
director via Wikidata (keyless, no account) — currently **718 directors from
1,504 of 1,559 canon films**, plus a short manual list for people whose work is
clearly worth grabbing but who have not yet charted.

The allowlist grows automatically as jawncite ingests more lists.

## Results

Replayed against the 24 torrents the regex rule actually grabbed, with IMDb ids
resolved by asking Prowlarr rather than by hand:

| | regex rule | gate |
|---|---|---|
| admitted | 24 / 24 | **4 / 24** |
| free-ad-tier admitted | 3 | **0** |

Against a live 50-article feed sample: **8 / 50 admitted**, 0 free-ad-tier.
Admits included Rohmer's *Le rayon vert* (acclaim), Ferrara's *Body Snatchers*
and Dumont's *Hors Satan* (pedigree); rejects included Piranha 3DD, Wrong Turn,
Balls of Fury, Big Stan, Mortal Kombat II and Bullet to the Head.

## One open judgment call

*L'Orphéline avec en plus un bras en moins* (2012, dir. Jacques Richard) is
rejected — Richard has no canon film. It was on my first-pass keeper list purely
because the title reads as French arthouse, which is not a founded judgment. The
replay harness **reports** it and does not assert on it, because silently adding
Richard to `MANUAL_DIRECTORS` would be tuning the allowlist to make a test pass.

To admit it: add `"Jacques Richard"` to `MANUAL_DIRECTORS` in `src/policy.ts`.

## Usage

```bash
npm install
bash scripts/link-dev.sh                      # dedupe drizzle-orm across the linked repos
export JAWNCITE_DATABASE_URL="$(bash ~/projects/jawncite/scripts/devdb.sh url)"
npm run pedigree                              # derive the director allowlist (slow: ~1500 Wikidata lookups, cached)
npm run replay                                # judge both fixtures, assert
npm run gate -- --fixture fixtures/hdbits-feed-50.json
```

## Not yet wired

Live feed polling and the push-to-qBittorrent step. `gate.ts` deliberately
refuses to run without `--fixture` so that a dry run cannot grab anything. The
push should use category+tag `ratio-race` so the existing qbit-manage priority-0
group applies the 14-day HnR floor.
