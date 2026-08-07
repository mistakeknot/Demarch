---
artifact_type: melange-synthesis
method: flux-melange
target: "Sylveste: os/Clavain + core/intercore + interverse"
target_description: "Three plugin layers of the Sylveste autonomous-dev-agency ecosystem"
goal: "identify high leverage opportunities for improvement across the Clavain, intercore, and interverse plugins"
weights: balanced
rounds_run: 4
halt_reason: CEILING
total_fusions: 3
emergent_findings: 6
date: 2026-08-05
---

# Melange Synthesis: Clavain × intercore × interverse

The eye of distance. 192 findings (f-001..f-192) from 9 lenses (6 base, 3 fused) across a seed round and 4 adaptive rounds. Final ledger state: 145 upheld, 44 raw, 3 refuted. Halt: CEILING at max_rounds=4 with budget 8/30 unspent — the loop stopped on the round cap, not on dryness (round-4 yield was 9, novel_cluster_rate 0.24).

**Re-scoring note.** The per-round novelty/risk scores were fast triage estimates. On re-score I kept the ledger's risk decompositions (they were verifier-stamped, not guessed) but normalized novelty: round-0 seed findings were systematically scored novelty 2 by convention, which flattened the head of the distribution. The re-scored heat ranking (novelty × risk.product) below is what every view in this document uses. The material changes: f-038 (lock fuse) drops out of the top heat band (novelty 2 × 9 = 18, not a 27-peer of the emergent findings); f-086 and f-120 hold novelty 3 on the strength of their emergence-gate verdicts; f-101 (dead gate-audit emitter) earns its novelty 3 — it is the kind of defect (a call to a subcommand that has never existed, error discarded) that only surfaces on adversarial re-read. No finding moved more than one novelty point. Severity is retained for reference only and never sorts anything in this document.

**If you read one thing:** **f-184** — *replay certifies the curve with holes* (heat 27, novelty 3 × risk 9, emergent from fd-firing-witness). `ic run replay` gates only on `run.Status==completed`, builds its timeline from whatever events exist, and exits 0 in simulate mode with no completeness check. A run executed through the 15 nil-recorder dispatch paths replays "successfully" with only phase events, and `reconstruct.go:36` silently drops coordination/review/discovery sources even when they were recorded. The certification instrument converts a known instrumentation gap into a false certificate that recovery and re-execute gating will trust. It is the run's top finding because it is the point where every other kernel finding compounds: fix the nil recorders without fixing replay and you have built a machine that manufactures confident lies. Runner-up at equal heat: f-158 (the implemented-never-wired meta-finding), which is the highest-leverage single *fix* — see the program below.

---

## 1. Novelty×Risk Frontier

The Pareto front over upheld findings on (novelty, risk.product). The front has four tiers:

| tier | novelty × risk.product | findings |
|---|---|---|
| apex | 3 × 9 | **f-184, f-158, f-084, f-029** |
| | 2 × 9 | **f-038** |
| | 1 × 9 | f-049, f-063 |
| | 0 × 9 | f-094 |

(Findings at novelty 3 with risk 6 — f-188, f-173, f-120, f-101, f-086 — are dominated by the apex tier on the front strictly, but two of them lead below because the frontier view exists to surface what a severity sort buries.)

### Lead A — max-novelty / mid-risk: f-188 (novelty 3, risk 6)

**Claim:** The audit chain, wired naively, *manufactures* false tamper verdicts. `audit.New()` snapshots `lastHash`/`sequenceNum` into memory (audit.go:81-127); two CLI processes producing transitions for the same run both read prev_hash=H and both write sequence n+1 — a chain fork that `VerifyIntegrity` reports as "sequence gap"/"hash chain broken" on an honest firing. Spurious alarms retrain operators to ignore the verifier; real tampering later gets dismissed as "the fork bug again." The witness devalues the entire record's authority.

**Lens:** fd-firing-witness (fd-kernel-contract × fd-anagama-thermal-state), verifier V1-stamped emergent, round 4.

