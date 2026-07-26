/**
 * Derive the director allowlist FROM jawncite's own canon.
 *
 * The rule: if you directed something the canon already recognises, your next
 * film is worth grabbing before anyone has had time to write about it.
 *
 * This is what makes the pedigree path self-bootstrapping rather than a
 * hand-maintained list of favourites — it grows automatically as jawncite
 * ingests more lists, and it is auditable (every director traces to a specific
 * acclaimed film).
 *
 * Why it is the PRIMARY path and not a fallback: canonical lists skew hard to
 * pre-2000. Of the four films the old regex racer grabbed that were actually
 * worth keeping — Body Snatchers (1993), Hors Satan (2011), Mank (2020),
 * L'Orpheline (2012) — NONE appear in TSPDT 2026, Sight & Sound 2022 or the
 * Criterion Collection. An acclaim-only gate would have rejected all four.
 */
import { writeFile } from "node:fs/promises";
import { sql } from "drizzle-orm";
import { getMigrationsDb } from "@jawnverse/jawnlink";
import { MANUAL_DIRECTORS } from "./policy.js";
import { directorsFor } from "./wikidata.js";

const CACHE = new URL("../.cache/wikidata-directors.json", import.meta.url).pathname;
const OUT = new URL("../pedigree-directors.json", import.meta.url).pathname;

/**
 * Only directors of genuinely-acclaimed films earn a slot. Criterion-only
 * inclusion is a real signal but a broad one (1500 films); requiring a score
 * above the median keeps the allowlist meaningful rather than "anyone Criterion
 * ever pressed a disc for".
 */
const MIN_SCORE_FOR_PEDIGREE = 1.0;

async function main() {
  const db = getMigrationsDb();
  try {
    const rows = await db.drizzle.execute<{ natural_key: string; display_name: string }>(sql`
      SELECT e.natural_key, e.display_name
        FROM jawncite.entity_acclaim a
        JOIN jawncite.entities e ON e.entity_id = a.entity_id
       WHERE a.domain = 'screen'
         AND a.score >= ${MIN_SCORE_FOR_PEDIGREE}
         AND e.natural_key LIKE 'imdb:%'
    `);
    console.log(`canon films above score ${MIN_SCORE_FOR_PEDIGREE}: ${rows.rows.length}`);

    const ttIds = rows.rows.map((r) => r.natural_key.replace(/^imdb:/, ""));
    const index = await directorsFor(ttIds, CACHE, {
      onProgress: (d, t) => t && console.log(`  wikidata ${d}/${t}`),
    });

    const directors = new Set<string>(MANUAL_DIRECTORS);
    let resolved = 0;
    for (const tt of ttIds) {
      const ds = index[tt];
      if (ds?.length) {
        resolved++;
        for (const d of ds) directors.add(d);
      }
    }

    const sorted = [...directors].sort();
    await writeFile(
      OUT,
      JSON.stringify(
        {
          generated_from: `jawncite entity_acclaim score>=${MIN_SCORE_FOR_PEDIGREE}`,
          canon_films: ttIds.length,
          films_with_director: resolved,
          manual_additions: MANUAL_DIRECTORS.length,
          directors: sorted,
        },
        null,
        2,
      ),
    );
    console.log(
      `pedigree: ${sorted.length} directors ` +
        `(${resolved}/${ttIds.length} canon films resolved, +${MANUAL_DIRECTORS.length} manual)`,
    );
    console.log(`wrote ${OUT}`);
  } finally {
    await db.close();
  }
}

await main();
