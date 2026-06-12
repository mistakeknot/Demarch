---
artifact_type: quality-review
reviewer: fd-quality
target: docs/prds/2026-05-25-auraken-distribution-v01.md
bead: sylveste-heh8
date: 2026-05-25
---

# Quality Review — Auraken Distribution PRD v0.1

Perspective: senior engineer reviewing feature decomposition for AC specificity, naming consistency, idiomatic patterns (bash / Python MCP / Go binary / YAML), error-handling expectations, test coverage adequacy, documentation gaps, conformance to project conventions, and unit-test feasibility.

---

## F-QUA-1 — MANIFEST schema language and schema-file location are unresolved

**Severity:** P1

**Evidence:** F1 AC reads "Schema validates against an explicit JSON Schema or YAML schema file under `dist/v0.1/`." Two schema languages are named but the AC does not commit to either. The filename is not given. The `schema: auraken-distribution/v1` header string in the brainstorm's YAML example is not a resolvable URI — it would fail any validator that does `$id`/`$schema` lookup. No AC item specifies where the machine-readable schema lives (`manifest.schema.json`? `manifest.schema.yaml`? Something else?), what dialect (`draft-07`, `2020-12`), or how validation is invoked in CI/build-dist.sh.

**Recommendation:** Add a dedicated AC item: "A JSON Schema file `dist/v0.1/manifest.schema.json` (draft-07) exists and `python3 -c \"import jsonschema, yaml; jsonschema.validate(yaml.safe_load(open('dist/v0.1/MANIFEST.yaml')), json.load(open('dist/v0.1/manifest.schema.json')))\"`exits 0." Commit to one schema language. Rename the `schema:` header value from `auraken-distribution/v1` to something inert (e.g., `auraken-distribution-v1`) or make the URI resolvable. Remove the alternative "or YAML schema file" to avoid implementer choice-paralysis.

**Quality lens:** AC specificity — "explicit JSON Schema or YAML schema file" is not measurable without a filename and dialect.

---

## F-QUA-2 — "Graceful error on missing binary" is undefined: no exit code, no MCP response field, no log expectation

**Severity:** P1

**Evidence:** F2 AC specifies: "the tool returns `{empty: true, error: <human-readable>}` and the MCP server stays alive (does not crash Hermes)." This is better than the brainstorm but still incomplete. "Stays alive" is not testable from a pytest unit test without starting the server process and sending a second request. The AC does not specify: (a) what `<human-readable>` means (minimum information content — e.g., must include the resolved binary path that was tried); (b) whether the MCP server should return an MCP-level error response or an application-level JSON error embedded in the tool result text; (c) what happens if `AURAKEN_LENS_BIN` is set but the binary is not executable (permission error vs not-found are distinct). The existing `server.py` wraps errors in `{"error": str(e), "lenses": [], "count": 0}` — the PRD's target shape drops `lenses`/`count`, but the AC doesn't say "no `lenses` key in error responses."

**Recommendation:** Expand AC item 3 of F2 to: "When the Go binary is absent or returns non-zero exit, `lens_select` returns `{lens: null, rationale: null, next_question: null, empty: true, error: \"<message including resolved path>\"}` with no `lenses` key; the MCP session remains live and a subsequent valid call succeeds (verified by pytest sending two requests in sequence)." Add a fourth pytest scenario: binary present but non-executable (permission denied) returns a distinct error string.

**Quality lens:** Error-handling expectations — idiomatic Python MCP servers return errors either in the tool result or as MCP error responses; the PRD must pick one and test it.

---

## F-QUA-3 — Ctrl-C atomicity AC is untestable as written

**Severity:** P1

