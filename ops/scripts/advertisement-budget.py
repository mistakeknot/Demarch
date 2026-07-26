#!/usr/bin/env python3
"""Measure the advertisement budget: what enabled plugins cost in system prompt.

WHY THIS FILE EXISTS AT ALL

This is the instrument for the entire context-engineering program, and until now
it lived only in an ephemeral session scratchpad -- one `/tmp` sweep from gone.
That is not a filing accident; it is *why* three separate baselines were published
and later retired as wrong (34,141 / 46,416 / 36,837). An ad-hoc measurement gets
re-derived slightly differently each time and nobody can diff two runs. Checked in,
it can be reviewed, corrected once, and re-run identically.

WHAT IS COUNTED

The "advertisement budget" is the sum of `name` + `description` characters for
every skill, command, and agent that an enabled plugin registers. Claude Code
loads those two fields into the system prompt at session start, for every session,
whether or not the entry is ever used. The body of a skill or agent costs nothing
until it is actually dispatched -- which is why relocating worked examples out of
a `description` and into the body is the standard fix.

RESOLUTION RULES -- read these before trusting a number

1. It reads the CACHE, never source. `~/.claude/plugins/cache/<marketplace>/
   <plugin>/<version>/` is what Claude Code actually loads. A source checkout can
   be ahead, behind, or entirely absent, and measuring it answers a different
   question than "what is in my context right now".

2. Consequently, a plugin that is ENABLED but NOT YET INSTALLED reads as ZERO.
   This is correct -- it genuinely costs nothing until Claude Code installs it --
   but it means enablement and cost are separated in time. cujgel was recorded as
   free on 2026-07-24 and billed 1,250 chars two days later when its cache
   appeared. A zero here is a statement about now, not a prediction.

3. Multiple installed versions: the LAST directory in sorted order wins. This is
   lexical, not semver, so 0.10.0 sorts before 0.9.0. It matters only when two
   versions are cached simultaneously, which is transient.

4. An entry counts only if it has YAML frontmatter WITH a description. Files
   without frontmatter are not registered by Claude Code and cost nothing. Both
   were bugs in the first version of this script.

5. `disable-model-invocation: true` entries are counted separately as "demoted".
   They remain user-invocable by typing the command, but their descriptions are
   not loaded, so they do not bill. Demoting is the other standard fix.

6. agents/ is globbed RECURSIVELY. Non-recursive globbing missed agents in
   subdirectories and was the second bug in the original.

USAGE

    advertisement-budget.py              # human table
    advertisement-budget.py --json       # machine-readable, for rig-health-check
    advertisement-budget.py --top 10     # limit the table

Environment overrides (used by tests and by the forced-failure harness):
    CLAUDE_SETTINGS   path to settings.json
    CLAUDE_CACHE      path to the plugins cache directory
"""
import glob
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
SETTINGS = os.environ.get("CLAUDE_SETTINGS", os.path.join(HOME, ".claude", "settings.json"))
CACHE = os.environ.get("CLAUDE_CACHE", os.path.join(HOME, ".claude", "plugins", "cache"))

# Where the entries live inside a plugin, and how deep to look.
PATTERNS = ("skills/**/SKILL.md", "commands/**/*.md", "agents/**/*.md")

FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)
# Stops at the next top-level YAML key so multi-line descriptions are captured
# whole. A description that runs to end-of-frontmatter is also handled.
DESCRIPTION = re.compile(r"^description:\s*(.*?)(?=\n[a-z_-]+:\s|\Z)", re.S | re.M)
NAME = re.compile(r"^name:\s*(.*)$", re.M)
DEMOTED = re.compile(r"^disable-model-invocation:\s*true\s*$", re.M)


def enabled_plugins(settings_path=SETTINGS):
    """Return ["name@marketplace", ...] for plugins switched on in settings.json.

    A missing or unparseable settings.json raises. The caller decides whether that
    is fatal; silently returning an empty list would report a budget of 0, which
    is the most dangerous possible wrong answer here -- it looks like success.
    """
    with open(settings_path, encoding="utf8") as fh:
        settings = json.load(fh)
    return [k for k, v in settings.get("enabledPlugins", {}).items() if v]


def entries(base):
    """Measure one installed plugin directory. Returns (live, demoted) cost lists."""
    live, demoted = [], []
    seen = set()
    for pat in PATTERNS:
        for path in glob.glob(os.path.join(base, pat), recursive=True):
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, encoding="utf8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            m = FRONTMATTER.match(text)
            if not m:
                continue  # not registered by Claude Code
            block = m.group(1)
            d = DESCRIPTION.search(block)
            if not d:
                continue  # nothing advertised
            n = NAME.search(block)
            name = n.group(1).strip() if n else os.path.basename(path)[:-3]
            cost = len(name) + len(d.group(1).strip())
            (demoted if DEMOTED.search(block) else live).append((cost, name))
    return live, demoted


def measure(settings_path=SETTINGS, cache=CACHE):
    """Measure the whole rig. Returns a dict safe to serialise and diff."""
    rows = []
    uninstalled = []
    for spec in enabled_plugins(settings_path):
        name, _, marketplace = spec.partition("@")
        if not marketplace:
            marketplace = "unknown"
        versions = sorted(glob.glob(os.path.join(cache, marketplace, name, "*") + os.sep))
        if not versions:
            # Enabled but not installed: genuinely free right now. Recorded by
            # name so a later appearance is explicable rather than mysterious.
            uninstalled.append(name)
            continue
        live, demoted = entries(versions[-1])
        rows.append({
            "plugin": name,
            "marketplace": marketplace,
            "chars": sum(c for c, _ in live),
            "live": len(live),
            "demoted": len(demoted),
            "demoted_chars": sum(c for c, _ in demoted),
        })

    rows.sort(key=lambda r: (-r["chars"], r["plugin"]))
    total = sum(r["chars"] for r in rows)
    mine = sum(r["chars"] for r in rows if r["marketplace"] == "interagency-marketplace")
    return {
        "total": total,
        "approx_tokens": total // 4,
        "ours": mine,
        "third_party": total - mine,
        "plugins": rows,
        "enabled_not_installed": sorted(uninstalled),
        "settings": settings_path,
        "cache": cache,
    }


def main(argv):
    as_json = "--json" in argv
    top = None
    if "--top" in argv:
        try:
            top = int(argv[argv.index("--top") + 1])
        except (IndexError, ValueError):
            print("--top needs a number", file=sys.stderr)
            return 2

    try:
        result = measure()
    except FileNotFoundError as exc:
        print("advertisement-budget: cannot read %s" % exc.filename, file=sys.stderr)
        return 2
    except (json.JSONDecodeError, OSError) as exc:
        print("advertisement-budget: %s" % exc, file=sys.stderr)
        return 2

    if as_json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    rows = result["plugins"]
    print("%7s  %-22s %4s %4s" % ("chars", "plugin", "live", "dem"))
    for r in rows if top is None else rows[:top]:
        if r["chars"]:
            print("%7s  %-22s %4d %4d" % (format(r["chars"], ","), r["plugin"], r["live"], r["demoted"]))
    print()
    print("  ours (interagency) : %s" % format(result["ours"], ","))
    print("  third-party        : %s" % format(result["third_party"], ","))
    print("  TOTAL              : %s chars  (~%s tok)"
          % (format(result["total"], ","), format(result["approx_tokens"], ",")))
    if result["enabled_not_installed"]:
        print()
        print("  enabled but not installed (free NOW, will bill when installed):")
        print("    %s" % ", ".join(result["enabled_not_installed"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
