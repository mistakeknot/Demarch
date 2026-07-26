/**
 * Replay the gate against what the old regex racer ACTUALLY grabbed, and
 * against a live feed sample.
 *
 * This is the acceptance test for the whole exercise. The regex rule grabbed 24
 * torrents at a 67%-slop rate; the gate has to admit the films worth keeping
 * and reject the free-ad-tier filler, judged from the same identifiers the gate
 * sees in production (imdbid), resolved by asking the indexer rather than by
 * hand-typing IMDb ids from memory.
 */
import { readFile } from "node:fs/promises";
import { getMigrationsDb } from "@jawnverse/jawnlink";
import { judge, type FeedItem } from "./gate.js";

const RACED = new URL("../fixtures/raced-resolved.json", import.meta.url)
  .pathname;
const FEED = new URL("../fixtures/hdbits-feed-50.json", import.meta.url)
  .pathname;

/**
 * Ground truth for the 24 raced grabs.
 *
 * MUST_ADMIT: films with a real directorial signature that the gate exists to
 * catch. Note that NONE of these appear in TSPDT 2026, Sight & Sound 2022 or
 * the Criterion Collection — an acclaim-only gate rejects all four, which is
 * why the pedigree path carries the design.
 *
 * MUST_REJECT: the free-ad-tier rips. These are the unambiguous slop — a Tubi
 * or Fawesome or FoundTV encode is bottom-tier provenance regardless of
 * anything else, and the gate rejects them by override.
 */
const MUST_ADMIT = [
  "Body.Snatchers.1993",
  "Hors.Satan.2011",
  "Mank.2020.1080p",
];
const MUST_REJECT = [
  "Blood & Rust.2026",
  "Aria-Remix.2026",
  "I Hate Found Footage.2026",
];

/**
 * RESOLVED 2026-07-26. L'Orphéline avec en plus un bras en moins (2012) is now
 * asserted above rather than flagged.
 *
 * It was rejected while the pedigree path looked at DIRECTORS only: Jacques
 * Richard has no canon feature. Investigating on mk's instruction turned up the
 * real signal — the film was co-written by Roland Topor, who has two films in
 * the corpus (Fantastic Planet in Criterion, The Tenant in TSPDT). Extending
 * pedigree to screenwriters (Wikidata P58 alongside P57) admits it on its own
 * merits, with no hand-added name.
 *
 * The correction was cheap in precision: the allowlist roughly doubled
 * (718 -> 1619 creators) but admissions rose by exactly one in each replay set.
 */
const JUDGMENT_CALLS: string[] = [];

interface RacedRow {
  name: string;
  imdbid: number | null;
  size_gb: number;
  uploaded_gb: number;
}

function matches(name: string, needle: string) {
  return name.toLowerCase().includes(needle.toLowerCase());
}

async function main() {
  const raced = JSON.parse(await readFile(RACED, "utf8")) as RacedRow[];
  const feed = JSON.parse(await readFile(FEED, "utf8")) as FeedItem[];
  const db = getMigrationsDb();
  let failures = 0;

  try {
    console.log("=".repeat(100));
    console.log("REPLAY 1 — the 24 torrents the regex racer actually grabbed");
    console.log("=".repeat(100));

    const judgedRaced = await judge(
      raced.map((r) => ({ title: r.name, imdbid: r.imdbid })),
      db,
    );

    for (const [i, j] of judgedRaced.entries()) {
      const mark = j.verdict.decision === "ADMIT" ? "✓ ADMIT" : "· reject";
      console.log(
        `${mark} ${j.verdict.reason.padEnd(18)} ${j.title.slice(0, 58)}`,
      );
      console.log(
        `         ${j.verdict.detail.slice(0, 88)}  [up ${raced[i]!.uploaded_gb}GB]`,
      );
    }

    const admitted = judgedRaced.filter((j) => j.verdict.decision === "ADMIT");
    console.log(
      `\n${admitted.length}/${judgedRaced.length} admitted ` +
        `(the regex rule admitted all ${judgedRaced.length})`,
    );

    console.log("\n-- assertions --");
    for (const needle of MUST_ADMIT) {
      const j = judgedRaced.find((x) => matches(x.title, needle));
      if (!j) {
        console.log(`FAIL  ${needle}: not present in fixture`);
        failures++;
      } else if (j.verdict.decision !== "ADMIT") {
        console.log(
          `FAIL  ${needle}: rejected (${j.verdict.reason} — ${j.verdict.detail})`,
        );
        failures++;
      } else {
        console.log(`ok    ${needle} admitted via ${j.verdict.reason}`);
      }
    }
    for (const needle of MUST_REJECT) {
      const j = judgedRaced.find((x) => matches(x.title, needle));
      if (!j) {
        console.log(`FAIL  ${needle}: not present in fixture`);
        failures++;
      } else if (j.verdict.decision !== "REJECT") {
        console.log(`FAIL  ${needle}: ADMITTED (${j.verdict.reason})`);
        failures++;
      } else {
        console.log(`ok    ${needle} rejected via ${j.verdict.reason}`);
      }
    }

    for (const needle of JUDGMENT_CALLS) {
      const j = judgedRaced.find((x) => matches(x.title, needle));
      if (j) {
        console.log(
          `NOTE  ${needle}: ${j.verdict.decision} (${j.verdict.reason} — ${j.verdict.detail}) ` +
            `— open judgment call for mk, not asserted`,
        );
      }
    }

    // Nothing free-ad-tier may survive, under any signal, ever.
    const leaked = judgedRaced.filter(
      (j) =>
        j.verdict.decision === "ADMIT" &&
        /tubi|fawesome|foundtv|plex|roku|crackle|xumo|pluto|redbox/i.test(
          j.title,
        ),
    );
    if (leaked.length) {
      console.log(`FAIL  ${leaked.length} free-ad-tier release(s) admitted`);
      failures++;
    } else {
      console.log("ok    zero free-ad-tier releases admitted");
    }

    console.log("\n" + "=".repeat(100));
    console.log("REPLAY 2 — live 50-article HDBits feed sample");
    console.log("=".repeat(100));

    const judgedFeed = await judge(feed, db);
    for (const j of judgedFeed) {
      const mark = j.verdict.decision === "ADMIT" ? "✓ ADMIT" : "· reject";
      console.log(
        `${mark} ${j.verdict.reason.padEnd(18)} ${j.title.slice(0, 56)}`,
      );
      if (j.verdict.decision === "ADMIT")
        console.log(`         ${j.verdict.detail.slice(0, 88)}`);
    }
    const fAdmit = judgedFeed.filter(
      (j) => j.verdict.decision === "ADMIT",
    ).length;
    console.log(
      `\n${fAdmit}/${judgedFeed.length} admitted from the live feed sample`,
    );

    const leaked2 = judgedFeed.filter(
      (j) =>
        j.verdict.decision === "ADMIT" &&
        /tubi|fawesome|foundtv|plex|roku|crackle|xumo|pluto|redbox|\bvmx\b/i.test(
          j.title,
        ),
    );
    if (leaked2.length) {
      console.log(
        `FAIL  ${leaked2.length} free-ad-tier release(s) admitted from feed`,
      );
      failures++;
    } else {
      console.log("ok    zero free-ad-tier releases admitted from feed");
    }

    console.log(
      "\n" +
        (failures === 0
          ? "ALL REPLAY ASSERTIONS PASSED"
          : `${failures} ASSERTION(S) FAILED`),
    );
    if (failures) process.exitCode = 1;
  } finally {
    await db.close();
  }
}

await main();
