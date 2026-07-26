/**
 * Live I/O: read the Prowlarr feed, push to qBittorrent.
 *
 * Kept apart from gate.ts so the decision logic stays pure and testable against
 * fixtures. Everything here talks to the network; nothing here decides anything.
 *
 * Secrets are read from the on-disk service configs at call time and never
 * passed as arguments, so they cannot leak into a process list or a shell
 * history. Same discipline as the existing ratio scripts on grey.
 */
import { readFile } from "node:fs/promises";
import type { FeedItem } from "./gate.js";

/**
 * Prowlarr's own v1 API, NOT the torznab XML endpoint. Two reasons: it returns
 * JSON (no XML parser exposed to third-party tracker content), and it exposes
 * `imdbId` directly — which is the natural key the gate needs and the single
 * reason it can decide anything at all. Sampling showed imdbId present on 50 of
 * 50 articles.
 */
const PROWLARR = process.env.PROWLARR_URL ?? "http://100.123.250.67:9696";
const QBIT = process.env.QBIT_URL ?? "http://100.123.250.67:8080";
const PROWLARR_XML = "/home/mk/grey-media/config/prowlarr/config.xml";
const QBM_CONFIG = "/home/mk/grey-media/config/qbit-manage/config.yml";

/** HDBits. Not Karagarga — unresolved datacenter-IP exposure, bead sylveste-e3fh. */
const INDEXER_ID = 1;

export async function prowlarrKey(): Promise<string> {
  const xml = await readFile(PROWLARR_XML, "utf8");
  const m = xml.match(/<ApiKey>([^<]+)<\/ApiKey>/);
  if (!m) throw new Error(`no <ApiKey> in ${PROWLARR_XML}`);
  return m[1]!.trim();
}

/** qbit-manage's config is the single source of truth for the qBittorrent password. */
export async function qbitPassword(): Promise<string> {
  const text = await readFile(QBM_CONFIG, "utf8");
  let inBlock = false;
  for (const line of text.split("\n")) {
    const s = line.trim();
    if (s.startsWith("qbt:")) {
      inBlock = true;
      continue;
    }
    if (inBlock && line.length > 0 && !/^[ \t#]/.test(line)) break;
    if (inBlock && s.startsWith("pass:")) return s.slice(5).trim().replace(/^['"]|['"]$/g, "");
  }
  throw new Error(`no qbt.pass in ${QBM_CONFIG}`);
}

export interface ProwlarrResult {
  title: string;
  imdbId?: number;
  size?: number;
  seeders?: number;
  publishDate?: string;
  downloadUrl?: string;
  guid?: string;
  infoUrl?: string;
}

export async function fetchFeed(limit = 100): Promise<Array<FeedItem & ProwlarrResult>> {
  const key = await prowlarrKey();
  const url =
    `${PROWLARR}/api/v1/search?` +
    new URLSearchParams({
      indexerIds: String(INDEXER_ID),
      categories: "2000",
      type: "search",
      limit: String(limit),
    });
  const res = await fetch(url, {
    headers: { "X-Api-Key": key },
    signal: AbortSignal.timeout(120_000),
  });
  if (!res.ok) throw new Error(`prowlarr HTTP ${res.status}`);
  const rows = (await res.json()) as ProwlarrResult[];
  return rows.map((r) => ({ ...r, title: r.title, imdbid: r.imdbId ?? null }));
}

/**
 * qBittorrent Web API session.
 *
 * The Referer and Origin headers are not optional — qBittorrent 5.x rejects the
 * login without them, and returns 204 (not 200) on success.
 */
export class Qbit {
  private cookie = "";
  constructor(private base = QBIT) {}

  async login(): Promise<void> {
    const password = await qbitPassword();
    const res = await fetch(`${this.base}/api/v2/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Referer: this.base,
        Origin: this.base,
      },
      body: new URLSearchParams({ username: "admin", password }),
    });
    if (res.status !== 200 && res.status !== 204) {
      throw new Error(`qbit login HTTP ${res.status}`);
    }
    this.cookie = (res.headers.get("set-cookie") ?? "").split(";")[0] ?? "";
    if (!this.cookie) throw new Error("qbit login returned no SID cookie");
  }

  /**
   * Category AND tag are both `ratio-race` so the existing qbit-manage
   * priority-0 group governs the torrent — that group carries the 14-day HnR
   * floor and cleanup:false. Grabbing outside it would put a private-tracker
   * torrent under no retention policy at all.
   */
  async add(urls: string[]): Promise<void> {
    const form = new URLSearchParams({
      urls: urls.join("\n"),
      category: "ratio-race",
      tags: "ratio-race,hdbits",
      savepath: "/data/torrents/race",
      paused: "false",
    });
    const res = await fetch(`${this.base}/api/v2/torrents/add`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Referer: this.base,
        Cookie: this.cookie,
      },
      body: form,
    });
    if (!res.ok) throw new Error(`qbit add HTTP ${res.status}`);
  }

  async existingHashesByName(): Promise<Set<string>> {
    const res = await fetch(`${this.base}/api/v2/torrents/info`, {
      headers: { Referer: this.base, Cookie: this.cookie },
    });
    if (!res.ok) throw new Error(`qbit info HTTP ${res.status}`);
    const rows = (await res.json()) as Array<{ name: string }>;
    return new Set(rows.map((r) => r.name));
  }

  /**
   * Both global RSS master switches must stay false. The gate pushes torrents
   * directly; if the old regex rule were re-armed it would race the gate over
   * the same feed and reintroduce exactly the slop the gate exists to stop.
   */
  async assertRssDisarmed(): Promise<void> {
    const res = await fetch(`${this.base}/api/v2/app/preferences`, {
      headers: { Referer: this.base, Cookie: this.cookie },
    });
    if (!res.ok) throw new Error(`qbit preferences HTTP ${res.status}`);
    const p = (await res.json()) as Record<string, unknown>;
    if (p.rss_processing_enabled || p.rss_auto_downloading_enabled) {
      throw new Error(
        "REFUSING TO PUSH: qBittorrent's RSS auto-downloader is ENABLED. The old " +
          "regex rule would race this gate over the same feed. Disarm it first: " +
          "python3 /root/grey-ops/setup_rss_race.py --disarm",
      );
    }
  }
}
