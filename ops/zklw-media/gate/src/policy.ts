/**
 * The admission policy — what the gate lets through and, more importantly, why.
 *
 * Background: grey's HDBits channel used to be a qBittorrent RSS rule matching
 * on title regex. That produced a 67% slop rate (Tubi/Fawesome/FoundTV and
 * no-name 2026 filler), and it could not have done better: an RSS rule sees
 * only the release NAME, and no regex over release names distinguishes a
 * Bruno Dumont from a Tubi original. The gate exists to bring an external
 * judgment — jawncite — to bear on that decision.
 */

/**
 * Free-ad-tier streaming sources. These are an OVERRIDE, not a weight: a
 * release carrying one of these tags is rejected no matter how acclaimed the
 * underlying film is, because the tag identifies a bottom-tier encode of a
 * bottom-tier catalogue rather than something worth seeding to a private
 * tracker.
 *
 * Matched as dot/space-delimited tokens in the release name so that "Tubi"
 * cannot fire on a film actually called something like "Tubitsky".
 */
export const FREE_AD_TIER = [
  "Tubi",
  "Fawesome",
  "FoundTV",
  "Plex",
  "Roku",
  "Crackle",
  "Xumo",
  "Pluto",
  "Redbox",
  "VMX",
] as const;

const tokenRe = (tag: string) => new RegExp(`(^|[.\\s_\\-\\[])${tag}([.\\s_\\-\\]]|$)`, "i");
const FREE_AD_RES = FREE_AD_TIER.map(tokenRe);

export function freeAdTierTag(releaseName: string): string | null {
  for (const [i, re] of FREE_AD_RES.entries()) {
    if (re.test(releaseName)) return FREE_AD_TIER[i]!;
  }
  return null;
}

/**
 * Production companies whose involvement is itself a curatorial signal — the
 * studio analogue of a festival slot. Deliberately short: this is a list of
 * houses whose *whole output* is worth a look, not merely good studios.
 */
export const PEDIGREE_STUDIOS = [
  "A24",
  "Neon",
  "Mubi",
  "Janus Films",
  "The Criterion Collection",
  "Arte",
  "Why Not Productions",
  "Zentropa",
  "Film4",
  "BFI",
] as const;

/**
 * Directors always admitted regardless of what the canon lists say.
 *
 * The auto-derived allowlist (see build-pedigree.ts) covers directors who
 * already have a film in jawncite's canon, which is most of what matters. This
 * manual list is for the gap that leaves: someone whose work is clearly worth
 * grabbing but who has not yet accumulated a 1000-greatest-films entry.
 */
export const MANUAL_DIRECTORS = [
  "Bruno Dumont",
  "Abel Ferrara",
  "Lucrecia Martel",
  "Apichatpong Weerasethakul",
  "Hong Sang-soo",
  "Claire Denis",
  "Kelly Reichardt",
  "Pedro Costa",
  "Albert Serra",
  "Radu Jude",
  "Jia Zhangke",
  "Tsai Ming-liang",
  "Cristi Puiu",
  "Corneliu Porumboiu",
  "Miguel Gomes",
  "Ryusuke Hamaguchi",
  "Bi Gan",
  "Alice Rohrwacher",
  "Jonathan Glazer",
  "Paul Thomas Anderson",
] as const;

export interface GateThresholds {
  /** entity_acclaim.score at or above which a film is admitted outright. */
  minScore: number;
  /** …or membership in at least this many canonical lists. */
  minListCount: number;
}

/**
 * Tuned against the seeded corpus: 2061 entities across TSPDT 2026, Sight &
 * Sound 2022 (critics + directors), Criterion and one personal list.
 *
 * minListCount 1 is deliberate and not lax. Every list in the corpus is a
 * curated canon; appearing on even one of them is already a strong statement,
 * and requiring two would exclude the entire Criterion-only tail (films
 * Criterion chose to preserve but that never charted on an all-time poll).
 */
export const DEFAULT_THRESHOLDS: GateThresholds = {
  minScore: 0.5,
  minListCount: 1,
};

export type Decision = "ADMIT" | "REJECT";

export interface Verdict {
  decision: Decision;
  /** Machine-readable so the replay harness can assert on it. */
  reason:
    | "free_ad_tier"
    | "acclaim"
    | "pedigree_director"
    | "pedigree_studio"
    | "no_signal"
    | "no_imdb_id";
  detail: string;
}

export function reject(reason: Verdict["reason"], detail: string): Verdict {
  return { decision: "REJECT", reason, detail };
}
export function admit(reason: Verdict["reason"], detail: string): Verdict {
  return { decision: "ADMIT", reason, detail };
}

/** Feed gives `imdbid` as an integer; the natural key wants tt-zero-padded-7. */
export function imdbNaturalKey(imdbid: number | string | null | undefined): string | null {
  if (imdbid == null) return null;
  const n = typeof imdbid === "string" ? imdbid.replace(/^tt/, "") : String(imdbid);
  if (!/^\d+$/.test(n) || Number(n) === 0) return null;
  return `imdb:tt${n.padStart(7, "0")}`;
}
