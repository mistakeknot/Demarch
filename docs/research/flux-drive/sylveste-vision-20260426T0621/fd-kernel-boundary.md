# fd-kernel-boundary — Review of sylveste-vision.md v5.0

**Lens:** Systems architect tracking host-assumption leakage in "host-agnostic" kernels.
**Decision question:** If Claude Code disappeared tomorrow, would Intercore actually run, and what is the recovery effort?

## P0 Findings

### P0-1: Multi-OS coordination problem is unaddressed
The doc says "Clavain and Skaffen are L2 peers — different runtimes sharing the same kernel." Two L2 peers writing to the same SQLite kernel is a concurrency problem that the doc does not address. SQLite WAL allows concurrent readers but serializes writers. If Clavain (Claude Code plugin) and Skaffen (Go binary with its own OODARC loop) both want to advance phases for the same run, either (a) they coordinate through some out-of-kernel channel, (b) one of them blocks on the other, or (c) they write conflicting state. The doc doesn't say which, and "every ic invocation opens, does work, exits" makes (b) costly under load.
**Fix:** Specify the L2 coordination contract — either (i) per-run ownership (one OS at a time per run), (ii) advisory lock through kernel sentinel rows, or (iii) optimistic concurrency with retry.

### P0-2: "Host-agnostic" claim has no falsification test
"If the host platform changes, opinions survive; UX adapters are rewritten." This is asserted, not tested. Today Clavain ships as a Claude Code plugin. The skill files, agent files, hook configs, and slash command syntax are all Claude-Code-shaped. A real port to Codex CLI or to Gemini would surface the actual host-coupling, but the doc doesn't claim such a port exists or is in progress beyond the Skaffen Go runtime.
**Fix:** Either (a) commit to a host-portability test as a milestone (e.g., Clavain on Codex by date X), or (b) downgrade the survival claim from "host-agnostic" to "host-replaceable with rewriting effort."

## P1 Findings

### P1-1: Mechanism vs policy boundary is convention-only
Design Principle #1 says "the kernel provides primitives. The OS provides opinions." The kernel "doesn't know what 'brainstorm' means." Good. But there is no test that catches policy creep into the kernel. If a future kernel commit adds a "brainstorm_complete" column to a table, the principle is silently violated.
**Fix:** Add a test/lint that flags kernel schema or code that references domain-specific phase names. Or document the policy boundary in code comments that gate-check additions.

### P1-2: Event taxonomy versioning is undocumented
The kernel records "events" as part of its system of record. As OS-layer policy evolves, new event types appear. Is the event taxonomy versioned? When Interspect reads events to compute Routing maturity, can it correctly interpret events written by a newer/older kernel? The "Persistence M2" cell suggests this works today but doesn't explain how.
**Fix:** Specify event taxonomy versioning — likely event_type as a (name, schema_version) pair, with migration policy.

### P1-3: SQLite scaling envelope is asserted, not measured
"No daemon, no server" is good for simplicity but the doc claims "any session, any agent, any process can query the true state." With 64 plugins and 589 agents, contention on a single WAL file is a real risk. The doc has cost data ($1.17 → $2.93) but no kernel-throughput data.
**Fix:** Publish a kernel-event-rate observation and a budget. Where does WAL contention start to bite?

## P2 Findings

### P2-1: Layer survival is described as nesting, but apps depend on kernel behavior
"If everything above disappears, the kernel and all its data survive." True, but the inverse claim ("apps survive their UX rendering choice") is weaker than implied. If Autarch breaks because of a TUI library change, the "data" survives in the kernel but the user-facing capability is gone. The survival hierarchy is real for data, less real for capability.

### P2-2: SQLite-as-system-of-record creates a backup/restore obligation that isn't stated
The kernel "is the durable system of record" but the doc has no backup policy, no restore procedure, no max acceptable restore-point-objective. For a 1,456-bead corpus, this is non-trivial.

### P2-3: Skaffen migration creates a transient dual-writer state
The "intelligence replatforming" (Auraken Python → Skaffen Go) is in progress. During migration, both runtimes may exist. The kernel-boundary thesis assumes a single OS-layer writer; transient duals are not addressed.

## Summary
The layered-survival thesis is the doc's strongest architectural claim, and it is real for data persistence. It is weaker for capability survival, and it is operationally undertested for the multi-OS L2-peer scenario that the doc itself introduces with Clavain+Skaffen.
