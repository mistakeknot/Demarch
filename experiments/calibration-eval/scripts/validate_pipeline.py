"""End-to-end harness validation with no API key and no cost.

Runs the real Inspect pipeline (task -> solver -> scorer -> log) against the
``mockllm`` provider, then runs ``src.analyze`` over the produced log to confirm the
log -> metrics -> figures bridge works. This exercises every line of the harness that
unit tests can't reach (because they deliberately avoid importing ``inspect_ai``).

    python scripts/validate_pipeline.py

Exits non-zero if any stage fails. Intended as a pre-flight check before spending
real API budget.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.model import ModelOutput, get_model

from src.tasks import calibration_custom

# A deterministic fake model. It always answers "A" but cycles confidence across the
# 0-100 range so reliability bins populate and the metrics have something to chew on.
_CONF_CYCLE = [10, 30, 50, 50, 70, 70, 90, 90, 100, 60]


def _mock_outputs():
    i = 0
    while True:
        conf = _CONF_CYCLE[i % len(_CONF_CYCLE)]
        i += 1
        yield ModelOutput.from_content(
            model="mockllm/model",
            content=f"I'll go with option A.\nANSWER: A\nCONFIDENCE: {conf}",
        )


def main() -> int:
    model = get_model("mockllm/model", custom_outputs=_mock_outputs())

    with tempfile.TemporaryDirectory() as tmp:
        log_dir = Path(tmp) / "runs"
        print("[1/3] running calibration_custom against mockllm ...")
        logs = inspect_eval(
            calibration_custom(),
            model=model,
            log_dir=str(log_dir),
            display="plain",
        )
        log = logs[0]
        assert log.status == "success", f"eval status was {log.status}"
        n = len(log.samples or [])
        assert n == 45, f"expected 45 samples, got {n}"

        # confirm the scorer recorded correctness + parsed confidence per sample
        sample = (log.samples or [])[0]
        score = next(iter(sample.scores.values()))
        md = score.metadata or {}
        assert "confidence" in md and md["confidence"] is not None, "confidence not recorded"
        assert "correct" in md, "correctness not recorded"
        assert "domain_type" in md, "domain_type not propagated"
        print(f"      ok: {n} samples scored; sample0 metadata = {md}")

        # locate the written .eval log and run the analysis bridge over it
        eval_files = list(log_dir.glob("*.eval"))
        assert eval_files, "no .eval log written"
        print(f"[2/3] analyzing {len(eval_files)} log(s) -> metrics + figures ...")

        from src import analyze

        out_dir = Path(tmp) / "figures"
        summary = Path(tmp) / "summary.csv"
        rc = analyze.main(
            [str(f) for f in eval_files] + ["--out", str(out_dir), "--summary", str(summary)]
        )
        assert rc == 0, "analyze returned nonzero"
        assert summary.exists(), "summary.csv not written"
        figs = list(out_dir.glob("*.png"))
        assert figs, "no figures written"
        print(f"      ok: summary.csv + {len(figs)} figure(s)")

        print("[3/3] summary.csv contents:")
        print(summary.read_text().strip())

    print("\nPIPELINE OK — harness validated end-to-end with no API calls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
