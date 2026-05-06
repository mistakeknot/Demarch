# F6 A/B harness

Scaffolding for the F6b A/B test (legacy flux-drive triage vs. lattice-ontology triage). Shipped at F6a (`sylveste-2n8i`) as the runner + metrics + Backend protocol; both real backends (`legacy`, `ontology`) are stubs that raise `NotImplementedError` and land in F6b (`sylveste-g939`).

## Layout

```
scripts/f6_ab_harness/
  __init__.py        # public re-exports
  runner.py          # run_corpus + RunnerResult
  metrics.py         # primary + secondary metric computation
  cli.py             # python -m scripts.f6_ab_harness
  backends/
    base.py          # Backend Protocol + Finding + BackendResult (frozen at F6a)
    legacy.py        # NotImplementedError stub (F6b lands)
    ontology.py      # NotImplementedError stub (F6b lands)
    fake.py          # in-memory deterministic backend for tests
  tests/
    test_harness.py  # end-to-end exercises FakeBackend + metric edge cases
```

## Run the tests

```bash
python -m pytest scripts/f6_ab_harness/tests/test_harness.py -v
```

## Smoke-test against the real corpus

```bash
python3 -c "
from pathlib import Path
from scripts.f6_ab_harness import run_corpus
from scripts.f6_ab_harness.backends import FakeBackend
agg = run_corpus(
    corpus_dir=Path('docs/research/f6-ab-corpus'),
    backend=FakeBackend(script={}),
    baseline_sha='f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d',
    output_path=Path('/tmp/f6-smoke.jsonl'),
)
print(f'runs={len(agg.results)} skipped={len(agg.skipped)}')
"
```

Expected: `runs=30 skipped=0` (FakeBackend with empty script returns empty results for all 30 diffs).

## CLI (F6b will use)

```bash
python -m scripts.f6_ab_harness \
    --backend legacy \
    --corpus-dir docs/research/f6-ab-corpus \
    --output /tmp/legacy.jsonl \
    --baseline-sha f72d3cfd7d72a33c1a97ec37cfe99c5708a5fa0d \
    --metrics-output /tmp/legacy-metrics.txt
```

Currently fails on `--backend legacy` and `--backend ontology` with the F6a stub — `--backend fake` succeeds. F6b lands the real implementations.

## Why monorepo and not `interverse/lattice/`?

F2 closed lattice as the home for ontology *type extensions*. The harness is not a lattice extension — it tests legacy flux-drive against lattice templates *via* a backend protocol. At F6a, neither backend imports lattice (both are stubs). F6b's ontology backend can import lattice or shell out; that decision belongs to F6b's plan.

Living next to the corpus (`docs/research/f6-ab-corpus/`) keeps the F6 evaluation kit self-contained and avoids cross-repo commit choreography during F6b.

## See also

- Pre-registration doc — `docs/research/f6-measurement-preregistration.md`
- Corpus README — `docs/research/f6-ab-corpus/README.md`
- PRD §F6a — `docs/prds/2026-04-21-persona-lens-ontology.md`
- Bead — `bd show sylveste-2n8i`
