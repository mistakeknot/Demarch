<!-- run-uuid: 2d871615-d6bb-4cfd-98c8-abc8112442d7 -->

### Findings Index
- P1 | MY-01 | "install.sh contract" | Colonization assumed, never observed — install.sh has no take-check after deposit
- P1 | MY-02 | "Bundle layout / install.sh contract" | No substrate-readiness check — install.sh detects Hermes version but not profile composition
- P2 | MY-03 | "MANIFEST.yaml schema" | MANIFEST lists model compatibility but does not flag substrate-incompatibility cases (hostile profiles, competing personalities)
- P2 | MY-04 | "What We're Building / install.sh contract" | No first-72-hours scaffolding — the colonization window is unstructured
- P2 | MY-05 | "Bundle layout / mcp-servers/auraken-lens/trajectory.py" | trajectory.py's colonization role is unspecified — passive responder or active habit-reshaper?
Verdict: needs-changes

---

## Summary

Mycorrhizal colonization fails silently when substrate conditions are wrong: the fungal culture is present in the soil, germination appears to have occurred, and the matsutake mycelium is technically alive — but it never forms the symbiotic relationship with the host tree that produces fruiting. The host and inoculum coexist without integration. This brainstorm describes exactly this failure mode for Auraken: install.sh deposits the culture (SKILL.md + MCP), but nothing in the distribution verifies that colonization is occurring rather than coexistence.