**Evidence:** F4 AC: "Aborting (Ctrl-C) at any step leaves the system in either the original state OR a fully-installed state — never partially installed." The PRD's strategy for proving this is "Tested in a clean Docker container against a vanilla Hermes install" — but the Docker test (last AC item) does not specify Ctrl-C injection. Interrupt-at-arbitrary-point testing requires either: (a) a synthetic `sleep` injected between steps and a test harness that sends SIGINT at each sleep; (b) a staged-directory design that makes partial states structurally impossible (the `trap EXIT` approach in the brainstorm), in which case the AC is about the `trap` mechanism not random Ctrl-C. The two framings require different test designs and neither is specified.

**Recommendation:** Replace the Ctrl-C AC item with a mechanism-level assertion: "install.sh registers a `trap EXIT` handler at startup that (a) removes `config.yaml.auraken-stage` if it exists and (b) restores `config.yaml.auraken.bak` to `config.yaml` if it exists. A pytest test (using `subprocess` + `SIGINT` sent after the staging-dir is written but before the atomic `mv`) confirms the handler fires and leaves no staging artifact." This makes the AC testable without random timing.

**Quality lens:** Unit-test feasibility — "random Ctrl-C is hard to repro" is resolved by testing the `trap` handler deterministically, not the interrupt itself.

---

## F-QUA-4 — voice-rubric.md "two-section schema" AC is structural, not behavioral: 3-5 examples is countable but not quality-gated

**Severity:** P2

**Evidence:** F6 AC: "Each section has 3-5 concrete examples and 1-2 anti-patterns." This is countable but not quality-gated — a reviewer can ship three trivially identical examples and pass the check. More critically, the AC does not specify what makes an example "concrete." The brainstorm's synthesis ("voice constraint, not recipe") introduces a distinction between constraint-testable and recipe-declarative examples, but the AC does not require any example to be phrased as a constraint (e.g., "if output contains a list of lenses offered to the user, it fails this rubric" is testable; "Auraken should feel like a camera" is not). The AC also doesn't require voice-rubric.md to be machine-parseable by `scripts/voice_check.py` (which already exists in the hermes integration tree).

**Recommendation:** Add: "At least two examples in `## Mandatory Form` are phrased as falsifiable constraints (i.e., a concrete output that would fail the rubric), not descriptions of desired behavior. `scripts/voice_check.py` loads `voice-rubric.md` without error." This turns a structural check into a behavioral one without requiring full automation.

**Quality lens:** AC specificity — countable but not verifiable against intent.

---

## F-QUA-5 — F9 ">=8/10 recognizably Auraken" has no scoring rubric location and no scorer identity

**Severity:** P1

**Evidence:** F9 AC: "At minimum, claude-opus-4-7 transcript is captured and scored against voice-rubric.md (target: 8/10 recognizably Auraken)." The AC does not specify: (a) where the rubric for mapping transcript to a numeric score lives — voice-rubric.md describes Mandatory Form and Permitted Variation but gives no aggregation method; (b) who scores (the implementing engineer? An LLM judge? A separate human reviewer?); (c) whether "8/10" is a blocking gate for the release or an aspirational target; (d) what happens if the first transcript scores 6/10 — is the release blocked, or is the score recorded in MANIFEST with a note?

**Recommendation:** Either (a) specify a machine scorer: "`scripts/voice_check.py --score tests/transcripts/v0.1-opus-4-7.md` returns score >= 8 (exit 0), where the script implements rubric criteria from `voice-rubric.md`"; or (b) acknowledge it is a human-reviewer gate and specify: "The transcript is reviewed by the release engineer against voice-rubric.md; a score sheet with per-criterion scores (Mandatory Form: N criteria pass/fail, Permitted Variation: observed/absent) is committed alongside the transcript. Aggregate score >= 8/10 gates the F8 release step." Without one of these, F9 is untestable in CI and non-reproducible across reviewers.

**Quality lens:** AC specificity — "8/10" without a rubric and a scorer is decorative.

---

## F-QUA-6 — "soundpost" is used as a technical term without a canonical definition in the PRD or any linked doc

**Severity:** P2