**Risk decomposition:** blast 3 (the audit chain is positioned to become the ONE cross-layer witness for the gate-trace remediation — its corruption poisons the trust basis of every later decision) × likelihood 2 (**contingent**: the audit package is never imported today — f-143 — so the catastrophe only materializes when the f-158 wiring remediation lands *and* lands naively). Severity P1, for reference only.

This is where the run's buried catastrophe surfaces. The ledger contains no literal blast-3 × likelihood-1 finding — every ancestor of this one (f-143 "audit chain is dead code," severity P3) framed the audit package as *harmless* dead code. The fused lens caught what the ancestors buried: the harm is not in the dead code, it is in the *contingent resurrection* — the one remediation everyone is about to execute is precisely the one that arms the false-tamper generator. A finding whose blast is 3 and whose likelihood is gated on your own fix is the finding every severity-sorted report drops to page three.

### Lead B — mid-novelty / max-risk: f-038 (novelty 2, risk 9)

**Claim:** The filesystem lock has a 5-second staleness fuse. `tryBreakStale` breaks any lock purely by `owner.json` age — no heartbeat, no PID-liveness check — so mutual exclusion does not exist for any dispatch longer than 5 seconds. `pidAlive` exists one file over and is wired only into `Clean`, never the acquire/break path, and `TestStaleBreaking` actively pins the bad behavior as correct (f-063). The sole production lock holder is Clavain's sprint-claim, bought precisely to prevent a TOCTOU double-claim (f-066).

**Lens:** fd-anagama-thermal-state (seed), confirmed and deepened by fd-kernel-contract probes in round 1 (f-063, f-064, f-066).

**Risk decomposition:** blast 3 (every concurrent dispatch across every host that shares the lock directory; the bash fallback path never breaks stale locks at all, so behavior diverges by implementation — f-065) × likelihood 3 (any dispatch >5s trips it; that is most dispatches). Severity P0, for reference only — and here severity and heat agree, which is exactly why this needs no headline: it is the commodity catastrophe, fully converged (f-038/f-063/f-064/f-066), and its fix is ~small.

The frontier's two leads are the run in miniature: the loudest danger is a five-line kernel bug anyone can fix this week; the quietest danger is a trust-erosion machine that only switches on when you do the *right* thing carelessly.

## 2. Top Fusions

Six emergent findings no single lens could produce, from three fused lenses. **Zero-emergent fusions: none — 3/3 fusions produced emergent findings** (no negative results to report). Ranked by novelty×risk.

### 1. f-184 — replay false certificate (heat 27)
**Parents:** fd-kernel-contract × fd-anagama-thermal-state (fd-firing-witness). **Emergence gate:** V1, genuine emergent, novelty floor 3.
**Intersection justification:** Contract alone calls the sparse timeline correct-per-schema; firing alone cannot see the 15/16 event gap is wiring, not kiln accident. Only the intersection catches the certification instrument converting a known instrumentation gap into a false certificate later decisions trust.
**Evidence:** full reads of `run_replay.go:79-107` + `reconstruct.go:36`; gates only on Status==completed; no events_expected vs events_found; simulate exits 0 regardless.

### 2. f-084 — exemplar misdeclaration (heat 27)
**Parents:** fd-lifecycle-drift × fd-scriptorium-transmission (fd-provenance-drift). **Emergence gate:** upheld as emergent, frontier #1 tie at round 1.
**Intersection justification:** Lifecycle contributes "clones up-to-date with origin, pull --ff-only clean, doctor green" — machinery working exactly as designed; stemmatics contributes that the exemplar was silently re-declared (GitHub published line vs Sylveste/zklw living line). Lifecycle alone never questions *which* remote is the exemplar; stemmatics alone cannot see the exemplar choice is an install-path constant.
**Evidence:** `plugin_repo_url` hardcodes github.com/mistakeknot (install-codex-interverse.sh:322-324,905); all 39 clones report behind=0 vs origin while 20/37 lag their Sylveste source versions (interwatch 0.3.3 vs 0.6.1, interflux 0.2.52 vs 0.2.86, interpulse 0.1.5 vs 0.1.10).

