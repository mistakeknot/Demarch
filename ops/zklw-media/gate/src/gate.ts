/**
 * The HDBits curation gate.
 *
 * Replaces grey's qBittorrent RSS auto-download rule, which stays DISARMED —
 * both `rss_processing_enabled` and `rss_auto_downloading_enabled` must remain
 * false. A regex rule and this gate racing each other over the same feed would
 * reintroduce exactly the slop the gate exists to stop.
 *
 * Decision order, and each step's rationale:
 *
 *  1. FREE-AD-TIER → reject. An override, checked first so that nothing below
 *     can rescue a Tubi rip. Acclaim is irrelevant if the encode's provenance
 *     is a free ad-supported catalogue.
 *  2. NO IMDB ID → reject. Without a natural key there is nothing to ask
 *     jawncite about. The feed supplies imdbid on effectively every article,
 *     so this is rare and cheap to be strict about.
 *  3. ACCLAIM → admit. jawncite says the canon recognises this film.
 *  4. PEDIGREE (director, then studio) → admit. For films too new or too
 *     obscure to have charted. This is the path that actually carries most
 *     admissions — see build-pedigree.ts.
 *  5. otherwise reject as no_signal.
 */
import { readFile } from "node:fs/promises";
import {
  acclaimForNaturalKeys,
  getMigrationsDb,
  type MigrationsDb,
} from "@jawnverse/jawnlink";
import {
  DEFAULT_THRESHOLDS,
  PEDIGREE_STUDIOS,
  admit,
  freeAdTierTag,
  imdbNaturalKey,
  reject,
  type GateThresholds,
  type Verdict,
} from "./policy.js";
import { directorsFor } from "./wikidata.js";

const DIRECTOR_CACHE = new URL(
  "../.cache/wikidata-directors.json",
  import.meta.url,
).pathname;
const PEDIGREE_FILE = new URL("../pedigree-directors.json", import.meta.url)
  .pathname;

export interface FeedItem {
  title: string;
  imdbid?: number | string | null;
  size?: number | null;
  seeders?: number | null;
  pubDate?: string | null;
}

export interface Judged extends FeedItem {
  naturalKey: string | null;
  verdict: Verdict;
}

/**
 * Render a creator for humans without pretending a bare Wikidata id is a name.
 *
 * Some people have a Wikidata item and an enwiki article but NO English label —
 * Roland Topor (Q550806) is one, labelled only in arz/fa/he/ja/ru/zh. The SPARQL
 * label service then returns the raw q-id, and that turns out to be a feature
 * rather than a bug: matching on q-ids caught Topor as the shared creator
 * between Fantastic Planet and L'Orphéline, which name-matching would have
 * missed outright. So keep the id, just don't print it as if it were a name.
 */
function creatorLabel(hit: string): string {
  return /^Q\d+$/.test(hit)
    ? `creator wikidata:${hit} (no English label; matched by id)`
    : `creator ${hit}`;
}

export async function loadPedigreeDirectors(): Promise<Set<string>> {
  try {
    const raw = JSON.parse(await readFile(PEDIGREE_FILE, "utf8")) as {
      directors: string[];
    };
    // Case-folded: Wikidata labels and hand-typed names disagree on case often
    // enough that an exact-match set would silently miss.
    return new Set(raw.directors.map((d) => d.toLowerCase()));
  } catch {
    throw new Error(
      `${PEDIGREE_FILE} missing — run \`npm run pedigree\` first (it derives the ` +
        `director allowlist from jawncite's canon).`,
    );
  }
}

