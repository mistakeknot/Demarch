<!-- flux-drive:complete -->
<!-- run_uuid: 8c99a137-eefe-4344-9430-c945afe281c1 -->
<!-- agent: fd-kernel-syscall-stability-contract -->

# fd-kernel-syscall-stability-contract — Findings

## Findings Index
- F-K1 (P0): No published stability contract for AGENTS.md / hook protocol / MCP shape — absorbed primitives become a moving ABI
- F-K2 (P0): Memory primitive (target line 19) bundles policy with mechanism — forecloses the retrieval-policy substrate
- F-K3 (P1): No loadable-module equivalent — every primitive expansion forces a Claude Code release cycle
- F-K4 (P1): Parallel-fleet absorption (target line 20) reads as ioctl-style: capability without a userspace contract for orchestrators
- F-K5 (P2): Token observability (target line 22) is a candidate for cgroups-style absorption — pure mechanism, no policy
- F-K6 (P3): Userspace-first test absent in success criteria (target lines 154-161)

## Verdict
The prior-7 list is shaped like a feature roadmap, not a kernel-vs-userspace adjudication. Three of the seven (memory, parallel-fleet, AGENTS.md) need the userspace-first test applied **before** absorption shape is locked.

## Summary
The target document (target lines 17-25) lists seven primitives for absorption but does not specify the **stability contract** each will ship with. Linus's "we never break userspace" rule is the single discipline that kept Linux's plugin/driver substrate viable across 30 years. Without an equivalent commitment from Anthropic, plugin authors cannot price the cost of building against an absorbed primitive — and the rational response is to defer building, which is exactly the ecosystem-freeze risk the document's "premature absorption" warning (target line 37) names but does not solve.

The document also conflates **mechanism absorption** (cgroups, eBPF — host ships plumbing, userspace ships policy) with **policy absorption** (a stock implementation that bundles a particular shape). Of the prior-7, only #4 (cost/context observability) is unambiguously plumbing-shaped. The other six all carry policy that, once shipped, freezes the substrate's ability to compete on shape.

## Issues Found

### F-K1 (P0): No published stability contract — ecosystem freeze risk

**Where:** target lines 17-25 (the prior-7 list); success criteria lines 154-161
**Failure scenario:** Anthropic ships "durable hierarchical agent memory" in CC v3.0. Plugin authors who built intermem/intercache/interknow have to choose: rebuild on the new primitive (and discover its shape is unstable across point releases), or stay on their own substrate and watch users migrate. Without a published "we don't break this surface for N versions" commitment, the rational author choice is **wait and see** — which collapses the marketplace's input flow for 6-18 months. This is the LKML out-of-tree-driver problem: forks survive precisely because the in-tree interface keeps moving.
**Smallest fix:** For each absorbed primitive, ship a `STABILITY.md` declaring (a) which surface is forever-stable (the syscall equivalent), (b) which is best-effort (the internal-API equivalent that can churn), (c) the deprecation window for breaking changes (Linux: forever; web: 5 years; CC: propose >= 18 months). The commitment matters more than the duration.
**Question:** Does Anthropic have an internal precedent for this kind of public stability commitment, and if not, does shipping one create regulatory/legal exposure that explains its absence?

### F-K2 (P0): Memory primitive bundles policy with mechanism

**Where:** target line 19 ("Durable, hierarchical agent memory")
**Failure scenario:** "Hierarchical" is already a policy choice. Sylveste's six memory plugins (intermem, intercache, interknow, interseed, interlearn, intertree, target lines 47-52) explore at least four different shapes: graduation-based (intermem), content-addressed (intercache), provenance-with-decay (interknow), idea-garden (interseed). If Claude Code ships one shape natively, the substrate stops exploring the others — even if the others would have won on workload-fit. Compare: Linux ships VFS (mechanism: file ops, mount points) but doesn't ship one filesystem; ext4/btrfs/zfs/xfs all coexist because the absorption was at the right layer.
**Smallest fix:** Reframe the memory primitive as a **storage + retrieval substrate** (SQLite-equivalent: schema, transactions, indexing) and let "hierarchical" be a userspace pattern on top. Concretely: ship key-value store + cross-session persistence + content addressing + retrieval API. Don't ship a graduation policy, decay policy, or hierarchy enforcement.
**Question:** Of the six Sylveste memory plugins, are any genuinely competing on **mechanism** (vs. just on policy)? If they all share a mechanism gap, that gap is the absorption candidate.