### 3. f-188 — audit-chain false tamper (heat 18)
**Parents:** fd-kernel-contract × fd-anagama-thermal-state (fd-firing-witness). **Emergence gate:** emergent novelty 3 (trust-erosion path).
**Intersection justification:** Contract parent frames "verifier cannot distinguish fork from tamper" as contract defect; firing parent holds the firing log's authority as the asset outliving any firing. Neither alone produces the emergent harm: spurious alarms retrain the humans who are the final consumer of the tamper signal.
**Evidence:** full read of audit.go; `loadLastEntry` race traced at audit.go:81-127; VerifyIntegrity at :214-280; audit package confirmed never imported (V4).

### 4. f-120 — twin guard double-blind (heat 18)
**Parents:** fd-kernel-contract × fd-ecosystem-consolidation (fd-canonization-safety). **Emergence gate:** V2, genuine emergent.
**Intersection justification:** Consolidation alone picks the repo-local "source" (core) as canonical — the wrong one; contract analysis alone finds each call site internally consistent; only the intersection reveals the executed contract and archived template diverged in *opposite directions per function*, so neither copy can be canonized wholesale, and the guard that should pin this observes nothing.
**Evidence:** both copies stamp INTERCORE_WRAPPER_VERSION 1.1.0 over 266 diff lines; the only sync check points at `../../hub/clavain/hooks/lib-intercore.sh`, dead since the hub/clavain→os/Clavain move; consumer census: all 9 runtime hooks execute the Clavain copy, only test-integration.sh executes the core copy; sentinels fail open in Clavain/fail closed in core while state ops invert.

### 5. f-086 — gitleaks colophon orphaning (heat 18)
**Parents:** fd-lifecycle-drift × fd-scriptorium-transmission (fd-provenance-drift). **Emergence gate:** verifier-upheld genuine-emergent.
**Intersection justification:** Lifecycle contributes the guard logic (marker-grep protects local edits — a sound overwrite-safety rule doing exactly what it was told); stemmatics contributes that a colophon naming a dead scriptorium makes an identical text "foreign," so the provenance stamp itself — not any content difference — is the drift vector. Lifecycle alone sees 37 correctly-protected unmanaged files; stemmatics alone sees one renamed comment line with no functional effect.
**Evidence:** the demarch→sylveste marker rename orphaned 37 byte-identical validators; `is_managed_file` greps only the new marker; all 47 copies hashed; every future template change propagates to only 10/47 of the fleet.

### 6. f-083 — upstream deletion amnesia (heat 12)
**Parents:** fd-lifecycle-drift × fd-scriptorium-transmission (fd-provenance-drift). **Emergence gate:** upheld emergent novelty 3 (risk 4 caps its heat).
**Intersection justification:** Lifecycle contributes the mechanism reading (diff-window + pointer advance = "sync succeeded, nothing to do"); stemmatics contributes the corpse (a folio whose exemplar was burned but which the concordance still lists as living); neither alone suffices — lifecycle sees a green sync run, stemmatics alone cannot see that the pointer-advance machinery certifies the orphaned copies as converged.
**Evidence:** status==D files silently skipped, then `lastSyncedCommit` advances unconditionally (sync-upstreams.sh:750-752,953-963; clavain_sync/__main__.py:126-127,228-229); 39/65 dead fileMap targets verified on disk (f-179).

## 3. Taste Calls

Taste annotations are sparse this run: **zero +taste findings** and seven [t]-flagged −1 smells. Reported as found.

### +taste — elegance to preserve (none annotated; two implicit, named with low confidence)
The ledger's taste axis ran negative-only. The closest thing to positive elegance the run recorded, in structure rather than annotation:

- **f-110 (taste_kind: form-follows-function, implicit).** The correct durable-consumer contract is *already written* in intercore-vision.md:336-349 — read-only tail, explicit `ic events cursor set`, durable vs ephemeral cursors, prune with durable-cursor protection. The elegant move the evidence supports is converge-code-to-vision, not new design. Preserve: the vision doc as the single design surface.
- **f-097 (taste_kind: right-constant, implicit).** `install.sh`'s `find_local_clavain_source()` prefers the local Sylveste checkout over any remote — the one place in the install fleet that declares the exemplar correctly. This is the pattern f-100's fix generalizes; it is worth naming as the exemplar *of* exemplar routing.