export async function judge(
  items: FeedItem[],
  db: MigrationsDb,
  opts: { thresholds?: GateThresholds; offline?: boolean } = {},
): Promise<Judged[]> {
  const thresholds = opts.thresholds ?? DEFAULT_THRESHOLDS;
  const pedigree = await loadPedigreeDirectors();

  // Resolve keys up front so acclaim is ONE query for the whole batch rather
  // than one per release.
  const keyed = items.map((it) => ({
    it,
    naturalKey: imdbNaturalKey(it.imdbid),
  }));
  const keys = keyed
    .map((k) => k.naturalKey)
    .filter((k): k is string => k !== null);
  const acclaim = await acclaimForNaturalKeys(db.drizzle, "screen", keys);

  // Only look up directors for releases acclaim did not already settle.
  const needDirector = keyed
    .filter(({ it, naturalKey }) => {
      if (freeAdTierTag(it.title)) return false;
      if (!naturalKey) return false;
      const a = acclaim.get(naturalKey);
      return !(
        a &&
        (Number(a.score) >= thresholds.minScore ||
          a.listCount >= thresholds.minListCount)
      );
    })
    .map(({ naturalKey }) => naturalKey!.replace(/^imdb:/, ""));

  const directorIndex = opts.offline
    ? await (async () => {
        try {
          return JSON.parse(await readFile(DIRECTOR_CACHE, "utf8")) as Record<
            string,
            string[]
          >;
        } catch {
          return {};
        }
      })()
    : await directorsFor(needDirector, DIRECTOR_CACHE);

  return keyed.map(({ it, naturalKey }): Judged => {
    const adTag = freeAdTierTag(it.title);
    if (adTag) {
      return {
        ...it,
        naturalKey,
        verdict: reject("free_ad_tier", `${adTag}-sourced release`),
      };
    }
    if (!naturalKey) {
      return {
        ...it,
        naturalKey,
        verdict: reject("no_imdb_id", "feed article carried no imdbid"),
      };
    }

    const a = acclaim.get(naturalKey);
    if (
      a &&
      (Number(a.score) >= thresholds.minScore ||
        a.listCount >= thresholds.minListCount)
    ) {
      return {
        ...it,
        naturalKey,
        verdict: admit(
          "acclaim",
          `${a.displayName} — score ${Number(a.score).toFixed(2)}, ${a.listCount} list(s)`,
        ),
      };
    }

    const tt = naturalKey.replace(/^imdb:/, "");
    const directors = directorIndex[tt] ?? [];
    const hit = directors.find((d) => pedigree.has(d.toLowerCase()));
    if (hit) {
      return {
        ...it,
        naturalKey,
        verdict: admit("pedigree_creator", creatorLabel(hit)),
      };
    }

    const studio = PEDIGREE_STUDIOS.find((s) =>
      it.title.toLowerCase().includes(s.toLowerCase()),
    );
    if (studio)
      return { ...it, naturalKey, verdict: admit("pedigree_studio", studio) };

    return {
      ...it,
      naturalKey,
      verdict: reject(
        "no_signal",
        directors.length
          ? `dir. ${directors.join(", ")} — not in canon or allowlist`
          : "no acclaim, no director resolved",
      ),
    };
  });
}

/**
 * Poll the live feed (or replay a fixture), judge it, and optionally push.
 *
 *   --fixture <path>   judge a saved feed sample instead of polling
 *   --offline          use only the cached director index; no Wikidata calls
 *   --push             ACTUALLY add the admitted torrents to qBittorrent
 *
 * PUSHING IS OPT-IN AND SEPARATE. Without --push this is a report and nothing
 * else, which is the same arm/disarm discipline the ratio scripts use: an
 * outward-facing act against a private tracker should never be the default
 * behaviour of running a command to see what it thinks.
 */
async function main() {
  const fixtureIdx = process.argv.indexOf("--fixture");
  const offline = process.argv.includes("--offline");
  const push = process.argv.includes("--push");

  let items: FeedItem[];
  if (fixtureIdx >= 0) {
    items = JSON.parse(
      await readFile(process.argv[fixtureIdx + 1]!, "utf8"),
    ) as FeedItem[];
    console.log(`judging ${items.length} articles from fixture`);
  } else {
    const { fetchFeed } = await import("./sources.js");
    items = await fetchFeed();
    console.log(`judging ${items.length} articles from the live Prowlarr feed`);
  }

  const db = getMigrationsDb();
  try {
    const judged = await judge(items, db, { offline });
    for (const j of judged) {
      const mark = j.verdict.decision === "ADMIT" ? "✓" : "·";
      console.log(
        `${mark} ${j.verdict.decision.padEnd(6)} ${j.verdict.reason.padEnd(18)} ${j.title.slice(0, 62)}`,
      );
      if (j.verdict.decision === "ADMIT")
        console.log(`         ${j.verdict.detail}`);
    }
    const admitted = judged.filter((j) => j.verdict.decision === "ADMIT");
    console.log(`\n${admitted.length}/${judged.length} admitted`);

    if (!push) {
      console.log(
        "dry run — nothing pushed. Re-run with --push to grab the admitted releases.",
      );
      return;
    }
    if (fixtureIdx >= 0) {
      throw new Error(
        "refusing to --push from a fixture; that would grab against stale data",
      );
    }

    const { Qbit } = await import("./sources.js");
    const qb = new Qbit();
    await qb.login();
    // Belt and braces: the regex rule must not be racing us over this feed.
    await qb.assertRssDisarmed();

    const already = await qb.existingHashesByName();
    const toAdd = admitted.filter(
      (j) =>
        !already.has(j.title.replace(/\.(mkv|mp4|avi)$/i, "")) &&
        !already.has(j.title),
    );
    const urls = toAdd
      .map((j) => (j as { downloadUrl?: string }).downloadUrl)
      .filter((u): u is string => !!u);

    if (urls.length === 0) {
      console.log(
        "nothing new to push (all admitted releases are already in the client)",
      );
      return;
    }
    await qb.add(urls);
    console.log(`pushed ${urls.length} torrent(s) as category+tag ratio-race:`);
    for (const j of toAdd) console.log(`  ${j.title}`);
    console.log(
      "\nqbit-manage's priority-0 ratio-race group now governs them " +
        "(14-day HnR floor, cleanup:false).",
    );
  } finally {
    await db.close();
  }
}

if (
  process.argv[1]?.endsWith("gate.ts") ||
  process.argv[1]?.endsWith("gate.js")
)
  await main();
