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
- `mk-ldnb` — this decision
- `mk-1wj0` — the settings guard outage, same failure shape: a check that could
  not fail
- intercore commit `1999806`
