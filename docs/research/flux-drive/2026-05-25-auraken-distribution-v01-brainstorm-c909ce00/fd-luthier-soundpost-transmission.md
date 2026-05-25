<!-- run-uuid: 2d871615-d6bb-4cfd-98c8-abc8112442d7 -->

### Findings Index
- P1 | LU-01 | "install.sh contract" | install.sh constitutes placement, not voicing — the instrument is deposited, not adjusted to the room
- P1 | LU-02 | "Bundle layout / SKILL.md" | SKILL.md's behavioral contract is declarative, not structural — the soundpost is glued, not wedged
- P1 | LU-03 | "Bundle layout / mcp-servers/auraken-lens" | auraken-lens MCP API surface is unconstrained — no behavioral coupling to Auraken personality means the soundpost is absent
- P2 | LU-04 | "Bundle layout / voice-rubric.md" | voice-rubric.md is recipe transmission, not constraint transmission — examples decay across model versions
- P2 | LU-05 | "MANIFEST.yaml schema / capabilities" | Version-pinning preserves API contract but not soundpost calibration — the binary's specific gesture-forcing behavior is undocumented
Verdict: needs-changes

---

## Summary

The Cremonese luthier tradition holds that the soundpost — a small wooden cylinder wedged between top and back plate — determines whether an instrument resonates with the maker's specific voice or as a generic wooden box. Remove the soundpost and the violin plays; it just no longer carries the maker's ear. This brainstorm ships a bundle with all the structural components present but no soundpost: the MCP API surface is unconstrained, SKILL.md's behavioral contract is declarative, and install.sh constitutes a deposit rather than a voicing.

The three P1 findings converge on the same failure mode: a user installs the bundle, invokes `/auraken`, and receives generic model behavior with the lens-selection tool available. The Auraken-stance (never-offer-menu, opening-with-one-question) survives only if the model happens to follow SKILL.md — but nothing in the MCP schema, the tool return shapes, or the prompt-template constraints forces the right gestures. The maker's ear is glued on, not wedged in.

---

## Issues Found

**1. [P1] LU-01 — install.sh constitutes placement, not voicing**

Section: "install.sh contract" — steps 4 and 5.

The contract describes: "Copies `skills/auraken/` into the chosen profile's `skills/`" and "Builds + registers the `auraken-lens` MCP server." This is the act of depositing an instrument in a new room, not the act of voicing it for that room. A Cremonese luthier who ships an instrument to a new climate adjusts the soundpost position after delivery — the act of copying SKILL.md into the profile makes no such adjustment.

Failure scenario: User has a Hermes profile with specific system-prompt conventions, a non-default temperature setting, or model-level overrides that suppress SKILL.md's behavioral constraints. install.sh deposits the SKILL.md without reading the room. The instrument plays but produces the wrong voice — the maker's ear does not travel because no voicing step occurs.

