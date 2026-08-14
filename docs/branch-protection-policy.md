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
| `required_status_checks` | **none by default; the drift gates on 3 lane repos** | See "the tradeoff, resolved" below. |

Direct pushes to the default branch remain allowed on the 62 non-lane repos.
That is deliberate, not an oversight. On the three lane repos they are blocked.

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

## The tradeoff, resolved 2026-07-28: lane branches

The constraint below was real and is now lifted for repos that opt in. Autosync
no longer pushes `main` on those repos, so `main` can require checks.

**How it works.** A repo opts in with `LANE=1` in its `.git-autosync` marker.
Autosync then pushes `HEAD` to `refs/heads/autosync/<machine>` instead of to the
checked-out branch; `main` advances only via `git-autosync-promote.sh`, which
fast-forwards it to the lane tip. Because required status checks are evaluated
against **the commit's** check runs, and the lane tip already has them from the
lane push, a green lane fast-forwards `main` and a red one is refused and stays
parked on the lane — visible, revertable, and with nothing stranded on the
machine.

HEAD stays on `main`. That is what makes the existing session-start
`pull --rebase origin main` the cross-machine reconciliation point, so promotion
is always a clean fast-forward with nothing to adjudicate. See
`dotfiles/projects/docs/dual-machine-sync.md` for why this overrides that doc's
original "live on the lane" model.

## That gate stopped holding when lanes went private, 2026-08-14

The paragraph above says a red lane "is refused and stays parked on the lane".
That was true of the three lane repos it was written about, all public. It has
not been true of the estate for some time, and the reason is a billing boundary
rather than anything in the design: **required status checks are a paid feature
on private repositories**, so a private repo cannot carry the gate the lane
model delegates to.

Measured across all eight lane repos on 2026-08-14:

| Lane repo | Visibility | What actually gates `main` |
|---|---|---|
| Sylveste | public | required check: `Generator and parity checkers` |
| interchart | public | required check: `generate.sh refuses bad input` |
| interflux | public | required check: `audit` |
| tldr-swinton | public | protected — on **required signatures**, which never reads CI |
| intermute | public | protected — on **PR reviews**, which never reads CI |
| fluxrig-data | private | nothing; not protected at all |
| fluxrig | private | nothing; not protected at all |
| Khouri | private | nothing; not protected at all |

**Five of eight promoted red and green alike.** The two worth naming are
tldr-swinton and intermute: their `main`s *are* protected, so every audit that
asks "is this branch protected" gets a yes, and neither protection reads a check
run. A gate that is present but pointed at something else is harder to see than
one that is absent.

### What changed

`git-autosync-promote.sh` now asks GitHub about its own gate before it moves
`main`:

- `main` **names required status checks** → delegate to the push, exactly as
  before. GitHub remains the single source of truth wherever it has anything to
  say, which is what the original design was protecting.
- `main` **names none** → read the check runs on the lane tip and refuse a
  failure.

That is one authority answered twice, not two opinions. The drift the original
design feared was drift from a rule GitHub was enforcing; the second path only
ever runs where GitHub is enforcing nothing.

**It reads check runs, never check suites.** Every repo in this estate carries
check suites from Apps that are installed but never run here — railway, vercel,
netlify, cursor, fly-io — and those sit `queued` indefinitely; six of them have
been queued on one interflux commit since 2026-08-04. Waiting on a pending suite
would freeze `main` permanently. Those suites contain zero check runs, so
reading runs makes them correctly invisible: a suite that reported nothing has
no verdict. Runs also **accumulate** on a commit — a nightly `gitleaks` cron had
put ten of itself on one interflux commit — so they are deduplicated by name
with the newest id winning, which is how GitHub itself resolves a required check
to a single verdict.

**Refusing is the fail-closed direction, deliberately.** If GitHub cannot be
reached at all — an expired `gh` token is a failure this estate has had, and a
silent one — the promoter reports `UNVERIFIED` and does not promote. A gate that
opens when it cannot reach its authority is not a gate, and a frozen `main` is
recoverable in a way a shipped red one is not. The refusal is counted in the
summary line so it cannot be silent twice.

A repo with **no workflows at all** still promotes, reported as `[NO-CI]`.
Khouri is that repo, and intermute is the second shape of the same thing: its
workflows trigger on `branches: [main]`, so a lane tip carries no run either.
Nothing was ever going to report, which is not the same as reporting badly —
the `rig-report.sh` distinction, applied to a branch instead of a check.

