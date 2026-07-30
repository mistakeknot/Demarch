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