### −taste — smells to fix (all taste_kind: smell, −1)
Ranked by heat:

1. **f-052 — dead automation is worse than none** (heat 8). `codex-auto-refresh.sh` has no crontab entry, no LaunchAgent, and its refresh log was never written — while docs imply freshness. The smell is the *confidence* the corpse confers.
2. **f-104 — the '(audited)' overclaim** (heat 4). The CLAVAIN_SKIP_GATE block message prints "(audited)" exactly when the gate is being bypassed and no audit record is written on either path. A user-facing lie at the precise moment of weakening.
3. **f-131 — canonization half-executed, then reverted by accident** (heat 8). The flux-drive→flux-engine rename commit silently re-created a 310-line SKILL-compact.md directly contradicting d2a1ded's deliberate canonization to a single SKILL.md — and the re-created compact is itself stale.
4. **f-054 / f-098 — split-brain routing, both machines** (heat 4/8). Three ~/.agents/skills links point at canonical Sylveste trees while 44 siblings point at ~/.codex snapshots, no documented rule, an agent cannot tell which regime it is reading; zklw replicates the pattern *plus* a third undeclared Clavain lineage at ~/projects/Clavain.
5. **f-125 — version-stamp schizophrenia** (heat 2, raw). Three version witnesses (header comment 0.1.0 with a dead provenance path, machine stamp 1.1.0, docs citing 0.4.0/0.6.0) plus two function-count witnesses — no consumer can tell which string IS the contract version.
6. **f-037 — root-bound interlab folios** (heat 2, raw). A finished campaign report and 8 harness scripts unlinked at the Clavain repo root, citing a since-renamed file.

## 4. Convergence Spine

flux-review's signal, kept but demoted: high convergence = high confidence, low novelty. This is the commodity you can trust — one section, not the headline. Ranked by convergence_refs count:

- **f-158 implemented-never-wired (10 refs)** — four tested intercore subsystems (stall detector f-133, scheduler f-136, audit chain f-143, replay reexecution f-134) with zero production callers; the pattern extends to the compact guard (f-128), inert config (f-107), and the dead gate-audit emitter (f-101). A landing-process gap, not four oversights.
- **f-084 exemplar misdeclaration (10 refs)** — the GitHub-exemplar constant confirmed from five independent angles (f-093..f-097, f-099) across two machines.
- **f-075 gate-mode self-weakening (8 refs)** — the code-enforced lever is project-level `.clavain/agency-spec.yaml`; 27 weakening-resolution sites, 23 leaving zero durable trace (f-102).
- **f-029 skills-symlink apocrypha (8 refs)** — 44/47 routing links resolve to stale snapshots; adjudicated and substantiated (f-049).
- **f-039 dispatch-event recording gap (7 refs)** — nil recorders at all 9 CLI dispatch subcommands plus six more construction sites; `ic run advance` is the only path that records.
- **f-018 event-delivery at-most-once (6 refs)** — cursor advances on stdout write; the whole batch drops on consumer crash; TTL undocumented.
- **f-101 dead gate-audit emitter (7 refs)** — `emitInterspectEvent` calls `ic events add`, a subcommand that has never existed; the error is discarded by `_, _ =`.
- **f-014 drift-detection coverage gap (7 refs)** and **f-122/f-127/f-128 compact-drift cluster (7 refs)** — the compact fleet is 0% fresh (15/15 Clavain pairs fail, max drift 126d) and the guard is wired nowhere.

These are safe to assign to any competent pair of hands. They do not need another lens; they need commits.

## 5. Live Disagreements

**None remain open.** All three disagreements this run were adjudicated and RESOLVED:

1. **f-029 × f-014 (skills routing, round 1, probe-0-adjudicator):** both-partially-right — f-029 substantiated (44/47 links resolve to stale snapshots, non-default-profile clones frozen at 2026-03-24); f-014's "covered install cache" frame holds only for the clavain clone (f-049).
2. **f-008 × f-122 (compact-drift guard, round 3, verifier V6):** f-008's existence-claim refuted (a root guard exists and lists 8 Clavain skills) but its effect-claim stands (guard is broken, unwired, incomplete; interflux's own hook is a dead unregistered file — f-130); f-122 holds in full. Resolution on record: canonize to single SKILL.md per the interflux d2a1ded pattern.
3. **f-028 × f-083 × f-090 (upstreams.json, round 4, verifier V4):** prune + shrink ruling — f-028's staleness upheld in full on disk audit (39/65 dead targets, including RELOCATED ones — f-179); the resurrection mechanism stays refuted but demoted to "incidentally prevented" (the guard is presence-based, not intent-based — f-181); deletedLocally is a reader-with-no-writer (f-180); the 3-step migration is on record (f-183).

---

## Appendix A — Spice Trail

How the loop moved. Yields are findings-per-round; novel_cluster_rate is the fraction landing in new clusters.

**Round 0 (seed) — yield 46, novel_cluster_rate 0.96.** Six base lenses fanned across the three layers: fd-ecosystem-consolidation (duplication), fd-lifecycle-drift (release engineering), fd-kernel-contract (kernel/API boundary), fd-scriptorium-transmission (textual transmission), fd-anagama-thermal-state (irreversible transitions), plus the adjudicator. Produced the raw material everything else mined: the lock fuse (f-038), nil recorders (f-039), symlink apocrypha (f-029), upstreams palimpsest (f-028), and the P0 publish-state claim (f-017) that round 1 would cut down.

**Round 1 — yield 19, novel_cluster_rate 0.39.** Directives: PROBE-DISAGREEMENT on f-029×f-014 ("one is wrong, and f-029 currently leads the report"); DEEPEN on f-017 ("hand-run sqlite3 DELETE … would lead the report — confirm the mechanism"); DEEPEN on the lock/event/gate hotspot ("densest unconfirmed hotspot … five P0/P1 clusters, zero convergence"); FUSE fd-lifecycle-drift×fd-scriptorium-transmission ("both lenses hit upstreams.json with complementary root causes"). Outcomes: f-017 refuted as written (self-healing shipped June 2026; downgraded P0→P2 remainder); f-029 substantiated; the dispatch-event and lock clusters hardened; the first fusion produced the run's biggest early spice — f-084 (exemplar misdeclaration, heat 27) and f-086.

**Round 2 — yield 11, novel_cluster_rate 0.27.** Two deliberately narrow DEEPENs (novel_cluster_rate dropped by design): f-084's exemplar constant + the unprobed zklw mirror ("the zklw mirror host is unprobed — confirm the mechanism, the intent, and the mirror side"), and the gate_mode resolution surface ("the fix surface is unscoped: enumerate every gate_mode resolution site"). Plus FUSE fd-kernel-contract×fd-ecosystem-consolidation ("which copies are load-bearing divergence vs accidental, and what breaks if you canonize the wrong twin?"). Outcomes: zklw confirmed replicating the pattern (f-098); 27-site weakening inventory (f-102); f-101 (dead audit emitter, novelty 3); the second fusion produced f-120 (double-blind twin guard).

**Round 3 — yield 20, novel_cluster_rate 0.58.** The recovery round. PROBE-DISAGREEMENT f-008×f-122 ("existence-claim vs effect-claim — adjudicate what the guard should actually do"); DEEPEN the unread intercore internals ("the kernel is the highest-yield-density region this run"); STEER-WIDE into the 43-plugin cold fleet — a documented coverage exception ("novel_cluster_rate 0.27 reflects two deliberately narrow DEEPEN rounds, not target dryness") under a new distant lens, fd-menu-engineering-triage. Outcomes: the compact-guard disagreement closed; the implemented-never-wired meta-finding f-158 landed (heat 27); the fleet census produced dogs/stars placements (f-146 interfluence, f-152 intervox) and the first demand-telemetry findings.

