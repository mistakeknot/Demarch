---
artifact_type: track-findings
track: C
distance: distant
target: /home/mk/projects/Sylveste/interverse/interflux
target_description: interflux plugin (multi-agent review + research engine)
date: 2026-04-17
model: sonnet (review); opus (agent design)
agents_applied_as_perspectives:
  - fd-monastic-scriptoria (medieval manuscript production, quire assembly, signature marks)
  - fd-tidal-harmonic-analysis (ocean tide decomposition into constituent harmonics)
  - fd-ikebana-negative-space (Japanese floral composition, mikomi, structural restraint)
  - fd-lost-wax-casting (cire perdue metalwork: mould-investment, burnout, pour)
---

# Track C — Distant (Structural-Isomorphism Findings)

These findings apply structural patterns from distant knowledge domains. The value is in **mechanism specificity**: not metaphors, but named operational practices from the source domain that map concretely to interflux's architecture.

## C-P1-1: No "signature marks" — agents produce pages that can shuffle undetected

Source domain: monastic scriptoria and early-modern printing.

Medieval scribes and early printers organized manuscripts into **quires** (gatherings of folded sheets). To assemble them correctly without confusion, they inscribed **signature marks** at the foot of the first recto of each quire — a letter and numeral (`A.i`, `A.ii`, `B.i` ...) that made out-of-order assembly impossible to miss. The binder could verify the stack visually before sewing.