Verified 2026-08-14 against real lane branches, deleted afterwards: a
deliberately failing tip was refused with `main` unmoved on GitHub, a green tip
promoted, a workflow-less repo promoted unchanged, and a simulated broken `gh`
refused rather than defaulted open.

**GitHub Pro is still the other answer** and is not foreclosed by this. It would
buy server-side protection that cannot be bypassed by editing a script on the
box, on private repos, for money. This is the no-money route to the same
verdict, and it is enforced on the machine that promotes rather than by GitHub.


**Live as of 2026-07-28** — 6 repos on lanes; 3 of them carry required checks,
which are the only repos in the estate with genuine drift gates:

| Repo | Required context | Why on a lane |
|---|---|---|
| `Sylveste` | `Generator and parity checkers` | drift gate |
| `interchart` | `generate.sh refuses bad input` | drift gate |
| `interflux` | `audit` | drift gate |
| `apps/Khouri` | — | had work stranded by non-fast-forward pushes |
| `core/intermute` | — | same |
| `interverse/tldr-swinton` | — | same |

The last three were opted in because their autosync pushes had been failing
silently. A lane does not repair divergence — all three were ahead *and* behind,
so their work still could not reach `main` — but it does convert **silently
stranded** into **visibly parked**, which is what `git-autosync-lane-status.sh`
then reports.

**A lane that never reaches main is the failure mode this creates.** Lane pushes
always succeed, so nothing complains while work piles up. That already happened
once: `jawnfit` accumulated 24 commits over 26 days with its trunk frozen at the
fork point, and no tool said anything.
`git-autosync-lane-status.sh` exists for that: it reports every `autosync/*` ref
on the remote — not just the local machine's, since a lane frozen on the other
machine is exactly the one you cannot see — and flags anything waiting longer
than `--days` (default 7). Its first live run found `apps/Khouri` **frozen 109
days**. Exit 1 when any lane needs attention.

`git-autosync-promote.sh` runs on a `git-autosync-promote.timer` on zklw and
promotes *any* machine's fast-forwardable lane, not only its own — if only one
machine runs the timer, restricting it to that machine's lane would let every
other lane rot.

`strict: false` deliberately — strict additionally requires the branch be up to
date with its base before every push, which the lane model already guarantees
via the session-start rebase.

**Path filters are incompatible with required checks.** Two of these three
workflows were path-filtered. A path-filtered workflow does not run on a commit
that misses the filter, and GitHub does not read "did not run" as "passed" — the
required context stays pending and the branch freezes. Both filters were
removed. Anything added to `required_status_checks` later must run
unconditionally.

**A required check must be green before it is required.** interchart's
`generate.sh refuses bad input` had been failing since the day it was added: its
`tests/structural/conftest.py` imported `interverse/_shared`, a separate repo
absent from a standalone `actions/checkout`, so collection aborted before any
test ran. It passed locally, where `_shared` is a sibling directory. Requiring a
red check would have frozen `main` instead of gating it.

## The original tradeoff (superseded, kept for the reasoning)

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

## Workflow health, audited 2026-07-28

57 workflows across 37 repos were inventoried against `gh api` run history, not
just their YAML. The structural red flags were confined to the monorepo — it is
the only repo that gitignores its own code — but the largest finding was not
structural at all:

**GitHub had disabled `secret-scan.yml` on 17 of 36 plugin repos.** A workflow
with a `schedule:` trigger is auto-disabled after 60 days of repository
inactivity, and a disabled workflow does not run on push either. Each showed 100
successful runs and then silence, from 2026-06-09 onward. All 17 re-enabled.

`scripts/check-workflow-health.py` now reports any workflow that is disabled or
has never produced a run, and exits non-zero. It carries a `--require-repos N`
vacuity guard so a partial checkout cannot report "all clear". Without it this
recurs in 60 days, silently.

Also settled:

| Workflow | Verdict |
|---|---|
| `interverse-inventory.yml` | **deleted** — gated on `[ -d interverse ]`, gitignored, so it never checked anything on a runner |
| `kimi-manifest-drift.yml` | kept — its dir-guard is a deliberate pytest skip; it is a required check doing real work |
| `calibration-eval.yml` | kept — never run, so dispatched manually: **success**. Dormant, not broken |
| `skill-listing-budget.yml` | kept — same, **success** |
| `introspection-probe.yml` | phantom: the file was deleted, GitHub keeps the record |

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