**Round 4 — yield 9, novel_cluster_rate 0.24.** DEEPEN graph-plugin three-way ("one probe reading the three schemas either confirms a merge candidate or documents boundaries"); DEEPEN intercache consumer verification ("settles demote-or-prove"); PROBE-DISAGREEMENT upstreams.json ("last live disagreement — close it"); FUSE fd-kernel-contract×fd-anagama-thermal-state ("where the witness machinery itself corrupts the irreversible transitions it records"). Outcomes: lattice confirmed orphaned (488 tests, zero consumers — f-159); fleet MCP zero-demand pattern upheld (f-173, heat 18); upstreams adjudicated closed; the third fusion produced f-184 and f-188 — the frontier leads.

**Halt: CEILING.** Round 4 = max_rounds. Budget (8 remaining ≥ floor 3) and yield (9 > 1) would both have allowed continuation; precedence went to the round cap. The controller's own note: not BUDGET, not DRY — the loop was still finding spice (f-184 landed in the final round) when the ceiling hit.

## Appendix B — High-Leverage Improvement Program

Consolidated from the upheld findings, grouped into 10 work items, ordered by leverage (blast radius ÷ cost of fix), not by severity. Finding ids behind each item in brackets.

1. **Wire the witness spine: one `ic sweep` command plus tx-admitting witness APIs.** [f-158, f-039, f-067, f-068, f-185, f-190, f-133, f-136, f-143, f-191, f-192, f-040] Four fully implemented, tested subsystems (stall detector, scheduler, audit chain, replay) sit with zero production callers — the fix is wiring, not building, and the witness-obligation spec (f-191) and tombstone design (f-192) are already on record. Highest leverage in the program: converts every silent wedge into observable state in one pass. **Size L.**
2. **Fix the 5-second lock fuse.** [f-038, f-063, f-064, f-065, f-066] Wire the existing `pidAlive` into `tryBreakStale`, repair `TestStaleBreaking` (which pins the bad behavior), reconcile the bash/Go divergence. A P0 mutual-exclusion hole whose fix is measured in lines — the best blast/cost ratio in the ledger. **Size S.**
3. **Make replay honest before anything trusts it.** [f-184, f-045, f-134, f-144, f-145] Add events_expected vs events_found completeness checks, put sparsity in the exit code, stop dropping coordination/review/discovery sources. Must land *before* the re-execute gating that item 1 enables, or item 1 arms the false-certificate machine. **Size M.**
4. **Durable consumer contract for `ic events` — converge code to the already-written vision.** [f-018, f-110, f-119, f-135, f-186, f-187, f-113, f-116, f-117, f-072, f-112, f-142] The design exists (intercore-vision.md:336-349): read-only tail, `ic events cursor set` ack verb, prune with durable-cursor floor. Includes the ~10-line coordination-cursor-0 fix (f-135) that currently re-fires command-shaped events, and the interspect unique-index dedup (f-116). **Size M.**
5. **Gate-trace policy: every weakening leaves a witness.** [f-075, f-102, f-081, f-101, f-104, f-105, f-106, f-108, f-042, f-076, f-079, f-080] One-line fix first (`ic events add`→`record` — the dead emitter), then the 3-file policy fix on record (f-108): enforce-by-default, `gate_mode_resolved` event on every off/shadow resolution, PreToolUse Bash matcher so push/close can't bypass the stack. 27 resolution sites, 23 currently silent. **Size M.**
6. **Declare the exemplar and re-route the fleet.** [f-084, f-029, f-049, f-050, f-051, f-053, f-054, f-093, f-094, f-095, f-096, f-097, f-098, f-099, f-100, f-052, f-014, f-033, f-124, f-148, f-026, f-031] One `SYLVESTE_EXEMPLAR_ROOT` helper through the `ensure_repo` chokepoint (design on record, ~60-90 lines, 3 call sites — f-100), repoint the 44 stale symlinks, prune the still-invocable deprecated flux-research skill, delete or schedule the dead auto-refresh automation, extend drift checks to marketplace-cache and Kimi installs, and refresh the routing/index documents (PHILOSOPHY.md, PRD.md, fleet registries) in the same pass. **Size M.**
7. **upstreams.json prune + shrink migration.** [f-028, f-083, f-179, f-180, f-181, f-182, f-183, f-088, f-178, f-015] The 3-step migration is on record (f-183): prune the 39 dead fileMap entries (repoint relocated skills to their interverse owners), teach clavain_sync a shrink rule (N=3 consecutive SKIP → deletedLocally), and switch the weekly CI off the deprecated bash engine it still runs. **Size S.**
8. **Canonize per-function, not wholesale: the lib-intercore twins and the compact fleet.** [f-120, f-001, f-025, f-078, f-125, f-086, f-121, f-002, f-122, f-127, f-128, f-129, f-130, f-131, f-132, f-008] The twins diverge in *opposite directions per function* — wholesale canonization of either copy flips failure direction across all 9 hooks. Per-function reconciliation with a repointed guard; re-attach the 37 orphaned gitleaks validators via hash allowlist (naive grep-both-markers stomps intent — f-121); regenerate the 0%-fresh compact fleet and wire the guard into CI. **Size M.**
9. **Fleet menu triage: retire dogs, place stars, cut session-start cost.** [f-173, f-151, f-167, f-168, f-169, f-170, f-171, f-172, f-174, f-176, f-146, f-152, f-150, f-153, f-147, f-034, f-148, f-156, f-157] Remove the 6 zero-demand auto-start MCP servers (~1,950ms p50 + ~281MB RSS per session, measured) from the default rig; swap deprecated interfluence out and its tested successor intervox in (one-line rig change); bury intersense properly; fix the marketplace registry lies. **Size S/M.**
10. **Graph-plugin consolidation: merge lattice into intergraph.** [f-155, f-159, f-161, f-162, f-163, f-164, f-165, f-166] An 8,329-LOC orphan platform (488 passing tests, zero consumers, a SessionStart hook burning cycles on a DB nothing reads) duplicating intergraph's ingest machinery. The analytical recommendation is on record (f-163): port lattice's unique connectors (beads/interlens/architecture) into intergraph, retire the rest, publish intergraph to the marketplace, and document the canongraph boundary (distinct domain, real demand). **Size M.**

