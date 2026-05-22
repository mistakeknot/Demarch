---
artifact_type: canon
bead: sylveste-ewy3.3
supersedes: (none)
superseded_by: (none)
---

# Gridfire — v1: MCP OAuth Resource Indicators

Gridfire's **P6 Capability** primitive (see `docs/brainstorms/2026-02-27-gridfire-brainstorm.md` and `MISSION.md`) is the deny-by-default, unforgeable capability-token system that replaces ambient authority for agent action. The full vision — unforgeable tokens with effects allowlists, resource bounds, expiry, and delegation chains — is a multi-quarter build. This document specifies the **v1 implementation**: Sylveste adopts **MCP OAuth Resource Indicators (RFC 8707)** as its capability-scoped token mechanism for agent-to-tool calls.

Resource Indicators are already required in MCP clients as of late 2025; ten thousand-plus active MCP servers ship the primitive in production. The standard is peer-reviewed (IETF RFC 8707), interoperable across the 500+ public MCP servers, and removes the entire class of token-confusion attacks. Adopting it for v1 frees the Gridfire team to focus on the v2 primitives that no one else is building yet.

This document is the normative spec for Gridfire-v1 token semantics, scope rules, and the v1→v2 migration path. It anchors `sylveste-ewy3.3` and is referenced from `docs/canon/intercom-transport-target.md` (which advertises Resource Indicators as the security scheme in Sylveste Agent Cards).

## What Gridfire-v1 covers and does not cover

**v1 covers** — agent-to-tool calls via MCP, including:

- Sylveste agents (Hermes, Hassease, Skaffen, Auraken, Codex-bridge, Clavain workflow agents) invoking tools exposed by Sylveste plugins that ship MCP servers.
- Sylveste agents invoking external (non-Sylveste) MCP servers.
- External A2A clients invoking Sylveste MCP servers indirectly through a Sylveste agent.

**v1 does NOT cover** — these stay on existing mechanisms:

- **Internal Clavain gate operations** (publish, bead-close, push, etc.) — these continue to use the v2 atomic-consume token spec in `docs/canon/authz-token-model.md`. Different system; different scope; different threat model.
- **Agent-to-agent calls over A2A** — these are scoped at the A2A Agent Card level (per-agent identity URI; the OAuth2 scheme advertised in `securitySchemes` is the v1 Resource Indicators mechanism applied to *the agent's HTTP endpoint*, not to MCP tools).
- **Unforgeable tokens, delegation chains, effects allowlists, resource bounds** — these are v2 primitives. Out of scope here.

## Token shape

A Gridfire-v1 token is an **OAuth 2.0 access token** issued by an authorization server, carrying a **resource** parameter (RFC 8707 §2) that identifies the specific MCP server the token is valid against. The Authorization Server narrows the token's audience to that resource at issue time.

Request to issue:

```http
POST /token HTTP/1.1
grant_type=client_credentials
&client_id=<agent-client-id>
&resource=<mcp-server-identity-uri>
&scope=<tool-scopes>
```

The `resource` value is the canonical URI of the target MCP server (e.g. `sylveste://mcp/intermap` or `https://mcp.tool.example/`). Tokens with this resource value MUST NOT be accepted by any other MCP server. Token verifiers reject tokens whose `aud` (audience) claim does not match their own canonical URI.

## Scope semantics

Scope is a coarse capability declaration (`mcp:read`, `mcp:write`, `mcp:exec`, etc.) joined with the per-server resource binding. The combination "this token, this server, these scopes" produces the v1 capability. Cross-server replay is denied by audience mismatch; cross-scope escalation is denied because scopes are bound to the token at issue time and immutable.

**v1 does not enforce per-tool scopes.** A token valid for a server is valid for any tool that server exposes within the granted scopes. Per-tool scoping is a v2 concern (the effects allowlist).

## Identity bindings

Per `docs/canon/intercom-transport-target.md`, each Sylveste agent has a stable identity URI: `sylveste://agent/<name>`. The client_id used to issue a Gridfire-v1 token MUST be derived from this identity, so token issuance is auditable per-agent. A token issued for `sylveste://agent/hassease` and resource `sylveste://mcp/intermap` is auditable as "Hassease has authority to call intermap-MCP."

## Cross-project consistency

When a Sylveste agent in project A invokes an MCP server in project B, the Resource Indicator MUST carry the cross-project canonical URI. The Authorization Server is responsible for cross-project trust; the consuming MCP server validates only that its own audience matches.

This is *additive* to `docs/canon/authz-cross-project-consistency.md`, which governs the *internal* gate-op token system. The two systems do not share infrastructure; both can be in flight on the same Sylveste session without conflict.

## Discovery

Sylveste MCP servers publish their **canonical resource URI** in `.well-known/mcp-resource.json` (the MCP spec's discovery location). Sylveste Agent Cards reference this URI in the agent's `securitySchemes.oauth2.resource` field. The combination: clients fetch the agent's Card to learn which MCP resources the agent can access; clients fetch the MCP resource's well-known JSON to learn its token requirements; the Authorization Server issues a properly scoped token.

## Threat model — v1

**Denied by v1:**

- Token-confusion attack (token issued for server X replayed against server Y) — denied by audience claim.
- Cross-tenant token leakage (token captured in one project replayed in another) — denied by Resource Indicator scoping at issue time.
- Scope escalation (token with `mcp:read` used for `mcp:write` ops) — denied by immutable scope claim.
- Ambient authority (agent calls tool without explicit token) — denied by deny-by-default; Sylveste plugins MUST refuse MCP calls lacking a verifiable token.

**NOT denied by v1 (deferred to v2):**

- A compromised agent identity (stolen client credentials) — v2 adds delegation chains with per-call freshness proofs.
- Per-tool effect overrun (token valid for server X used to call tool X.dangerous_tool that the issuer didn't intend) — v2 adds effects allowlists.
- Resource exhaustion (token valid but called too many times) — v2 adds resource bounds.
- Replay attack against a single resource (intercepted token used by a third party against the same audience) — v2 adds proof-of-possession (DPoP or mTLS-bound tokens).

## v1 → v2 migration path

v2 strengthens v1's coarse "audience + scope" model into a precise "audience + scope + effects + bounds + proof-of-possession" model. The migration is **additive, not replacing**:

1. **v1 tokens remain valid** during v2 transition. v2-aware servers accept v1 tokens with default "no effects allowlist, unbounded resources" semantics.
2. **v2 adds DPoP or mTLS binding.** Tokens become non-bearer (proof-of-possession). v1 bearer tokens deprecate over a 90-day window once v2 ships.
3. **v2 adds per-call effects allowlists.** The token carries a signed `effects` claim listing which tools and operations the token covers. v1 tokens (no effects claim) are interpreted as "all tools on the audience server, within the scope."
4. **v2 adds resource bounds.** Token carries `max_calls`, `max_tokens_in`, `max_tokens_out` claims. v1 tokens are unbounded.
5. **v2 adds delegation.** Tokens can be exchanged (per RFC 8693) with narrower scope/effects/bounds, producing a child token that can be exchanged again (max chain depth: 3, matching the internal `authz-token-model.md` v2 depth limit).

v2 is **out of scope for the Mythos window**. v1 is the launch surface; v2 is post-launch hardening.

## Acceptance criteria

This canon doc is the spec; landing it satisfies the docs-level component of `sylveste-ewy3.3`. Implementation gates are separate follow-up beads:

1. Choose Authorization Server (candidates: self-hosted Keycloak, Auth0, dex; defer decision until first MCP server needs production tokens).
2. Wire one Sylveste plugin's MCP server through Resource Indicators end-to-end as a proof of correctness. (Suggested first plugin: intermap, since its MCP surface is mature and its tool set is well-bounded.)
3. Publish `.well-known/mcp-resource.json` template + plugin-standard.md addition requiring it.
4. Update `docs/canon/plugin-standard.md` to require Gridfire-v1 token verification on any plugin shipping an MCP server.

## References

- RFC 8707 — Resource Indicators for OAuth 2.0: https://datatracker.ietf.org/doc/html/rfc8707
- MCP authorization spec: https://modelcontextprotocol.io/specification/ (auth section)
- Gridfire vision: `docs/brainstorms/2026-02-27-gridfire-brainstorm.md` (P6 Capability primitive)
- A2A security scheme advertisement: `docs/canon/intercom-transport-target.md` (Authentication)
- Internal gate-op token system (distinct): `docs/canon/authz-token-model.md`
- Synthesis source: `docs/research/flux-research/sylveste-ecosystem-strategic-scan-2026q2-mythos-gate-e359cecd/SYNTHESIS.md` (Tier 2 #6)
- Beads: `sylveste-ewy3.3` (this doc), `sylveste-ewy3.4` (A2A target, referencing this), `sylveste-3xl3` (Agent Teams epic that will exercise Resource Indicators on the first MCP integration).
