---
artifact_type: research
bead: Sylveste-sqq
goal: ceb0f3a6
---

# Hook Inventory & Exec-Form Conversion — 2026-07-22

Every command-hook entry across os/Clavain and the interverse plugins,
classified and converted per CC 2.1.139's exec-form capability (goal
ceb0f3a6, bead Sylveste-sqq).

**Grounding** (live docs + changelog, fetched 2026-07-22): presence of
`args: string[]` makes a hook exec-form — the command is spawned directly
with no shell; `${CLAUDE_PLUGIN_ROOT}` placeholders substitute as plain
strings into command and each args element. `continueOnBlock` (changelog
2.1.139, not yet on the docs page): PostToolUse-only — `true` feeds the
hook's rejection reason back to Claude and continues the turn.

**Result: 59 live entries — 58 exec-form (44 converted this pass, 14 were
bare paths converted via `args: []`), 1 kept shell-form with reason.**
All referenced scripts verified executable (exec-form spawns directly).
Version floor: exec-form fields require CC >= 2.1.139; the interagency
marketplace is personal and current (2.1.216), so no compatibility shim.

**Blocking analysis**: exactly ONE PostToolUse hook emits a block today —
Clavain's `agents-md-refresh.sh` (`decision:block` with an advisory
"run /interdoc" reason). It is the sole feedback-worthy gate and now
carries `continueOnBlock: true`, so its reason reaches Claude without
ending the turn. No other gate blocks; making non-blocking gates
(e.g. auto-publish) start blocking would be a semantic change, explicitly
out of scope per charter.

**Deprecated**: interfluence's single hook is intentionally disabled
(`_original_hooks`, migration to intervoice) — untouched.

| plugin | event | matcher | form | command | note |
|---|---|---|---|---|---|
| intercheck | PostToolUse | Edit|Write|NotebookEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/syntax-check.sh` |  |
| intercheck | PostToolUse | Edit|Write|NotebookEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/auto-format.sh` |  |
| intercut | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interflux | SessionStart | * | exec | `bash` |  |
| interflux | SessionStart | * | exec | `bash` |  |
| interhelm | PostToolUse | mcp__plugin_tuivision_tu | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/browser-on-native.sh` |  |
| interhelm | PostToolUse | Edit|Write | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/auto-health-check.sh` |  |
| interhelm | PostToolUse | Bash | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/cuj-reminder.sh` |  |
| interject | SessionStart |  | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interkasten | SessionStart |  | exec | `bash` |  |
| interkasten | SessionStart |  | exec | `bash` |  |
| interkasten | Stop |  | exec | `bash` |  |
| interknow | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interlab | SessionStart |  | exec | `bash` |  |
| interlearn | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh` |  |
| interline | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interlock | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interlock | PreToolUse | Edit|Write|MultiEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/pre-edit.sh` |  |
| interlock | Stop | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/stop.sh` |  |
| interlock | SubagentStop | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/subagent-stop.sh` |  |
| intermem | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| intermux | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interphase | PostToolUse | Bash|Edit|Write|MultiEdi | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/heartbeat.sh` |  |
| interphase | PostToolUse | Bash | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/bead-autoclaim.sh` |  |
| interphase | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-end-release.sh` |  |
| interpulse | PostToolUse | Edit|Write|Bash|Task|Not | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/context-monitor.sh` |  |
| intership | SessionStart |  | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interspect | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/interspect-session.sh` |  |
| interspect | PostToolUse | Task | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/interspect-evidence.sh` |  |
| interspect | Stop |  | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/interspect-session-end.sh` |  |
| interstat | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interstat | PostToolUse | Task | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/post-task.sh` |  |
| interstat | PostToolUse | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/post-tool-all.sh` |  |
| interstat | PostToolUseFailure | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/post-tool-failure.sh` |  |
| interstat | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-end.sh` |  |
| intersynth | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| intertrack | SessionStart | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| interwatch | PreToolUse | Read|Edit|Write|MultiEdi | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/pretool-doc-access.sh` |  |
| tool-time | PreToolUse | Task | exec | `bash` |  |
| tool-time | PostToolUse | * | exec | `bash` |  |
| tool-time | SessionStart | * | exec | `bash` |  |
| tool-time | SessionEnd | * | exec | `bash` |  |
| tool-time | SessionEnd | * | shell | `INPUT=$(cat); echo "$INPUT" | bash "$CLAUDE_PLUGIN_ROOT/scripts/emit-i` | compound shell (pipe/subst/fallback chain) — needs a shell by design |
| Clavain | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh` |  |
| Clavain | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/peer-telemetry.sh` |  |
| Clavain | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/release-canary-check.sh` |  |
| Clavain | SessionStart | startup|resume|clear|com | exec | `${CLAUDE_PLUGIN_ROOT}/scripts/remontoire-attention.sh` |  |
| Clavain | PreToolUse | Edit|Write|MultiEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/guard-plugin-cache.sh` |  |
| Clavain | PostToolUse | Skill | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/peer-routing-telemetry.sh` |  |
| Clavain | PostToolUse | Bash | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/auto-publish.sh` |  |
| Clavain | PostToolUse | Bash | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/bead-agent-bind.sh` |  |
| Clavain | PostToolUse | Bash | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/agents-md-refresh.sh` | continueOnBlock=true: advisory block, reason instructs /interdoc |
| Clavain | PostToolUse | Edit|Write|MultiEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/catalog-reminder.sh` |  |
| Clavain | PostToolUse | Edit|Write|MultiEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/validate-plugin-edit.sh` |  |
| Clavain | PostToolUse | Edit|Write|MultiEdit | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/temple-invariant.sh` |  |
| Clavain | Stop | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/auto-stop-actions.sh` |  |
| Clavain | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/dotfiles-sync.sh` |  |
| Clavain | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/auto-push.sh` |  |
| Clavain | SessionEnd | * | exec | `${CLAUDE_PLUGIN_ROOT}/hooks/gate-calibration-session-end.sh` |  |

Shell-kept entry (tool-time SessionEnd): a stdin-tee pipeline with
redirect and fallback chain — needs a shell by design; left as-is.

