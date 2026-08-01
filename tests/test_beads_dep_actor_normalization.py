"""Guard the reconciler in scripts/beads_normalize_dep_actors.py.

The property under test is symmetry: both machines run the same script against
the same pair of exports with the roles of --local and --peer swapped, and they
must reach the SAME canonical value. If they do not, the row is written one way
here and the other way there, and it goes straight back to oscillating — which
is the entire condition this repair exists to end.

Symmetry alone is cheap to satisfy, though. A resolver that always returned
"unknown" would be perfectly symmetric and would erase every attribution in the
tracker, so the tests below also pin what the rules must actually decide, and
that agreeing rows are left alone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "beads_normalize_dep_actors.py"
_spec = importlib.util.spec_from_file_location("beads_normalize_dep_actors", MODULE_PATH)
norm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(norm)


# (local dep actor, peer dep actor, local issue actor, peer issue actor)
CASES = [
    # the bulk: two machine identities, corroborated by an agreed issue creator
    ("mistakeknot", "Claude Code", "Claude Code", "Claude Code"),
    ("mistakeknot", "Claude Code", "mistakeknot", "mistakeknot"),
    # a session id on one side only
    ("mistakeknot", "7e50a41c", "Claude Code", "Claude Code"),
    ("a12f4a80", "Claude Code", "somebody-else", "somebody-else"),
    # both sides are session ids
    ("8610227f", "5b08ed3c", "e1cf964b", "e1cf964b"),
    # nothing corroborates
    ("mistakeknot", "Claude Code", "d85edec9", "d85edec9"),
    # the corroborator is ITSELF divergent — the defect this file was written for
    ("mistakeknot", "Claude Code", "mistakeknot", "Claude Code"),
    ("mistakeknot", "d85edec9", "mistakeknot", "d85edec9"),
    ("900667a0", "Claude Code", "900667a0", "Claude Code"),
    # missing corroborator entirely
    ("mistakeknot", "Claude Code", None, None),
]


@pytest.mark.parametrize("local,peer,local_issue,peer_issue", CASES)
def test_resolution_does_not_depend_on_which_machine_asks(local, peer, local_issue, peer_issue):
    """The anti-oscillation property, stated directly."""
    here, _ = norm.resolve(local, peer, local_issue, peer_issue)
    there, _ = norm.resolve(peer, local, peer_issue, local_issue)
    assert here == there, (
        f"{local!r}/{peer!r} resolves to {here!r} on one machine and {there!r} on the other; "
        "the row would be rewritten in both directions forever"
    )


def test_resolution_always_picks_one_of_the_two_observed_values():
    """Never invents a third value. Attribution may be wrong; it may not be fiction."""
    for local, peer, local_issue, peer_issue in CASES:
        canonical, _ = norm.resolve(local, peer, local_issue, peer_issue)
        assert canonical in (local, peer)


def test_an_agreed_issue_creator_decides_the_row():
    assert norm.resolve("mistakeknot", "Claude Code", "Claude Code", "Claude Code") == (
        "Claude Code",
        "issue-creator",
    )


def test_a_divergent_issue_creator_is_not_trusted():
    """Falls through to a symmetric rule rather than believing the local copy."""
    _, rule = norm.resolve("mistakeknot", "Claude Code", "mistakeknot", "Claude Code")
    assert rule != "issue-creator"


def test_a_session_id_beats_a_machine_identity():
    """`mistakeknot` and `Claude Code` are git identities — bd's fallback when no
    session actor is set, which is the hook context that did the importing. A
    session id names something that actually ran."""
    assert norm.resolve("mistakeknot", "7e50a41c", None, None) == ("7e50a41c", "session-id")
    assert norm.resolve("a12f4a80", "Claude Code", None, None) == ("a12f4a80", "session-id")


def test_two_session_ids_fall_to_the_arbitrary_rule():
    canonical, rule = norm.resolve("8610227f", "5b08ed3c", None, None)
    assert rule == "arbitrary"
    assert canonical == "5b08ed3c"


def issue(issue_id, created_by, deps):
    return {"id": issue_id, "created_by": created_by, "dependencies": deps}


def dep(issue_id, depends_on, created_by, dep_type="parent-child"):
    return {
        "issue_id": issue_id,
        "depends_on_id": depends_on,
        "type": dep_type,
        "created_by": created_by,
    }


def as_export(*issues):
    by_id = {i["id"]: i for i in issues}
    deps = {}
    for i in issues:
        for d in i["dependencies"]:
            deps[(d["issue_id"], d["depends_on_id"], d["type"])] = d
    return by_id, deps


def test_rows_the_machines_agree_on_are_never_rewritten():
    """Agreement is the evidence. 68 real rows agree on a value that is not the
    issue creator's, and a blunt rule would have rewritten every one."""
    local = as_export(issue("a-1", "someone", [dep("a-1", "a", "third-party")]))
    peer = as_export(issue("a-1", "someone", [dep("a-1", "a", "third-party")]))
    plan, counts, _, _ = norm.plan_changes(*local, *peer)
    assert plan == {}
    assert counts["agree"] == 1


def test_a_divergent_row_actually_produces_a_change():
    """Non-vacuity. Every other test here passes against a resolver that plans
    nothing at all, which would leave the churn exactly where it was."""
    local = as_export(issue("a-1", "zed", [dep("a-1", "a", "mistakeknot")]))
    peer = as_export(issue("a-1", "zed", [dep("a-1", "a", "zed")]))
    plan, counts, _, _ = norm.plan_changes(*local, *peer)
    assert plan == {"zed": [("a-1", "a", "parent-child")]}
    assert counts["issue-creator"] == 1


def test_the_machine_that_was_right_writes_nothing():
    """Run on the corroborated side, the repair must be a no-op — otherwise the
    two machines write in a loop chasing each other."""
    local = as_export(issue("a-1", "zed", [dep("a-1", "a", "zed")]))
    peer = as_export(issue("a-1", "zed", [dep("a-1", "a", "mistakeknot")]))
    plan, counts, _, _ = norm.plan_changes(*local, *peer)
    assert plan == {}
    assert counts["already-canonical"] == 1


def test_both_machines_plans_converge_on_the_same_value():
    """The end-to-end statement: apply both plans, and the field agrees."""
    left = as_export(issue("a-1", "zed", [dep("a-1", "a", "mistakeknot")]))
    right = as_export(issue("a-1", "zed", [dep("a-1", "a", "Claude Code")]))

    def resulting_value(mine, theirs, current):
        plan, _, _, _ = norm.plan_changes(*mine, *theirs)
        for canonical, keys in plan.items():
            if ("a-1", "a", "parent-child") in keys:
                return canonical
        return current

    assert resulting_value(left, right, "mistakeknot") == resulting_value(
        right, left, "Claude Code"
    )


def test_a_dependency_only_one_machine_has_is_left_alone():
    """Unshared rows carry no second opinion, so there is nothing to reconcile —
    and rewriting them would destroy the only attribution that exists."""
    local = as_export(issue("a-1", "zed", [dep("a-1", "a", "mistakeknot")]))
    peer = as_export(issue("a-1", "zed", []))
    plan, _, _, shared = norm.plan_changes(*local, *peer)
    assert shared == set()
    assert plan == {}


def test_sql_literal_escapes_quotes():
    """Actor values are free text and go into a generated statement."""
    assert norm.sql_literal("O'Brien") == "'O''Brien'"
