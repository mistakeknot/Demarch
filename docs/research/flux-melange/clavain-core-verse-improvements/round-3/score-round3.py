#!/usr/bin/env python3
"""Round-3 assayer/scorer: append f-126..f-158 to heat-ledger.jsonl and
back-link existing entries (convergence_refs both directions, status flips)."""
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

# ---- cross-ledger linking (both directions) --------------------------------
# f-044 / f-045 raw round-0 findings now CONFIRMED by probe-1
add_refs("f-044", "convergence_refs", ["f-133", "f-137", "f-158"]); set_status("f-044", "upheld")
add_refs("f-045", "convergence_refs", ["f-134", "f-145", "f-158"]); set_status("f-045", "upheld")
# probe-0 adjudication vs f-008 / f-122
add_refs("f-008", "convergence_refs", ["f-127", "f-128", "f-130"])
add_refs("f-122", "convergence_refs", ["f-126", "f-127", "f-128", "f-129"]); set_status("f-122", "upheld")
# probe-2 registry findings vs f-033 / f-089 / f-124 / f-034
add_refs("f-033", "convergence_refs", ["f-149"]); set_status("f-033", "upheld")
add_refs("f-089", "convergence_refs", ["f-148", "f-149"])
add_refs("f-124", "convergence_refs", ["f-148", "f-149"]); set_status("f-124", "upheld")
add_refs("f-034", "convergence_refs", ["f-147"])
# earlier instances of the implemented-never-wired meta-pattern
add_refs("f-107", "convergence_refs", ["f-133", "f-158"])
add_refs("f-101", "convergence_refs", ["f-143", "f-158"])
add_refs("f-115", "convergence_refs", ["f-135", "f-142"])
add_refs("f-041", "convergence_refs", ["f-140"])

# ---- new findings -----------------------------------------------------------
ADJ = {"kind": "adjudicator",
       "agents": ["fd-canonization-safety", "fd-ecosystem-consolidation"],
       "parent_lenses": ["fd-kernel-contract", "fd-ecosystem-consolidation"],
       "source_domains": ["kernel/API boundary engineering", "platform-consolidation architecture"]}
KC  = {"kind": "lens", "agents": ["fd-kernel-contract"], "parent_lenses": [],
       "source_domains": ["kernel/API boundary engineering"]}
ME  = {"kind": "lens", "agents": ["fd-menu-engineering-triage"], "parent_lenses": [],
       "source_domains": ["restaurant menu engineering / product-portfolio triage"]}
SYN = {"kind": "synthesis", "agents": ["assayer"], "parent_lenses": [],
       "source_domains": ["cross-probe meta-synthesis"]}

def F(fid, src, claim, loc, sev, ev, nov, br, lk, cluster, conv=None, dis=None,
      taste=0, taste_kind=None, status="upheld", ij=None):
    return {"id": fid, "round": 3, "source": src, "claim": claim, "location": loc,
            "severity": sev, "evidence": ev, "novelty": nov,
            "risk": {"blast_radius": br, "likelihood": lk, "product": br * lk},
            "taste": taste, "taste_kind": taste_kind, "cluster_id": cluster,
            "convergence_refs": conv or [], "disagreement_refs": dis or [],
            "intersection_justification": ij, "status": status}

