# Intercom Vision — Safety Review

**Date:** 2026-02-22
**Reviewer:** Flux-drive Safety Reviewer
**Document reviewed:** `apps/intercom/docs/intercom-vision.md` (v0.1, draft)
**Supporting files read:**
- `apps/intercom/AGENTS.md` (NanoClaw developer guide)
- `apps/intercom/docs/SECURITY.md` (current security model)
- `apps/intercom/src/mount-security.ts` (mount validation)
- `apps/intercom/src/ipc.ts` (IPC handler + authorization)
- `apps/intercom/src/container-runner.ts` (volume mounts, container args)
- `apps/intercom/src/types.ts` (interfaces)

---

## Threat Model (Established Before Flagging)

**System exposure:** Intercom faces the public internet via Telegram Bot API and WhatsApp Web. The host process runs on a server with access to the full project root. Containers run with bind-mounted filesystem segments.

**Untrusted inputs:** Every inbound messaging platform message is untrusted. Message senders (Telegram user IDs, WhatsApp JIDs) are not authenticated against any internal identity store — the platform tells you who sent it, but that platform identity has no verified mapping to a Demarch role.

**Current trust model (from `SECURITY.md`):**

| Entity | Trust Level |
|---|---|
| Main group | Trusted (self-chat) |
| Non-main groups | Untrusted |
| Container agents | Sandboxed |
| Messaging platform messages | Untrusted user input |

**Credential locations:** OAuth tokens for Claude, Gemini, and Codex live in `.env`. They are passed to containers via stdin at invocation time, not mounted as files. The WhatsApp session store is host-only. The mount allowlist lives outside the project root at `~/.config/nanoclaw/mount-allowlist.json` and is never mounted into containers.

**Deployment:** Single-host Node.js process managing Docker containers. No CI/CD deployment described for the vision features. All kernel operations (H1/H2) would be `ic` CLI invocations or `bd` CLI invocations from within containers or from the host process.

---

## Risk Classification

| Area | Risk Level | Rationale |
|---|---|---|
| H1 Option A (ic binary + DB read) | High | DB contains run secrets, agent dispatch context, potentially sensitive artifacts |
| H1 Option B (IPC bridge) | Medium | Adds a new IPC command class; trust boundary already exists but unauthenticated |
| H1 Option C (HTTP API) | Medium-High | New network surface inside Docker; depends on bind configuration |
| H1 Option D (snapshot files) | Medium | Static state; information disclosure risk; stale data risk |
| H2 write operations | High | Auth changes — messaging users triggering kernel mutations |
| H3 multi-user RBAC | High | Privilege escalation via group identity spoofing |
| H3 container boundary erosion | High | Invariant "containers are the security boundary" breaks under H2/H3 |

---

## Finding 1 — Option A: IC Binary + DB Read-Only Mount

**Risk: High**

The vision proposes mounting the `ic` binary and kernel DB read-only into containers. The current security model lists the Intercore DB as a possible source for `demarch_run_status` and `demarch_sprint_phase`.

**What a container agent can do with direct DB read access:**

The Intercore SQLite DB contains, at minimum: run state, phase history, artifact metadata, dispatch records, token budget figures, and gate states. Depending on schema version (v10–v14 from MEMORY.md), it may also contain: artifact content or artifact file paths, agent dispatch command strings, and phase action templates. An agent with `run_shell_command` access (all three runtimes have this) can run arbitrary `sqlite3` queries against the mounted DB file. The `readonly` mount flag prevents writes but does not limit query scope — every table, every column, every row is readable.

**Concrete risks:**

1. **Artifact content disclosure.** If artifact content is stored in the DB (or artifact paths are stored and the referenced files are also mounted), an agent can exfiltrate spec documents, code review verdicts, PRD content, and research findings that belong to other projects or runs — including runs the messaging user had no business asking about.

2. **Dispatch command reconstruction.** `phase_actions` rows contain command templates with `${artifact:...}` and `${run_id}` variables. A container agent reading these can understand what commands the kernel is about to execute and potentially pre-stage inputs to influence outcomes.

