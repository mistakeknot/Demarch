// cross-seed config TEMPLATE for grey-area. Rendered by render-config.sh on the
// host, which substitutes the two placeholders from secrets that already exist
// on grey. This template is safe to commit; the rendered config is NOT and must
// never leave /home/mk/grey-media/config/cross-seed/.
//
// Placeholders: __QBIT_PASS__ __PROWLARR_KEY__
//
// Posture: MEASUREMENT ONLY. `action: "save"` writes .torrent files to
// outputDir and injects NOTHING, so running this creates zero tracker-side
// obligation — no announce, no Hit-and-Run exposure. Flipping to
// action: "inject" is the decision that actually commits the box, and it is
// gated on the prerequisites in ops/zklw-media/cross-seed/README.md.

module.exports = {
  // --- what to match against -------------------------------------------------
  // Torznab endpoints proxied by Prowlarr. Deliberately only the two trackers
  // it is safe to cross-seed to today:
  //   1 = HDBits, 2 = TorrentLeech
  // Karagarga (indexer 3) is EXCLUDED on purpose. grey already announces 125 KG
  // torrents from a Hetzner datacenter IP against a charter that said KG seeding
  // should stay on jarmusch's home IP (bead sylveste-e3fh, unresolved). Adding
  // cross-seed announces would deepen an exposure nobody has signed off on.
  torznab: [
    "http://prowlarr:9696/1/api?apikey=__PROWLARR_KEY__",
    "http://prowlarr:9696/2/api?apikey=__PROWLARR_KEY__",
  ],

  // --- client ----------------------------------------------------------------
  // `qbittorrentUrl` is deprecated in v6; torrentClients is the current form.
  torrentClients: ["qbittorrent:http://admin:__QBIT_PASS__@qbittorrent:8080"],

  // --- what cross-seed is allowed to do --------------------------------------
  // "save" = write the .torrent and stop. Change to "inject" only after sign-off.
  action: "save",
  outputDir: "/data/cross-seeds",

  // Hardlink, never copy. Everything lives under the single /data mount
  // (/dev/md3), which is what makes this free in disk terms. Violating the
  // one-mount invariant silently turns hardlinks into full copies (2x disk) and
  // breaks *arr imports — DESIGN.md calls this the #1 misconfiguration.
  linkType: "hardlink",

  // linkDirs is intentionally ABSENT while action is "save": cross-seed rejects
  // that combination outright ("you cannot use action 'save' with linkDirs"),
  // because linking is something only the inject path does. When this flips to
  // inject, add:
  //     linkDirs: ["/data/cross-seed-links"],
  // and note the path must sit OUTSIDE outputDir/dataDirs/torrentDir — nesting
  // it under /data/cross-seeds is also rejected. Still on /data, so hardlinks
  // remain hardlinks.

  // Where the existing library actually is. Note BOTH movie roots: /data/movies
  // (4.2 TB, HDBits) and /data/Movies (72 GB, the Karagarga rips) are genuinely
  // different directories on this case-sensitive filesystem — see bead
  // sylveste-f5ly. Until that is reconciled, both must be listed or the rare KG
  // material is invisible to matching.
  dataDirs: [
    "/data/movies",
    "/data/Movies",
    "/data/tv",
    "/data/Shows",
    "/data/torrents",
  ],
  maxDataDepth: 2,

  // --- politeness ------------------------------------------------------------
  // DESIGN.md's ban firewall: never hammer trackers with bulk searches. 30s
  // between searches, and a hard cap so a first run cannot turn into a 436-
  // torrent stampede across two private trackers.
  delay: 30,
  searchLimit: 20,

  // --- matching strictness ---------------------------------------------------
  // "safe" only accepts matches it can verify are byte-identical. "risky" trades
  // false positives for volume and is not worth it on private trackers, where a
  // bad inject means seeding something that fails a hash check.
  matchMode: "safe",
  skipRecheck: false,
  includeSingleEpisodes: false,
  includeNonVideos: false,
  seasonFromEpisodes: null,
  duplicateCategories: false,

  // --- daemon behaviour ------------------------------------------------------
  // Both cadences intentionally unset: no automatic searching, no RSS polling.
  // This container does nothing until invoked by hand. Turning either on is part
  // of the same sign-off as action: "inject".
  searchCadence: undefined,
  rssCadence: undefined,

  // Do not let cross-seed manage torrent lifecycle — qbit-manage is the single
  // owner of deletion on this box (the "HnR firewall"), and two things pruning
  // the same client is how obligated torrents get removed early.
  linkCategory: "cross-seed",
  flatLinking: false,
  apiAuth: true,
  port: 2468,
  host: "0.0.0.0",
  verbose: false,
};

// Prerequisites before action: "inject" — do not flip this on a hunch:
//   1. TorrentLeech REQUIRES the seedbox be declared in the profile (DESIGN.md
//      Part 3, "Declare your seedbox on TorrentLeech (mandatory)"). Unverified.
//      TL also has STRICT HnR, 4-10 days by userclass.
//   2. Every injected torrent inherits that tracker's HnR obligation, and
//      qbit-manage must already hold the matching min_seeding_time floor.
//   3. Disable qBittorrent's tracker auto-merge first, or cross-seed produces
//      phantom announces — upload on tracker A reported to trackers B/C, which
//      reads as cheating.
//   4. Resolve bead sylveste-e3fh before ever adding Karagarga (indexer 3) here.
