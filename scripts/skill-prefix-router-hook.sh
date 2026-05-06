#!/usr/bin/env bash
# skill-prefix-router-hook.sh — UserPromptSubmit hook.
#
# When the user's prompt opens with a known slash command, emit a routing
# hint via additionalContext so the LLM skips the skill-deliberation phase.
#
# Reads stdin JSON of the form {"prompt": "<text>", ...}, looks up the
# first whitespace-delimited token in the prefix table at
# ~/.claude/skill-prefix-table.json, and emits a JSON object on stdout
# per the UserPromptSubmit hook protocol when matched.
#
# No-op (exit 0, empty stdout) on miss, missing table, malformed input.
# This hook is purely additive: the original prompt is never blocked.
#
# Performance: ~5-15ms typical via jq. The lookup is O(1) once jq parses
# the table; jq invocation dominates.
# NOTE: do NOT enable set -e here. UserPromptSubmit hooks must exit 0 even
# on malformed input — non-zero exit blocks the user's prompt.
set -u

TABLE="${SKILL_PREFIX_TABLE:-${HOME}/.claude/skill-prefix-table.json}"
[[ -f "$TABLE" ]] || exit 0
command -v jq >/dev/null 2>&1 || exit 0

# Read stdin once (UserPromptSubmit input is small JSON)
input=$(cat)
prompt=$(jq -r '.prompt // empty' <<<"$input" 2>/dev/null) || exit 0
[[ -z "$prompt" ]] && exit 0

# Find a slash command in the prompt prefix.
# Strategy: prefer first-token (cleanest signal), but also scan the first 200
# chars for `/<plugin>:<cmd>` patterns. Cass-derived empirical evidence
# (a4oj.9.2 investigation): 25 of 34 "imperative-no-opening-slash" prompts
# embed a slash command after a discourse marker (e.g., "yes, /handoff",
# "let's /flux-review the brainstorm"). A naive POLY-2 keyword router on
# WORK/REVIEW/RESEARCH/MEMORY had a 95.6% false-positive rate and was
# rejected; the slash-anywhere extension captures 25/34 with zero ambiguity.
first_token=$(awk '{print $1; exit}' <<<"$prompt")
match=""
case "$first_token" in
    /*:*) match="$first_token" ;;
    /*)
        # Top-level slash like /loop or /init. Use first token.
        match="$first_token"
        ;;
    *)
        # Not a leading slash — scan first 200 chars for /<plugin>:<cmd>.
        # The pattern requires a namespace colon to keep noise low; bare
        # `/something` mid-sentence is too ambiguous (could be a path,
        # regex, etc.) and the cass data shows namespaced is what users
        # write when they mean an invocation.
        prefix=${prompt:0:200}
        match=$(grep -oE '/[a-z][a-z0-9-]*:[a-z][a-z0-9-]+' <<<"$prefix" | head -1) || match=""
        ;;
esac
[[ -z "$match" ]] && exit 0

# Look up in table. jq returns empty for missing keys.
hit=$(jq -r --arg key "$match" '.commands[$key] // .global_commands[$key] // empty' "$TABLE" 2>/dev/null)
[[ -z "$hit" ]] && exit 0
first="$match"

plugin=$(jq -r --arg key "$first" '.commands[$key].plugin // .global_commands[$key].plugin // empty' "$TABLE")
cmd=$(jq -r --arg key "$first" '.commands[$key].command // .global_commands[$key].command // empty' "$TABLE")
desc=$(jq -r --arg key "$first" '.commands[$key].description // .global_commands[$key].description // empty' "$TABLE")

# Build the hint. Keep it short (every token here is paid input).
if [[ -n "$plugin" ]]; then
    skill_id="${plugin}:${cmd}"
else
    skill_id="${cmd}"
fi

hint="Routing hint: user invoked ${first} → invoke skill \"${skill_id}\" via Skill tool. (description: ${desc:0:120})"

# Emit JSON per UserPromptSubmit hook protocol
jq -nc --arg ctx "$hint" '{
    hookSpecificOutput: {
        hookEventName: "UserPromptSubmit",
        additionalContext: $ctx
    }
}'