3. **Token budget extraction.** Token budget figures help an attacker understand how long a run has left and whether approval gates are approaching.

4. **The `ic` binary itself is a risk.** If the `ic` binary is mounted with execute permission (even read-only mounts allow execution of an already-executable binary in Docker), the agent gains the full read capability of every `ic` subcommand — including subcommands that are more sensitive than what the vision's seven `demarch_*` tools intend to expose. The container can run `ic run list`, `ic dispatch list`, `ic run events --json`, and `ic portfolio relay` with no additional authorization check.

**Mitigation required before implementing Option A:**

- Do not mount the raw DB. If DB access is needed, expose only through a host-side proxy that enforces per-query authorization.
- If the `ic` binary is mounted, enumerate exactly which subcommands are permissible and implement a wrapper that whitelists them. Do not mount the raw binary.
- Audit every DB table for sensitive content before enabling any direct DB access from containers.

---

## Finding 2 — Option B: IPC Bridge for Kernel Queries

**Risk: Medium**

The IPC bridge pattern already exists for messaging and task scheduling. The existing implementation in `src/ipc.ts` has reasonable per-group authorization: non-main groups can only send to their own JID, can only manage their own tasks, and cannot register new groups.

**What changes under H1 Option B:**

New IPC command types would be added — `demarch_run_status`, `demarch_search_beads`, etc. The host process receives these, executes `ic` or `bd` CLI commands, and writes results back to the container's IPC namespace.

**Trust boundary implications:**

The IPC file boundary is the existing security layer, and it works. The structural weakness is that **IPC identity derives entirely from directory path** (`sourceGroup` is determined by which subdirectory the file appeared in). This is secure as long as:

1. No container can write into another group's IPC directory.
2. The host never processes IPC files from a directory that does not correspond to a running container.

Both conditions hold today because each group's IPC directory is separately mounted into only that group's container. The weakness is that this is an **operational invariant**, not a code-enforced one. If a future change mounts a shared IPC parent directory (e.g., to allow cross-group communication), the authorization model collapses silently — the `isMain` check becomes trivially bypassable by any container that can write files at the parent level.

**Additional risk under H1 Option B:**

The host process would now execute `ic` and `bd` as the host user on behalf of any container. The authorization question the host must answer is not just "which group is this?" but "is this group allowed to query this run?" The current IPC handler has no concept of per-run access control — it only models per-group isolation. A non-main group that has been given IPC access to H1 tools can query any run, any sprint, any bead — there is no run-level authorization in the IPC layer.

**Mitigation required:**

- Before adding H1 IPC commands, define the authorization policy: which groups can query which runs? Implement this in the host-side handler, not in the container.
- Add an explicit invariant test: assert that no container's IPC namespace includes a parent directory that is shared with another container.
- Log every `demarch_*` IPC command with the sourceGroup and the query parameters — these become the audit trail for who asked about what.

---

## Finding 3 — Option C: HTTP API on the Host

**Risk: Medium-High**

The vision mentions an HTTP API on the host that containers can call. This is the highest-attack-surface option among the four.

**Docker networking and localhost:**

Docker containers (with default bridge networking) cannot reach the host's `127.0.0.1` unless the API binds to `0.0.0.0` or the Docker bridge IP (`172.17.0.1` on Linux). An API binding to `0.0.0.0` on the host is reachable from any container — not just Intercom's containers. It is also reachable from any process on the host network or, depending on firewall configuration, from external hosts.

The vision does not specify the bind address. This is a go/no-go blocker for Option C.

**Authentication on a localhost API:**

Even on a loopback-bound API, there is no ambient authentication for containers calling it. HTTP requests from containers carry no verified identity. A token-based scheme is required. That token must be:

- Generated per-container-invocation (not a static shared secret)
- Passed to the container via the existing stdin protocol (not mounted as a file)
- Validated on the host side before executing any kernel command
- Scoped to specific commands and specific run/group context

Without this, any container (including a compromised one) can call any API endpoint. The existing IPC authorization model would need to be replicated in HTTP middleware.

