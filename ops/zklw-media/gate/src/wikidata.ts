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

/**
 * P57 = director, P58 = screenwriter.
 *
 * Writers matter as much as directors for this purpose, and leaving them out
 * was a real gap. L'Orphéline avec en plus un bras en moins (2012) has a
 * director with no canon feature — but it was co-written by Roland Topor, who
 * has TWO films in the corpus (Fantastic Planet in Criterion, The Tenant in
 * TSPDT). A director-only allowlist cannot see that; a creator-level one
 * catches it automatically, with no hand-added name.
 */
export const P_DIRECTOR = "P57";
export const P_WRITER = "P58";

async function queryBatch(ttIds: string[], props: string[]): Promise<DirectorIndex> {
  const values = ttIds.map((t) => `"${t}"`).join(" ");
  const union = props
    .map((p) => `{ ?film wdt:${p} ?person }`)
    .join(" UNION ");
  const query = `
    SELECT ?imdb ?personLabel WHERE {
      VALUES ?imdb { ${values} }
      ?film wdt:P345 ?imdb .
      ${union}
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
    results: { bindings: Array<{ imdb: { value: string }; personLabel: { value: string } }> };
  };

  const out: DirectorIndex = {};
  for (const b of json.results.bindings) {
    const tt = b.imdb.value;
    const list = (out[tt] ??= []);
    if (!list.includes(b.personLabel.value)) list.push(b.personLabel.value);
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
  opts: {
    batchSize?: number;
    onProgress?: (done: number, total: number) => void;
    props?: string[];
  } = {},
): Promise<DirectorIndex> {
  const props = opts.props ?? [P_DIRECTOR, P_WRITER];
  const cache = await loadCache(cachePath);
  const missing = [...new Set(ttIds)].filter((t) => !(t in cache));
  const batchSize = opts.batchSize ?? 150;

  for (let i = 0; i < missing.length; i += batchSize) {
    const batch = missing.slice(i, i + batchSize);
    try {
      const got = await queryBatch(batch, props);
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
