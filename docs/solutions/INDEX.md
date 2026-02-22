# Solution Docs Index

Cross-repo index of institutional knowledge across the Interverse monorepo.

**Generated:** 2026-02-21T15:30:46Z | **Total:** 73 docs

---

## agent-rig (3 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Best Practice: Reversible CLI Installation with MCP Server Configuration](infra/agent-rig/docs/solutions/best-practices/reversible-cli-install-with-mcp-config-agent-rig-20260211.md) | best_practice | high | 2026-02-11 | mcp-servers, state-tracking, uninstall, claude-code, reversible-install, cli-lifecycle |
| [Best Practice: State-Diff Incremental Updates with Dependency Ordering](infra/agent-rig/docs/solutions/best-practices/state-diff-incremental-update-agent-rig-20260211.md) | best_practice | medium | 2026-02-11 | state-diff, incremental-update, topological-sort, idempotent-install, dependency-ordering, cli-lifecycle |
| [Best Practice: Tagged-Block Shell Profiles and Hash-Based File Modification Detection](infra/agent-rig/docs/solutions/best-practices/tagged-block-env-and-hash-based-merge-agent-rig-20260211.md) | best_practice | medium | 2026-02-11 | tagged-blocks, shell-profile, env-vars, sha256-hash, behavioral-merge, idempotent-file-management |

## autarch (13 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Spec Phase Reordering Strategy](hub/autarch/docs/solutions/architecture-decisions/spec-phase-reordering-strategy.md) | architecture-decisions |  | 2026-02-04 | prd, phases, cuj, requirements, ordering |
| [Spec Propagation Consistency Pattern](hub/autarch/docs/solutions/architecture-decisions/spec-propagation-consistency-pattern.md) | architecture-decisions |  | 2026-02-04 | orchestrator, propagation, claude-code, token-efficiency |
| [PRD Requirements Blank on Generation](hub/autarch/docs/solutions/logic-errors/prd-requirements-blank-on-generation.md) | logic-errors |  | 2026-02-04 | orchestrator, phase-generation, claude-code, exploration |
| [Arbiter Spec Sprint Architecture Patterns](hub/autarch/docs/solutions/patterns/arbiter-spec-sprint-architecture.md) | architecture | medium | 2026-01-26 | arbiter, import-cycle, architecture, hunter-api, tui |
| [Chat-First TUI Design: Keybindings, Slash Commands, and Layout](hub/autarch/docs/solutions/patterns/chat-first-tui-design-20260204.md) | patterns |  | 2026-02-04 | tui, chat-first, keybindings, slash-commands, layout, accessibility, bubble-tea |
| [Oracle Architecture Review: Issues 3-6 Resolution](hub/autarch/docs/solutions/patterns/oracle-review-issues-3-6-20260201.md) | patterns |  | 2026-02-01 | architecture-review, oracle, code-cleanup, constants, error-surfacing, focus-routing |
| [Fix Arbiter State() Pointer Escape and Concurrency Races](hub/autarch/docs/solutions/runtime-errors/arbiter-state-pointer-escape-20260201.md) | runtime-errors |  | 2026-02-01 | concurrency, race-condition, pointer-escape, deep-copy, go |
| [ANSI-Aware String Splicing for TUI Overlays](hub/autarch/docs/solutions/ui-bugs/ansi-aware-string-splicing-for-overlays.md) | ui_bug | medium | 2026-02-01 | tui, ansi, lipgloss, overlay, charmbracelet, string-width |
| [Fix Swallowed GenerationErrorMsg in UnifiedApp](hub/autarch/docs/solutions/ui-bugs/swallowed-generation-error-msg-20260131.md) | ui-bugs |  | 2026-01-31 | bubble-tea, message-routing, error-handling, swallowed-error |
| [TUI Breadcrumb Header Hidden by Oversized Child View](hub/autarch/docs/solutions/ui-bugs/tui-breadcrumb-hidden-by-oversized-child-view-20260127.md) | ui-bugs |  | 2026-01-27 | bubbletea, lipgloss, tui, layout, window-size, breadcrumb |
| [TUI Dimension Mismatch: Parent Padding vs Child Sizing](hub/autarch/docs/solutions/ui-bugs/tui-dimension-mismatch-splitlayout-20260126.md) | ui_bug | high | 2026-01-26 | tui, lipgloss, bubble-tea, layout, visual-bug, dimension-mismatch, ansi-handling |
| [TUI Scrolling - Keyboard and Mouse Focus Issues](hub/autarch/docs/solutions/ui-bugs/tui-scrolling-keyboard-and-mouse.md) | ui-bugs |  | 2026-02-04 | bubble-tea, tui, focus, keyboard, mouse, scrolling |
| [Over-Planning Before Bug Reproduction](hub/autarch/docs/solutions/workflow-issues/over-planning-before-reproduction-20260203.md) | workflow-issues |  | 2026-02-03 | planning, debugging, reproduction, process, over-engineering, reviewers |