**Evidence:** "soundpost" appears three times in the PRD: in the Solution narrative ("incorporates the 'soundpost' decision"), in F2's feature title ("soundpost response shape"), and in F9's AC ("the lens MCP response shape is the single-object soundpost"). In the synthesis document (`2026-05-25-synthesis.md`), "soundpost" is an internal flux-review agent metaphor (`fd-luthier-soundpost-transmission`) that became shorthand for the single-object schema constraint. The PRD promotes this internal metaphor into a normative term without defining it. An implementer reading the PRD cold — particularly the F9 AC "single-object soundpost" — cannot determine the shape from the term alone. The actual shape (`{lens, rationale, next_question}`) is defined in F2 but is not cross-referenced from F9.

**Recommendation:** Remove "soundpost" from AC items where it substitutes for a concrete spec. Replace "the lens MCP response shape is the single-object soundpost" with "the lens MCP response shape is `{lens: str|null, rationale: str|null, next_question: str|null, empty: bool}` with no `lenses` key." Keep "soundpost" as explanatory prose in the Solution section where its metaphorical origin is appropriate. Add a footnote or inline gloss on first normative use if the term is to be retained as project vocabulary.

**Quality lens:** Naming consistency — internal flux-review agent names should not leak into normative AC without a definition.

---

## F-QUA-7 — F1 unit-test coverage is absent: MANIFEST validator has no specified test location or runner

**Severity:** P1

**Evidence:** F1 creates the MANIFEST schema and the MANIFEST.yaml. The only validation AC item is a manual `python3 -c` invocation. There is no AC item specifying a pytest, a `make validate`, or a `build-dist.sh --validate-only` target that runs as part of CI. F7 (build-dist.sh) specifies structural validation at script exit but does not reference F1's schema validator — so it's unclear whether build-dist.sh calls the JSON Schema validator or only checks file presence. The gap means MANIFEST schema evolution in v0.2 has no regression harness.

**Recommendation:** Add to F1 AC: "A pytest or shell-level test in `tests/unit/test_manifest.py` (or `tests/manifest-validate.sh`) verifies: (a) the v0.1 MANIFEST.yaml validates against `manifest.schema.json`; (b) a MANIFEST with a missing required field fails validation with a non-zero exit; (c) a `capabilities[].type` value outside `{skill, mcp-server, binary, asset}` fails validation." Add to F7 AC: "build-dist.sh invokes the F1 schema validator as step 1; exits non-zero if validation fails."

**Quality lens:** Test coverage adequacy — schema validators without regression tests are runtime surprises.

---

## F-QUA-8 — F2 unit tests do not specify where the pytest suite lives or how it is invoked

**Severity:** P2

**Evidence:** F2 AC: "pytest in `mcp-servers/auraken-lens/` verifies: shape contract holds for thinking-through input; null/empty path for factual input; graceful error on missing binary." The path `mcp-servers/auraken-lens/` is the source directory, not a test directory. The existing tree has no `tests/` subdirectory under `mcp-servers/auraken-lens/`. The AC does not specify the test file name, whether tests run against the dist bundle or the dev tree, or whether they are included in the bundle's `pyproject.toml` test dependencies. An implementer must decide all of this.

**Recommendation:** Specify: "Tests live at `mcp-servers/auraken-lens/tests/test_server.py`. `cd mcp-servers/auraken-lens && python -m pytest tests/` exits 0. Tests mock the Go binary via `subprocess` patching; no real binary is required for unit-test runs. The `pyproject.toml` `[project.optional-dependencies]` section lists `test = [\"pytest\", \"pytest-asyncio\"]`." This maps exactly to idiomatic Python MCP project layout and is implementable without re-deriving the decision.

**Quality lens:** Idiomatic Python conventions — test location is a first-class decision, not an afterthought.

---

## F-QUA-9 — F3 "deterministic build" AC conflicts with Go's build timestamp embedding

