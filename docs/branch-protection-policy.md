# Branch protection policy, Sylveste estate

Applied 2026-07-27 to all 65 repos: `os/Clavain`, the 63 repos under
`interverse/`, and the `Sylveste` monorepo itself.

## The policy

| Setting | Value | Why |
|---|---|---|
| `enforce_admins` | **true** | The point of the exercise. It was `false` on every protected repo, so nothing bound the owner. |
| `allow_force_pushes` | false | Now genuinely blocked, for everyone. |
| `allow_deletions` | false | Same. |
| `required_pull_request_reviews` | **removed** | It never bound. Keeping it advertised a gate that did not exist. |
| `required_status_checks` | **none** | Would break autosync — see the tradeoff below. |

Direct pushes to the default branch remain allowed. That is deliberate, not an
oversight.

## What the "Bypassed rule violations" message actually was

Every push during 2026-07-25..27 printed:

```
remote: Bypassed rule violations for refs/heads/main:
remote: - Changes must be made through a pull request.
```

It was **repo-level classic branch protection with `enforce_admins: false`** —
not a ruleset. `mistakeknot` is a User account, not an organisation, so no
org-level rulesets exist; all 65 repos reported zero rulesets and zero effective
rules from `/repos/{o}/{r}/rules/branches/{branch}`.

GitHub's documented behaviour: *"By default, the restrictions of a branch
protection rule do not apply to people with admin permissions to the
repository."* As owner, `required_pull_request_reviews` never applied, so the
push succeeded and GitHub printed the bypass notice.

The split that looked arbitrary — some repos printing the notice, some silent —
correlated **12 for 12** with protection state. Repos that printed it had classic
protection; repos that were silent had **none at all**. There was nothing to
bypass, not a different rule.

Before this change:

| State | Count |
|---|---|
| Classic protection, `enforce_admins: false`, PR required, 0 required checks | 42 |
| No protection whatsoever | 23 |
| Rulesets (repo-level or inherited) | 0 |
| Repos with any required status check | **0** |

After: 65 of 65 conforming, verified by re-reading the API.

## The tradeoff: no required status checks, and why

The goal that produced this work wanted CI drift gates wired into protection.
That is **not possible while autosync exists**, and the reason is worth writing
down so nobody re-litigates it from first principles.

- 93 repos on zklw carry `.git-autosync` markers, **84 of them inside Sylveste**.
- `~/bin/git-autosync-sweep.sh` pushes with `git push -u origin "$branch"`,
  where `$branch` is the checked-out branch — `main`. Direct pushes, no PR.
- Required status checks gate **direct pushes as well as merges**: GitHub
  requires a successful check run on the commit before it lands on a protected
  branch. A freshly pushed commit has no check runs yet, so the push is rejected.

So `required_status_checks` and unattended direct-push autosync are mutually
exclusive. Enabling checks today would turn every sweep on 84 repos into
`PUSH-FAIL` and quietly accumulate unpushed commits.

The resolution already exists on paper and is not yet built: the per-machine
lane design (`autosync/zklw`, `autosync/clavain`, with `main` reached by
deliberate merge). Once autosync stops pushing to `main`, `main` can take the
full treatment — required PR, required checks, `enforce_admins`. Until then, CI
is advisory and the enforcement that *is* real covers the operations that
destroy work.

**What this policy does and does not buy.** It does not stop a bad commit
reaching `main`. It does stop `main` being rewound or deleted, by anyone,
including the account that owns the repos — which was previously impossible to
prevent because the owner was exempt from every rule.

## Outlier: `interlore` is on `master`

`interlore` has a single branch named `master`, locally and upstream, against the
estate's `init.defaultBranch = main` convention. The policy is applied to
`master` there so the repo is not left unprotected, but the naming is
unreconciled. Renaming affects every clone and reference, so it is a separate
decision rather than something to fold into a protection sweep.

## Verifying and reapplying

Read the live state for one repo:

```bash
gh api repos/mistakeknot/<repo>/branches/main/protection \
  --jq '{enforce_admins: .enforce_admins.enabled,
         force: .allow_force_pushes.enabled,
         deletions: .allow_deletions.enabled,
         pr: has("required_pull_request_reviews"),
         checks: has("required_status_checks")}'
```

Expected: `enforce_admins: true`, everything else `false`.

A new repo starts unprotected — GitHub applies nothing by default — so this has
to be reapplied whenever a plugin repo is created. That is the standing gap in
this policy: it is a sweep, not an invariant, and nothing currently notices a new
repo that never received it.

## Proof the rule binds

```
$ git push --force origin HEAD~1:main
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Cannot force-push to this branch
 ! [remote rejected] HEAD~1 -> main (protected branch hook declined)
```

Exit 1, `main` unmoved, and no `Bypassed rule violations` line — the difference
between a rule that binds and one that merely reports being ignored.