The brainstorm's install.sh contract has no step that reads the destination profile's existing configuration and adjusts the SKILL.md installation accordingly (e.g., detecting conflicting personality overlays, noting the model's known register-drift characteristics from the MANIFEST model matrix). This is the missing voicing step.

Smallest viable fix: Add a step 3.5 to the install.sh contract: "Reads the destination profile's existing skills/ for conflicting personality declarations. If found, warns: 'Profile contains personality overlay [name] — Auraken may not voice correctly alongside it. Proceed?' This is a check, not a block — it surfaces the room before the instrument is placed."

**2. [P1] LU-02 — SKILL.md's behavioral contract is declarative, not structural**

Section: "Bundle layout" — `skills/auraken/SKILL.md`.

The brainstorm describes SKILL.md as "copied/symlinked from ../../skills/auraken/SKILL.md." The actual content of SKILL.md is not specified in the brainstorm, but the agent's prior context establishes that it contains the never-offer-menu posture and opening-with-one-question as its core behavioral constraints. These are specified as: "the agent should..." — declarative language.

Failure scenario: User upgrades their Hermes model from `claude-haiku-4-5-20251001` to a new model version that has been instruction-tuned to be more proactive with menus and option-lists. SKILL.md's declarative constraints ("do not offer menus") are overridden by the model's base behavior. The soundpost falls out: the instrument plays, but the specific way of resonating — the never-offer-menu posture that constitutes the maker's ear — is absent.

The structural alternative is a SKILL.md that enforces the posture through tool schema constraints: if the only available tool returns a single lens (not a list to choose from), the model cannot offer a menu regardless of its base behavior. The MCP tool schema is the geometry; the geometry doesn't permit the wrong sound.

The brainstorm does not specify whether SKILL.md's contracts are declarative or structural. This gap will propagate to the plan phase, which will implement SKILL.md without the constraint-over-example discipline.

Smallest viable fix: Add one constraint to the bundle layout description: "SKILL.md's behavioral constraints (never-offer-menu, opening-with-one-question) must be cross-referenced against the auraken-lens tool schema — if the tool can return multiple lenses as a list, the declarative constraint alone is insufficient. The tool should return one lens with rationale, not a list to select from."

**3. [P1] LU-03 — auraken-lens MCP API surface is unconstrained — soundpost absent**

Section: "Bundle layout / mcp-servers/auraken-lens/" — server.py, trajectory.py.

The brainstorm specifies the MCP server's file structure (server.py, trajectory.py, pyproject.toml) but not its API surface. The `auraken-lens` MCP "registered" by install.sh is callable by any agent in any posture — the brainstorm has no specification of what gestures the tool schema forces or forbids.

Failure scenario: A user with Auraken installed invokes `/auraken` alongside another Hermes skill that also has access to `auraken-lens`. That other skill calls the lens-selection tool with no Auraken personality context active. The tool returns lens candidates; the other agent uses them without the looking-discipline. The MCP is now decoupled from the personality — the soundpost (the coupling between maker's ear and instrument body) is absent. The tool works but carries no voice.

More critically: if `auraken-lens` exposes `select_lens(query)` → `[lens1, lens2, lens3]` (a list), then even the Auraken personality cannot enforce never-offer-menu — it receives a list from its own tool and must then decide not to show it. The constraint is now in SKILL.md's declarative posture, which is exactly the glued-on soundpost.

The structural fix is a tool schema that returns `{lens: ..., rationale: ..., next_question: ...}` — one lens, one rationale, one move. The schema itself prevents the model from offering alternatives because there are no alternatives to show.

Smallest viable fix: Add to the brainstorm's `auraken-lens` section: "server.py's primary tool must return a single-lens response shape `{lens, rationale, next_question}`, not a list. This is a schema constraint, not a behavioral suggestion — the shape prevents multi-lens enumeration regardless of model posture." This is a one-sentence addition that determines whether the soundpost is wedged in or glued on.

**4. [P2] LU-04 — voice-rubric.md is recipe transmission, not constraint transmission**

Section: "Bundle layout" — `skills/auraken/voice-rubric.md`.

The brainstorm describes voice-rubric.md as "extracted voice criteria for register_check." This is criteria-as-recipe: the rubric tells a checker what Auraken sounds like, which allows the checker to verify imitation. But imitation decays across model versions and providers. The MANIFEST model matrix notes "observed register drift documented" for gpt-5.5 — this is exactly the decay that recipe transmission produces.

Cremonese luthiers did not transmit ear by writing down what a good violin sounds like. They transmitted it through the geometry: the specific f-hole positioning, the arch height, the thickness graduation. These geometric constraints produce the sound without a checker needing to verify that the sound is correct — the wrong sound is impossible given the geometry.

voice-rubric.md as currently conceived checks whether the output sounds right. A constraint-based voice-rubric would specify what response shapes are structurally prohibited (offering a menu, describing the method before asking the question, providing analysis before invitation). Prohibition-based constraints hold across model upgrades; example-based criteria do not.

Smallest viable fix: Specify in the brainstorm that voice-rubric.md must include at least three structural prohibitions ("Auraken cannot: list multiple options for the user to choose from; describe its own methodology before the user's first response; provide a full analysis before asking a question") alongside any examples. The prohibitions are checkable regardless of model version.

**5. [P2] LU-05 — Version-pinning preserves API contract but not soundpost calibration**

Section: "MANIFEST.yaml schema" — `binary_required: github.com/mistakeknot/Sylveste/apps/Auraken/dist/auraken-lens@v0.1.0`.

The MANIFEST pins the lens binary at `@v0.1.0`. This preserves the API contract (the function signatures, the tool schema, the response format). But the brainstorm does not specify what `@v0.1.0` of the binary actually constrains — whether the `select_lens` response shape is a list or a single-lens object is not documented in the version pin.

SemVer on the binary (`@v0.1.0`) means breaking changes increment the major version. But "breaking" in SemVer means API breakage — it does not mean soundpost-calibration breakage. A `@v0.1.1` patch release that changes the selection algorithm (returning different lenses) is not a SemVer break, but it changes the maker's specific calibration without the MANIFEST detecting it.

Smallest viable fix: Add a note in the MANIFEST schema section: "The `binary_required` pin must be accompanied by a `binary_behavior_contract` field that documents the expected single-lens response shape and the selection algorithm version. This is separate from the API version — soundpost calibration changes without API changes must still be documented."

---

## Improvements

1. **Specify `auraken-lens` single-lens response shape** — this is the highest-leverage single constraint in the brainstorm. One sentence in the mcp-servers section determines whether the soundpost is wedged or glued.

2. **Add profile-conflict detection to install.sh** — step 3.5 that reads the destination profile's existing personality declarations before depositing the SKILL.md. This is the voicing step: adjusting the instrument to the room.

3. **Cross-reference SKILL.md constraints against MCP schema** — the brainstorm should state that SKILL.md's declarative constraints must be backed by structural couplings in the tool schema wherever possible. Each declarative "should not" should have a corresponding schema-level enforcement.

4. **Specify prohibition-based voice-rubric criteria** — at least three structural prohibitions in voice-rubric.md that hold across model versions, distinct from example-based criteria.

5. **Add `binary_behavior_contract` to MANIFEST schema** — documents what the pinned binary is expected to *do*, not just what API it exposes. Soundpost-calibration changes are documented separately from API changes.

---

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 3, P2: 2, P3: 0)
SUMMARY: Three P1 findings converge on the same structural failure — the auraken-lens MCP API is unconstrained, SKILL.md's posture is declarative, and install.sh deposits rather than voices — together these mean the maker's ear does not travel with the bundle. The highest-leverage single fix is specifying the single-lens response shape for auraken-lens server.py.
---
<!-- flux-drive:complete -->