**Severity:** P2

**Evidence:** F3 AC: "Build script under `apps/Auraken/dist/build-binaries.sh` produces all four binaries deterministically." F7 AC: "Running the script twice produces byte-identical output (deterministic file ordering, no timestamps in files)." These assertions are technically ambitious: Go's default build injects build IDs but not timestamps; however, Go module proxy fetch times and `go mod download` cache state can produce different binary hashes across environments if the module cache is cold. The standard approach is `go build -trimpath -ldflags="-buildid="`. Neither F3 nor F7 specifies these flags. Without them, "byte-identical" is aspirational on a cold build machine.

**Recommendation:** Add to F3 AC: "Build flags include `-trimpath -ldflags='-buildid='` to suppress path and build-ID embedding. A determinism test runs the build script twice in the same environment and confirms `sha256sum` of both outputs matches." Reference `go build` reproducibility docs. Distinguish "byte-identical in same environment" from "bit-for-bit reproducible across machines" — v0.1 need only claim the former.

**Quality lens:** Go idioms — `-trimpath` and `-buildid=` are the canonical flags for Go build reproducibility; their absence from the AC will be re-derived (incorrectly) by the implementer.

---

## F-QUA-10 — F3 tag naming vs F8 tag naming creates two coexisting tag conventions with no disambiguation rule

**Severity:** P2

**Evidence:** F3 AC: "Go module tag `auraken-lens@v0.1.0` exists in git history." F8 AC: "Git tag `auraken-distribution/v0.1.0` exists." These are two different tag naming conventions in the same repo for the same release event: one follows Go module proxy convention (`<module>@<semver>`), the other follows a GitHub release convention (`<artifact>/<semver>`). The PRD does not state whether these are the same commit or different commits. A Go module tag at `auraken-lens@v0.1.0` requires the module root to be at a specific directory; if the Go module is at `apps/Auraken/dist/` (as F3 implies with `build-binaries.sh`) or at `os/Skaffen/pkg/lens/` (as the benl.1 PRD implies), the tag must be prefixed with the module's directory path within the monorepo to work with the Go module proxy (e.g., `apps/Auraken/dist/auraken-lens@v0.1.0`). This is a non-obvious monorepo Go module convention that the AC obscures.

**Recommendation:** Add a decision: "The `auraken-lens` Go binary is a separate Go module at `<path>/`. Its module proxy tag is `<directory-prefix>/auraken-lens@v0.1.0`. The distribution tag `auraken-distribution/v0.1.0` is a separate git tag on the same commit. Document both tags in the CHANGELOG." The benl.1 PRD (`docs/prds/2026-04-08-lens-go-package.md`) places the module at `os/Skaffen/pkg/lens/` — if the binary entrypoint is elsewhere, that conflict needs resolution before F3 work begins.

**Quality lens:** Go idioms — Go monorepo module tagging requires directory-prefixed tags; omitting this is a P0 implementation ambiguity.

---

## F-QUA-11 — "benl.1" Go package is unshipped as of the filesystem state; F2/F3 depend on it without a status gate

**Severity:** P1

**Evidence:** F2 AC references "the `auraken-lens` Go binary" and F3 references "Build the `auraken-lens` Go binary from `benl.1`." Searching the monorepo finds no `.go` files under `apps/Auraken/`, no `go.mod` at any auraken-related path, and no `auraken-lens` binary anywhere. The benl.1 PRD (`docs/prds/2026-04-08-lens-go-package.md`) describes `os/Skaffen/pkg/lens/` as the target location. That Go package is not confirmed shipped in the filesystem. The PRD lists `benl.1 Go package built and tagged at auraken-lens@v0.1.0` under Dependencies but does not gate F2 or F3 on benl.1's completion — meaning these features will block at implementation time if benl.1 is not done first.