The two P1 findings address the most dangerous gap: there is no take-check (the inoculum is installed with no observation of whether the looking-discipline actually emerges in the first conversation), and there is no substrate-readiness check (the installer does not assess whether the destination profile's existing habits are hostile or receptive). A Hermes profile with an aggressive system-prompt prefix, a competing personality skill, or a model known to suppress instruction-following will silently kill the culture.

trajectory.py exists in the bundle — its name suggests interaction tracking — but the brainstorm does not specify its behavior. This is the most promising colonization-window instrument in the bundle, and it is undefined.

---

## Issues Found

**1. [P1] MY-01 — Colonization assumed, never observed — install.sh has no take-check**

Section: "install.sh contract" — step 6.

Step 6 reads: "Prints next steps: how to invoke `/auraken`, where logs go, how to uninstall." This is the final action of install.sh. After this print, the bundle is considered installed. There is no mechanism for verifying that the first invocation of `/auraken` exhibits Auraken-stance rather than generic model behavior with a lens-selection tool available.

Failure scenario: User on a profile with model `gpt-5.5` (noted in MANIFEST as having "observed register drift documented") installs the bundle. install.sh completes successfully. User invokes `/auraken`, receives a response from the model that exhibits generic behavior — offers options, describes its own methodology, does not open with a single question. The user concludes "Auraken is installed and this is what it does," normalizes the register-drifted behavior, and the looking-discipline never colonizes. The bundle is installed; Auraken is not present.

The mycorrhizal parallel: a forager inoculating a matsutake substrate does not walk away after introducing the culture. They return in 48-72 hours to check for mycelial threads — early indicators that colonization is occurring, not just that the culture was deposited. The bundle has no equivalent of the 48-hour check.

Smallest viable fix: Add a step 6.5 to the install.sh contract: "Generates a 'first invocation check' prompt and prints it at the end of setup. The prompt tells the user: 'After your first `/auraken` conversation, check: did Auraken open with a question rather than a statement? If not, see INSTALL.md § Colonization Check.' This is a post-install observation scaffold, not an automated test — it tells the user what to look for to know the inoculum is taking."

**2. [P1] MY-02 — No substrate-readiness check — install.sh detects Hermes version but not profile composition**

Section: "install.sh contract" — steps 1-3.

The install.sh contract specifies:
1. Detects Hermes install location
2. Asks which profile to install into (lists profiles)
3. Validates Hermes version against MANIFEST compatibility range

Step 2 lists profiles but does not inspect their contents. Step 3 checks Hermes version but not profile composition. The installer treats any Hermes profile above version `>=2026.4.0` as uniformly receptive substrate — analogous to assuming any soil above freezing temperature will support matsutake inoculation.

Failure scenario: User selects a Hermes profile that already contains a strong personality overlay (e.g., a "coder-agent" skill that opens every conversation with a code block and suppresses freeform questioning). install.sh copies `skills/auraken/` into this profile. Now two personality skills coexist. Hermes's skill-loading behavior determines which wins — but the brainstorm does not specify Auraken's skill priority, and install.sh provides no warning. The inoculum lands in hostile substrate. The coder-agent's calling-habits dominate; Auraken's looking-discipline never colonizes.

The substrate-readiness check the brainstorm omits: after step 2 (profile selection), inspect `~/.hermes-*/profiles/<selected>/skills/` for existing `SKILL.md` files. If found, surface them to the user: "This profile contains personality skills: [names]. Auraken's colonization may be affected by competing personality declarations. Proceed with caution?"

Smallest viable fix: Add to step 2 of the install.sh contract: "After profile selection, scans the chosen profile's skills/ directory for existing SKILL.md files. If any are found, prints: 'Profile contains existing personality skills: [names]. Auraken installs as an additive overlay — if another skill dominates the opening behavior, Auraken's posture may not establish. Proceed? [y/N]'"

**3. [P2] MY-03 — MANIFEST model compatibility does not flag substrate-incompatibility**

Section: "MANIFEST.yaml schema (v1)" — `compatibility.models`.

The MANIFEST lists:
```yaml
models:
  openai:
    - gpt-5.5                      # observed register drift documented
    - gpt-5.4
```

The comment "observed register drift documented" is the only signal that `gpt-5.5` is potentially hostile substrate. But this comment is internal to the MANIFEST — a user reading it has no way to know what "register drift" means for Auraken colonization, whether it is mild (slight voice deviation) or severe (complete suppression of the looking-discipline).

The mycorrhizal parallel: a substrate-readiness profile for matsutake inoculation specifies pH range, moisture level, competing organism counts, and tree species. "compatible" is not binary — it is a gradient with thresholds below which colonization fails. The MANIFEST currently has no colonization-risk rating per model.

Smallest viable fix: Extend the MANIFEST schema with a `colonization_notes:` field per model:
```yaml
models:
  openai:
    - id: gpt-5.5
      colonization_notes: "Observed register drift — opening-with-one-question posture degraded; never-offer-menu posture partially suppressed. Colonization possible but requires voice-rubric verification after first invocation."
```
This surfaces substrate risk at the manifest level where both the installer and the user can read it.

**4. [P2] MY-04 — No first-72-hours scaffolding — colonization window is unstructured**

Section: "What We're Building" — bundle-as-artifact framing.

The brainstorm frames v0.1 as "the bundle as artifact" — a drop-in distribution. There is no concept of a colonization window: the period immediately after inoculation when the culture is most vulnerable and the substrate's existing habits most competitive. For mycorrhizal inocula, this is typically 48-96 hours; for a cognitive habit like Auraken's looking-discipline, this might be the first 5-10 invocations.

The brainstorm specifies no INSTALL.md content (beyond "user-facing install instructions"). This means the plan phase will write INSTALL.md without any guidance about what the first week of Auraken use should look like. INSTALL.md will likely describe how to install and how to invoke — and say nothing about how to know that colonization is taking.

Failure scenario: User installs Auraken, invokes it 3 times, finds that it "asks questions" but does not visibly change how they see problems. They conclude Auraken doesn't work for them and uninstall. The colonization window closed before the mycelium had time to establish. No post-install guidance existed to tell them: "The discipline takes 5-7 invocations to establish. In the first 3 sessions, notice whether you're being shown something you weren't looking for — this is the early colonization signal."

Smallest viable fix: Add to the "What We're Building" section: "INSTALL.md must include a '§ First Week' section that describes the colonization window: what to look for in the first 5-7 invocations to know the looking-discipline is establishing, and what to do if it isn't (substrate-incompatibility diagnosis)."

**5. [P2] MY-05 — trajectory.py's colonization role is unspecified**

Section: "Bundle layout / mcp-servers/auraken-lens/trajectory.py."

The bundle includes `trajectory.py` in the `auraken-lens` MCP server. Its name implies interaction tracking — recording the trajectory of lens selections and conversation patterns over time. If this is what it does, it is the bundle's highest-leverage colonization-window instrument: it could detect early in the user's usage whether Auraken's calling-habits are establishing (user invokes single-question openings, accepts lens-selection without asking for alternatives) or whether the existing habits are dominating (user immediately asks follow-up questions that treat Auraken as a Q&A system).

But the brainstorm does not specify trajectory.py's behavior. The document lists it as a file that exists — not what it does, not whether it actively reshapes calling-habits (colonization) or only records existing habits (deposit without colonization).

Failure scenario: trajectory.py is implemented as passive logging — records which lenses were selected and when, for later analysis. The user's calling-habits are recorded but not interrupted. The bundle has the instrument for active colonization (a file explicitly named for tracking how the interaction trajectory develops) but uses it only as a passive observer. The inoculum has mycorrhizal threads but they never extend toward the host's root system.

Smallest viable fix: Add one sentence to the bundle layout description: "trajectory.py tracks the interaction trajectory — at minimum, it should detect whether the first invocation exhibited Auraken-stance (opened with a question) and surface this to the user via a log message or INSTALL.md reference. Passive logging is insufficient; trajectory.py is the bundle's primary colonization-window instrument."

---

## Improvements

1. **Add take-check step to install.sh** — step 6.5 generates a "first invocation check" observation prompt that tells the user what to look for after the first `/auraken` conversation. This is the 48-hour mycelial check.

2. **Add substrate-readiness scan to install.sh step 2** — inspect the destination profile's skills/ directory for existing personality SKILL.md files and surface them to the user before proceeding.

3. **Add `colonization_notes:` field to MANIFEST model entries** — documents substrate risk per model so users and INSTALL.md can set appropriate expectations.

4. **Specify '§ First Week' section in INSTALL.md** — describe the colonization window: what signals indicate the looking-discipline is establishing, what to do if it isn't (which substrate-incompatibility to diagnose first).

5. **Specify trajectory.py's active vs passive role** — the brainstorm must state whether trajectory.py actively reshapes calling-habits or only observes them. If passive, it is underutilized. If active, its colonization mechanism must be described.

---

--- VERDICT ---
STATUS: warn
FILES: 0
FINDINGS: 5 (P0: 0, P1: 2, P2: 3, P3: 0)
SUMMARY: Two P1 findings expose deposit-without-colonization: no take-check after install and no substrate-readiness check before deposit. Both are small additions to the install.sh contract specification that prevent the bundle from being silently installed into hostile substrate without signaling failure.
---
<!-- flux-drive:complete -->
