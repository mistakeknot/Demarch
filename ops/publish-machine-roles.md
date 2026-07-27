# Publish Machine Roles

> Which machine is allowed to be a source of plugin versions, and what
> `ic publish doctor` does about it. Companion to `plugin-enablement-policy.md`.

## The decision

**zklw is the signer. Clavain is a verifier.** Recorded 2026-07-26 (`mk-ldnb`).

| Machine | Role | Meaning |
|---|---|---|
| zklw (ReliableSite dedi, Linux x86_64) | `signer` | Publishes. Local `plugin.json` is authoritative. |
| Clavain (MacBook) | `verifier` | Does not publish. The marketplace is authoritative; a trailing local checkout is normal. |

The role lives in `~/.config/intercore/publish-role` and is overridable with
`IC_PUBLISH_ROLE`. An unconfigured machine defaults to `signer`, so nothing
silently stops reporting drift just because a file is missing.

```bash
cat ~/.config/intercore/publish-role     # signer | verifier
IC_PUBLISH_ROLE=signer ic publish doctor # one-off override
```

## The signer could not sign — 2026-07-27 (`mk-cg3z`)

For an unknown period the decision above was a convention reality violated.
zklw, the designated signer, **could not publish any plugin that ships Go
release artifacts** — which is `clavain`, the plugin published most often.
`scripts/verify-release-binaries.sh` exited on `go is required`, `ic` read every
verifier failure as `ErrStaleReleaseArtifacts`, then tried a rebuild that failed
for the identical reason. The operator was told the artifacts were stale by a
machine that had never looked at one. Clavain 0.6.290 was published from the Mac.

Two things were wrong and both are fixed:

**The reporting.** Release scripts now exit **3** for "this machine cannot reach
a verdict" and **1** for "the artifacts really are stale"; `ic` maps 3 to
`ErrReleaseVerifierUnavailable` and names the missing dependency and the host.
An exit code rather than matching phrases like `is required` — reword one `die`
message and string matching silently reverts, with nothing to catch it. Exit 0
alone no longer counts as a pass either: the verifier's `{"verified":true}`
receipt is now required, so a verifier that returns early cannot be read as
success. Both states are forced in
`internal/publish/release_unavailable_test.go`, with assertions that fail if
either sentinel starts wrapping the other.

**The environment.** zklw got Go — see below. The role stands: **zklw remains the
signer**, and can now act as one.

## Why zklw kept the signer role instead of the doc being amended

The alternative was to write down "Go-bearing plugins publish from the Mac". It
was rejected because the premise for zklw's exclusion was false:

- `/usr/local/go` held **go1.23.8**, root-owned, installed March 2025 and simply
  **never on `PATH`** — in login *or* non-interactive shells. `command -v go`
  reported nothing, and that was read as "no toolchain".
- A user-local install needs no root. `~/.local/go` now holds **go1.26.4**,
  matching Clavain, so builds from either machine are comparable.
- Removing it is one command: `rm -rf ~/.local/go ~/.local/bin/{go,gofmt}`.

Retreating in documentation from a constraint that was never real would have
made the docs consistent and the rig worse. The same missing `PATH` entry was
also what pinned the intercore test suite to one machine
(`rig-self-checks.md`) — one environment gap, two symptoms, both documented as
unfixable. zklw's verifier now reaches real verdicts, and its first scheduled
`intercore-tests` run reported 40 packages ok.

**Caveat, recorded rather than smoothed over:** the verifier compares each
binary's embedded Go version against `go_version` in the manifest, so the two
machines' toolchains must stay in step. If one upgrades to go1.26.5 and rebuilds,
the other cannot reproduce those digests until it matches. Nothing watches for
that drift today.

## Other plugins that ship release artifacts

Surveyed 2026-07-27 across all 67 marketplace entries (61 resolvable to local
checkouts): **`clavain` is the only one.** It alone has
`scripts/verify-release-binaries.sh`, `scripts/build-release.sh`, and
`bin/release-manifest.json`. Nothing else hits the conflation above.

