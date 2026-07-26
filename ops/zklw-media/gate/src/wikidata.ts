/**
 * IMDb ID → director, via Wikidata.
 *
 * Wikidata rather than TMDB/OMDb because it needs no API key and no account:
 * one fewer credential to provision on a box that already has too many. The
 * SPARQL endpoint is public and rate-limited by politeness, so queries are
 * batched (VALUES clause) and results are cached on disk.
 *
 * Coverage is good but not total — some films have no P57 (director) statement.
 * A miss is treated as "unknown director", never as "no pedigree", so the
 * caller falls through to its other signals rather than rejecting on absence.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const ENDPOINT = "https://query.wikidata.org/sparql";
// Wikidata asks for a descriptive UA identifying the tool; anonymous bulk
// querying is what gets clients blocked.
const UA = "jawncite-hdbits-gate/0.1 (https://github.com/mistakeknot/jawncite)";

export type DirectorIndex = Record<string, string[]>;

export async function loadCache(path: string): Promise<DirectorIndex> {
  try {
    return JSON.parse(await readFile(path, "utf8")) as DirectorIndex;
  } catch {
    return {};
  }
}

export async function saveCache(path: string, idx: DirectorIndex): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, JSON.stringify(idx, null, 2));
}

async function queryBatch(ttIds: string[]): Promise<DirectorIndex> {
  const values = ttIds.map((t) => `"${t}"`).join(" ");
  const query = `
    SELECT ?imdb ?directorLabel WHERE {
      VALUES ?imdb { ${values} }
      ?film wdt:P345 ?imdb ; wdt:P57 ?director .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }`;

  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      Accept: "application/sparql-results+json",
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": UA,
    },
    body: new URLSearchParams({ query }),
    signal: AbortSignal.timeout(120_000),
  });
  if (!res.ok) throw new Error(`wikidata HTTP ${res.status}`);

  const json = (await res.json()) as {
    results: { bindings: Array<{ imdb: { value: string }; directorLabel: { value: string } }> };
  };

  const out: DirectorIndex = {};
  for (const b of json.results.bindings) {
    const tt = b.imdb.value;
    (out[tt] ??= []).push(b.directorLabel.value);
  }
  return out;
}

/**
 * Resolve directors for many IMDb ids, using and updating a disk cache.
 * `onProgress` exists because a full canon sweep is ~2000 ids and takes minutes.
 */
export async function directorsFor(
  ttIds: string[],
  cachePath: string,
  opts: { batchSize?: number; onProgress?: (done: number, total: number) => void } = {},
): Promise<DirectorIndex> {
  const cache = await loadCache(cachePath);
  const missing = [...new Set(ttIds)].filter((t) => !(t in cache));
  const batchSize = opts.batchSize ?? 150;

  for (let i = 0; i < missing.length; i += batchSize) {
    const batch = missing.slice(i, i + batchSize);
    try {
      const got = await queryBatch(batch);
      // Record MISSES as empty arrays too. Without this every run re-queries
      // the same unanswerable ids forever and the cache never converges.
      for (const tt of batch) cache[tt] = got[tt] ?? [];
    } catch (err) {
      console.error(`  wikidata batch ${i / batchSize} failed: ${(err as Error).message}`);
    }
    opts.onProgress?.(Math.min(i + batchSize, missing.length), missing.length);
    await new Promise((r) => setTimeout(r, 800));
  }

  await saveCache(cachePath, cache);
  return cache;
}
