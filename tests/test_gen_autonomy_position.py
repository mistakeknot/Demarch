"""Coverage for gen-autonomy-position.py's rendering and splice.

The generator's real job runs where the monorepo is materialised: it reads a
live kernel and a live streak counter. Neither exists on a cloud runner, because
the monorepo .gitignore's core/ and os/. So what CI can check is the half that
does not need them — given two source readings, does the block say the right
thing, and does splicing it into the canon page leave everything else alone.

The half CI cannot check is guarded instead: `--check` must exit 2 on a
source-less checkout rather than comparing an "unavailable" block against an
"unavailable" block and reporting success. That assertion lives in
.github/workflows/kimi-manifest-drift.yml, next to the identical guard for the
Kimi manifests, whose absence let 21 of them drift.
"""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "gen_autonomy_position",
    Path(__file__).resolve().parents[1] / "scripts" / "gen-autonomy-position.py",
)
gen = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gen)


DECLARED = {
    "available": True,
    "declared": True,
    "level": 3,
    "name": "human sets policy, agent executes",
    "derives_auto_advance": True,
}

UNDECLARED = {
    "available": True,
    "declared": False,
    "level": 2,
    "name": "human reviews evidence post-hoc",
    "derives_auto_advance": True,
}

UNAVAILABLE = {"available": False}


def test_block_is_always_delimited():
    for d in (DECLARED, UNDECLARED, UNAVAILABLE):
        block = gen.render(d, None)
        assert block.startswith(gen.BEGIN), d
        assert block.endswith(gen.END), d
        assert block.count(gen.BEGIN) == 1
        assert block.count(gen.END) == 1


def test_declared_level_is_reported_with_its_meaning():
    block = gen.render(DECLARED, None)
    assert "L3" in block
    assert "human sets policy, agent executes" in block
    assert "auto_advance=true" in block
    # A declared level must not be described as a fallback.
    assert "not declared" not in block


def test_undeclared_level_says_it_is_a_fallback():
    # The distinction is the whole point: an unset key and an explicit L2
    # produce identical behaviour but very different confidence.
    block = gen.render(UNDECLARED, None)
    assert "not declared" in block
    assert "falls back" in block
    assert "ic config set autonomy.delegation_level" in block


def test_unavailable_source_does_not_invent_a_level():
    block = gen.render(UNAVAILABLE, None)
    assert "unavailable" in block
    for claim in ("Declared delegation level", "falls back"):
        assert claim not in block, "an unreachable kernel must not report a level"


def test_streak_is_labelled_as_evidence_not_a_level():
    block = gen.render(DECLARED, "A:L3 receipt proof 4/10 (routing=1 gate=2 phase=1; best=2)")
    assert "4/10" in block
    # Track levels are earned, delegation levels are declared. Printing them in
    # one block is exactly where that gets conflated, so the caveat is load-bearing.
    assert "earned, never set" in block


def test_absent_streak_renders_no_evidence_line():
    block = gen.render(DECLARED, None)
    assert "Track A evidence" not in block


def test_splice_replaces_only_the_block():
    page = f"before\n\n{gen.BEGIN}\nstale\n{gen.END}\n\nafter\n"
    out = gen.splice(page, gen.render(DECLARED, None))
    assert out.startswith("before\n")
    assert out.endswith("after\n")
    assert "stale" not in out
    assert "L3" in out


def test_splice_is_idempotent():
    page = f"x\n{gen.BEGIN}\nstale\n{gen.END}\ny\n"
    block = gen.render(DECLARED, None)
    once = gen.splice(page, block)
    assert gen.splice(once, block) == once


def test_splice_refuses_a_page_without_markers():
    # Silently appending would produce two blocks, and the next --check would
    # compare against whichever the regex found first.
    with pytest.raises(SystemExit):
        gen.splice("no markers here\n", gen.render(DECLARED, None))