Five plugins do carry a Go MCP server — `interlab`, `interlock`, `intermap`,
`intermix`, `intermux` — but ship a `bin/launch-mcp.sh` launcher rather than
compiled binaries, and their binaries are untracked and built on demand.

The survey did turn up the same defect **in the opposite direction** in
`BuildGoMCPBinary`, which pre-builds those servers into the cache at publish
time. Its launcher parser required a `/` inside the `-o` argument; every launcher
writes `-o "$BINARY"`, so it matched **none of them**, and the caller treated
"no match" as "nothing to do". The pre-build had therefore never run for any
plugin, silently, on every publish — the binaries in the cache today were built
by the launcher's own fallback on first MCP launch. Fixed, with the parser
pinned against the shipped launchers rather than synthetic strings, and an
unparseable launcher now reported instead of skipped.

## Why

Publishes run on zklw. Clavain holds checkouts that are never version-bumped, so
`plugin.json=0.2.2 marketplace=0.2.3` is the **expected steady state** there, not
a fault. Before this decision `ic publish doctor` reported 21 such plugins as
errors on Clavain. A permanent wall of 21 errors is worse than no check at all —
it teaches you to skip the output, which is how the four-month guard outage
(`mk-1wj0`) survived as long as it did.

There was also a live hazard. `--fix` responded to that drift by writing the
**local** version into the marketplace. On a machine whose checkouts trail, that
means downgrading the marketplace — 21 plugins rolled backwards in one command.
`--fix` now only ever moves a version forward, regardless of role.

## What doctor reports now

| Situation | signer | verifier |
|---|---|---|
| local checkout **behind** marketplace | warning — "pull before publishing" | **info** — no action |
| local checkout **ahead** of marketplace | **error** — unpublished work | **error** — unpublished work |
| marketplace clones disagree | **error** | **error** |

Local work ahead of the marketplace is an error on both roles: that is genuinely
unpublished work no matter which machine it sits on.

## Marketplace clones

`ic publish` resolves the marketplace by walking up from cwd. Two checkouts exist
on each machine and they are the same git remote:

```
~/.claude/plugins/marketplaces/interagency-marketplace   # Claude Code's copy
~/projects/Sylveste/core/marketplace                     # the monorepo copy
```

A plugin **inside** the Sylveste tree resolves to the monorepo copy; one
**outside** it — `interbrowse` lives at `~/projects/interbrowse` — resolves to the
Claude Code copy. Publishing therefore writes to whichever side the plugin
happens to sit on.

`SyncPeerMarketplaces` now propagates a published version to every known clone in
whichever direction the publish came from. Declare additional clones with
`IC_MARKETPLACE_CLONES` (path-list separated) for layouts the defaults do not
guess.

**Detecting the wrong state:**

```bash
ic publish doctor            # "marketplace clones disagree" is now an ERROR
```

Run it from **outside** the Sylveste tree at least occasionally. That used to be
the blind spot: the old check opened with `if absMarket == absCCPath { return }`,
which is true exactly when running from an outside-the-tree plugin — so it
disabled itself in the one directory where the divergence gets created.

When clones disagree and they are the same remote, prefer `git pull` in the stale
clone over `--fix`; `--fix` edits and pushes version fields, a pull just catches
up.

## Adding a plugin outside the Sylveste tree

Nothing breaks, but know what you are opting into:

1. Its publishes resolve to the Claude Code marketplace copy, not the monorepo one.
2. Peer sync covers the propagation, and doctor covers the detection.
3. It will not be found by `discoverPluginDirs`, which scans `interverse/` and
   `os/Clavain` — so it is absent from the per-plugin drift checks.

Moving it under `interverse/` avoids all three. `interbrowse` has not been moved;
that stays open as a judgement call rather than a bug.

## Related

- `mk-963o` — clone divergence, closed by the peer sync + detector
- `mk-ldnb` — the role decision
- `mk-cg3z` — the signer that could not sign, and the Go toolchain that was there all along
- `mk-1wj0` — the settings guard outage, same failure shape: a check that could
  not fail
- intercore commit `1999806`
