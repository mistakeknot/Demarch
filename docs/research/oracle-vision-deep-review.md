I can’t access `/tmp/oracle-vision-review-prompt.txt` from here (it isn’t present in this environment). What I *can* do is:

1. give you a solid “Oracle vision review” prompt you can save as that file, and
2. run that review against the vision/architecture docs you *did* upload.

Below is both.

---

## oracle-vision-review-prompt.txt (drop-in prompt text)

```text
You are “Oracle”: a skeptical, high-precision reviewer for a product/architecture vision doc.

GOAL
Produce an actionable review that improves correctness, coherence, and implementability.
Assume the author is competent and time-constrained. Optimize for signal.

INPUTS
- Vision doc(s) + any supporting architecture/glossary/roadmap.
- Treat explicit statements in the docs as the only ground truth.
- If different docs conflict, call it out explicitly (with citations/quotes).

OUTPUT FORMAT (strict)
1) Executive verdict (5–10 bullets)
   - What this is, who it’s for, why it wins.
   - The 3 biggest risks.
   - The 3 changes that most increase odds of success.

2) Coherence & consistency
   - Cross-doc contradictions (status, terminology, timelines, ownership).
   - Ambiguities that will cause implementation drift.
   - Missing invariants and unclear boundaries.

3) Architecture review
   - Layer boundaries: what belongs where, what must not leak.
   - Write path / state ownership / durability story.
   - Failure modes: crash recovery, concurrency, partial failures.
   - Operational model: lifecycle, pruning/retention, observability.

4) Product & UX review
   - Day-1 workflow: does it deliver value quickly?
   - What users will misunderstand.
   - Adoption ladder: are steps independently valuable?

5) Self-improvement loop review (if applicable)
   - Signal taxonomy and grounding quality.
   - Proposal/apply safety model (guardrails, rollback, evals, canaries).
   - Goodhart / reward-hacking risks and mitigations.

6) Roadmap critique
   - Is ordering correct? What should be pulled forward / pushed back?
   - Concrete “next 5 beads” (or equivalent) with rationale.

7) Redlines (must-fix before public launch)
   - Issues that would cause user harm, data loss, or credibility loss.

STYLE CONSTRAINTS
- Be direct. No praise filler.
- Prefer concrete changes over theory.
- If you propose a change, also state what it would cost/trade off.
```

---

## Oracle-style review of the uploaded Interverse/Demarch vision set

### 1) Executive verdict

* The core differentiation is **durable, kernel-owned orchestration state + kernel-enforced gates + event log**, with policy living above it and UI above that. This is a coherent “workflow kernel” thesis. 
* The second differentiator is an explicit **learning loop** (Interspect) that proposes OS-level changes from outcome evidence, with “observe-before-act” and overlay-based reversibility. 
* The platform story (Demarch) is crisp: autonomy × quality × token efficiency as co-equal axes, improved via profiling flywheel. 
* The biggest architecture risk is **boundary leakage**: today, multiple docs acknowledge “aspirational” write-path enforcement and app-layer logic living where it “shouldn’t” (e.g., Gurgeh/Coldwine). Without fast enforcement, the system becomes “everything calls everything,” killing the survivability thesis.
* The biggest correctness risk is **cross-doc inconsistency about what is shipped vs planned**, especially around discovery primitives and kernel reality vs target state. If not cleaned up, this will create roadmap thrash and external trust loss.
* The biggest product risk is **scope sprawl**: 30+ modules, multiple TUIs, kernel, OS, profiler, discovery, portfolio orchestration. The adoption ladder helps, but only if each step has extremely sharp “standalone value” and minimal setup friction.
* The 3 changes that most increase odds of success:

  1. **Normalize terminology + phase model across kernel/OS**, eliminating known gate-coverage mismatches (see “plan-reviewed” and “shipping/polish”).
  2. Publish a **single “Status & Truth” table** (per subsystem) used by all docs: “shipped in code”, “designed”, “planned”, with dates + version tags.
  3. Pull forward **write-path enforcement primitives** (namespace validation + caller audit) earlier than later, because it protects the architectural bet.

---

### 2) Coherence & consistency issues

#### A. Phase naming and gate coverage mismatch is a real correctness bug (not cosmetic)

