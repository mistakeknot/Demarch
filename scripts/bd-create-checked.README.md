# bd-create-checked.sh

Wrapper around `bd create` that warns on likely duplicate beads before creating.

## Why

`bd search` before `bd create` is workflow-discipline-dependent and gets skipped. Result: duplicate beads accumulate (e.g., `sylveste-zn70` was a duplicate of `sylveste-itsc`). This wrapper runs an automatic similarity check against all non-closed beads (open/in_progress/blocked/deferred) and prompts before creating.

## Signal stack

Per finding KF-02 + POLY-5 (`docs/research/flux-review/sylveste-improvements-multi-axis/2026-05-04-synthesis.md`):

- **Title TF-IDF cosine** (45%) — high precision for rename-style dups; rare-token-weighted
- **Title+description TF-IDF cosine** (25%) — broader semantic overlap when titles diverge
- **3-gram Jaccard** (20%) — POLY-5's bird-homing tertiary signal; catches phrase repetitions
- **Label Jaccard** (10%) — soft prior for same-domain beads
- **Recency** — multiplier (saturating, range 0.4–1.0) attenuating year-old dups

Default threshold: `0.30`. Below this, the wrapper proceeds silently. Above, it lists the top 5 candidates and prompts.

## Usage

Basic:

```bash
bash scripts/bd-create-checked.sh -t task -p 2 \
  --title "..." --description "..." [--labels a,b,c]
```

As an alias (drop into `~/.bashrc` or shell init):

```bash
alias bd-create='bash /home/mk/projects/Sylveste/scripts/bd-create-checked.sh'
```

…or to make it the default `bd create` everywhere, define a function override:

```bash
bd() {
    if [[ "${1:-}" == "create" ]] && [[ -f /home/mk/projects/Sylveste/scripts/bd-create-checked.sh ]]; then
        shift
        bash /home/mk/projects/Sylveste/scripts/bd-create-checked.sh "$@"
    else
        command bd "$@"
    fi
}
```

## Bypass

- `BD_DUP_CHECK_SKIP=1` — disable the check entirely (forwards directly to `bd create`)
- `BD_DUP_AUTO_PROCEED=1` — print warnings but still create (useful for CI / batch flows where duplicates are intentional)
- No TTY: refuses to create on dup match. Override with `BD_DUP_AUTO_PROCEED=1`.

## Tuning

Run the dup-check directly to inspect score components for any candidate:

```bash
python3 scripts/lib-bd-dup-check.py \
    --title "<my title>" --description "<my desc>" --labels x,y \
    --threshold 0.0 --top 10 --json
```

Adjust the threshold downward (e.g. `0.20`) for stricter dup-catching at cost of more false positives.

## Known limitation: semantic dups with very different surface phrasing

The TF-IDF stack catches **lexical / rename dups** well — same content, slight phrasing change. It misses **semantic dups** where two titles describe the same problem with completely different vocabulary.

Acid-test case: `sylveste-zn70` ("Bash git() function override breaks subrepo operations") vs `sylveste-itsc` ("interlock session-start: fix git wrapper corrupting nested git repos"). Same root cause, identical fix; share only the token "git" at the title level. The wrapper scores this at 0.116 — well below the default 0.30 threshold.

For this class of dup, true embedding similarity is needed. Tracked under follow-up `sylveste-a4oj.9.3.1` (semantic-embedding extension via intersearch CLI or local embedding model).
