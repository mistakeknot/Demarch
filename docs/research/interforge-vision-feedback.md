# Vision Feedback: What the Current Plugin Constellation Implies Beyond Existing Visions

## Context

I reviewed the current module set (`README.md`, plugin READMEs, and the current vision docs) and compared what is explicitly described in
- `docs/interverse-vision.md`
- `os/clavain/docs/clavain-vision.md`
- `hub/autarch/docs/autarch-vision.md`
- `infra/intercore/docs/product/intercore-vision.md`

This note highlights what the ecosystem appears to be building toward that is not fully explicit in those docs.

## What the constellation implies

1. **A trust and epistemic layer, not only execution**
- `interpeer` introduces multi-model disagreement extraction and converts disagreement into tests/spec questions.
- This is more than review quality control: it is model-consensus arbitration and uncertainty extraction as product-level capability.

2. **A memory and evidence canon**
- `intermem` plus `interdoc` and `interwatch` together imply a deliberate move from ad hoc context to a curated, confidence-ranked knowledge layer.
- The system is trending toward stable artifacts that outlive raw auto-memory and regenerate themselves from evidence.

3. **A platform for measurability and learning loops**
- `interstat`, `tool-time`, and `interbench` push the stack toward continuous evaluation of behavior, efficiency, and outcomes.
- This is stronger than “token efficiency”: it is an artifact/evidence-driven optimization layer.

4. **Inter-plugin compatibility and operating substrate**
- `interband` (`~/.interband` sideband protocol) + `interbase` (`shared integration SDK`) signal a first-class interoperability layer between plugins.
- This suggests the platform is maturing from “plugin bag of tools” into a coordinated runtime with shared contracts and contracts-driven degradation.

5. **Discovery-to-action and communication as native workflows**
- `interwatch` + `interinject` + `interline`/`intermap`/`intermux` show a pattern: eventing, signal propagation, and situational awareness are being treated as core primitives.
- The platform is not only about writing code; it is about maintaining workflow and team cognition state during execution.

## Notable gaps versus current vision language

- The visions emphasize autonomous execution and review quality, but do not clearly frame **agent disagreement synthesis** as a first-class system objective (now visible via `interpeer`).
- The vision docs mention durability and observability, but the current modules imply explicit investment in **post-hoc evidence quality metrics**, benchmark capture, and reproducible workflow evaluation (`interbench`-style direction).
- The “Apps/OS/Kernel” framing does not yet explicitly call out a dedicated **epistemic layer** (uncertainty, conflict, confidence decay) sitting between review/retrieval and action.

## Proposed framing for next doc revision

Treat the ecosystem as five coordinated planes:

1. **Execution plane** (`interphase` workflows, `interflux`, `interlock`, `intermute`, `interbench`)
2. **Knowledge plane** (`intermem`, `interdoc`, `interwatch`, `interpath`, `intervision` artifacts)
3. **Adjudication plane** (`interpeer`, disagreement mining -> test/spec loop)
4. **Economics plane** (`interstat`, `tool-time`, `intercheck`, `interserve`)
5. **Integration plane** (`interband`, `interbase`, plugin hooks/sidebands, shared transports)

## Open questions for validation

1. Is this a planned architecture phase, or implementation drift requiring a vision update?
2. Should the visions explicitly define an *uncertainty/consensus* contract for reviews and discovery?
3. Should `intercore` explicitly include support for evidence-quality metrics and reproducibility artifacts as first-class outputs?
4. Should `interbase` become the explicit “public protocol layer” for all companion interoperability?

## Suggested next artifact

Create a short “Interverse 2.0 extension” section in the vision documents that:
- adds the adjudication and knowledge-canon planes,
- defines cross-plugin telemetry contracts as explicit requirements,
- and clarifies how disagreement-derived outputs (tests, specs, questions) close the loop from model outputs to safe action.
