---
artifact_type: flux-drive decision review
source: docs/plans/2026-04-21-auto-proceed-authz-v2.md
source_handoff: docs/handoffs/2026-04-21-authz-v2-tokens-delegation-handoff.md
date: 2026-04-21
reviewer: fd-qdqr
---

# Flux-drive Decision Review: Auto-proceed Authorization v2 Implementation Plan

## Summary

The v2 plan answers 5 explicit open questions from the handoff and pins 8 implementation tasks mirroring v1.5's proven shape. Strengths: forward-auditable token lifecycle, atomic single-use semantics, delegation chain representation with proof-of-possession. Decision quality gaps: premature commitment to linear-chain-only architecture despite DAG-ready schema; anchoring on v1.5's single project-wide key with understated v2.1 refactoring cost; depth cap of 3 treated as immutable without justification; token-string format locked into public interfaces; deprecation threshold (95% marker-file adoption) stated without evidence base. Review reveals 8 decision gaps ranging from schema lock-in (P1) to uncertainty quantification (P2).

---

## Decisions Well-Made

**Schema organization clarity:** Separate `authz_tokens` table (not column-extension of `authorizations`) is correctly justified by sig_version=2 discrimination and schema shape; the decision explicitly acknowledges but defers DAG representation, preserving forward optionality via denormalized `root_token`.