Sequencing note: items 2, 7, and the cheap halves of 9 are same-week fixes. Item 3 must precede the replay-consuming parts of item 1. Item 5's one-liner (f-101) should land before any audit wiring from item 1, and item 1's audit wiring must heed f-188 — naive wiring manufactures false tamper verdicts.

## Appendix C — Caveats

- **f-017 is refuted as written.** The P0 "hand-run sqlite3 DELETE is de-facto recovery" claim was overtaken: self-healing shipped June 2026 (`ic publish unlock` + INTERCORE_DISABLE_PUBLISH_SELF_HEAL). The downgraded remainder (stale docs/beads still prescribing the DELETE — f-056..f-059, f-062) is real but P2.
- **f-048's mechanism is refuted.** `degraded-modes.yaml` is advisory-only — no code reads it. The real self-weakening lever is project-level `.clavain/agency-spec.yaml` (f-075), which is upheld and feeds item 5.
- **f-160 is refuted.** The claimed divergent interweave checkouts were one checkout simply one commit behind — fast-forward, not a fork. Kept for audit.
- **f-028 is partial.** Staleness upheld in full (39/65 dead targets, disk-verified — f-179); the resurrection mechanism refuted (SKIP:not-present-locally holds in both engines) and demoted to "incidentally prevented" — the guard is presence-based, not intent-based (f-181).
- **The zklw probe was a single-sample, read-only pass** (round 2): 46 links sampled, no scheduler inspection beyond crontab/systemd registration, no execution of any installer or sync engine. Mirror-side conclusions (f-098, f-099) carry that confidence ceiling.
- **The interverse census used demand telemetry (usageCount)** which cannot prove MCP-specific non-use for plugins with usageCount>0: a non-zero count may reflect skill/command use while the plugin's MCP server still auto-starts unused. The zero-demand claims (f-173, f-174) are safe directionally (usageCount=0 is decisive); claims about partially-used plugins' MCP servers are not established.