**The network access row in `SECURITY.md` is "unrestricted" for all containers.** This means if Option C is implemented with a static token or no token, any container — including containers for non-main, untrusted groups — can query or mutate kernel state through the API.

**Mitigation required if Option C is chosen:**

- Bind to the Docker bridge IP only (`172.17.0.1`), not `0.0.0.0`.
- Generate a per-invocation, cryptographically random token and pass it via stdin alongside secrets.
- Validate the token server-side. The token must be short-lived (expire when the container exits).
- Enforce group-scoped authorization on every endpoint: the token encodes which group it belongs to, and the API handler rejects requests that exceed that group's authorization.
- Do not use Option C until these controls are in place.

---

## Finding 4 — Option D: Pre-Populated Snapshot Files

**Risk: Medium**

Snapshot files (pre-populated state that containers read on startup) avoid runtime kernel calls. The existing `writeGroupsSnapshot` function in `src/ipc.ts` already uses this pattern for group metadata.

**Information leakage risks:**

Snapshots are written to the group's workspace folder, which is mounted read-write into the container. The container can read everything in the snapshot. If the snapshot contains state from multiple projects or runs, the container gains access to information about runs it was not authorized to query.

The snapshot must be scoped tightly: only include state relevant to the current group's authorized runs, no cross-project information, no token budget details, no artifact content.

**Stale data risk:**

A snapshot taken at container start time is immediately stale. For H1 queries ("what's the current sprint status?"), a response that is several minutes old may be misleading without a staleness indicator. If Intercom presents stale phase information and a user approves a gate based on it (a precursor to H2), the decision was made on incorrect state. The snapshot approach requires explicit staleness timestamps in the response and a user-facing caveat.

**The snapshot write path is a new host-side privilege:**

Writing snapshots requires the host to read kernel DB state and write it to a group workspace directory. That read must be authorized (same concern as Option B) and the write path must not overwrite files that the container has already written into its workspace.

**Mitigation required:**

- Scope snapshots to the requesting group's authorized runs only.
- Include a `fetched_at` timestamp in every snapshot field. Surface staleness to users ("as of 3 minutes ago").
- Do not include artifact content or full run event history in snapshots. Only include summary state.

---

## Finding 5 — H2 Write Operations: Kernel Mutations from Chat

**Risk: High — this is the most significant trust boundary change in the vision**

The vision's design principle states: "Containers are the security boundary. Every user message passes through a container sandbox. The host process handles channel I/O and event routing but never executes LLM-generated actions directly."

H2 breaks this invariant. Under the proposed IPC intent model:

```
Container agent writes intent file
  → Host reads intent file
    → Host executes ic run create / ic gate override / bd create
```

The host is now executing kernel mutations in response to LLM-generated intent files. The container is no longer just a sandbox that produces a conversational response — it produces executable instructions that the host carries out without further human confirmation.

**Trust boundary analysis:**

The current design relies on the IPC authorization model to distinguish legitimate from illegitimate intents. But that model answers the question "which group wrote this?" — it does not answer "did a human authorize this action?" or "is this action appropriate for the current kernel state?"

A concrete attack chain:

1. A malicious or confused message triggers prompt injection in a non-main group's container.
2. The injected prompt instructs the agent to write a `demarch_approve_gate` IPC intent file.
3. The host, seeing a valid intent from a registered non-main group, executes `ic gate override`.
4. A gate that was blocking a destructive phase advance (e.g., deploy, schema migration) is bypassed.

The current SECURITY.md acknowledges non-main groups as untrusted, but the existing IPC commands (send message, schedule task) are limited to Intercom's own state — they cannot reach the kernel. H2 removes this firewall.

**Specific operations and their blast radius:**

| H2 Operation | Blast Radius if Abused |
|---|---|
| `demarch_create_issue` (bd create) | Low — creates a bead, reversible |
| `demarch_start_run` (ic run create) | Medium — starts a sprint run, consumes tokens, may trigger agent dispatch |
| `demarch_approve_gate` (ic gate override) | High — bypasses a human-approval checkpoint, potentially irreversible phase advance |
| `demarch_advance_phase` (OS intent advance-run) | High — same as above |
| `demarch_register_finding` (ic discovery submit) | Medium — pollutes the discovery corpus |

