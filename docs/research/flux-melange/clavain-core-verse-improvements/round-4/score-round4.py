#!/usr/bin/env python3
"""Round-4 (FINAL) assayer/scorer: append f-159..f-192 to heat-ledger.jsonl,
back-link existing entries (convergence both directions), status flips
(f-155/f-156 -> upheld; dual-checkout finding recorded as refuted per V2),
and close out melange-state.json (should_stop=true, halt_reason=CEILING)."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "heat-ledger.jsonl"

rows = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
by_id = {r["id"]: r for r in rows}

def add_refs(rid, key, ids):
    r = by_id[rid]
    for i in ids:
        if i not in r[key]:
            r[key].append(i)

def set_status(rid, status):
    by_id[rid]["status"] = status

EC = {"kind": "lens", "agents": ["fd-ecosystem-consolidation"], "parent_lenses": [],
      "source_domains": ["platform-consolidation architecture"]}
ME = {"kind": "lens", "agents": ["fd-menu-engineering-triage"], "parent_lenses": [],
      "source_domains": ["restaurant menu engineering / product-portfolio triage"]}
ADJ = {"kind": "adjudicator", "agents": ["fd-provenance-drift", "fd-scriptorium-transmission"],
       "parent_lenses": ["fd-lifecycle-drift", "fd-scriptorium-transmission"],
       "source_domains": ["release engineering x manuscript stemmatics", "medieval scriptorium practice"]}
FW = {"kind": "fusion", "agents": ["fd-firing-witness"],
      "parent_lenses": ["fd-kernel-contract", "fd-anagama-thermal-state"],
      "source_domains": ["kernel/API boundary engineering", "anagama firing-record discipline"]}

def F(fid, src, claim, loc, sev, ev, nov, br, lk, cluster, conv=None, dis=None,
      status="upheld", ij=None):
    return {"id": fid, "round": 4, "source": src, "claim": claim, "location": loc,
            "severity": sev, "evidence": ev, "novelty": nov,
            "risk": {"blast_radius": br, "likelihood": lk, "product": br * lk},
            "taste": 0, "taste_kind": None, "cluster_id": cluster,
            "convergence_refs": conv or [], "disagreement_refs": dis or [],
            "intersection_justification": ij, "status": status}

new = [
# ---- probe-0: DEEPEN graph three-way (f-155) — fd-ecosystem-consolidation ----
F("f-159", EC, "Lattice is an orphaned platform: 49 src files / 8,329 LOC Python+Go, 42 test files (488 tests pass, re-run this probe) with ZERO external consumers — nothing imports lattice, reads .lattice/crosswalk.db, or invokes its engine; only historical docs mention it.", "interverse/lattice", "P1",
  "488/488 tests pass live; Sylveste-wide grep returns docs-only hits; off-marketplace, off-rig, uninstalled", 2, 2, 3,
  "graph-plugin-three-way-overlap", conv=["f-155"]),
F("f-160", EC, "REFUTED (verifier V2): probe claimed two divergent checkouts of github.com/mistakeknot/interweave (core/interweave @09a7f94 with src/interweave rename vs interverse/lattice @8532bd2) where 'neither is a superset'. Verifier: one checkout is simply one commit behind — fast-forward, not divergence. Kept for audit.", "core/interweave + interverse/lattice", "P2",
  "V2 refutation: 8532bd2 is a strict descendant of 09a7f94; no divergent history", 2, 1, 1,
  "graph-plugin-three-way-overlap", conv=["f-155"], status="refuted"),
F("f-161", EC, "Duplicated ingest machinery confirmed at file level: lattice's cass connector (connectors/cass.py) and tldr-code connector (connectors/tldr_code.py) re-implement what intergraph's behavior.py (session co-occurrence) and code.py (tldrs imports) already ingest — two parallel 'cass + tldrs -> SQLite graph' implementations over the same ecosystem (~2 of lattice's 8 connectors).", "interverse/lattice/src/lattice/connectors/{cass,tldr_code}.py vs interverse/intergraph/intergraph/{behavior,code}.py", "P2",
  "direct side-by-side read of all four files this probe", 1, 2, 2,
  "graph-plugin-three-way-overlap", conv=["f-155", "f-159"]),
F("f-162", EC, "Hook with no consumer: lattice's SessionStart hook (registered in kimi.plugin.json + hooks/hooks.json) background-harvests crosswalk.db on every session start inside the Sylveste monorepo — recurring session-start cost maintaining a database no agent or command queries.", "interverse/lattice/hooks/sessionstart-reharvest.sh", "P2",
  "hook registration re-read; zero crosswalk.db readers per f-159 grep", 2, 1, 3,
  "graph-plugin-three-way-overlap", conv=["f-159"]),
F("f-163", EC, "RECOMMENDATION (analytical): intergraph is the natural consolidation target — working code (22 tests pass), live DB (274 nodes / 2,332 edges), MCP registered in .kimi-code/mcp.json, interchart consumes its export. Merge lattice into intergraph (port beads/interlens/architecture connectors, skip cass/tldrs) or retire lattice outright; publish intergraph to marketplace.", "interverse/intergraph", "P3",
  "hidden-gem verification re-confirmed (tests, DB counts, interchart scan.json shape); merge plan is assayer/probe judgment", 1, 1, 1,
  "graph-plugin-three-way-overlap", conv=["f-155", "f-033"], status="raw"),
F("f-164", EC, "Intergraph partial wiring: its MCP server is registered for Kimi only (.kimi-code/mcp.json); absent from Claude Code installs, agent-rig profiles, and marketplace.json — the 'queryable from any MCP host' premise holds for exactly one host (a live instance of the f-033/f-124 ghost pattern).", "interverse/intergraph", "P3",
  "direct re-read of .kimi-code/mcp.json, agent-rig.json, marketplace.json", 1, 1, 2,
  "graph-plugin-three-way-overlap", conv=["f-033", "f-124"]),
F("f-165", EC, "Canongraph is a distinct domain with real demand — user-world memory graph (people/projects/decisions with provenance), external product, user-scope MCP in ~/.claude.json, consumed by 5 Clavain commands (/recall C3 entity-graph source) + upstream-sync-engine + ops drift-check service. NOT a merge candidate with either internal graph plugin; the three-way merge is refuted, coexistence boundary documented.", "../canongraph (external)", "P3",
  "direct re-read of ~/.claude.json registrations, Clavain command call sites, ops/canongraph docs", 2, 1, 1,
  "graph-plugin-three-way-overlap", conv=["f-155"]),
F("f-166", EC, "Marketplace asymmetry: canongraph (external) is marketplace-listed while the two internal graph plugins are not — discovery currently favors the plugin that needs it least.", "core/marketplace/.claude-plugin/marketplace.json", "P3",
  "direct re-read of marketplace.json", 1, 1, 1,
  "graph-plugin-three-way-overlap", conv=["f-033", "f-164"]),

# ---- probe-1: DEEPEN intercache (f-151) + f-156 add-on — fd-menu-engineering-triage ----
F("f-167", ME, "Intercache's plugin.json mcpServers block auto-starts the server via bash launcher in every session where installed, with no opt-in gate (401ms p50 + 36MB RSS per session).", "interverse/intercache/.claude-plugin/plugin.json:19-27", "P2",
  "direct re-read of plugin.json; cost from mcp-cold-start-breakdown-2026-04-18.md (4/4 runs)", 1, 1, 3,
  "mcp-autostart-no-consumer", conv=["f-151"]),
F("f-168", ME, "Decisive demand telemetry: intercache usageCount=0 across 20,852 recorded startups (marketplace entry; inline entry also 0 across 20,864) — installed, auto-started ~20k times, never once used. Settles f-151: DEMOTE.", "~/.claude.json pluginUsage", "P1",
  "direct read of pluginUsage counters this probe", 2, 1, 3,
  "mcp-autostart-no-consumer", conv=["f-151", "f-167"]),
F("f-169", ME, "Demand is manufactured by the installer: rig `mcp` profile (agent-rig.json:257) plus install-codex-interverse.sh:118 install intercache by default for every Clavain user — one-line removal each.", "os/Clavain/agent-rig.json:257", "P2",
  "direct re-read of agent-rig.json + install script", 1, 1, 3,
  "mcp-autostart-no-consumer", conv=["f-151", "f-168"]),
F("f-170", ME, "Intercache's shipped post-commit hook is a stub: checks `command -v intercache-mcp` then only echoes; never calls the server, not registered in plugin.json, not installed into any repo — the brainstorm's one wired consumer (2026-02-23) never landed.", "interverse/intercache/hooks/post-commit.sh", "P2",
  "direct re-read of hook body + plugin.json + brainstorm:67", 1, 1, 1,
  "mcp-autostart-no-consumer", conv=["f-151"]),
F("f-171", ME, "~/.intercache does not exist on this machine — the server has never persisted a blob despite being auto-started ~20k times. A cache with no writes and no reads is not a cache.", "~/.intercache", "P2",
  "disk check this probe: 0 bytes, directory absent", 2, 1, 2,
  "mcp-autostart-no-consumer", conv=["f-151", "f-168"]),
F("f-172", ME, "Sylveste-wide grep over all 8 intercache tool names + MCP namespaces + launcher + store path returns zero code callers outside intercache itself — hits are docs, transcripts, plans only.", "Sylveste-wide grep (8 tool names)", "P2",
  "exhaustive grep this probe", 1, 1, 2,
  "mcp-autostart-no-consumer", conv=["f-151", "f-168"]),
F("f-173", ME, "FLEET PATTERN (verifier V3 upheld): 6 installed auto-start MCP servers with usageCount=0 — intercache (401ms/36MB), interdeep (779ms/38MB), interlens (59ms/60MB), intermap (3ms/8MB, launcher broken), tuivision (190ms/97MB), tldr-swinton tldr-code (519ms/42MB) — aggregate ~1,950ms p50 + ~281MB RSS of zero-demand session-start cost per session. The rig installs the full menu by default; roughly a third has never been ordered.", "fleet mcpServers x pluginUsage", "P1",
  "cross-reference of every interverse plugin.json mcpServers block vs installed_plugins.json vs pluginUsage telemetry; V3 upheld", 3, 2, 3,
  "fleet-mcp-zero-demand", conv=["f-151", "f-168"]),
F("f-174", ME, "22 more installed interverse plugins carry usageCount=0 without MCP servers (interchart, intercraft, interdev, interdoc, interform, interleave, intermonk, intername, interpeer, interplug, interscribe, intersense, intersight, interskill, interslack, intertest, intertrace, intertree, intertrust, interjawn, interbrowse, interstate) — menu carries ~28 zero-demand items total; clutter, not process cost.", "~/.claude.json pluginUsage", "P3",
  "direct telemetry read; conservative (usageCount is plugin-level)", 1, 2, 1,
  "fleet-zero-demand-menu-clutter", conv=["f-173"]),
F("f-175", ME, "Interbrowse (f-156 add-on): installed and well-signposted (8 commands, 8 skills, rich keywords) but usageCount=0 (marketplace) / 1 (inline); exactly one documented consumer — cujgel's `interbrowse:teardown` (README.md:36, prompts/02-teardown.md:8). Signage exists, demand hasn't followed: this is a demand-generation problem (no Clavain top-of-funnel command points to it), not a demote case.", "interverse/interbrowse", "P3",
  "telemetry + consumer grep this probe; converts f-156's 'demand unverifiable' into verified-near-zero", 2, 1, 1,
  "demand-unverifiable-no-surface", conv=["f-156"]),
F("f-176", ME, "Language/launcher class is the cost driver, not any single server: Python `uv run` MCP servers cost 516ms p50 each as a class (intercache ranked #10/17 at 401ms, measured 4/4 runs) — launcher choice is the fleet lever.", "docs/research/mcp-cold-start-breakdown-2026-04-18.md", "P3",
  "measured cold-start breakdown doc, 4/4 runs", 2, 1, 2,
  "mcp-launcher-class-cost", conv=["f-173"]),
F("f-177", ME, "Confirms prior: round-3 probe-2 already recommended 'demote-or-prove intercache: remove from rig mcp profile unless a consumer is documented' — this probe supplies the consumer proof: none exists.", "round-3/probe-2/verdict.md:112", "P3",
  "direct citation; restatement for audit trail", 0, 1, 1,
  "mcp-autostart-no-consumer", conv=["f-151", "f-168"]),

# ---- probe-2: adjudicator CLOSING f-028 x f-083 x f-090 (RESOLVED) ----
F("f-178", ADJ, "Weekly CI cron (sync.yml:76-82) invokes scripts/sync-upstreams.sh --auto --no-ai directly — the engine whose own header declares itself DEPRECATED in favor of clavain_sync — bypassing pull-upstreams.sh's Python default. The tested successor (atomic state writes, structural tests) is never exercised by automation; every weekly sync PR is generated by unmaintained code whose classification semantics can silently diverge. (f-088 re-verified: still true two rounds later; verifier V4 upheld.)", "os/Clavain/.github/workflows/sync.yml:76-82", "P1",
  "full read of sync.yml; sync-upstreams.sh:4 DEPRECATED header; tests/structural/test_clavain_sync exists; V4 upheld", 1, 2, 3,
  "deprecated-engine-on-cron", conv=["f-088", "f-090"]),
F("f-179", ADJ, "Catalog staleness disk-verified: 39 of 65 fileMap targets do not exist locally — and several were not deleted but RELOCATED (systematic-debugging/test-driven-development/verification-before-completion now live under interverse/intertest/skills/, oracle refs under the standalone interpeer repo) while upstreams.json still claims Clavain paths as their sync targets. Relocation changes the fix: repoint to the new owner's sync config, not just delete. (f-028 residual, upheld in full.)", "os/Clavain/upstreams.json", "P1",
  "python3 disk audit of all 65 targets, 39 dead listed verbatim in verdict appendix; V4 upheld", 2, 2, 2,
  "upstreams-palimpsest", conv=["f-028", "f-083"]),
F("f-180", ADJ, "deletedLocally is a reader-with-no-writer channel: wired into both engines (bash DELETED: guard at sync-upstreams.sh:124; Python SKIP_DELETED at classify.py:58) but the array is empty and grep for any writer returns nothing — negative events have a consumer and no producer. (f-090 re-verified verbatim; V4 upheld.)", "os/Clavain/upstreams.json:127 + scripts/clavain_sync/classify.py:58", "P2",
  "grep for writers across os/Clavain: none; V4 upheld", 1, 2, 2,
  "upstream-deletion-amnesia", conv=["f-090", "f-083"]),
F("f-181", ADJ, "The resurrection guard is presence-based, not intent-based: SKIP:not-present-locally fires only because the file is absent. If any of the 39 stale paths is recreated for an unrelated reason, the next weekly sync re-engages the mapping and AUTO-overwrites the file with upstream content via automated PR. Latent, not live — the f-028 hazard demoted from 'impossible' to 'incidentally prevented'.", "os/Clavain/scripts/sync-upstreams.sh:315 + scripts/clavain_sync/classify.py:61", "P2",
  "direct re-read of both guard sites this probe", 1, 2, 2,
  "upstreams-palimpsest", conv=["f-028", "f-090"]),
F("f-182", ADJ, "No shrink mechanism exists in either engine: nothing removes a fileMap entry, nothing demotes a chronically-skipped entry, nothing propagates an upstream deletion into a local deletion proposal — the catalog is append-only by construction and lastSyncedCommit advances over upstream deletions each run. (Extends f-083/f-090 with the no-removal-path verification.)", "os/Clavain/scripts/clavain_sync (whole package)", "P2",
  "grep for entry-removal/demotion code paths: none found; V4 upheld", 1, 2, 2,
  "upstream-deletion-amnesia", conv=["f-083", "f-090"]),
F("f-183", ADJ, "RECOMMENDATION (analytical): prune + shrink migration in 3 steps — (1) prune the 39 dead fileMap entries (repoint relocated skills to their interverse owners' sync configs, demote true deletions into deletedLocally so the guard becomes intent-based); (2) teach clavain_sync a shrink rule (N=3 consecutive SKIP -> deletedLocally; upstream deletion -> local deletion proposal in the sync PR); (3) switch sync.yml to `python3 -m clavain_sync` and delete the bash engine after one clean cycle. Side observation: ~39 fossil SKIP lines/run desensitize weekly-PR reviewers to the SKIP category that also carries protected/deleted signals.", "os/Clavain/upstreams.json + scripts/clavain_sync + .github/workflows/sync.yml", "P3",
  "migration design is adjudicator judgment (ruling option i); desensitization claim unmeasured", 1, 1, 2,
  "upstreams-palimpsest", conv=["f-028", "f-083", "f-090"], status="raw"),

# ---- probe-3: FUSE fd-firing-witness (fd-kernel-contract x fd-anagama-thermal-state) ----
F("f-184", FW, "Replay certifies the curve with holes: `ic run replay` gates only on run.Status==completed, builds the timeline from whatever events exist, and exits 0 in simulate mode — no completeness check against the dispatches table, no events_expected vs events_found, exit code carries no sparsity signal. A run executed through the 15 nil-recorder paths replays 'successfully' with only phase events; reconstruct.go:36 also silently drops coordination/review/discovery sources, so even recorded coordination events are invisible to certification. The certification instrument converts a known instrumentation gap into a false certificate that recovery and reexecute gating will trust. (Verifier V1: genuine emergent, upheld.)", "core/intercore/cmd/ic/run_replay.go:79-107 + internal/replay/reconstruct.go:36", "P1",
  "full reads of run_replay.go + reconstruct.go; V1 upheld, novelty floor 3", 3, 3, 3,
  "replay-false-certificate", conv=["f-039", "f-045", "f-134"],
  ij="Contract alone calls the sparse timeline correct-per-schema; firing alone cannot see the 15/16 gap is wiring, not kiln accident. Only the intersection catches the certification instrument converting a known instrumentation gap into a false certificate later decisions trust."),
F("f-185", FW, "CancelByRun is a second, undocumented transition channel: bulk UPDATE ... SET status='cancelled' (dispatch.go:473-488) that bypasses UpdateStatus entirely — no per-row from/to, recorder structurally unable to fire even on the 1/16 wired path, no dispatch_events row, no replay input. The single most irreversible dispatch operation (mass-killing in-flight processes) is the one channel with zero witness on ALL 16 paths; after a CancelByRun rollback, state says cancelled while the event log asserts running/spawned. (Verifier V5 upheld.)", "core/intercore/internal/dispatch/dispatch.go:473-488", "P1",
  "full read of dispatch.go; recorder only fires in UpdateStatus; V5 upheld", 2, 2, 3,
  "dispatch-event-recording-gap", conv=["f-039", "f-184"],
  ij="Contract parent frames the DispatchEventRecorder contract violated by a sibling Store method; firing parent names the unlogged-irreversible-act. Neither alone sees that the MOST irreversible transition is the ONLY one unreachable by the witness even where wired."),
F("f-186", FW, "Coordination events are command-shaped and the cursor-0 bug arms re-execution: `.acquired`/`.released`/`.expired` read as commands ('pattern free — act now'), so a non-idempotent reactor on `ic events tail -f --consumer=<name>` (the documented pattern) commits an irreversible effect on every poll interval — duplicate dispatches, duplicate token spend, duplicate edits under a new owner. (Deepens settled f-135: the cursor bug was upheld; this enumerates WHICH events re-execute and what they commit.)", "core/intercore/cmd/ic/events.go:126,128,143-154 + internal/coordination/store.go", "P1",
  "coordination event taxonomy from store.go; cursor handling column-diff vs four sibling sources", 1, 2, 2,
  "coordination-cursor-hardcoded-zero", conv=["f-135"],
  ij="Contract alone files a cursor bug; firing alone files a re-execution hazard; only together: the re-delivered event is command-shaped, so the cursor bug commits irreversible acts rather than duplicating log lines."),
F("f-187", FW, "Same transition, two producer paths, opposite witness behavior: the inline sweep inside Reserve expires locks with an explicit 'does NOT emit events' tradeoff (store.go:82-85) while standalone Sweep DOES emit `.expired` (store.go:390-395) — and the silent path runs inside someone else's Reserve transaction, the most common path in the system. Divergent-belief outcome: a cursor-0 consumer sees acquired with no terminal event and waits forever; the DB says free and another consumer reserves and edits. Two contradictory witnesses of the same state, no rule for which to trust.", "core/intercore/internal/coordination/store.go:82-85 vs 390-395", "P1",
  "full read of coordination/store.go this probe", 2, 2, 3,
  "coordination-sweep-divergence", conv=["f-135", "f-186"],
  ij="Contract parent: `.expired` is in the EventFunc contract while delivery is conditional on internal path — undocumented semantic. Firing parent: the unlogged stoke corrupts the wait-for-release decision. Only the intersection names the divergent-belief outcome."),
F("f-188", FW, "Audit chain wired naively manufactures false tamper verdicts: New() snapshots lastHash/sequenceNum into memory (audit.go:81-127); two CLI processes producing transitions for the same run both read prev_hash=H and both write sequence n+1 — a chain fork that VerifyIntegrity reports as 'sequence gap'/'hash chain broken' on an honest firing. Spurious alarms retrain operators to ignore the verifier; real tampering later gets dismissed as 'the fork bug again' — the witness devalues the entire record's authority. Emergent trust-erosion path neither parent produces alone.", "core/intercore/internal/audit/audit.go:81-127,130-193 + VerifyIntegrity:214-280", "P1",
  "full read of audit.go; loadLastEntry race traced; audit package never imported (V4 re-confirmed)", 3, 3, 2,
  "audit-chain-false-tamper", conv=["f-143", "f-101", "f-102", "f-158"],
  ij="Contract parent frames 'verifier cannot distinguish fork from tamper' as contract defect; firing parent holds the firing log's authority as the asset outliving any firing. Neither alone: the emergent harm is trust erosion — spurious alarms retrain the humans who are the final consumer of the tamper signal."),
F("f-189", FW, "computeChecksum zeroes TraceID before hashing 'to preserve backward compatibility' (audit.go:196-201) — the one field correlating an audit entry to the run/dispatch trace sits outside the tamper evidence, so trace_id can be rewritten post-hoc on a valid chain. The specific property (cross-layer trace correlation) that would justify the audit chain as the ONE witness for f-101/f-102 is non-evidentiary.", "core/intercore/internal/audit/audit.go:196-201", "P2",
  "direct read of computeChecksum + doc comment", 2, 2, 1,
  "audit-chain-false-tamper", conv=["f-143", "f-101", "f-188"],
  ij="Contract alone accepts a documented versioned hashing policy; firing alone says provenance labels can be re-papered. Only the intersection sees the exclusion guts the exact property the one-witness design is chosen for."),
F("f-190", FW, "Both witness APIs structurally exclude the transition transaction: UpdateStatus's doc comment claims it 'records a dispatch event in the same transaction' — false; the recorder fires post-commit, fire-and-forget, and the one wired call site (run_lifecycle.go:132-134) demotes witness-write failure to slog.Debug. audit.Logger.Log has no tx-admitting variant. The interface shape (no tx admission in either witness API) makes the correct discipline unexpressible — every future subsystem wired through these APIs inherits the crash window: transition commits, process dies, witness never written.", "core/intercore/internal/dispatch/dispatch.go:236-237,299-306 + internal/audit/audit.go:130,172", "P2",
  "comment-vs-behavior diff at dispatch.go:236-237; API surface read of both witness packages", 2, 2, 2,
  "witness-api-no-tx", conv=["f-039", "f-143", "f-158"],
  ij="Contract alone fixes the comment; firing alone demands logging discipline; only the intersection names the real defect: the interface shape makes correct discipline unexpressible, so the hole is inherited by every future wiring."),
F("f-191", FW, "DESIGN SPEC (recommendation): per-subsystem witness obligations for the f-158 ic-sweep wiring, to be specified as contract before wiring, not retrofitted — (a) scheduler: persist job-transition events (enqueued->started->completed/failed/retried + pause/resume with actor+reason) in the same tx as the scheduler_jobs UPDATE, linked job_id->dispatch_id; (b) stall-detector/reaper: write dispatch_transition with reason=reaped:<evidence> inside the kill transition, else reaped is indistinguishable from natural failure; (c) coordination inline sweep: buffer per-lock .expired events inside the Reserve tx, emit post-commit; (d) scheduler pause/resume: record operator identity + reason.", "core/intercore/internal/scheduler/scheduler.go:19-37 + scheduler/store.go:57-60 + coordination/store.go:82-85 + publish/state.go:163-179", "P2",
  "scaffolds re-read (Hooks are in-memory callbacks; store.Update mutates eventlessly); obligations are fused-lens design judgment", 2, 2, 2,
  "implemented-never-wired", conv=["f-158", "f-136", "f-133"], status="raw",
  ij="Contract alone lists 'add events' as a feature; firing alone says 'log everything'; the intersection specifies WHICH transitions are irreversible-enough to require in-tx witnesses and what evidence each entry must carry."),
F("f-192", FW, "DESIGN (recommendation): ClearLocks should write a classified tombstone per deleted row — {plugin, from_ver, to_ver, phase_at_deletion, started_at, updated_at, idle_seconds, actor, reason, classification} where classification = stuck_lock_cleared vs live_publish_murdered — because the DELETE erases exactly the evidence (phase, updated_at) needed to make that distinction, and the command's contract returns only a count. Minimal shape: UPDATE phase='force_unlocked' with error=json payload instead of DELETE (ListActive's phase filter extended to exclude it), so the row itself becomes the firing-record entry. (Answers settled f-060.)", "core/intercore/internal/publish/state.go:163-179 + cmd/ic/publish.go:466-515", "P2",
  "DELETE path + return contract re-read; tombstone design is fused-lens judgment", 2, 2, 2,
  "publish-unlock-unguarded", conv=["f-060"], status="raw",
  ij="Contract alone would add a --force flag or count breakdown; firing alone says 'log the unlock'; only the intersection sees the entry's CONTENT must come from the row being deleted — the witness write must precede/replace the DELETE, not follow it."),
]

# sanity: ids sequential, no collision
assert not any(f["id"] in by_id for f in new), "id collision"
assert [f["id"] for f in new] == [f"f-{i}" for i in range(159, 193)], "non-sequential ids"

# ---- cross-ledger linking, existing side -----------------------------------
# probe-2 vs f-028 / f-083 / f-090 / f-088 (disagreement RESOLVED)
add_refs("f-028", "convergence_refs", ["f-179", "f-181", "f-183"])
add_refs("f-083", "convergence_refs", ["f-179", "f-180", "f-182"])
add_refs("f-090", "convergence_refs", ["f-178", "f-180", "f-181", "f-182"])
add_refs("f-088", "convergence_refs", ["f-178"])
# probe-0 vs f-155 / f-033
add_refs("f-155", "convergence_refs", ["f-159", "f-160", "f-161", "f-163", "f-165"])
set_status("f-155", "upheld")   # overlap confirmed + quantified; merge scope adjudicated (lattice->intergraph yes, canongraph no)
add_refs("f-033", "convergence_refs", ["f-164", "f-166"])
# probe-1 vs f-151 / f-156
add_refs("f-151", "convergence_refs", ["f-167", "f-168", "f-169", "f-170", "f-171", "f-172", "f-177"])
add_refs("f-156", "convergence_refs", ["f-175"])
set_status("f-156", "upheld")   # demand now verified (usageCount 0/1, one consumer cujgel); classification refined to demand-generation
# probe-3 vs f-039 / f-045 / f-135 / f-158 / f-060 / f-101 (+ f-134, f-143, f-136)
add_refs("f-039", "convergence_refs", ["f-184", "f-185", "f-190"])
add_refs("f-045", "convergence_refs", ["f-184"])
add_refs("f-134", "convergence_refs", ["f-184"])
add_refs("f-135", "convergence_refs", ["f-186", "f-187"])
add_refs("f-158", "convergence_refs", ["f-188", "f-190", "f-191"])
add_refs("f-136", "convergence_refs", ["f-191"])
add_refs("f-060", "convergence_refs", ["f-192"])
add_refs("f-101", "convergence_refs", ["f-188", "f-189"])
add_refs("f-143", "convergence_refs", ["f-188", "f-189", "f-190"])

rows.extend(new)
LEDGER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
print(f"ledger now {len(rows)} findings (added {len(new)})")

# ---- lens records -----------------------------------------------------------
LENSES = ROOT / "lenses"
def lens_append(name, ids):
    p = LENSES / f"{name}.json"
    d = json.loads(p.read_text())
    for i in ids:
        if i not in d["findings"]:
            d["findings"].append(i)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")

lens_append("fd-ecosystem-consolidation", [f"f-{i}" for i in range(159, 167)])
lens_append("fd-menu-engineering-triage", [f"f-{i}" for i in range(167, 178)])
lens_append("fd-provenance-drift", [f"f-{i}" for i in range(178, 184)])
lens_append("fd-scriptorium-transmission", [f"f-{i}" for i in range(178, 184)])
fused = [f"f-{i}" for i in range(184, 193)]
lens_append("fd-kernel-contract", fused)
lens_append("fd-anagama-thermal-state", fused)
print("lens records updated")