## clavain (18 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Extract SKILL.md Inline Logic into Testable Library Functions](os/clavain/docs/solutions/2026-02-19-extract-skillmd-inline-logic-to-library.md) | architecture | P2 | 2026-02-19 | skill-md, testing, library-pattern, flock, interspect |
| [Best Practice: Agent Consolidation with Complete Reference Sweep](os/clavain/docs/solutions/best-practices/agent-consolidation-stale-reference-sweep-20260210.md) | best_practice | medium | 2026-02-10 | agent-consolidation, rename-sweep, stale-references, plugin-maintenance, grep-sweep |
| [Best Practice: Provenance Tracking Breaks Compounding Feedback Loops](os/clavain/docs/solutions/best-practices/compounding-false-positive-feedback-loop-flux-drive-20260210.md) | best_practice | high | 2026-02-10 | compounding, feedback-loop, knowledge-layer, provenance, flux-drive, multi-agent |
| [Best Practice: Smoke Test Agent Prompts Must Override the Task Tool Write-First Wrapper](os/clavain/docs/solutions/best-practices/smoke-test-agent-instruction-conflict-20260210.md) | best_practice | medium | 2026-02-10 | smoke-test, subagent, instruction-conflict, task-tool, mandatory-first-step |
| [Best Practice: Template System Has Multiple Independent Consumers](os/clavain/docs/solutions/best-practices/template-system-has-multiple-consumers-clodex-20260211.md) | best_practice | medium | 2026-02-11 | clodex, flux-drive, templates, dispatch, refactoring-safety |
| [Unify Content-Assembly Abstractions Before Adding Variants](os/clavain/docs/solutions/best-practices/unify-content-assembly-before-adding-variants-20260211.md) | best_practice | high | 2026-02-11 | flux-drive, content-assembly, diff-slicing, pyramid-mode, abstraction, strongdm |
| [Troubleshooting: Codex CLI Deprecated Flags Cause Agent Dispatch Failures](os/clavain/docs/solutions/integration-issues/codex-cli-deprecated-flags-clodex-20260211.md) | integration_issue | medium | 2026-02-11 | codex-cli, deprecated-flags, approval-mode, full-auto, clodex, ai-agent-hallucination |
| [Troubleshooting: Glob Pattern Misses Subproject Files in Monorepo](os/clavain/docs/solutions/integration-issues/glob-misses-subproject-files-galiana-20260215.md) | integration_issue | medium | 2026-02-15 | glob, monorepo, findings, python, path-discovery |
| [Troubleshooting: MCP Plugin Cache Missing node_modules](os/clavain/docs/solutions/integration-issues/mcp-plugin-missing-node-modules-20260210.md) | integration_issue | high | 2026-02-10 | mcp, plugin-cache, node-modules, native-modules, canvas, libgif |
| [New Agent Files Not Available as subagent_type Until Session Restart](os/clavain/docs/solutions/integration-issues/new-agents-not-available-until-restart-20260210.md) | integration_issue | medium | 2026-02-10 | agents, subagent-type, session-start, plugin-registry, flux-drive-v2 |
| [Troubleshooting: Oracle Browser Mode Output Lost in Flux-Drive Reviews](os/clavain/docs/solutions/integration-issues/oracle-browser-output-lost-flux-drive-20260211.md) | integration_issue | high | 2026-02-11 | oracle, browser-mode, flux-drive, stdout-redirect, write-output, timeout |
| [Stop Hooks Break After Mid-Session Plugin Publish](os/clavain/docs/solutions/integration-issues/stop-hooks-break-after-mid-session-publish-20260212.md) | integration_issue | medium | 2026-02-12 | hooks, stop-hooks, plugin-cache, bump-version, publish, symlink, session-lifecycle |
| [Hierarchical Config Resolution with Sentinel Values](os/clavain/docs/solutions/patterns/2026-02-20-hierarchical-config-resolution.md) | patterns |  | 2026-02-20 | routing, yaml-parsing, shell, config-resolution |
| [Troubleshooting: Cannot Import Functions from conftest.py in Pytest](os/clavain/docs/solutions/test-failures/pytest-conftest-import-error-20260210.md) | test_failure | medium | 2026-02-10 | pytest, conftest, imports, test-helpers, python |
| [Troubleshooting: Beads Pre-Commit Hook Blocks Git Commits Due to JSONL Permission Mask](os/clavain/docs/solutions/workflow-issues/beads-precommit-hook-permission-denied-20260210.md) | workflow_issue | medium | 2026-02-10 | beads, git-hooks, pre-commit, acl, permissions, claude-user |
| [Troubleshooting: disable-model-invocation Blocks All Command Chaining in /lfg Pipeline](os/clavain/docs/solutions/workflow-issues/disable-model-invocation-blocks-lfg-pipeline-clavain-20260211.md) | workflow_issue | high | 2026-02-11 | claude-code-plugin, disable-model-invocation, command-chaining, lfg, orchestration, clavain |
| [Troubleshooting: Duplicate MCP Server Registration Wastes Context Budget](os/clavain/docs/solutions/workflow-issues/duplicate-mcp-server-context-bloat-20260210.md) | workflow_issue | medium | 2026-02-10 | mcp, context-budget, duplicate-registration, settings-hygiene, claude-doctor |
| [Troubleshooting: Settings Permission Bloat from Heredoc Bash Commands](os/clavain/docs/solutions/workflow-issues/settings-heredoc-permission-bloat-20260210.md) | workflow_issue | high | 2026-02-10 | settings-hygiene, heredoc, permissions, bloat, pretooluse-hook |