**What authentication and authorization is required:**

At minimum, before H2 is implemented:

1. **Explicit human confirmation for gate approvals.** The gate approval flow must not be end-to-end automated. When a container writes a `demarch_approve_gate` intent, the host must not execute it immediately. It must send a confirmation message back to the user ("Are you sure you want to approve gate X for run Y? Reply YES to confirm.") and only execute after receiving an explicit affirmative reply that is not itself LLM-generated.

2. **Main-group-only for destructive operations.** `demarch_approve_gate` and `demarch_advance_phase` must be restricted to the main group (the self-chat that SECURITY.md treats as trusted). Non-main groups (Engineering, Product, Stakeholders from H3) must never be able to trigger gate approvals regardless of their H3 role.

3. **Run-scoped authorization.** "Start a run" must be gated on which project the run is for. A non-main group should not be able to start a run on a project they have no registered context for.

4. **Audit log for every H2 intent.** Every intent file processed by the host must be logged with: sourceGroup, intent type, parameters, timestamp, and whether it was executed or rejected.

5. **Rate limiting.** Without rate limiting, a container can flood the host with `ic run create` intents and exhaust token budgets across all runs.

---

## Finding 6 — H3 Multi-User RBAC: Privilege Escalation via Group Identity

**Risk: High**

H3's role model maps messaging groups to permission tiers:
- Engineering: start runs, approve gates
- Product: query specs, prioritize work
- Stakeholders: read-only status

**The privilege escalation surface:**

Group identity in the current system derives from the messaging platform (Telegram group ID, WhatsApp group JID). There is no cryptographic binding between a messaging group and its assigned Intercom role. The role is stored in Intercom's SQLite DB (the `RegisteredGroup` record). The `register_group` IPC command is restricted to main-group-only, which is correct. But:

1. **A user in a lower-privileged group cannot directly upgrade their group's role through IPC.** However, if the role field is stored in the `RegisteredGroup` record in Intercom's DB, and the group's workspace folder is mounted read-write, a container agent running in that group could potentially write to the group's SQLite state (if the DB path is accessible from the workspace mount).

   The kernel DB and the Intercom SQLite DB must not be accessible from within any container. Verify the Intercom DB path (`db.ts`) is outside all mounted directories.

2. **Cross-channel group impersonation.** In H3, a Telegram group maps to a role. A Telegram user ID that has access to an Engineering group is implicitly granted Engineering-level permissions. Telegram group membership is managed on Telegram's servers — anyone added to that Telegram group by any current member gains Engineering-level kernel access. This is a significant operational security gap: the access control boundary is Telegram group membership, which is not under the operator's direct control.

3. **Message crafting for privilege escalation.** Can a Stakeholder-group user craft a message that triggers Engineering-level operations? In the H2 IPC model, the container executes with the group's identity. If the LLM in a Stakeholder container is manipulated (prompt injection) into writing a `demarch_approve_gate` intent, and the host does not enforce role-based command restrictions per group, the gate approval executes.

   The host-side IPC handler must enforce: "this group's role permits these commands and no others." It cannot rely on the LLM not generating privileged intents.

4. **The vision diagram shows no trust boundary between the Channel Router and the Container Orchestrator.** Under H3, the Channel Router knows a message came from the Engineering Telegram group. It must pass this role assertion to the Container Orchestrator, which must enforce it throughout the container's IPC session. The current IPC model uses `isMain` as the only privilege flag — there is no "role" field in the IPC authorization path.

**Mitigation required before H3:**

- Store the role assignment in the host process (not in any container-accessible path).
- Pass the effective role as a signed, tamper-resistant claim to the container's IPC namespace — or preferably, enforce role-based command filtering entirely on the host side without trusting any role claim written by the container.
- Add a warning to the operator documentation: Telegram/WhatsApp group membership is the de facto access control boundary. Group membership changes must be treated as permission changes.
- Restrict `demarch_approve_gate` and `demarch_advance_phase` to main-group regardless of H3 role. Gate approvals from a messaging group introduce unacceptable social-engineering risk even if the role check passes.