**Recommendation:** Add an explicit dependency gate to F2 and F3: "Blocked on benl.1 (`sylveste-benl.1`) shipping a functional `auraken-lens` CLI binary at the agreed import path. If benl.1 is not complete at v0.1 work-start, stub the binary with a shell script that returns a hardcoded `{lens: null, rationale: null, next_question: null, empty: true}` for CI; document the stub in MANIFEST `compatibility_evidence` as `tested: false (binary: stub)`." This makes the dependency explicit and gives implementers a fallback path.

**Quality lens:** Documentation gaps — the PRD implies benl.1 is done; the filesystem says otherwise. This will surface as a blocker at plan-start.

---

## F-QUA-12 — F4 install.sh idempotency AC does not specify what "no duplicate config blocks" means structurally

**Severity:** P2

**Evidence:** F4 AC: "Running install.sh twice in a row produces no errors and no duplicate config blocks." Hermes `config.yaml` is a YAML file with a `mcp_servers:` key. "No duplicate config blocks" requires the installer to either (a) check for an existing `auraken-lens` entry before appending, or (b) use a named sentinel comment as a guard. The AC does not specify the detection mechanism — a naive `grep auraken-lens config.yaml` check will false-positive on comments and false-negative on a block with a renamed key. Without specifying the detection mechanism, two implementers will produce incompatible idempotency approaches.

**Recommendation:** Add to F4 AC: "Idempotency is implemented via a sentinel comment pair (`# BEGIN auraken-lens` / `# END auraken-lens`) that install.sh checks for before writing and that `--uninstall` uses as the removal boundary. Running install.sh when the sentinel block is present prints 'auraken-lens already registered; skipping.' and exits 0. A test confirms the sentinel is present exactly once after two installs."

**Quality lens:** Bash idioms — sentinel-comment delimiters are the standard bash installer idempotency pattern; the AC should specify this rather than leaving it to implementer discovery.

---

## F-QUA-13 — F5 INSTALL.md AC: "all commands are copy-pasteable" collides with "beyond an obvious profile name" exception — what is "obvious"?

**Severity:** P3

**Evidence:** F5 AC: "All commands in INSTALL.md are copy-pasteable (no placeholders for user to fill in beyond an obvious profile name)." "Obvious placeholder" is subjective. The existing recon-spike README uses `/ABSOLUTE/PATH` as a placeholder — that is clearly not copy-pasteable. But the profile name placeholder (e.g., `<your-profile>` vs `default`) is ambiguous: the install command either hard-codes a profile name or it doesn't. If it doesn't, "copy-pasteable" is false. If it does, is `default` the right name for all users?

**Recommendation:** Resolve the ambiguity: "INSTALL.md's install command uses `bash install.sh` with no profile argument; install.sh prompts for the profile interactively when one is not specified." OR: "INSTALL.md documents `bash install.sh --profile <profile-name>` with `<profile-name>` as the only placeholder, and the Prerequisites section defines how to find the user's profile name via `hermes profiles list`." Either resolution makes the AC testable.

**Quality lens:** Documentation gaps — this will generate a user support question on first external install.

---

## F-QUA-14 — Cross-file consistency: brainstorm's excluded_from_v01 uses opaque bead IDs; PRD's F1 AC corrects this, but brainstorm's MANIFEST.yaml example still uses old form

**Severity:** P3

**Evidence:** The brainstorm's Key Decisions MANIFEST.yaml example (lines 103-108) uses `- thinker-profile-mcp` with a comment `# → v0.3 (sylveste-i0px)`. The Synthesis-Driven Amendments section on line 45 states: "the list uses prose descriptors with bead IDs as a parenthetical." The PRD F1 AC correctly implements this (prose string with bead ref as parenthetical). The brainstorm's example is now inconsistent with the PRD's AC. Since the brainstorm's YAML example is the most concrete schema illustration available, an implementer reading the brainstorm alongside the PRD will be confused about which form is normative.