## intercore (2 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [E8 Portfolio Orchestration — Sprint Learnings](infra/intercore/docs/solutions/e8-portfolio-orchestration-learnings.md) | architecture | medium | 2026-02-21 | intercore, portfolio, cross-db, relay, sqlite, gates |
| [E9 Portfolio Dependency Scheduling Learnings](infra/intercore/docs/solutions/e9-portfolio-dependency-scheduling-learnings.md) | correctness | high | 2026-02-20 | portfolio, gate-evaluation, cycle-detection, toctou, sqlite, intercore |

## interfluence (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Marketplace plugin not visible after publishing](plugins/interfluence/docs/solutions/marketplace-cached-clone-stale.md) | plugin-publishing | moderate | 2026-02-11 | marketplace, cache, git, plugin-publishing, interagency-marketplace |

## interkasten (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Troubleshooting: New Marketplace Plugin Not Auto-Installed](plugins/interkasten/docs/solutions/integration-issues/new-marketplace-plugin-not-installed-20260215.md) | integration_issue | high | 2026-02-15 | plugin, marketplace, installed-plugins, cache, claude-code, onboarding |

## interlearn (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Awk sub() Mutates $0 Causing Pattern Fall-Through on Same Line](plugins/interlearn/docs/solutions/patterns/awk-sub-pattern-fallthrough-20260221.md) | correctness | P2 | 2026-02-21 | awk, shell, parsing, frontmatter, pattern-matching, sub, $0-mutation |

## interlock (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Advisory-Only Timeout Eliminates TOCTOU Race in Multi-Agent Coordination](plugins/interlock/docs/solutions/2026-02-16-advisory-only-timeout-eliminates-toctou.md) | concurrency | P0 | 2026-02-16 | race-condition, toctou, idempotency, advisory-pattern, go |

## intermute (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Troubleshooting: Silent JSON Marshal/Unmarshal Errors in Event-Sourced SQLite Store](services/intermute/docs/solutions/database-issues/silent-json-errors-sqlite-storage-20260211.md) | database_issue | critical | 2026-02-11 | json-marshal, json-unmarshal, sqlite, event-sourcing, data-integrity, error-handling |

