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
import { acclaimForNaturalKeys, getMigrationsDb, type MigrationsDb } from "@jawnverse/jawnlink";
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

const DIRECTOR_CACHE = new URL("../.cache/wikidata-directors.json", import.meta.url).pathname;
const PEDIGREE_FILE = new URL("../pedigree-directors.json", import.meta.url).pathname;

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

export async function loadPedigreeDirectors(): Promise<Set<string>> {
  try {
    const raw = JSON.parse(await readFile(PEDIGREE_FILE, "utf8")) as { directors: string[] };
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
  const keyed = items.map((it) => ({ it, naturalKey: imdbNaturalKey(it.imdbid) }));
  const keys = keyed.map((k) => k.naturalKey).filter((k): k is string => k !== null);
  const acclaim = await acclaimForNaturalKeys(db.drizzle, "screen", keys);

  // Only look up directors for releases acclaim did not already settle.
  const needDirector = keyed
    .filter(({ it, naturalKey }) => {
      if (freeAdTierTag(it.title)) return false;
      if (!naturalKey) return false;
      const a = acclaim.get(naturalKey);
      return !(a && (Number(a.score) >= thresholds.minScore || a.listCount >= thresholds.minListCount));
    })
    .map(({ naturalKey }) => naturalKey!.replace(/^imdb:/, ""));

  const directorIndex = opts.offline
    ? await (async () => {
        try {
          return JSON.parse(await readFile(DIRECTOR_CACHE, "utf8")) as Record<string, string[]>;
        } catch {
          return {};
        }
      })()
    : await directorsFor(needDirector, DIRECTOR_CACHE);

  return keyed.map(({ it, naturalKey }): Judged => {
    const adTag = freeAdTierTag(it.title);
    if (adTag) {
      return { ...it, naturalKey, verdict: reject("free_ad_tier", `${adTag}-sourced release`) };
    }
    if (!naturalKey) {
      return { ...it, naturalKey, verdict: reject("no_imdb_id", "feed article carried no imdbid") };
    }

    const a = acclaim.get(naturalKey);
    if (a && (Number(a.score) >= thresholds.minScore || a.listCount >= thresholds.minListCount)) {
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
    if (hit) return { ...it, naturalKey, verdict: admit("pedigree_director", `dir. ${hit}`) };

    const studio = PEDIGREE_STUDIOS.find((s) =>
      it.title.toLowerCase().includes(s.toLowerCase()),
    );
    if (studio) return { ...it, naturalKey, verdict: admit("pedigree_studio", studio) };

    return {
      ...it,
      naturalKey,
      verdict: reject(
        "no_signal",
        directors.length ? `dir. ${directors.join(", ")} — not in canon or allowlist` : "no acclaim, no director resolved",
      ),
    };
  });
}

/** Live run: judge the current feed and report. Pushing is a separate, explicit step. */
async function main() {
  const fixtureIdx = process.argv.indexOf("--fixture");
  const offline = process.argv.includes("--offline");
  if (fixtureIdx < 0) {
    throw new Error(
      "live feed polling not wired yet — run with --fixture <path>. " +
        "Pushing to qBittorrent is deliberately a separate step so a dry run cannot grab anything.",
    );
  }
  const items = JSON.parse(await readFile(process.argv[fixtureIdx + 1]!, "utf8")) as FeedItem[];
  const db = getMigrationsDb();
  try {
    const judged = await judge(items, db, { offline });
    for (const j of judged) {
      const mark = j.verdict.decision === "ADMIT" ? "✓" : "·";
      console.log(`${mark} ${j.verdict.decision.padEnd(6)} ${j.verdict.reason.padEnd(18)} ${j.title.slice(0, 62)}`);
      console.log(`         ${j.verdict.detail}`);
    }
    const admitted = judged.filter((j) => j.verdict.decision === "ADMIT").length;
    console.log(`\n${admitted}/${judged.length} admitted`);
  } finally {
    await db.close();
  }
}

if (process.argv[1]?.endsWith("gate.ts") || process.argv[1]?.endsWith("gate.js")) await main();