**Recommendation:** Update the brainstorm's MANIFEST.yaml example to match the PRD's AC form, or add a note in the PRD: "The MANIFEST.yaml example in the brainstorm uses an older form; the AC here is authoritative." Low effort; prevents downstream confusion when the brainstorm is referenced in the plan.

**Quality lens:** Cross-file consistency — the brainstorm is the closest thing to a schema example; it should match the PRD.

---

## F-QUA-15 — F8 GPG signing: signing identity decision is deferred to plan but F8 AC presumes its resolution

**Severity:** P2

**Evidence:** F8 AC: "checksums.txt.asc verifies against a known public key documented in INSTALL.md." PRD Open Question #2: "GPG signing identity — use mistakeknot's existing GPG key, or generate a project-specific key?" The AC presumes a public key exists and is documented; the signing-identity decision is deferred to plan. If plan resolves "use mistakeknot's existing key," the key ID must be discoverable and documented. If it resolves "generate project-specific key," the key generation and publication steps are non-trivial and are unscoped from F8. Either way, F8's last AC item cannot be verified until the plan resolves the identity question — but the PRD does not flag this as a dependency.

**Recommendation:** Either (a) resolve the signing identity in the PRD ("F8 uses mistakeknot's existing GPG key at fingerprint `<key-id>`; INSTALL.md documents `gpg --recv-keys <key-id> && sha256sum -c checksums.txt && gpg --verify checksums.txt.asc`"); or (b) add to F8 AC: "Blocked on Open Question #2 resolution. Plan phase commits the signing identity before F8 implementation begins." Make the dependency explicit rather than implicit.

**Quality lens:** Documentation gaps — GPG key identity is a release-blocking decision; leaving it to plan while writing AC as if it's resolved creates a false sense of completeness.

---

## Summary

| ID | Severity | Title |
|---|---|---|
| F-QUA-1 | P1 | MANIFEST schema language and schema-file location are unresolved |
| F-QUA-2 | P1 | "Graceful error on missing binary" is undefined |
| F-QUA-3 | P1 | Ctrl-C atomicity AC is untestable as written |
| F-QUA-4 | P2 | voice-rubric.md "two-section schema" AC is structural, not behavioral |
| F-QUA-5 | P1 | F9 ">=8/10 recognizably Auraken" has no scoring rubric or scorer |
| F-QUA-6 | P2 | "soundpost" used as normative term without definition |
| F-QUA-7 | P1 | F1 MANIFEST validator has no unit-test location or runner specified |
| F-QUA-8 | P2 | F2 unit tests do not specify test location or invocation |
| F-QUA-9 | P2 | F3 "deterministic build" AC conflicts with default Go binary hashing |
| F-QUA-10 | P2 | F3 vs F8 tag naming conventions conflict; monorepo Go module prefix unresolved |
| F-QUA-11 | P1 | benl.1 Go package not shipped; F2/F3 depend on it without a gate |
| F-QUA-12 | P2 | F4 idempotency AC does not specify detection mechanism |
| F-QUA-13 | P3 | F5 INSTALL.md "copy-pasteable" exception is undefined |
| F-QUA-14 | P3 | Brainstorm MANIFEST.yaml example inconsistent with PRD's excluded_from_v01 form |
| F-QUA-15 | P2 | F8 GPG signing identity deferred to plan but AC presumes resolution |

**Severity counts:** P0: 0 / P1: 6 / P2: 6 / P3: 3

**Highest-leverage finding: F-QUA-11.** The benl.1 Go package (`os/Skaffen/pkg/lens/`) does not exist in the filesystem. F2 (MCP server rewrite) and F3 (prebuilt binaries) both depend on it. The PRD lists benl.1 as a dependency but neither gates F2/F3 on it nor provides a stub fallback. Without a fallback stub, F2 and F3 cannot be integrated or tested at all until a separate bead ships. This is the most likely cause of plan-start blockage.