Interflux writes per-agent outputs to `{OUTPUT_DIR}/{agent-name}.md` — all named, all sortable — but there is **no cross-agent sequence discipline**. If two concurrent reviews race the same OUTPUT_DIR (confirmed risk per the skill's own note about `find -delete` racing slow agents), the assembler (synthesis subagent) has no way to detect that, say, fd-safety's output is from run N while fd-architecture's is from run N-1. They share a directory and the timestamps are close; the synthesis merges them as if they were one review.

**Mechanism transfer:** Every agent's output should carry a **quire mark**: `{run_uuid}.{agent_position}` in a YAML frontmatter block. The synthesis subagent refuses to merge outputs whose run_uuid doesn't match. The current timestamp-based OUTPUT_DIR suffix partially addresses this but doesn't prevent concurrent-run cross-contamination within a single timestamped directory (if the user invokes two reviews in the same minute with `--output-dir` forced).

## C-P1-2: The reaction round is a single pour — no tidal harmonic decomposition

Source domain: tidal harmonic analysis (Darwin-Doodson method).

Ocean tides are decomposed into independent harmonic constituents (M2, S2, N2, K1, O1 ...), each with its own period, amplitude, and phase. The actual tide at a port is the sum of dozens of these. Predictors compute each constituent from its own astronomical driver and sum them — they do **not** try to model "the tide" as a single system.

Interflux's reaction round (Phase 2.5) runs all reaction agents in parallel with the same peer-findings context, then synthesis averages. Looking at the fixative config (`discourse-fixative.yaml` triggers: drift, imbalance, convergence, collapse) and the dispatch structure, the reaction round **treats the finding-set as a single signal with a few aggregate metrics** (Gini, novelty). Tidal analysis would reject this: each severity band (P0/P1/P2/P3) and each domain (architecture, safety, performance ...) is a separate harmonic constituent with its own "astronomical driver" (the nature of the reviewed artifact). The Gini of P0 findings tells you something very different from the Gini of P3 improvements.

**Mechanism transfer:** Compute and emit fixative signals **per severity band and per domain axis separately**. A high-Gini concentration of P0 findings in one agent is a different pathology than high-Gini P3 improvements — the first means agent overlap on real bugs, the second means one reviewer is chattier. Single-number aggregates mix these.

## C-P1-3: No mikomi — every review produces maximal finding output, never negative space

Source domain: Ikebana (Japanese floral arrangement), specifically the principle of *mikomi* (the deliberately empty space that defines the arrangement).

Ikebana arrangements derive their meaning from what isn't placed — the negative space directs the eye and makes the placed elements legible. A master will remove rather than add to strengthen a composition.

Interflux review agents are incentivized (via the prompt template in `references/prompt-template.md` — "## Prioritization") to produce findings at all four severity levels. The template literally lists P0-P3 as equal-priority buckets to fill. An agent that legitimately has nothing to say at P3 still feels prompt-pressured to list "Improvements and polish" entries. The result: synthesis reports with too many low-severity findings drown the high-severity ones. This is the opposite of mikomi — it's additive noise.

**Mechanism transfer:** The prompt template should explicitly authorize **empty severity bands** as a positive signal. Add: *"If you have no genuine P3 findings, write only `### P3: (no entries — this review surfaced no polish-level concerns).` An empty section is preferred over invented polish items."* Currently no such permission exists, so agents fill the space. The synthesis stage could additionally downweight P3 entries from agents whose P0/P1 findings lacked specificity — classic mikomi reasoning that strong statements require restraint elsewhere to have weight.

## C-P2-4: Lost-wax casting's burnout step is missing — wax artifacts remain in the mould

Source domain: Cire perdue (lost-wax) bronze casting.

In lost-wax: a wax model is invested in a clay mould, then the mould is **fired** to melt and drain the wax — the cavity is completely empty before the bronze pour. Modern investment-casting foundries measure the burnout completeness (visual or weight). An incomplete burnout means wax residue contaminates the cast.

Interflux has the analogous setup: agents write `.md.partial` files, which are renamed to `.md` on completion (the "wax-out" step). But there is no **burnout verification** before synthesis reads the files. Per `phases/launch.md` Step 2.3, "List OUTPUT_DIR — expect `.md` per agent" is the check. But `.md.partial` cleanup happens **after** the retry logic, and there's a window where a slow agent from a previous run can leave a `.md.partial` that gets renamed to `.md` mid-synthesis. The SKILL itself acknowledges this risk (the reason for timestamped OUTPUT_DIRs).

**Mechanism transfer:** Before launching synthesis, execute a **burnout-verify step**: checksum every `.md` file, wait 2 seconds, checksum again, reject any file whose hash changed. Any `.md.partial` found at this point fails the review with a clear error. Currently the "wait for completion" check trusts the `<!-- flux-drive:complete -->` sentinel to be in the final file — but a racing write can produce a half-written `.md` with the sentinel at the top and garbage after if the partial-rename happens during a synthesis read. Real foundries don't trust "I poured ok"; they weigh the wax that came out.

## C-P2-5: Quire misbinding check — cross-run output directories can collide

Source domain: monastic scriptoria (bookbinder's signature verification).

The scribe writes the signature mark; the binder verifies it before sewing. In interflux, the caller generates OUTPUT_DIR and the agents write into it — but **no subagent verifies it's writing into the right run's directory**. If the main session passed `/tmp/flux-drive-old-session` as OUTPUT_DIR (copy-paste error in manual invocation), the agents dutifully write there. The main session's synthesis then reads the "new" OUTPUT_DIR and finds nothing.

**Mechanism transfer:** Agents should receive the expected `run_uuid` and write it into a header of their output. Synthesis reads the header; if `run_uuid` mismatches, it rejects the file. Medieval binders caught misbound quires because the signature marks didn't sequence correctly; interflux can catch mis-directed writes the same way.

## C-P2-6: Knowledge compounding has no "translation room" discipline

Source domain: monastic scriptoria (the separation between scriptorium and correctorium).

A scriptorium produced copies; a separate **correctorium** compared them against exemplars and marked corrections. The two rooms had different rules and different people — a scribe never corrected their own work.

Interflux's synthesis step writes knowledge entries back to `{PROJECT_ROOT}/interverse/interknow/config/knowledge/` in the same pass as it writes findings (`phases/synthesize.md` §"Knowledge compounding"). The agent that found a pattern is also the agent that canonicalizes it. This is the scribe correcting their own work — no independent verification that the pattern is genuinely durable (vs a fluke of this review). Historically, this produces **self-reinforcing errors**: a scribe who miscopies a word propagates the error through all future copies.

**Mechanism transfer:** Knowledge compounding should be a **second pass** with a different agent population, happening only after K reviews have independently confirmed the pattern. The existing `independently confirmed vs primed confirmation` distinction in `references/progressive-enhancements.md` Step 2.1 hints at this, but the compounding step currently bypasses that bar. Making knowledge-write a "correctorium phase" with its own agent and a requirement for N=3 confirmations would prevent the self-reinforcement.

## Verdict

The distant-domain view produces five findings that the adjacent view could not reach. The quire / signature-mark mechanism is a concrete prevention for the concurrent-write race already acknowledged in the code. Tidal harmonic decomposition reframes the "single Gini for all findings" design flaw. Mikomi offers a prompt-engineering change that would improve signal-to-noise. Lost-wax burnout names the missing verification step between partial-write and synthesis-read. The correctorium pattern identifies a latent self-reinforcement risk in knowledge compounding. These are not analogies — each names a specific mechanism with a specific implementation path.