new = [
# ---- probe-0: compact-guard adjudication (f-126..f-132) ----
F("f-126", ADJ,
  "Root compact-drift guard's hardcoded KNOWN_SKILLS registry (14 entries, duplicated in gen-skill-compact.sh) contains 3 phantom paths — interflux/skills/flux-drive (renamed flux-engine, interflux@18d393e), os/clavain/skills/interserve (renamed interserve-engine, clavain@6b352a9), os/clavain/skills/brainstorming (never existed in os/clavain) — so the guard always exits non-zero and is useless as a signal.",
  "scripts/test-compact-freshness.sh:21-36 + scripts/gen-skill-compact.sh:27-42",
  "P1", "3 phantom entries verified against git history; guard permanently red", 1, 2, 2,
  "compact-drift-guard-missing", conv=["f-122"]),
F("f-127", ADJ,
  "All 15/15 Clavain SKILL.md/SKILL-compact.md pairs now fail the guard's own freshness check (round-2 measured 13/15): 9 genuine source-hash drifts + 6 pairs missing .skill-compact-manifest.json entirely; oldest drift 126 days. All 4 non-Clavain registry entries with existing dirs also fail — the compact fleet is 0% fresh, and agents load the stale compact unconditionally per the compact directive.",
  "os/clavain/skills/*/SKILL-compact.md",
  "P1", "9 hash mismatches + 6 missing manifests enumerated; 126d max drift", 1, 2, 3,
  "compact-drift-guard-missing", conv=["f-008", "f-122"]),
F("f-128", ADJ,
  "The compact-drift guard is wired nowhere: no root CI workflow mentions compact, none of Clavain's 7 workflows invoke it, and the pre-commit hook doesn't either. Broken guard + zero enforcement = compacts drift silently — f-008's effect-claim confirmed at fleet scale.",
  ".github/workflows/ + os/clavain/.github/workflows/ + scripts/pre-commit-hook.sh",
  "P1", "zero invocations across root CI, 7 Clavain workflows, pre-commit", 1, 2, 3,
  "compact-drift-guard-missing", conv=["f-008", "f-122"]),
F("f-129", ADJ,
  "The guard registry is incomplete even where dirs exist: 7 live compact pairs are uncovered (flux-engine, galiana, interserve-engine-under-old-name, lane, project-onboard, refactor-safely, upstream-sync-engine, using-tmux-for-interactive-commands). A root-level hardcoded list cannot keep pace with per-plugin renames — structural flaw, not a one-time oversight.",
  "scripts/gen-skill-compact.sh:27-42",
  "P2", "7 uncovered live pairs enumerated against on-disk dirs", 1, 1, 3,
  "compact-drift-guard-missing", conv=["f-122", "f-126"]),
F("f-130", ADJ,
  "interflux's per-plugin drift hook — the guard f-008 credited as the only working one — was deliberately deleted in canonization commit d2a1ded, then resurrected onto main via b5f537c ('rescue uncommitted deliverables') but never registered in hooks/hooks.json, so it is an inert dead file. f-008's premise is stale on both sides.",
  "interverse/interflux/hooks/check-compact-drift.sh",
  "P2", "file exists, absent from hooks/hooks.json; deletion+resurrection commits cited", 2, 1, 2,
  "canonization-partially-reverted", conv=["f-008", "f-131"]),
F("f-131", ADJ,
  "The flux-drive→flux-engine rename commit interflux@18d393e silently re-created a 310-line SKILL-compact.md — directly contradicting d2a1ded's deliberate canonization to a single SKILL.md (motivated by the compact silently dropping Phase 2.5 reaction-round orchestration). The re-created compact has no compact-mode preamble in SKILL.md and is itself stale per the checker. Canonization was half-executed, then partially reverted by accident. Verifier V6: upheld.",
  "interverse/interflux/skills/flux-engine/SKILL-compact.md",
  "P2", "310-line compact present post-rename; no preamble in SKILL.md; stale per checker", 2, 2, 2,
  "canonization-partially-reverted", conv=["f-130", "f-122"], taste=-1, taste_kind="smell"),
F("f-132", ADJ,
  "Freshness is defined as source-file hash equality with the manifest: any SKILL.md edit (even a typo fix) marks the compact stale without evidence the compact's content is wrong — maximizes false-positive pressure and trains maintainers to ignore the guard. Design critique; the mechanism is verified, the consequence is analytical.",
  "scripts/test-compact-freshness.sh:106-111",
  "P3", "hash-equality check at cited lines", 1, 1, 2,
  "freshness-hash-false-positive", conv=["f-122"], status="raw"),
# ---- probe-1: DEEPEN intercore internals (f-133..f-145) ----
F("f-133", KC,
  "f-044 CONFIRMED and worse: the lifecycle stall detector (CheckStall/CheckStalls, lifecycle.go:225-247,374-385) is dead code with zero production callers (only lifecycle_test.go); TimeoutSec is enforced only while a caller is blocked in `ic dispatch wait --timeout` (dispatch.go:299); dispatch.Poll returns nil-PID non-terminal dispatches unchanged forever (collect.go:37-39); no reaper exists for dispatches stuck spawned/running. The serving path has no stall detection at all.",
  "core/intercore/internal/lifecycle/lifecycle.go:374 + core/intercore/internal/dispatch/collect.go:37",
  "P1", "zero callers of NewRegistry/CheckStalls outside tests; Poll nil-PID path read directly", 1, 2, 3,
  "stall-detector-unwired", conv=["f-044", "f-107", "f-137", "f-158"]),
F("f-134", KC,
  "f-045 CONFIRMED with nuance: kernel replay is recovery-inert by construction — `ic run replay` refuses any run not status=completed (run_replay.go:79-82, exactly the crashed/stalled runs recovery exists for) and reexecute mode is a hardcoded stub that always exits 1 ('currently disallowed by kernel policy', lines 115,135-137). Internal hook/spawn handlers have no execution cursor, so a crash between event insert and handler completion permanently loses the handler effect (run_lifecycle.go:195-206).",
  "core/intercore/cmd/ic/run_replay.go:79 + core/intercore/cmd/ic/run_replay.go:115",
  "P1", "status guard and exit-1 stub read at cited lines; no handler cursor anywhere", 1, 2, 2,
  "replay-no-gap-check", conv=["f-045", "f-115"]),
F("f-135", KC,
  "events tail hardcodes the coordination cursor to 0 in every query (ListAllEvents/ListEvents 4th arg, events.go:126,128) and the high-water-mark loop (events.go:143-154) has no coordination case — coordination events are redelivered in every poll batch to --follow consumers and on every restart regardless of cursor; any consumer treating events as commands re-executes them. The saved/loaded 'interspect' cursor field (events.go:712-733) is never used in any query. Fix ~10 lines. Verifier V1: upheld.",
  "core/intercore/cmd/ic/events.go:126 + core/intercore/cmd/ic/events.go:128",
  "P1", "literal 0 at both call sites; no SourceCoordination case in HWM loop; dead cursor field", 2, 2, 3,
  "coordination-cursor-hardcoded-zero", conv=["f-115"]),
F("f-136", KC,
  "Scheduled dispatch is a write-only queue: `ic dispatch spawn --scheduled` and `ic scheduler submit` persist scheduler_jobs rows and return success, but scheduler.New/Start has no production caller and no `ic scheduler run` subcommand exists (scheduler_cmd.go:21-41) — jobs sit pending forever. Store.RecoverPending (store.go:110) is also never called, so even a future runner has no crash recovery wired. Verifier V2: upheld.",
  "core/intercore/cmd/ic/dispatch.go:102 + core/intercore/internal/scheduler/scheduler.go:144",
  "P1", "no caller of scheduler.New/Start; no run subcommand; RecoverPending uncalled", 2, 2, 2,
  "scheduler-write-only", conv=["f-158"]),
F("f-137", KC,
  "Auto-spawn failure is doubly invisible: the spawn handler swallows per-agent spawn errors with a Warn log and returns nil (handler_spawn.go:46-51), and run advance discards Notify's error return (run_lifecycle.go:135,205) — advance exits 0, the run sits in 'executing' with no agent, no failure event recorded, nothing retries. This is the concrete stall window behind f-044/f-133.",
  "core/intercore/internal/event/handler_spawn.go:46 + core/intercore/cmd/ic/run_lifecycle.go:205",
  "P1", "error-swallow + discarded Notify return read at cited lines", 2, 2, 2,
  "spawn-failure-swallowed", conv=["f-133", "f-044"]),
F("f-138", KC,
  "relay queryChildEvents has no run_id filter (relay.go:238-241): it relays the child DB's entire phase_events history across all runs into the portfolio run's phase_events; a missing cursor (new child, expired/deleted state key) replays full child history, durably contaminating the portfolio run's event stream with events from unrelated historical runs. Verifier V3: upheld.",
  "core/intercore/internal/portfolio/relay.go:238",
  "P1", "query lacks run_id predicate at cited lines", 2, 2, 2,
  "relay-no-run-id-filter"),
F("f-139", KC,
  "mapChildEventType collapses every unknown child event type to child_advanced via the default branch (relay.go:87-98) — gate failures, custom events, or any future child event type silently become 'advanced'; relayed rows carry child from/to phases but run_id=portfolioID (relay.go:177-182), so portfolio consumers cannot distinguish real portfolio transitions from relayed child noise.",
  "core/intercore/internal/portfolio/relay.go:87",
  "P2", "default-branch mapping and run_id stamping read at cited lines", 2, 1, 2,
  "relay-type-collapse", conv=["f-138"]),
F("f-140", KC,
  "Portfolio dispatch limit silently disables when the relay is down: checkPortfolioDispatchLimit 'degrades gracefully' to not-enforced with only a slog.Warn when the relay-maintained active-dispatch-count key is missing/stale (dispatch.go:706-710) — same inert-enforcement pattern as the settled nil-recorder budget finding (f-041/f-077).",
  "core/intercore/cmd/ic/dispatch.go:706",
  "P2", "graceful-degrade branch read at cited lines", 1, 2, 2,
  "enforcement-degrades-silent", conv=["f-041", "f-077", "f-138"]),
F("f-141", KC,
  "MIGRATION.md landmine: the kernel's own live-stats path still reads /tmp/clavain-dispatch-<pid>.json (collect.go:46), so the Phase-3 cleanup the doc prescribes (rm /tmp/clavain-dispatch-*.json, MIGRATION.md:77) silently freezes turns/commands/messages updates — Poll swallows the read error (collect.go:47) — and `ic compat status` will perpetually report dispatch as LEGACY=yes because the kernel itself is the legacy writer.",
  "core/intercore/internal/dispatch/collect.go:46 + core/intercore/MIGRATION.md:77",
  "P2", "tmp-file read + swallowed error at cited lines; MIGRATION.md cleanup step quoted", 2, 1, 2,
  "migration-cleanup-landmine"),
F("f-142", KC,
  "events tail cursor TTL defaults to 24h for non-durable consumers (cursorTTL, events.go:749-754): a consumer down >24h loses its cursor silently and restarts at 0, triggering a full-history replay into possibly non-idempotent consumers with no warning or machine-readable signal.",
  "core/intercore/cmd/ic/events.go:753",
  "P2", "cursorTTL default read at cited lines", 2, 2, 2,
  "cursor-ttl-silent-loss", conv=["f-115", "f-135"]),
F("f-143", KC,
  "Audit chain is stronger than 'write-only': it is never written and never verified — VerifyIntegrity (audit.go:214) and audit.New/Logger.Log have no callers anywhere in cmd/ or internal/ outside audit_test.go; the audit_log table (schema.sql:366) is dead schema and the whole tamper-evident package is dead code. Verifier V4: upheld.",
  "core/intercore/internal/audit/audit.go:214",
  "P3", "zero non-test callers; dead schema table cited", 1, 2, 1,
  "audit-chain-dead", conv=["f-045", "f-101", "f-158"]),
F("f-144", KC,
  "Replay input capture silently no-ops when run_replay_inputs is missing or the FK fails (replay_capture.go:33-36): replay fidelity degrades with no error, so `ic run replay inputs` can under-report without anyone knowing.",
  "core/intercore/internal/event/replay_capture.go:33",
  "P3", "silent no-op branch read at cited lines", 2, 1, 2,
  "replay-capture-silent-noop", conv=["f-134"]),
F("f-145", KC,
  "BuildTimeline drops coordination, review, discovery, and agency events from the 'deterministic' timeline (reconstruct.go:36 keeps only phase+dispatch sources): lock acquisitions and gate-adjacent events that influenced decisions are absent from the replay record — the completeness gap behind f-045 made concrete.",
  "core/intercore/internal/replay/reconstruct.go:36",
  "P3", "source filter read at cited line", 1, 1, 2,
  "replay-no-gap-check", conv=["f-045", "f-134"]),
# ---- probe-2: cold-fleet census, fd-menu-engineering-triage (f-146..f-157) ----
F("f-146", ME,
  "Load-bearing dog: DEPRECATED interfluence (README: 'Replaced by intervox') is wired into the installer's plugins.optional list so install-codex-interverse.sh can install it, and it is currently installed in Claude Code — while the successor intervox is installed nowhere and appears in no rig profile. The machinery actively serves an item the kitchen stopped cooking. Verifier V5: upheld.",
  "os/Clavain/agent-rig.json:124",
  "P1", "rig optional list + installed_plugins.json + interfluence README deprecation notice", 2, 2, 3,
  "retirement-never-executed", conv=["f-152", "f-034"]),
F("f-147", ME,
  "Ghost install: intersense was ARCHIVED 2026-03-26 (ARCHIVED.md, no .claude-plugin/plugin.json) yet remains installed in Claude Code (intersense@interagency-marketplace in installed_plugins.json + cache) — an archived plugin still occupies a slot on the menu. f-034's archived-not-buried pattern now reaches the live install surface.",
  "interverse/intersense",
  "P1", "ARCHIVED.md + missing plugin.json + live install entry verified", 1, 2, 2,
  "intersense-archived-not-buried", conv=["f-034", "f-148"]),
F("f-148", ME,
  "Registry lie: interflux's marketplace description still says 'Domain detection via intersense, knowledge via interknow' — intersense was archived in March; the registry advertises a dependency that no longer exists.",
  "core/marketplace/.claude-plugin/marketplace.json",
  "P2", "marketplace.json description quoted against ARCHIVED.md date", 1, 1, 2,
  "routing-ghosts-cold-spots", conv=["f-147", "f-089", "f-124"]),
F("f-149", ME,
  "f-033 CONFIRMED on the cold fleet: 7 plugin dirs missing from marketplace.json — interboxd, intercept, intergraph, interscout, intersense, intersite, lattice (plus _shared support dir). Two of them carry runtime machinery invisible to all install/discovery paths: intercept's adaptive-gate runtime and lattice's SessionStart reharvest hook.",
  "interverse/",
  "P2", "7 unlisted dirs enumerated against marketplace.json", 1, 2, 2,
  "routing-ghosts-cold-spots", conv=["f-033", "f-089", "f-124"]),
F("f-150", ME,
  "Deprecated-but-listed: intervoice entry still published in marketplace.json at v0.1.1 with '[DEPRECATED — use intervox]' description — a dog kept on the printed menu; retirement should mean removal from marketplace, not a footnote.",
  "core/marketplace/.claude-plugin/marketplace.json:1051-1068",
  "P2", "entry read at cited lines", 1, 1, 2,
  "retirement-never-executed", conv=["f-146", "f-152"]),
F("f-151", ME,
  "Dog on auto-start: intercache is in the rig mcp profile and installed, so its MCP server launches every session, but it ships 0 skills/commands, its post-commit hook is unregistered (no hooks.json in plugin.json), and no consumer is documented — kitchen capacity consumed with no evidence of orders.",
  "interverse/intercache",
  "P2", "rig mcp profile membership + plugin.json hook absence + skill census", 2, 1, 3,
  "mcp-autostart-no-consumer"),
F("f-152", ME,
  "Hidden star shelved: intervox (tested closed-loop voice engine, 52 tests, supersedes two deprecated plugins) is in the marketplace but absent from every rig profile and installed nowhere — the successor lost the slot to its own deprecated predecessor.",
  "interverse/intervox",
  "P2", "52 tests counted; zero rig/install presence verified; flip side of f-146", 1, 1, 2,
  "puzzle-no-placement-strategy", conv=["f-146", "f-150"]),
F("f-153", ME,
  "Dead weight on disk: interscout deprecated 2026-04-27 ('pre-public, early enough to retire cleanly') but the repo dir still sits in the fleet — retirement announced, never executed.",
  "interverse/interscout",
  "P2", "deprecation notice + live dir verified", 1, 1, 1,
  "retirement-never-executed", conv=["f-146", "f-150"]),
F("f-154", ME,
  "Puzzle cluster: four real implementations (interseed full MCP server; interdeploy 3-cycle auto-fix loop; interloop proof-loop; interlore philosophy observer) published in marketplace but present in zero rig profiles and zero installs — unpromoted items with no placement strategy.",
  "interverse/interseed, interverse/interloop, interverse/interlore, interverse/interdeploy",
  "P2", "marketplace-listed; zero profiles/installs verified per plugin", 2, 1, 2,
  "puzzle-no-placement-strategy", conv=["f-152"], status="raw"),
F("f-155", ME,
  "Duplication/overlap risk flagged, not confirmed: intercept (adaptive decision gates) overlaps Clavain's own scripts/gates/; interstate (LLM-legibility) overlaps interwatch/interdoc doc surfaces; lattice (ontology graph) overlaps intergraph (ecosystem graph) and canongraph (entity graph) — three graph plugins with no documented boundary.",
  "os/Clavain/agent-rig.json",
  "P3", "overlap inferred from plugin charters; no consumer-level verification", 2, 2, 1,
  "undocumented-capability-overlap", status="raw"),
F("f-156", ME,
  "Interbrowse ships 8 skills + 2 agents and is installed, but has no README and zero skills linked into ~/.agents/skills — inventory without signage; demand unverifiable.",
  "interverse/interbrowse",
  "P3", "skill count vs zero live symlinks verified; demand claim analytical", 1, 1, 1,
  "demand-unverifiable-no-surface", status="raw"),
F("f-157", ME,
  "Single-patron items: intersite (GSV portfolio site generator) and interboxd (personal Letterboxd discovery) are personal-project plugins off-marketplace — fine as experiments, but they dilute the fleet census and should live outside the interverse menu or be clearly marked personal.",
  "interverse/intersite, interverse/interboxd",
  "P3", "off-marketplace status verified; dilution claim analytical", 1, 1, 1,
  "personal-plugins-on-fleet-menu", status="raw"),
# ---- assayer synthesis (f-158) ----
F("f-158", SYN,
  "META-FINDING — implemented-never-wired: four fully implemented and tested intercore subsystems (lifecycle stall detector f-133, scheduler engine + crash recovery f-136, audit chain f-143, plus replay reexecution f-134) have zero production callers — each merged without the CLI wiring commit. The pattern extends beyond intercore (compact guard unwired f-128, inert-config lever f-107, dead gate-audit emitter f-101): this is a landing-process gap, not four independent oversights. Highest-leverage single fix: one `ic sweep`/`ic doctor --fix` command wiring dispatch.Poll-based reaping + lifecycle CheckStalls, converting all silent wedges into observable, contract-visible state.",
  "core/intercore (cross-cutting: lifecycle, scheduler, audit, replay)",
  "P1", "four verifier-stamped instances (V1-V4 confirmations) + three prior-ledger instances", 3, 3, 3,
  "implemented-never-wired", conv=["f-133", "f-136", "f-143", "f-134", "f-128", "f-107", "f-101"]),
]

ids = [f["id"] for f in new]
assert ids == [f"f-{n}" for n in range(126, 159)], ids
assert not any(i in by_id for i in ids), "id collision"

rows.extend(new)
LEDGER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

# stats
seen = set(r["cluster_id"] for r in rows[:125])
newc = {f["cluster_id"] for f in new} - seen
print(f"appended {len(new)} findings f-126..f-158")
print(f"new clusters: {len(newc)} -> rate {len(newc)/len(new):.2f}")
print(sorted(newc))
