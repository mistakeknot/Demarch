# adjudication — round 3

## Findings Index
- [P2] mycroft-drain-flag-is-dead-parameter — pauseCmd registers `--drain` but RunE never reads it; claim (2) is the fully-grounded version of the contradiction, claim (1) overstates shipped capability (§1/§5/§7, main.go:230-247,427)
- [P2] rimsky-brief-still-has-no-v1-abort-story — even with the corrected (weaker) Mycroft characterization, Q6's anti-abandonment framing never asks whether shippable-v1 needs a safe-abort/pause path for an in-flight fan-out (§5 Q6)

## Findings

### mycroft-drain-flag-is-dead-parameter
- Severity: P2
- Where: `apps/Autarch/cmd/mycroft/main.go:230-247` (pauseCmd.RunE), `main.go:427` (flag registration); brief §1 framing, §5 Q6, §7
- What: Claim (2) is CONFIRMED and should be adopted as the resolution; claim (1) is refuted on the specific "coordinated graceful-stop primitive (`pause --drain`)" characterization. Reading the full RunE body: `pauseCmd` opens the DB, calls `d.LogPause()` unconditionally, prints "Dispatching paused. In-flight agents will continue." — a message that is true regardless of whether `--drain` was passed — and returns. There is no `cmd.Flags().GetBool("drain")` call anywhere in the 434-line file (confirmed via full-file grep for drain/Drain), no branch on the flag's value, and no signal-dispatch or checkpoint codepath reachable from it. The flag is registered on the Cobra command (line 427: `pauseCmd.Flags().Bool("drain", false, "Also signal in-flight agents to checkpoint and stop")`) and nowhere else. This is not "graceful-stop" — it's a documented no-op. What Mycroft *does* ship as working code is exactly claim (2)'s narrower description: `pause`/`resume` as a "stop new dispatch only" pair (LogPause/LogResume, ~15 lines of state plus DB-logged events per the settled fact), which is real, complete, and reusable.
- Evidence: `main.go:230-246` full RunE body shows no flag read; `main.go:427` shows the flag exists only as a registration with a help string describing intended-but-unbuilt behavior; grep across the whole file for `GetBool|drain|Drain` returns only the registration line and the `Short`/help-text strings, zero call sites that branch on it.
- Suggestion: n/a (adjudication, not a code fix)
- Remediation: When synthesizing Q6/anti-abandonment guidance, cite Mycroft's shipped abort-adjacent primitive as "pause/resume (stop-new-dispatch-only)" only — never as "pause --drain" or "graceful-stop" — since the drain half is an unread Cobra flag with no implementation.

### rimsky-brief-still-has-no-v1-abort-story
- Severity: P2
- Where: §5 Q6 (lines 115-117), §7 (lines 128-134)
- What: Independent of which Mycroft characterization wins, the underlying gap both prior findings pointed at survives: the brief's only kill/abort/cancel/drain/pause/stop vocabulary is the deferred-P3 "dynamic kill-rule controller" (line 71), and Q6 asks only "one goal or v1+v2 decomposition, where do the gates go" — it never asks whether shippable-v1 (instrument + flat fan-out + cost gate) needs *any* safe-abort path for an in-flight fan-out that's already running when a human wants to stop it. Given that Mycroft's real, working, minimal mechanism (stop-new-dispatch-only) is cheap to reuse and directly answers "how do you stop a bad fan-out without corrupting in-flight work," its absence from Q6's question list is a scope gap, not just a citation gap.
- Evidence: brief line 71 is the only hit for kill|abort|cancel|drain|pause|stop outside this adjudication file; §5 Q6 (115-117) and §7 completion shape (128-134) both omit any abort-path acceptance criterion for v1.
- Suggestion: n/a
- Remediation: Add to Q6 an explicit sub-question — "does shippable-v1 need a stop-new-dispatch-only abort path (reusable from Mycroft's pause/resume), independent of the deferred P3 kill-rule controller" — so the v1/v2 cut doesn't silently ship a fan-out with no safe way to halt it mid-run.

## Verdict
Claim (2) holds as written and should be treated as the confirmed resolution; claim (1) is refuted on its strongest specific ("coordinated graceful-stop primitive (`pause --drain`)") because that flag is registered but never read — dead surface area, not working code. This is not a taste call: `grep`-verified absence of any `GetBool("drain")` call site is a factual, binary check, not an aesthetic judgment about what counts as "coordinated." The prior P1 confirmation (adjacent shipped prior art exists) survives via the narrower true claim — pause/resume alone, stop-new-dispatch-only — and that narrower claim is what should propagate into synthesis and into Q6.
