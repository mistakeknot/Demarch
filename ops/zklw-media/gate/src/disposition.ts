/**
 * Emit the keep/drop disposition for the torrents the regex racer grabbed.
 *
 * Two rules, applied in order:
 *
 *  1. THE GATE'S VERDICT. Whatever the gate would have admitted, we keep;
 *     what it would have rejected, we drop. Using the same judgment
 *     retroactively is the point — it makes the cleanup consistent with what
 *     the box will do from now on rather than a one-off taste exercise.
 *
 *  2. DEDUPE BY FILM. The racer grabbed several encodes of the same film
 *     (Mank at 720p and 1080p, Avatar Aang four times). Keep the largest
 *     admitted encode per imdbid and drop the rest — this is a separate
 *     question from acclaim, and the gate does not answer it because at feed
 *     time there is no "other copy" to compare against.
 *
 * Output feeds reconcile_raced.py on grey, which enforces the HnR floor.
 */
import { readFile, writeFile } from "node:fs/promises";
import { getMigrationsDb } from "@jawnverse/jawnlink";
import { judge } from "./gate.js";

const RACED = new URL("../fixtures/raced-resolved.json", import.meta.url).pathname;
const OUT = new URL("../disposition.json", import.meta.url).pathname;

interface RacedRow {
  name: string;
  imdbid: number | null;
  size_gb: number;
  uploaded_gb: number;
}

async function main() {
  const raced = JSON.parse(await readFile(RACED, "utf8")) as RacedRow[];
  const db = getMigrationsDb();
  try {
    const judged = await judge(
      raced.map((r) => ({ title: r.name, imdbid: r.imdbid })),
      db,
      { offline: true },
    );

    const rows = judged.map((j, i) => ({
      name: j.title,
      imdbid: raced[i]!.imdbid,
      size_gb: raced[i]!.size_gb,
      uploaded_gb: raced[i]!.uploaded_gb,
      verdict: j.verdict.decision,
      reason: j.verdict.reason,
      detail: j.verdict.detail,
      action: j.verdict.decision === "ADMIT" ? "keep" : "drop",
      note: "",
    }));

    // Rule 2 — one encode per film.
    const byFilm = new Map<number, typeof rows>();
    for (const r of rows) {
      if (r.action !== "keep" || r.imdbid == null) continue;
      const list = byFilm.get(r.imdbid) ?? [];
      list.push(r);
      byFilm.set(r.imdbid, list);
    }
    for (const [, dupes] of byFilm) {
      if (dupes.length < 2) continue;
      dupes.sort((a, b) => b.size_gb - a.size_gb);
      for (const d of dupes.slice(1)) {
        d.action = "drop";
        d.note = `duplicate encode — keeping the ${dupes[0]!.size_gb}GB copy`;
      }
    }

    const keep = rows.filter((r) => r.action === "keep");
    const drop = rows.filter((r) => r.action === "drop");
    await writeFile(
      OUT,
      JSON.stringify(
        {
          generated_note:
            "Disposition only. reconcile_raced.py enforces the 14-day HnR floor and " +
            "will refuse to remove anything seeding for less than min_seeding_time.",
          keep: keep.map((r) => r.name),
          drop: drop.map((r) => r.name),
          rows,
        },
        null,
        2,
      ),
    );

    console.log(`KEEP (${keep.length}):`);
    for (const r of keep) console.log(`  ${r.name}\n      ${r.detail}`);
    console.log(`\nDROP (${drop.length}), ${drop.reduce((a, r) => a + r.size_gb, 0).toFixed(1)}GB:`);
    for (const r of drop) console.log(`  ${r.name}\n      ${r.note || r.detail}`);
    console.log(`\nwrote ${OUT}`);
  } finally {
    await db.close();
  }
}

await main();