### F-K3 (P1): No loadable-module equivalent

**Where:** target document is silent on this — the gap itself is the finding
**Failure scenario:** Plugin author wants to extend an absorbed primitive (e.g., add a new memory-graduation policy). With no module-load surface, the only path is to fork Claude Code — which nobody can do — or wait for the next CC release that adds the hook. Cadence mismatch: ecosystem need cycles in weeks, platform releases in months. The result is the Apple-ecosystem failure mode: developers stop trying to extend at the primitive layer because the wait is longer than the project lifetime.
**Smallest fix:** Every absorbed primitive ships with a documented extension point (hook, callback, or strategy plugin) that lets the userspace substrate add policy without a CC release. Linux precedent: BPF programs let userspace add packet-filtering policy without recompiling the kernel.
**Question:** The hooks system already exists (PreToolUse/PostToolUse). Is it expressive enough to be the module-load surface for memory/parallel-fleet/observability primitives, or is a richer plugin-of-primitive layer needed?

### F-K4 (P1): Parallel-fleet absorption reads as ioctl-style

**Where:** target line 20 ("First-class parallel agent fleet + synthesis")
**Failure scenario:** "Synthesis" is the policy half of the primitive. interflux/intersynth/interpeer/intermonk (target lines 54-58) implement four genuinely different synthesis strategies (scored triage, dedupe-and-verdict, cross-AI peer review, Hegelian dialectic). If Claude Code ships **one** synthesis strategy, the others die — and we don't yet know which strategy wins on which workload. This is the vendor-ioctl ghetto: Anthropic's sync-and-merge becomes the only sync-and-merge anyone uses, even when it's wrong for their case.
**Smallest fix:** Absorb the **fan-out/fan-in mechanism** (parallel agent dispatch, output collection, structured-finding emission) but leave synthesis as a userspace concern. Ship a synthesis-result schema (the structured output shape) so plugin authors can compete on synthesis algorithm without re-inventing dispatch.
**Question:** Which of intermonk's dialectic, interpeer's cross-AI, interflux's scored triage would survive if Claude Code shipped a "default synthesis" — and is the answer "they all would, on different workloads," which is the signal that synthesis is policy?

### F-K5 (P2): Cost/context observability is the cleanest plumbing-shaped candidate

**Where:** target line 22 ("Built-in cost/context/token observability")
**Why this is the safe absorption:** Of the prior-7, this is the one where mechanism (count tokens, attribute to call sites, expose via API) is cleanly separable from policy (what to do when the budget is exceeded). cgroups is the precedent: kernel ships accounting + limits + notification, userspace ships scheduling decisions. interstat/intercept/interpulse/tool-time (target lines 65-68) all implement different *policies* on the same observability mechanism — exactly the signal that the mechanism should absorb and the policies should stay diverse.
**Smallest fix:** Ship token/cost/context-pressure observability as a host-owned API (read-only). Don't bundle a budget-policy or pressure-response policy. Let plugins compete on what to do when pressure hits 80%.

### F-K6 (P3): Add userspace-first test to success criteria

**Where:** target lines 154-161 (success criteria)
**What's missing:** The criteria ask for "primitives the prior pass missed" and "counter-arguments" but don't structurally require the kernel-discipline test: *can this be done in userspace without losing essential capability?* If yes, it stays. Adding this as criterion 6 forces the review to defend each absorption, not just propose more.
**Suggested edit:** Add criterion 6 — "For each prior-7 primitive AND each newly-proposed primitive, state the failure mode if it stayed in the plugin substrate. If the failure mode is 'inconvenience' or 'duplicated effort,' it is not a kernel candidate."

## Improvements
- Frame the prior-7 explicitly as **mechanism absorptions** vs. **policy absorptions** — current list mixes both.
- Cite Linux precedents specifically: cgroups (mechanism), eBPF (sandbox + extension point), FUSE (userspace filesystem), VFS (mechanism without policy). Each one is an explicit pattern for how to absorb without freezing.
- The document's "wired-or-it-doesn't-exist" principle (target line 138) is itself an argument for kernel-discipline: a primitive without callers is dead inventory. Surface this as the same lens applied to absorptions.
- One Linux-precedent counter-example worth naming: **systemd**. Absorbed too much, became policy-laden, fragmented the ecosystem (sysvinit/runit/openrc holdouts persist because policy was bundled). The seven-primitive list as-stated risks the systemd shape, not the cgroups shape.