---

## Finding 7 — The "Containers Are the Security Boundary" Invariant

**Risk: High — architectural**

The current system's central invariant, stated explicitly in the vision's Design Principles section 2:

> "Every user message passes through a container sandbox. The host process handles channel I/O and event routing but never executes LLM-generated actions directly. This is Intercom's core safety invariant and must survive all evolution."

The vision immediately proceeds to design H2 in a way that breaks this invariant. Under the H2 IPC intent model:

- The container writes an IPC intent file containing a kernel action (e.g., `demarch_approve_gate`).
- The host process reads this file and executes `ic gate override`.
- The LLM-generated content (the intent file) directly caused a kernel mutation.

The invariant says the host "never executes LLM-generated actions directly." The IPC intent model is one indirection away from that, but the host is still executing a kernel action that originated from an LLM-generated file with no interposing human decision for the approve-gate case.

This is not a reason to abandon H2 — it is a reason to be precise about what the invariant means at H2. The invariant needs to be restated:

**Proposed restatement:** "The host process never executes irreversible kernel mutations in response to LLM-generated content without an explicit, out-of-band human confirmation step that is not itself processed by an LLM."

This reformulation preserves the intent while being compatible with H2 for reversible actions (create bead, register finding) while blocking H2 automation for irreversible actions (gate override, phase advance, run create with downstream dispatch).

The vision document should adopt this restatement before any H2 implementation begins, so the invariant is not progressively eroded by each new IPC intent type.

---

## Finding 8 — Credential Exposure in Claude Containers (Existing, Amplified by H1)

**Risk: Medium (existing), elevated to High under H1 Option A or C**

From `SECURITY.md`:

> "Anthropic credentials are mounted so that Claude Code can authenticate when the agent runs. However, this means the agent itself can discover these credentials via Bash or file operations."

The `CLAUDE_CODE_OAUTH_TOKEN` is passed via stdin and is accessible within the container's process environment. A container agent can read its own environment with `run_shell_command("env")` or equivalent.

Under H1, if the container also receives a host API token (Option C) or can run the `ic` binary (Option A), the blast radius of credential exposure increases: a compromised container now holds both an LLM OAuth token and a kernel access credential. An attacker who achieves prompt injection in a Claude container gains both.

These two credentials should have different lifetimes. The LLM OAuth token is session-scoped. The kernel access credential (H1 Option C token) must be container-invocation-scoped — generated fresh per container run and invalid after container exit.

**Mitigation:** Do not reuse the existing secrets dict structure for H1 kernel access tokens. Generate a separate, short-lived, narrowly-scoped token per container invocation. Document explicitly in SECURITY.md that kernel access tokens are separate from LLM credentials and must rotate independently.

---

## Finding 9 — Network Access Is Unrestricted for All Containers

**Risk: Medium — existing gap that H1/H2 amplifies**

The current `SECURITY.md` states "Network access: Unrestricted" for all containers. No `--network` flag restricts containers to a specific Docker network or disables network access.

This is acceptable today when containers are conversational assistants with no kernel access. Under H1/H2, unrestricted network access means:

- A container can exfiltrate kernel state (Option A DB contents, Option C API responses) to an external endpoint.
- A container in a non-main group can reach the H1 HTTP API if it binds to a non-loopback address (Option C risk re-stated in network terms).
- A container can reach the host's other services (e.g., the Intercom host process's management port, if any).

**Mitigation:** Before H1 or H2 implementation, evaluate adding `--network=none` (for containers that need no external network), or a dedicated Docker network that isolates Intercom containers from the host's other services. At minimum, document that network access is a known residual risk and track it as a hardening item.

---

## Finding 10 — H1 Option B Register-Group and Sync-Metadata Commands Are Already Elevated

**Risk: Low-Medium — existing, not vision-specific**

Reading `src/ipc.ts` lines 350-379 (register_group) and lines 326-347 (refresh_groups): both are restricted to `isMain`. The main group is the private self-chat, which is treated as trusted.

