#!/usr/bin/env python3
"""One-time repair: make both machines agree on who created each dependency.

THE BUG
-------
`dependencies[].created_by` diverged between Clavain and zklw on 3,589 of 3,657
shared dependency rows. Everything else about those rows matched. The effect was
that every export that alternated machines rewrote ~3,300 issues, producing the
recurring 3,300-line commits, and handing `bd import` ~3,300 rows on exactly the
cross-machine pulls where it has been observed to block.

It is NOT bd stamping the importing actor, which is what the bead originally
claimed. bd 1.1.2 preserves the file's dependency created_by in every path
constructible against a real database: creating the issue and its dependency
together, adding a dependency to an issue the database already holds, and
re-importing a genuinely-newer row. What it never does is UPDATE the actor on a
dependency that already exists locally.

Preserve-on-create plus ignore-on-update is what makes it permanent. Each
database stamped its own identity once, long ago, under an older bd; neither
import since has had an operation that would reconcile it. So the field is a
fixed point per machine and the file oscillates between them forever.

WHY THE ORIGIN IS RECOVERABLE
-----------------------------
Issue-level created_by agrees across the two machines on 3,807 of 3,811 issues.
For 3,555 of the 3,589 divergent dependencies, exactly one machine's value
equals the dependent issue's own creator — and that is the machine that
originated the link, because a dependency is almost always created in the same
breath as the issue that carries it. The other machine's value is the fallback
its git identity supplied when it first materialized the row.

So this does not collapse the field to a constant. It resolves each row to the
side that can be corroborated, and reports the ones it cannot.

    rule 1  one side equals the dependent issue's created_by   -> that side
    rule 2  exactly one side is an 8-hex session id            -> that side
    rule 3  neither                                            -> lexicographic min, listed

Rule 3's tiebreak is arbitrary, and deliberately arbitrary in a way that does
not depend on which machine is running: "whichever side loses the comparison"
would resolve one way here and the other way there, and the row would go
straight back to oscillating. Lexicographic minimum of the two values is a
property of the pair, so both machines compute the same answer.

Rule 2 is weaker but still directional: a session id names a specific session,
while "mistakeknot" and "Claude Code" are the two machines' git identities and
are what bd falls back to when no session actor is set — which is the hook
context that did the historical importing.

Rows the two machines ALREADY agree on are never touched, whatever they say.
Their agreement is the evidence; a blunt "set every dependency to the issue's
creator" rule would rewrite them for nothing.

USAGE
-----
Needs both machines' exports, because no single machine can tell whether its own
value is the corroborated one:

    bd export -o /tmp/local.jsonl                     # here
    ssh peer 'cd repo && bd export -o /tmp/peer.jsonl' # there
    scp peer:/tmp/peer.jsonl /tmp/peer.jsonl

    scripts/beads_normalize_dep_actors.py --local /tmp/local.jsonl \
        --peer /tmp/peer.jsonl --dry-run
    scripts/beads_normalize_dep_actors.py --local /tmp/local.jsonl \
        --peer /tmp/peer.jsonl --apply

Run it on BOTH machines with the same pair of files. It is idempotent: the
second run reports zero rows to change, which is also how you check it worked.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SESSION_ID = re.compile(r"^[0-9a-f]{8}$")

# (issue_id, depends_on_id, type) — the natural key. The table's own `id` is a
# per-database UUID and so is exactly the thing that cannot be compared across
# machines.
DepKey = tuple


def load(path: Path) -> tuple[dict, dict]:
    """Return (issues by id, dependencies by natural key) from a bd export."""
    issues: dict[str, dict] = {}
    deps: dict[DepKey, dict] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            issue = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: not JSON: {exc}") from exc
        issues[issue["id"]] = issue
        for dep in issue.get("dependencies") or []:
            deps[(dep.get("issue_id"), dep.get("depends_on_id"), dep.get("type"))] = dep
    return issues, deps


def resolve(local_actor, peer_actor, local_issue_actor, peer_issue_actor):
    """Which of the two values is the originator's. Returns (actor, rule).

    Every branch is a function of data BOTH machines hold identically, never of
    which machine is asking. That is the whole requirement: both must reach the
    same answer independently, or the row simply resumes oscillating.

    Which is why rule 1 checks that its corroborator is itself corroborated.
    Issue-level created_by agrees on 3,807 of 3,811 issues — and all four
    exceptions carry a divergent dependency, so reading it from whichever export
    happened to be `--local` would have resolved those four rows one way here and
    the other way there. A 99.9%-agreed input is not an agreed input.
    """
    if (
        local_issue_actor is not None
        and local_issue_actor == peer_issue_actor
        and local_issue_actor in (local_actor, peer_actor)
    ):
        return local_issue_actor, "issue-creator"
    local_specific = bool(SESSION_ID.match(local_actor or ""))
    peer_specific = bool(SESSION_ID.match(peer_actor or ""))
    if local_specific != peer_specific:
        return (local_actor if local_specific else peer_actor), "session-id"
    return min(local_actor or "", peer_actor or ""), "arbitrary"


def plan_changes(local_issues, local_deps, peer_issues, peer_deps):
    """What this machine must write. Returns (plan, counts, arbitrary, shared).

    `plan` maps a canonical actor to the dependency keys that should carry it
    HERE — rows where the local value is already canonical are deliberately
    absent, so running this on the machine that was right is a no-op.
    """
    shared = local_deps.keys() & peer_deps.keys()
    plan: dict[str, list[DepKey]] = {}
    counts = {
        "agree": 0,
        "issue-creator": 0,
        "session-id": 0,
        "arbitrary": 0,
        "already-canonical": 0,
    }
    arbitrary: list[tuple[DepKey, str, str, str]] = []

    for key in sorted(shared):
        local_actor = local_deps[key].get("created_by")
        peer_actor = peer_deps[key].get("created_by")
        if local_actor == peer_actor:
            # Agreement is the evidence. Whatever it says, it is not churn.
            counts["agree"] += 1
            continue
        canonical, rule = resolve(
            local_actor,
            peer_actor,
            local_issues.get(key[0], {}).get("created_by"),
            peer_issues.get(key[0], {}).get("created_by"),
        )
        counts[rule] += 1
        if rule == "arbitrary":
            arbitrary.append((key, local_actor, peer_actor, canonical))
        if canonical == local_actor:
            counts["already-canonical"] += 1
            continue
        plan.setdefault(canonical, []).append(key)

    return plan, counts, arbitrary, shared


def sql_literal(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def run_sql(statement: str) -> None:
    result = subprocess.run(
        ["bd", "sql", statement], text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"bd sql failed: {result.stderr.strip()[:500]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", required=True, type=Path, help="this machine's bd export")
    parser.add_argument("--peer", required=True, type=Path, help="the other machine's bd export")
    parser.add_argument("--apply", action="store_true", help="write to the local database")
    parser.add_argument("--dry-run", action="store_true", help="report only (the default)")
    parser.add_argument("--batch", type=int, default=150, help="tuples per UPDATE statement")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        print("--apply and --dry-run are contradictory", file=sys.stderr)
        return 2

    local_issues, local_deps = load(args.local)
    peer_issues, peer_deps = load(args.peer)

    if not (local_deps.keys() & peer_deps.keys()):
        print("the two exports share no dependency rows — wrong pair of files?", file=sys.stderr)
        return 2

    plan, counts, arbitrary, shared = plan_changes(
        local_issues, local_deps, peer_issues, peer_deps
    )
    to_change = sum(len(v) for v in plan.values())
    print(f"shared dependency rows      : {len(shared)}")
    print(f"  already agree             : {counts['agree']}")
    print(f"  resolved by issue creator : {counts['issue-creator']}")
    print(f"  resolved by session id    : {counts['session-id']}")
    print(f"  arbitrary (lexicographic)  : {counts['arbitrary']}")
    print(f"  of the divergent rows, this machine already holds the canonical value:"
          f" {counts['already-canonical']}")
    print(f"ROWS TO CHANGE HERE         : {to_change}")

    if arbitrary:
        print(f"\nrows whose originator cannot be established ({len(arbitrary)}) —")
        print("these are the ones nobody can attribute after this runs:")
        for key, local_actor, peer_actor, canonical in arbitrary:
            print(f"  {key[0]} -{key[2]}-> {key[1]}")
            print(f"      local={local_actor}  peer={peer_actor}  -> {canonical}")

    if not args.apply:
        print("\n(dry run — nothing written; pass --apply)")
        return 0

    if to_change == 0:
        print("\nnothing to do; the local database already holds every canonical value")
        return 0

    written = 0
    for canonical, keys in plan.items():
        for start in range(0, len(keys), args.batch):
            chunk = keys[start : start + args.batch]
            tuples = ", ".join(
                "({}, {}, {})".format(sql_literal(i), sql_literal(d), sql_literal(t))
                for i, d, t in chunk
            )
            run_sql(
                "UPDATE dependencies SET created_by = {} "
                "WHERE (issue_id, depends_on_issue_id, type) IN ({})".format(
                    sql_literal(canonical), tuples
                )
            )
            written += len(chunk)
            print(f"  {written}/{to_change}", end="\r", flush=True)
    print(f"\nupdated {written} dependency rows")
    print("re-run with --dry-run to confirm ROWS TO CHANGE HERE is now 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
