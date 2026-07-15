#!/usr/bin/env bash
# Weekly estate-drift check (goal mk-t4x.3): pull source surfaces, run the checker,
# file ONE bead in the agent-fortress db when drift is found (dedup on open bead).
# Fail-open: pulls tolerate dirty/offline repos; the checker runs on whatever is local.
set -u
[ -f "$HOME/.claude-automations-paused" ] && exit 0
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

for r in Sylveste gsv-portfolio gsvdotcom; do
    git -C "$HOME/projects/$r" pull --rebase --autostash -q 2>/dev/null || true
done

report="$(mktemp)"
python3 "$HOME/projects/Sylveste/ops/canongraph/estate-drift.py" "$@" >"$report" 2>&1
rc=$?
cat "$report"

if [ "$rc" -ne 0 ]; then
    cd "$HOME/projects/agent-fortress" || exit 0
    if ! bd list --status=open 2>/dev/null | grep -qi "estate drift"; then
        bd create --title="estate drift: findings $(date +%F)" \
            --description="$(cat "$report")

Filed by estate-drift.timer on zklw. Re-run: python3 ~/projects/Sylveste/ops/canongraph/estate-drift.py" \
            --type=task --priority=2 >/dev/null 2>&1 || true
        echo "estate-drift: bead filed in agent-fortress"
    else
        echo "estate-drift: open bead exists, not re-filing"
    fi
fi
rm -f "$report"
exit 0