def test_kernel_default_matches_the_go_constant():
    """KERNEL_DEFAULT_LEVEL is duplicated from pkg/autonomy.DefaultLevel.

    It is duplicated deliberately — this script must render something honest
    when `ic` is missing — so something has to notice when the two diverge.
    On a checkout with core/ present, read the constant; otherwise skip.
    """
    src = (
        Path(__file__).resolve().parents[1]
        / "core"
        / "intercore"
        / "pkg"
        / "autonomy"
        / "autonomy.go"
    )
    if not src.exists():
        pytest.skip("core/intercore not materialised (gitignored in the monorepo)")
    for line in src.read_text(encoding="utf-8").splitlines():
        if line.startswith("const DefaultLevel = "):
            assert int(line.split("=")[1].strip()) == gen.KERNEL_DEFAULT_LEVEL
            return
    pytest.fail("DefaultLevel not found in pkg/autonomy/autonomy.go")


# ─── operation-floor table ────────────────────────────────────────────

WITH_OPS = {
    **UNDECLARED,
    "ops": [
        {"op": "bd-push-dolt", "floor": 3, "reason": "shared Dolt remote"},
        {"op": "bead-close", "floor": 0, "reason": "local and reversible"},
        {"op": "git-push-main", "floor": 3, "reason": "others act on it"},
    ],
}


def test_floors_block_is_always_delimited():
    for d in (WITH_OPS, {**UNDECLARED, "ops": []}, UNAVAILABLE):
        block = gen.render_floors(d)
        assert block.startswith(gen.FLOORS_BEGIN), d
        assert block.endswith(gen.FLOORS_END), d
        assert block.count(gen.FLOORS_BEGIN) == 1
        assert block.count(gen.FLOORS_END) == 1


def test_floors_table_renders_every_ruling_with_its_reason():
    block = gen.render_floors(WITH_OPS)
    for op in WITH_OPS["ops"]:
        assert f"`{op['op']}`" in block
        assert op["reason"] in block


def test_floored_and_exempt_ops_are_visually_distinct():
    """`none` vs a level is the distinction the table exists to carry.

    An exempt op rendered the same as a floored one would make the recorded
    exemption unreadable, which is the whole reason exempt ops are listed.
    """
    block = gen.render_floors(WITH_OPS)
    assert "| `git-push-main` | **L3** |" in block
    assert "| `bead-close` | none |" in block


def test_floors_block_says_absence_is_not_exemption():
    # The generated prose has to carry this, because the table alone cannot:
    # a reader seeing four rows has no way to know a fifth op was never ruled on.
    block = gen.render_floors(WITH_OPS)
    assert "never been ruled on" in block


def test_floors_block_survives_a_kernel_with_no_floors_at_all():
    # Not the same as an unreachable kernel: this is a real answer that happens
    # to be empty, and it must render a valid (headers-only) table.
    block = gen.render_floors({**UNDECLARED, "ops": []})
    assert "| Operation | Floor | Why |" in block
    assert "`git-push-main`" not in block


def test_floors_splice_replaces_only_its_own_block():
    """The two generated regions must not disturb each other.

    A streak tick rewrites the position block on its own cadence; if either
    splice matched the other's markers the unrelated region would churn.
    """
    page = (
        f"before\n{gen.BEGIN}\nold position\n{gen.END}\n"
        f"middle\n{gen.FLOORS_BEGIN}\nold floors\n{gen.FLOORS_END}\nafter\n"
    )
    out = gen.splice(page, gen.render_floors(WITH_OPS), gen.FLOORS_BEGIN, gen.FLOORS_END)
    assert "old floors" not in out
    assert "old position" in out
    assert "before" in out and "middle" in out and "after" in out


def test_floors_splice_is_idempotent():
    page = f"a\n{gen.FLOORS_BEGIN}\nx\n{gen.FLOORS_END}\nb\n"
    once = gen.splice(page, gen.render_floors(WITH_OPS), gen.FLOORS_BEGIN, gen.FLOORS_END)
    twice = gen.splice(once, gen.render_floors(WITH_OPS), gen.FLOORS_BEGIN, gen.FLOORS_END)
    assert once == twice


def test_canon_page_carries_both_marker_pairs():
    """Catches a canon edit that drops a region, which would otherwise only
    surface as a SystemExit from the pre-commit hook at commit time."""
    text = gen.CANON.read_text(encoding="utf-8")
    for marker in (gen.BEGIN, gen.END, gen.FLOORS_BEGIN, gen.FLOORS_END):
        assert text.count(marker) == 1, marker