## interverse (17 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Best Practice: Silent API Misuse Patterns in Go](docs/solutions/best-practices/silent-api-misuse-patterns-intercore-20260221.md) | best_practice | medium | 2026-02-21 | go, silent-failure, error-handling, utf8, sql, quality-gates, multi-agent-review |
| [Troubleshooting: TOCTOU in Gate-Phase Advance + Missing CAS on Dispatch Status](docs/solutions/database-issues/toctou-gate-check-cas-dispatch-intercore-20260221.md) | database_issue | high | 2026-02-21 | sqlite, toctou, cas, optimistic-concurrency, transaction, go, begintx, querier-interface |
| [Git Credential Store Lock Failure in Multi-User Setup](docs/solutions/environment-issues/git-credential-lock-multi-user-20260216.md) | environment_issue | high | 2026-02-16 | git, credentials, multi-user, claude-user, permissions, ACL, plugin-install |
| [Troubleshooting: Claude Code Plugin Loading Failures (4 Plugins)](docs/solutions/integration-issues/plugin-loading-failures-interverse-20260215.md) | integration_issue | high | 2026-02-15 | claude-code, plugin, mcp, hooks, orphaned-at, version-mismatch, binary-missing |
| [Plugin Validation Errors: Cache/Manifest Divergence (4 Plugins)](docs/solutions/integration-issues/plugin-validation-errors-cache-manifest-divergence-20260217.md) | integration_issue | high | 2026-02-17 | claude-code, plugin, cache-divergence, hooks-format, manifest, orphaned-at, hook-event-types |
| [argparse `parents=[shared]` Overwrites Flags Parsed by Main Parser](docs/solutions/patterns/argparse-parents-subparser-default-overwrite-20260219.md) | python_pattern | medium | 2026-02-19 | python, argparse, cli, subparsers, parents, defaults, suppress |
| [CAS Dispatch Linking with Orphan Process Cleanup](docs/solutions/patterns/cas-spawn-link-orphan-cleanup-20260219.md) | concurrency_pattern | medium | 2026-02-19 | sqlite, concurrency, cas, spawn, orphan-cleanup, single-connection, go |
| [Critical Patterns — Required Reading](docs/solutions/patterns/critical-patterns.md) | patterns |  |  |  |
| [Guard Fallthrough: Validation That Silently Skips on Null](docs/solutions/patterns/guard-fallthrough-null-validation-20260216.md) | security_pattern | high | 2026-02-16 | path-traversal, validation, guard-clause, null-safety, security, typescript |
| [intercore Schema Upgrade + Binary Deployment Pattern](docs/solutions/patterns/intercore-schema-upgrade-deployment-20260218.md) | patterns | medium | 2026-02-18 | intercore, sqlite, migration, deployment, go-embed |
| [`set -euo pipefail` with Fallback Recovery Paths](docs/solutions/patterns/set-e-with-fallback-paths-20260216.md) | shell_pattern | medium | 2026-02-16 | bash, set-e, error-handling, hooks, fallback, shell |
| [Synthesis Subagent for Context-Efficient Multi-Agent Orchestration](docs/solutions/patterns/synthesis-subagent-context-isolation-20260216.md) | patterns | high | 2026-02-16 | multi-agent, context-window, synthesis, intersynth, verdict, subagent |
| [Token Accounting: Billing Tokens vs Effective Context](docs/solutions/patterns/token-accounting-billing-vs-context-20260216.md) | measurement_error | high | 2026-02-16 | tokens, context-window, cache, billing, measurement, decision-gate, interstat |
| [WAL Protocol Completeness: Every Write Path Needs Protection](docs/solutions/patterns/wal-protocol-completeness-20260216.md) | data_integrity_pattern | high | 2026-02-16 | wal, crash-recovery, write-ahead-log, conflict-resolution, data-integrity, typescript |
| [Troubleshooting: jq Null-Slice Runtime Error from Empty-String Function Returns](docs/solutions/runtime-errors/jq-null-slice-from-empty-string-return-clavain-20260216.md) | runtime_error | high | 2026-02-16 | jq, null-safety, shell, bash, checkpoint, json, empty-string, runtime-error |
| [Troubleshooting: Compiled MCP Binary Missing After Plugin Install](docs/solutions/workflow-issues/auto-build-launcher-go-mcp-plugins-20260215.md) | workflow_issue | medium | 2026-02-15 | go, mcp, plugin, auto-build, launcher, compiled-binary |
| [`bd sync --from-main` Fails on Trunk-Based Repos](docs/solutions/workflow-issues/bd-sync-from-main-trunk-based-20260216.md) | workflow_issue | medium | 2026-02-16 | beads, bd, sync, trunk-based, git, workflow |