However, the `register_group` IPC command allows the main group's container to register a new group with arbitrary `containerConfig.additionalMounts`. This is the path by which a compromised main-group container could register a group with a mount pointing at a sensitive path. The mount allowlist is the defense here — `validateAdditionalMounts` runs against the external allowlist. The allowlist is not mounted into any container, so a container cannot modify it. This defense is sound as long as the allowlist file permissions are correct on the host (`~/.config/nanoclaw/mount-allowlist.json` should be readable only by the Intercom process user, not world-readable).

No action required for the vision, but track as an operational hardening item.

---

## Rollback Feasibility for Each Horizon

**H1 (read-only agency awareness):**
Rollback is straightforward — H1 adds new IPC command types and possibly a new container mount. Removing H1 tools from the container image and the host IPC handler returns to the current state. No persistent kernel state is written. Rollback is safe.

**H2 (write operations):**
Rollback is not safe for all operations. If H2 has been used to:
- Create beads: reversible via `bd close` or `bd delete`
- Start runs: partially reversible via `ic run cancel`, but agent dispatches may have already consumed tokens and produced artifacts
- Override gates: irreversible if the phase advance triggered downstream dispatch that itself spawned agents or wrote artifacts

H2 requires a rollback plan that distinguishes reversible from irreversible operations before implementation. Gate overrides must have explicit undo documentation.

**H3 (multi-user RBAC):**
Rollback of H3 requires removing role assignments from the DB and reverting group registrations. The operational risk is that users have been given Telegram/WhatsApp access to Engineering-level operations; revoking those requires removing them from the messaging group, which is external to Intercom's control.

---

## Prioritized Findings Summary

| # | Finding | Risk | Action Required |
|---|---|---|---|
| 5 | H2 gate override with no human confirmation | High | Mandatory confirmation step before any H2 gate/phase intent executes |
| 7 | "Containers are security boundary" invariant broken by H2 | High | Restate invariant formally; block H2 for irreversible operations without out-of-band confirmation |
| 6 | H3 role escalation via prompt injection + group identity | High | Host-side role enforcement; main-group-only for gate ops regardless of H3 role |
| 1 | Option A: full DB access exposes all run state | High | Do not mount raw DB; proxy with per-query authorization |
| 3 | Option C: HTTP API bind address and auth unspecified | Medium-High | Require bridge-IP bind + per-invocation token before Option C |
| 8 | Kernel credential co-located with LLM credential in H1 | Medium | Separate credential types; rotate kernel tokens per invocation |
| 2 | Option B: no run-level authorization in IPC | Medium | Add run-scoped authz to host IPC handler before H1 write commands |
| 9 | Unrestricted container network access amplified by H1/H2 | Medium | Evaluate Docker network isolation before H1/H2 |
| 4 | Option D: stale snapshots drive approval decisions | Medium | Require staleness timestamps; block snapshot use for gate approval |
| 10 | register_group allows mount injection via main group | Low-Medium | Verify allowlist file permissions on host; no code change needed |

---

## Go/No-Go Assessment

**H1 (read-only):**
- Option B (IPC bridge): Go with mitigations — add run-scoped authorization to host handler before shipping. Log all demarch_* queries.
- Option D (snapshots): Conditional go — require staleness timestamps and scope to authorized runs only.
- Option A (ic binary + DB): No-go until DB proxy with per-query authorization is designed and implemented.
- Option C (HTTP API): No-go until bind address, per-invocation token, and group-scoped endpoint authorization are specified.

**H2 (write operations):**
No-go as drafted. The IPC intent model requires a mandatory human confirmation loop for gate overrides and phase advances before the host executes them. Reversible operations (create bead, register finding) can proceed with logging. Gate and phase operations require the confirmation loop and main-group restriction regardless of H3 role.

**H3 (multi-user RBAC):**
No-go until H2's authorization model is stable and tested. H3 adds new principals to the H2 write surface before that surface has demonstrated safety with a single-user model. Sequence these: H2 single-user stable, then H3.

---

*Brainstorm-grade vision reviewed at brainstorm-grade depth. Findings are proportional to what the vision proposes, not to a fully-specified implementation. Implementation-time review required for each horizon before shipping.*