**Atomic consume contract:** Single-row UPDATE pattern with `RowsAffected()` discrimination (working around modernc.org/sqlite's CTE limitations) is well-reasoned and addresses a critical correctness property (exactly-once semantics). Concurrency test in Task 3 validates the constraint.

**Proof-of-possession in delegation:** Explicit `$CLAVAIN_AGENT_ID` match requirement (Task 3, DelegateToken signature) directly addresses brainstorm §P0.6 ship-blocker and is well-documented in the error classes.

**Token audit trail linking:** Consume events recorded as v1.5-shaped `authorizations` rows while tokens live in `authz_tokens` creates a clean separation between token lifecycle and audit events. `policy audit --tokens` can traverse the tree while preserving existing audit tools' assumptions.

**Deprecation as gradual path:** `.publish-approved` marker is not removed outright but escalated to louder warning, with explicit deferral to v2.x. Allows field migration without hard cutover. Task 6 correctly phases this.

**Early test-driven discovery:** Failing tests in Task 2 and golden-fixture tests in Task 3 (matching canonical payload examples from Task 1) create checkpoints to catch design drift early.

---

## P1 Findings: High-Risk Decision Gaps

### 1. Linear-Chain Assumption Locks In Future DAG Migration

**Severity: P1** | **Task affected: Task 3 (`pkg/authz/token.go`)** | **Lens: Reversibility of Options**

The plan defers DAG delegation to v2.x ("schema is DAG-ready; runtime is chain-only today") but implements chain assumptions directly into the runtime code. `DelegateToken` signature takes a single `parentID` string, not a slice. The `Token` struct has `ParentToken string` (singular). ConsumeToken walks UP via `parent_token` to validate scope.

**Concern:** If v2.1 or v2.x needs to support multi-parent delegation (e.g., joint-authorization or governance scenarios), migrating from single-parent to DAG requires non-trivial code rewrites: `DelegateToken` needs a new signature; scope validation becomes a dag-walk not a chain-walk; `root_token` denormalization strategy may need refinement. The schema is prepared but the runtime contracts are not. Once gate wrappers and CLI surface are built on chain assumptions, the coupling becomes harder to untangle.

**Suggested reframe:** In Task 1, add a section to `docs/canon/authz-token-model.md` explicitly documenting which runtime checks are chain-specific vs DAG-compatible. Identify which interfaces (DelegateToken, ConsumeToken signatures) would require breaking changes for DAG support. Add a note in Task 3's type definitions marking `ParentToken string` as "v2 chain-only; DAG transition will require signature change." This makes the cost of the deferral transparent at implementation time rather than discovery time during v2.1 planning.

---

### 2. v1.5's Single Project-Wide Key Anchors Trust Boundary Refactoring

**Severity: P1** | **Task affected: Task 3, Task 4** | **Lens: Sunk-Cost Anchoring + Design Coupling**

The plan states: "Same project-wide Ed25519 key signs authz rows AND tokens (v1.5 plumbing reused)." The handoff notes: "multi-agent-per-project keys" is deferred to v2.x. But v2 code directly loads the project key once and verifies all tokens against it. If v2.x needs per-agent-type keys (e.g., codex-specific vs claude-specific pubkeys), the current `LoadPubKey(projectDir)` pattern in Task 3's VerifyToken and Task 4's consume handler becomes a point-of-refactoring: you'd need a key registry keyed by `(agent_type, project)`, and `VerifyToken` would need to know which agent issued the token before it can load the right pubkey.

**Concern:** The v1.5 signing primitives are reused verbatim, but the key-lookup model is not documented as a v2-specific constraint. If a future requirement surfaces (delegation audit showing "this token was signed with Agent-X's key, but we're running as Agent-Y"), the gap between v2's assumptions and v2.x's needs is a schema change (add `signer_agent_id` column) plus code rewrites in verify paths. This is not a blocker but a deferred complexity spike.

**Suggested reframe:** In Task 1, add a "Trust Model" section to `docs/canon/authz-token-model.md` explicitly stating "v2 uses a single project-wide Ed25519 key for all token signatures within a project. This assumes all agents in the project trust the same key-holder to sign on their behalf. v2.x may split keys per agent-type, requiring a key registry and changes to verify paths." This frames the anchor as a deliberate scope boundary, not an oversight. Task 3 should add a code comment at the top of VerifyToken noting "Current implementation: single project-wide key. DAG + multi-agent keys deferred to v2.x."

---

### 3. Depth Cap of 3: Constant or Configurable Parameter?

**Severity: P1** | **Task affected: Task 2, Task 3 (`DelegateToken` runtime check), Task 4 (`clavain-cli policy token delegate`)** | **Lens: N-ply Thinking + Over-specification**

The plan pins a literal depth cap of 3: CHECK constraint in Task 2, literal `if depth > 3 { return ErrDepthExceeded }` in Task 3, and reject at CLI in Task 4. The plan offers no justification for why 3, vs 2, vs 5, vs configurable. The handoff mentions "linear delegation chain matches how sessions actually delegate today" but doesn't provide a projection of real-world delegation depth.

**Concern:** If Claude → codex → sub-codex (depth 2) becomes normal, and sub-sub-codex (depth 3) is the legal limit, then a 4th layer (depth 4) would breach the cap. The plan has no signpost criteria for "we've hit the cap in practice, time to adjust." The hard CHECK constraint means adjusting requires a schema migration; the CLI enforcement means a rebuild. This is not a breaking change but a "plan was too restrictive" discovery that requires coordination. Better to ask: is 3 a hard safety boundary (e.g., "we can't reason about trust transitivity beyond 3 hops") or a conservative default (e.g., "we've never seen >2 in the wild, so 3 is safe")?

**Suggested reframe:** In Task 1's `docs/canon/authz-token-model.md`, add a "Depth Reasoning" section: document the actual observed delegation patterns in current Sylveste sprints (Claude → codex, are there deeper chains?), state the safety assumption (e.g., "trust reasoning becomes unsafe beyond depth N due to ..."), and explicitly note "depth cap is set at 3. If deeper chains become necessary, this requires migration 035+ and CLI rebuild, so surface this gap early." In Task 3, change the check from a magic `3` to a const `MaxDelegationDepth = 3` with a comment. In Task 2, add a NOTE to the CHECK constraint. This doesn't change the implementation but makes the constraint's fragility visible.

---

### 4. Token-String Format `<ulid>.<sighex>` Locked Into Public API

**Severity: P1** | **Task affected: Task 3 (`TokenString` codec), Task 4 (`clavain-cli` output), Task 5 (gate wrappers assume format)** | **Lens: Reversibility of Format Decisions**

The plan pins: "opaque token string carried between agents is `<ulid>.<sighex>`." This format is baked into the public contract: gate wrappers read `$CLAVAIN_AUTHZ_TOKEN`, expect `<ulid>.<sighex>`, and fail on parse error. CLI subcommands output this format. The handoff notes the motivation: "opaque strings passable via env var without FS access."

**Concern:** Once any production fleet agent reads and parses `$CLAVAIN_AUTHZ_TOKEN`, changing the format requires coordinated migration across agents. If v2 ships with this format and six months later a security review finds "the `.` separator is ambiguous in some contexts" or "128-char hex is inefficient for proto serialization," changing it requires a format-version header or a breaking v3. The decision is locked in the moment the first agent in the wild parses it.

The plan does not validate that `<ulid>.<sighex>` is the best choice. Alternatives: base64 encoding (shorter, opaque), proto-serialized bytes (extensible, clear structure), URL-safe base64 + length prefix (versionable). The handoff chose `<ulid>.<sighex>` for "fits in an env var, easy to parse" — but env vars have no practical length limit (typically 256KB+), and "easy to parse" is not quantified.

**Suggested reframe:** In Task 1, add a "Token String Format" section to `docs/canon/authz-token-model.md` documenting the format choice: "(1) ULID for temporal ordering and collision-free generation, (2) sig_bytes in hex for human-readable debugging, (3) `.` separator for clear demarcation." Add a "Versioning" note: "The `<ulid>.<sighex>` format assumes no breaking changes to ULID spec or Ed25519 signature format. If a format change is needed (e.g., to support DAG parent chains or compressed encoding), a new version negotiation mechanism will be required." In Task 3, add a version marker or comment in `ParseTokenString` noting "Format is stable for v2; breaking changes deferred to v3+" This is not a blocker but prevents the format choice from being treated as accidental.

---

### 5. 95% Marker Adoption Threshold: Evidence-Based or Guess?

**Severity: P1** | **Task affected: Task 6 (`RequiresApproval` deprecation warning)** | **Lens: Uncertainty Quantification + Signposts**

The plan states: "full removal deferred to v2.x after telemetry confirms >95% approvals via tokens." This is a commitment to a future condition ("95% adoption") that triggers removal, but the plan does not define:
- How is "95% approvals via tokens" measured? (token consume events in audit log / total approval events)
- What's the baseline? (What % use markers today?)
- Over what time window? (30 days? 90 days?)
- What happens if the % plateaus at 80%?

**Concern:** Once v2.x ships with this warning, there's pressure to remove the marker path. But if the 95% threshold was a guess, not grounded in data, the removal will either happen too early (breaking late adopters) or get deferred indefinitely (leaving the code cluttered). This is a "future you will regret not pinning it" decision. The handoff mentions v1.5 landed "telemetry", but the plan doesn't reference which telemetry system, where the data lives, or who owns the v2.x removal decision.

**Suggested reframe:** In Task 1, add a "Deprecation Signpost" section documenting: "The `.publish-approved` marker is deprecated in v2. Removal in v2.x is contingent on telemetry showing ≥95% of `ic publish --patch` approvals flowing via tokens. Telemetry is collected via `authorizations` rows with `op='ic-publish-patch'` and `root_token IS NOT NULL` (token path) vs `root_token IS NULL` (marker path). Measurement window: rolling 30-day average. Decision gate: at v2.x planning time, if <90%, defer removal. If ≥95%, remove. If 90–95%, re-measure after another sprint." In Task 6, log a structured telemetry event on marker-file use so the decision threshold has data.

---

### 6. Exit-Code Contract as Unversioned API Surface

**Severity: P1** | **Task affected: Task 3 (error classes), Task 4 (`clavain-cli` exit codes), Task 5 (gate wrappers case on exit code)** | **Lens: Coupling and Extensibility**

The plan defines 9 distinct error classes → 9 exit codes (exit 2 = already consumed, exit 3 = expired, exit 4 = not found, exit 5 = sig-verify, exit 6 = proof-of-possession, exit 7 = revoked, exit 8 = cross-project, plus exit 0 success and exit 1 unknown error). Task 5's gate wrappers case on these codes: `case "$rc" in 2) ... 3) ... 4|5|8) ...`. This is now a public API.

**Concern:** Shell scripts in the wild will start hardcoding these exit codes. Adding a 10th error class (e.g., exit 9 = delegated-too-long) is additive but doesn't break existing scripts. Renumbering or reordering is breaking. The plan treats exit codes as stable constants, but they're not versioned. If Sylveste's CLI evolves and another tool collides with exit code 7, there's no version negotiation mechanism.

The plan also does not specify what happens if VerifyToken needs to distinguish "signature-verify-failed" (exit 5) from "signer-key-not-found" (unmapped). The error classes are tight but not proven exhaustive across the full v2.x roadmap.

**Suggested reframe:** In Task 1, add an "Exit Code Versioning" section to `docs/canon/authz-token-model.md` documenting the 9 codes as a v2-stable API, with a note "Breaking changes to exit code semantics require version negotiation in future versions (e.g., CLAVAIN_AUTHZ_PROTOCOL_VERSION env var). New error classes are additive and mapped to new exit codes; no renumbering." In Task 4, add a `--version` or `--help` output listing the exit-code table. This frames the exit codes as a versioned contract, not a private implementation detail.

---

### 7. "Same-Project-Only" as Guardrail or Over-Restriction?

**Severity: P2** | **Task affected: Task 2 (schema has `cross_project_id` ready), Task 3 (ConsumeToken enforces same-project), Task 4 (`policy token consume` exit 8 message)** | **Lens: Explore/Exploit Tension + Option Destruction**

The plan explicitly refuses cross-project tokens in v2: `policy token consume` exits 8 with "cross-project consumption not permitted in v2 — see v2.1." But the schema is already DAG-ready with `cross_project_id` column prepared. And the handoff notes: "Cross-project delegation is already live in Sylveste culture (Claude → codex can write to multiple projects)."

**Concern:** By refusing cross-project tokens, v2 forces some real delegation scenarios back to the marker-file path or v1.5 record path. If Claude in project A needs to delegate work to Codex operating on both A and B, the token can't represent that delegation at all. This is not a schema limitation but a runtime enforcement. The decision is justified ("scope containment; v2.1 handles it") but opts for simplicity over capability. The risk is that users find workarounds (marker files, out-of-band coordination) that make v2.1's adoption harder.

However, the schema being "cross-project-ID ready" but the runtime refusing it is a form of option preservation. The decision is defensible: v2 is MVP for single-project delegation chains, v2.1 adds cross-project. The downside is that early real-world delegation chains that need cross-project will have stale tokens in the v2 era.

**Suggested reframe:** In Task 1, add a "Scope Boundaries" section to `docs/canon/authz-token-model.md` documenting "v2 enforces same-project consumption. Tokens issued in project X cannot be consumed in project Y, even if the holder has permission in both. This simplifies scope validation but restricts delegation scenarios. v2.1 will support cross-project tokens via a `cross_project_id` column and per-project pubkey registries. Users needing cross-project delegation in v2 should fall back to .publish-approved markers or v1.5 records." This is honest about the trade-off: MVP scope vs capability trade-off, clear upgrade path.

---

### 8. Token Signer Trust Boundary: v2 Inherits v1.5 Limitation

**Severity: P2** | **Task affected: Task 1 (trust model), Task 3 (SignToken doesn't restrict who calls it)** | **Lens: Trust Model Clarity**

The plan states: "signer-key-holder can still forge tokens — that's the same threat envelope as v1.5; tightening requires the v1.6 out-of-band signer deferred in v1.5." This is documented but the implications are not fully explored. In v2, a single `~/.clavain/keys/authz-project.key` file, if compromised, can forge unforgeable tokens and consume them immediately.

**Concern:** The plan explicitly acknowledges this ("documented in `docs/canon/authz-token-model.md` §threat model") but the v2 trust claim is "proof-of-possession tokens with atomic single-use." This is weaker than it sounds: the token is proof that someone with possession of the key signed something, not proof that the intended agent signed it. If the key is on a shared dev machine, anyone with filesystem access can forge tokens. The plan defers the fix (out-of-band signer) to v1.6, but v2 users might assume the token is "tamper-proof" rather than just "tamper-evident."

The plan correctly notes this in Task 1's "Trust claim" section but doesn't add a loud warning in the token-payload spec or CLI output. A future user seeing a token in their audit log might assume it's unforgeable without reading the full threat model.

**Suggested reframe:** In Task 1, ensure the threat model section is explicitly titled "v2 Threat Model" and notes "Tokens are proof-of-possession against the project's Ed25519 public key. The private key is trusted to be held only by the issuer (e.g., gate wrapper process). Compromise of the private key allows arbitrary token forgery. Mitigation via out-of-band signer (v1.6) moves signing to a separate daemon. Audit logs show which tokens were consumed but do not prove which agent actually signed them without a separate signer audit trail." In Task 4's `policy token show` output, include a note "Trust: this token's signature is valid under the current project key. To verify the signer's identity, check `policy audit`'s signer logs (available in v1.6+)."

---

## P2 Findings: Medium-Risk Decision Gaps

### 9. Framing of "5 Resolved Questions": Were These the Right Questions?

**Severity: P2** | **Task affected: Entire plan** | **Lens: Decision Frame Bias**

The plan opens: "resolves 5 explicit open questions from the 2026-04-21 handoff." The 5 questions are:
1. Separate table vs. column extension of `authorizations`
2. Consume atomicity with `policy sign`
3. Gate wrapper auto-consume on env var
4. Same-project-only in v2
5. Marker deprecation path

These are legitimate design questions, and the plan pins clear answers. However, the handoff listed these as "open questions the plan has to answer" — were they the highest-leverage questions to freeze first? Or were they chosen because they were narrow enough to answer without reopening the broader design?

**Concern:** The plan's scope is notably focused on answering the handoff's 5 questions but is less explicit about what *wasn't* asked or is being implicitly pre-decided. For example: (a) Why isn't "should we version the token format" an open question? (b) Why isn't "how do we measure 95% adoption for marker removal" an open question? (c) Why isn't "should depth cap be configurable" an open question? These were all pre-decided implicitly, not via the 5 explicit questions. This suggests the 5 questions were curated to be answerable without disrupting the plan's schedule, not necessarily the most strategic decisions.

**Suggested reframe:** In the plan's introduction, add a section "Questions Explicitly Deferred" listing design decisions that the plan makes without reopening as questions: (1) token format is `<ulid>.<sighex>` (env-var-friendly, fixed for v2), (2) depth cap is immutable constant 3 (safety boundary, not configurable), (3) marker-removal threshold 95% is a future commitment without current measurement (will be gathered in v2), (4) exit-code API is stable v2 surface (versioning in v3+). This frames the scope boundaries honestly and signals what future sessions will need to revisit.

---

### 10. Forward-Only Commitment: No Schema Downgrade Story

**Severity: P2** | **Task affected: Task 2 (migration 034 adds cutover marker)** | **Lens: Reversibility and Blast Radius**

The plan adds a migration 034 with a synthetic `migration.tokens-enabled` audit row marking the cutover. This is good for forward audits ("at what point did v2 land?"). But if v2 needs to be rolled back after a few days in production (e.g., "discovered a critical bug in token verification, rolling back to v1.5"), the schema change is not reversible without manual intervention.

**Concern:** The plan does not document a rollback story. If production DBs are migrated to schema v34 and v2 is found to be broken, reverting the code to v1.5 will fail on a v34 database (v1.5 doesn't know how to handle `authz_tokens` table; it will be ignored but never cleaned up). This is not a blocker — the plan is not promoting unsafe rollback — but it's a one-way door that should be explicitly called out. The cutover marker helps with auditing but doesn't help with recovery.

**Suggested reframe:** In Task 2's schema section, add a "Rollback" note: "Migration 034 is forward-only. If v2 code is rolled back, the v34 database schema remains. The `authz_tokens` table will be unused and ignored by v1.5 code, but it persists in the schema. Full rollback (including schema cleanup) requires manual `DROP TABLE authz_tokens; UPDATE PRAGMA user_version = 33;` or a reverse migration (deferred to post-v2-stable). Deploy v2 only when confidence is high, or ensure a v2.0.1 hotfix path is ready before production rollout."

---

### 11. Task Complexity Estimate: No Risk Concentration Analysis

**Severity: P2** | **Task affected: Entire plan (8 tasks)** | **Lens: Implementation Risk Visibility**

The plan lists 8 tasks, each with an inline step-by-step breakdown. Estimated effort per the handoff: "1 week per handoff" (roughly 35-40 hours). But the plan doesn't flag which task is most likely to uncover design reconsideration, implementation complexity, or hidden dependencies.

**Concern:** Tasks are presented equally but likely have different risk profiles. Task 3 (token.go primitives) requires careful implementation of atomic consume semantics and concurrent correctness (test includes race scenario). Task 4 (CLI) is straightforward porting. Task 5 (gate wrapper integration) touches production code paths (bead-close, git-push-main, etc.) and has blast radius. Task 6 (publish path) crosses two modules (intercore + clavain-cli). If Task 3 discovers that modernc.org/sqlite has additional quirks around concurrent UPDATE + RowsAffected, the whole plan could slip a day.

**Suggested reframe:** Add a "Implementation Risk" section before Task 1: "High-risk tasks (likely to require design reconsideration): Task 3 (atomic consume under real concurrency), Task 5 (gate wrapper integration with production gates). Medium-risk: Task 4 (new CLI surface, needs vetting for usability). Low-risk: Task 1 (spec-lock), Task 2 (migration), Task 7 (docs). Run Task 3 and Task 5 early; if either hits complexity, adjust scope before committing to Task 7 + 8 (docs and E2E tests)." This is honest about where the plan is most fragile.

---

## P3 Findings: Low-Risk Suggestions

### 12. Confirmation Bias from v1.5 Shape

**Severity: P3** | **Task affected: Entire plan** | **Lens: Inertia vs Discipline**

The plan explicitly mirrors v1.5's 8-task structure: spec-lock, migration, primitives, CLI, integration, publish path, bootstrap, E2E tests. The handoff suggests: "mirror v1.5's 8-task shape." This is disciplined (reusing a proven pattern) but also risky if v2 needs a different shape. For example, v1.5 didn't have delegation semantics, so it didn't need a "DelegateToken + Proof-of-Possession" task separate from IssueToken. v2 combines them in Task 3. Is this the right granularity, or should delegation be its own task?

**Concern:** The plan follows the v1.5 template without questioning whether v2's dependencies are different. Mirroring a proven pattern is good, but it's not the same as asking "what would the optimal breakdown be for v2 specifically?" This is a low-risk issue (the plan will likely work) but a discipline gap.

**Suggested reframe:** At the top of the plan, add a "Why This Task Breakdown" section: "The 8-task structure mirrors v1.5 (spec-lock → migration → primitives → CLI → integration → publish → bootstrap → E2E). v2 adds delegation and proof-of-possession, which are integrated into Task 3 (primitives) rather than split into a separate task, because the POP logic is tightly coupled to delegation verification. If the primitive complexity becomes unmanageable, split into Task 3 (issue/consume/revoke) and Task 3b (delegate/verify), and renumber accordingly. This structure is not immutable, just proven."

---

## Mitigation Summary

| ID | Severity | Title | Mitigation |
|----|----------|-------|-----------|
| 1 | P1 | DAG assumption lock-in | Document v2 chain-only constraints in canon; mark runtime code with migration notes |
| 2 | P1 | Single key anchoring | Explicitly document v2's single-key assumption and v2.x refactoring cost in threat model |
| 3 | P1 | Depth cap magic constant | Add justification and signpost criteria in canon; use const in code |
| 4 | P1 | Token format fixed API | Document format choice and versioning strategy in canon; avoid "easy to parse" as sole justification |
| 5 | P1 | 95% threshold ungrounded | Define telemetry measurement, baseline, window, and decision gate in canon; add telemetry instrumentation in Task 6 |
| 6 | P1 | Exit code API unversioned | Document as v2-stable API with versioning plan in canon; include code comment in Task 4 |
| 7 | P2 | Same-project restriction | Document trade-off and v2.1 upgrade path in canon |
| 8 | P2 | Signer trust limitation | Ensure threat model is explicit in canon and CLI output; distinguish proof-of-possession from proof-of-signer-identity |
| 9 | P2 | Frame bias (5 questions) | Explicitly list questions *not* asked; distinguish pre-decided from open design choices |
| 10 | P2 | Forward-only rollback | Document rollback limitations and recovery path in Task 2 |
| 11 | P2 | Risk concentration blind | Add "Implementation Risk" section identifying high-risk tasks and ordering constraints |
| 12 | P3 | Shape confirmation bias | Add "Why This Task Breakdown" justification; retain flexibility to split if needed |

---

## Key Questions for Next Session

1. **Depth cap evidence:** What are the actual observed delegation depths in current Sylveste sprints? Is Claude → codex → sub-codex real, or theoretical?
2. **Marker telemetry baseline:** What % of `ic publish --patch` operations currently use `.publish-approved` markers? This anchors the 95% target.
3. **Token format stability:** Are there any known constraints that would make `<ulid>.<sighex>` problematic in v2.x? (e.g., serialization for gRPC, URL encoding in logs)
4. **Cross-project early warning:** Are there Sylveste real-world scenarios in the next 3 months that would require cross-project delegation? This informs whether v2.1 should be sprinted sooner.
5. **Delegation POP correctness:** Has the proof-of-possession check (`$CLAVAIN_AGENT_ID == parent.agent_id`) been reviewed by security? Any known bypasses or edge cases?

---

## Approval Gate

This plan is **ready for Task 1** (spec-lock) after:
- [ ] Product owner confirms depth cap = 3 is safe for next 2 sprints (or adjusts)
- [ ] Telemetry owner confirms marker-file adoption baseline is measurable in existing logs
- [ ] Security review approves POP logic and single-key threat model for v2 MVP
- [ ] Implementation owner confirms Tasks 3 and 5 don't have hidden complexity (run local prototypes if uncertain)

Post-Task-1 mitigations are reversible spec clarifications. Post-Task-3 mitigations require code rewrites.