Your glossary explicitly states the OS has a `plan-reviewed` phase with **no kernel equivalent**, and that kernel gate rule coverage is currently limited because phase names diverge (only `{reflect, done}: CheckArtifactExists` fires for OS-created sprints). That means “kernel-enforced discipline” is partially illusory for earlier phases *unless the OS is creating kernel chains that match kernel gate rules.* 

**Recommendation:** choose one of:

* **Option 1 (preferred):** OS creates kernel phase chains that exactly match the kernel’s expected phase labels (or the kernel stores gates keyed by phase *IDs* not names). This makes gate enforcement real everywhere.
* **Option 2:** add a kernel concept of **phase aliases** or OS-provided “canonicalization mapping” at run creation time, so gates can target stable canonical phases while UI can label freely.
* **Option 3:** treat `plan-reviewed` as a **gate-only transition** rather than a phase (i.e., “planned → executing” has a plan-review gate), removing OS-only phases entirely.

This is a must-fix because it goes directly to the project’s stated “gates are invariants, not prompt suggestions” promise.

#### B. “Discovery is shipped” vs “Discovery depends on future kernel work”

You have conflicting claims across docs:

* Demarch says the kernel has a “discovery pipeline” shipped and lists it among shipped kernel capabilities “as of February 2026.” 
* Clavain says Discover macro-stage is a future capability dependent on kernel discovery subsystem v3, while also saying interject implements much of it but kernel integration is missing. 
* Intercore vision contains both “discovery pipeline shipped (E5)” in a success table *and* later states the discovery subsystem/tables do not exist in the current schema and are “planned for v3.” 

**Recommendation:** publish a single “Discovery status” statement and reuse it everywhere. For example:

* “Interject has shipped discovery *in the OS layer*; kernel-native discovery primitives are designed and scheduled for vX; current kernel does/does not persist discovery records.”
  Then remove all contradictory lines.

#### C. “Apps are swappable” is true for some tools, not others (acknowledged, but needs sharper external messaging)

Autarch vision correctly flags Gurgeh/Coldwine as transitional and not yet swappable because they embed “arbiter/orchestration” logic that should live in Clavain. 
This is fine internally, but externally you need a shorter, stricter claim like:

* “Bigend and Pollard are pure surfaces today; Gurgeh/Coldwine are migrating to pure surfaces.”

Otherwise consumers will build on assumptions that aren’t yet stable.

---

### 3) Architecture review

#### A. The three-layer model is a strong backbone, but you need earlier enforcement

The architecture doc and kernel vision are consistent: L1 kernel owns durable state; L2 OS owns policy; L3 apps are surfaces; Interspect is cross-cutting and read-only to kernel.

However, Intercore itself admits enforcement is currently “convention-only” in v1, and that today apps/plugins may call `ic` directly. 
Given the survivability thesis (“swap layers without destroying below”), enforcement is not optional—it’s how you prevent accidental coupling.

**Recommendation:** reorder enforcement milestones:

* Pull **namespace validation** + **caller auditing** earlier (even if capability tokens remain v3).
* Add an Interspect rule to flag write-path violations as “governance events” as soon as `--caller` exists.

#### B. Kernel CLI process model is consistent and operationally sane, but you need a first-class ops playbook

CLI-not-daemon is a coherent choice. 
But with event retention/pruning, durable consumers, and WAL growth, you need an explicit ops guide (“run these cron jobs / hooks”):

* `ic events prune` cadence + “durable consumer lag” monitoring
* `ic run prune` cadence + backup policy
* `VACUUM` guidance
* “what breaks if clocks jump” (you mention monotonic assumptions) 

Right now those details exist scattered; consolidate into one “Operator Handbook”.

#### C. Dispatch / token accounting: self-reporting is an acceptable wedge, but cost metrics depend on reconciliation

You correctly note self-reported tokens aren’t verifiable and outline reconciliation as OS responsibility. 
Given your north star metric is explicitly economic (“cost to ship a reviewed, tested change”), this needs to be treated as “must reach correctness threshold,” not “nice-to-have.” 

**Recommendation:** define an explicit “Token accounting accuracy SLO” (e.g., “<2% error against billing”) and gate the more autonomous roadmap (L3/L4) on meeting it.

#### D. Security posture: strong baseline constraints, but artifact content and overlays deserve explicit threat modeling

You have “no secrets in kernel DB” as a hard invariant.
But the kernel tracks artifact paths, and artifacts can contain secrets; also Interspect overlays change runtime prompt behavior.

**Recommendation:** add a threat-model section specifically for:

* artifact leakage (paths, content, retention)
* overlay injection / prompt supply chain
* plugin trust boundaries (drivers are independently installable; that increases risk surface)

---

### 4) Product & UX review

#### A. Day-1 workflow is clear, but you should tighten “Discover” messaging

Clavain’s day-1 loop is “brainstorm → plan → plan review → execute → test → quality gates → ship.” 
Demarch also describes Discover as part of the 5 macro-stages and implies pipeline maturity. 
This will confuse new users.

**Recommendation:** make a single, prominent statement:

* “Day-1 ships Design→Build→Ship. Discover is optional / staged / plugin-driven.”

#### B. Adoption ladder is structurally correct—enforce it socially with docs and technically with contracts

The reference doc’s adoption ladder is the right mental model: one driver → OS → kernel → profiler → apps. 
To make it real:

* every module README should start with “Standalone value” + “Integration value when kernel present”
* define a minimal integration manifest (you already have an ecosystem trend toward manifests in the roadmap) 

#### C. “Apps submit intents to OS” needs a concrete interface spec (even if v1 is CLI)

The architecture doc describes intents from L3→L2. 
Autarch vision proposes a minimal v1 intent contract (start-run/advance-run/override-gate/submit-artifact) via calling OS CLI operations. 

**Recommendation:** define:

* exact JSON schema for an intent request/response (even if transported via CLI flags/stdin today)
* stable error codes and how UIs should present them
  This prevents every TUI from inventing its own semantics.

---

### 5) Interspect self-improvement loop review

Interspect is directionally correct: observe first, then propose overlays, then gated autonomy with shadow eval and privilege separation. 

Key issues to tighten:

#### A. Counting rules are good; define “minimum evidence” per change type

You already propose thresholds like “at least 3 sessions, at least 2 projects, at least N events.” 
Make this explicit per modification class:

* routing override vs prompt overlay vs gate threshold change
  Each should have different required evidence because blast radius differs.

#### B. Canary metrics: alert-only is sensible, but define rollback workflow and ownership

Alert-only avoids auto-thrashing, but you need a crisp playbook:

* when an alert fires, what exactly does a human do?
* what is “fast rollback” (disable overlay, revert commit, both)?
* how is blame assigned (overlay X, agent Y, model Z)?

This should be mechanical, not “operator intuition.”

#### C. Reward hacking / Goodhart risks should be handled as first-class

You mention Goodhart in principle (override rate alone is a trap). 
Add concrete adversarial examples:

* system “improves” by suppressing findings (lower override rate, but higher defect escape)
* system relaxes gates to increase completion rate

Then define “hard constraints” metrics (e.g., defect escape rate must not regress) and require them in eval.

---

### 6) Roadmap critique and ordering

Your roadmap’s “Next (P2)” cluster is heavy on Interspect and event-driven advancement. 
Given the architectural risks above, I’d order “next 5” as:

1. **Fix phase/gate alignment** (kernel↔OS naming/aliasing + gate coverage)
   Rationale: makes “kernel-enforced discipline” true system-wide.

2. **Write-path auditing (`--caller`) + namespace validation**
   Rationale: prevents layer boundary drift; enables governance events.

3. **Interspect routing overrides F1 + propose flow (schema + detection)**
   Rationale: lowest-risk, highest-visible “learning loop” win; matches your roadmap list.

4. **Privilege separation (proposer/applier) + allowlisted patch format**
   Rationale: unlocks safe application of changes; reduces fear of “self-modifying system.”

5. **Operational handbook + pruning/retention defaults**
   Rationale: open-source adoption dies on ops papercuts; kernel reliability is brand-critical.

Event-driven advancement is valuable, but I would not let it outrun correctness of gate semantics and write-path governance.

---

### 7) Redlines before public launch

1. **Resolve the phase/gate mismatch** (or explicitly disclaim that gates only enforce late phases today).
2. **Eliminate “shipped vs planned” contradictions** across Demarch/Clavain/Intercore on discovery and other major subsystems.
3. **Publish a stable contract for “intents” and “overlays”** (schemas, error handling, rollback mechanics).
4. **Define minimum viable “cost correctness”** for the north-star metric (token accounting accuracy + reconciliation plan).

---

If you want, I can also produce a single consolidated “Truth Table” (by subsystem: kernel/OS/apps/profiler) that harmonizes “shipped / in-progress / planned” across all these docs so future edits don’t reintroduce contradictions.