## tldr-swinton (12 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Extract engine-internal logic into shared modules before adding new modes](plugins/tldr-swinton/docs/solutions/best-practices/extract-engine-logic-into-shared-module-20260212.md) | best-practices | medium | 2026-02-12 | refactoring, architecture, block-compression, knapsack, difflens |
| [Best Practice: Hooks for Per-File Tactics, Skills for Session Strategy](plugins/tldr-swinton/docs/solutions/best-practices/hooks-vs-skills-separation-plugin-20260211.md) | best_practice | high | 2026-02-11 | plugin-design, hooks-vs-skills, separation-of-concerns, preset-naming, agent-adoption |
| [Best Practice: 4-Layer Defense-in-Depth for Agent Tool Adoption](plugins/tldr-swinton/docs/solutions/best-practices/layered-enforcement-architecture-plugin-20260211.md) | best_practice | high | 2026-02-11 | defense-in-depth, layered-enforcement, plugin-architecture, presets, hooks, skills |
| [Parallel agents miss cross-cutting schema bugs](plugins/tldr-swinton/docs/solutions/best-practices/parallel-agents-miss-cross-cutting-schema-bugs.md) | best-practices | medium | 2026-02-12 | multi-agent, quality-gates, schema-consistency, code-review |
| [Git LFS Submodule Blocks Claude Code Plugin Install](plugins/tldr-swinton/docs/solutions/build-errors/lfs-submodule-blocks-plugin-install.md) | build-errors | high |  | git, lfs, submodule, plugin-install, claude-code, gitmodules |
| [Plugin Version Drift Between Repo and Marketplace Breaks Loading](plugins/tldr-swinton/docs/solutions/build-errors/plugin-version-drift-breaks-loading.md) | build-errors | high |  | plugin, version, marketplace, cache, claude-code, publishing |
| [Stale Plugin Cache Creates Ghost Entries and Load Failures](plugins/tldr-swinton/docs/solutions/build-errors/stale-plugin-cache-ghost-entries.md) | build-errors | medium |  | plugin, cache, claude-code, ghost, cleanup, installation |
| [Claude Code Hook Scripts Use stdin JSON, Not Environment Variables](plugins/tldr-swinton/docs/solutions/integration-issues/claude-code-hook-stdin-api.md) | integration-issues | medium |  | claude-code, hooks, PreToolUse, stdin, json, plugin, bash |
| [Integration Pattern: CLI+Plugin vs MCP for Agent Tool Adoption](plugins/tldr-swinton/docs/solutions/integration-issues/cli-plugin-low-agent-adoption-vs-mcp-20260211.md) | integration_issue | high | 2026-02-11 | mcp, agent-adoption, token-savings, cli-vs-mcp, tool-descriptions, qmd |
| [Codex dispatch.sh Fails in Bash Tool Background Mode](plugins/tldr-swinton/docs/solutions/integration-issues/codex-dispatch-background-mode-failure.md) | integration-issues | medium |  | codex, dispatch, interclode, background, bash-tool, argument-parsing, shell-quoting |
| [Troubleshooting: Duplicated ProjectIndex Builds Across Engine Calls](plugins/tldr-swinton/docs/solutions/performance-issues/duplicated-index-builds-projectindex-20260211.md) | performance_issue | medium | 2026-02-11 | project-index, shared-state, deduplication, call-chain-threading, performance |
| [Troubleshooting: Beads `bd` Commands Hang Indefinitely Due to Stale Startlock](plugins/tldr-swinton/docs/solutions/workflow-issues/bd-commands-hang-stale-startlock-20260213.md) | workflow_issue | high | 2026-02-13 | beads, daemon, stale-lock, hang, bd-cli, unix-socket, ipc |

## tool-time (1 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [Best Practice: Event Type Contract for Hook-Based Analytics](plugins/tool-time/docs/solutions/best-practices/event-type-contract-analyze-20260214.md) | best_practice | high | 2026-02-14 | event-types, hook-events, double-counting, pre-post-pairs, analytics, tool-chains |

## tuivision (2 docs)

| Doc | Type | Severity | Date | Tags |
|-----|------|----------|------|------|
| [tuivision Critical Patterns](plugins/tuivision/docs/solutions/patterns/critical-patterns.md) | patterns |  |  |  |
| [RGB Color Rendering Incorrect in TUI Screenshots](plugins/tuivision/docs/solutions/ui-bugs/rgb-color-rendering-TerminalRenderer-20260126.md) | ui_bug | high | 2026-01-26 | xterm-js, rgb-colors, true-color, terminal-rendering |

