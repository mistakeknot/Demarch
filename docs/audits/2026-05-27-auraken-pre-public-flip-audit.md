# Pre-flip security audit — mistakeknot/auraken

Generated: 2026-05-27
Bead: sylveste-22oi.2
Repo: mistakeknot/auraken (currently PRIVATE)
HEAD: 11768cbd3c2d0542c9d43aa0fc1942bbe8f90ce1
Commit count: 136

## Audit scope
1. Git history scan for credential patterns
2. Legacy daemon (src/auraken/) for hardcoded credentials
3. .env / config files ever committed
4. Personal content (Signal/Telegram dumps, user emails, private corpora)
5. Voice samples / corpora
6. Backup files (.bak) that might contain secrets


## 1. `.env` file history

### Has .env EVER been committed?
git log --all --full-history -- .env returned 0 lines

### Was .env in any tree object?


## 2. .gitignore evolution — when was `.env` first excluded?

e56a947 bd init: initialize beads issue tracking
a6d54f9 Research Hermes Agent + OpenClaw, decide to fork Hermes
3a0a417 feat(core): Implement Phase 1 — project scaffold, conversation handler, Telegram bot
869fdc7 chore: Add wikifeedia sample data reference
3148fbd chore: migrate Auraken into Sylveste apps/ (sylveste-u3f)
b94813f bd init: initialize beads issue tracking
f713573 feat(hermes/dist): F1 — bundle scaffolding + v1 schemas (sylveste-heh8.63)
799603f feat(dist): F3 build-binaries.sh — reproducible cross-compile (sylveste-heh8.67)
c7f3cda feat(dist): F7 build-dist.sh — reproducible bundle assembly (sylveste-heh8.70)

### Earliest .gitignore content:
```
Commit: e56a947bdc6972ab467f9cf65033ce2a08dc01c2

# Dolt database files (added by bd init)
.dolt/
*.db
```

**Finding: .env never committed.**
- `git log --all --full-history -- .env` returned 0 commits touching .env
- Cross-check: `git rev-list --all` over all commits + `git ls-tree -r` looking for .env path:
```
Commits with .env in tree: 0
```


## 3. Credential-pattern sweep across all currently tracked files

Patterns scanned: API keys (sk-, ghp_, gho_, ghu_, ghs_, ghr_, pat_), bearer tokens, hardcoded `Authorization:`, common credential variable names.

```
### High-signal API key prefixes
(no hits — current HEAD content clean)

### Hardcoded bearer tokens / Authorization headers
(no hits — current HEAD content clean)

### Hardcoded passwords
(no hits — current HEAD content clean)
```

## 4. Historical credential sweep — every blob in every commit

This is the high-leverage check: secrets removed from HEAD but still in history are the *exact* class of leak that public-flip cannot recover from.

```
### Sweep over all blobs across all commits
Pattern set: sk-/ghp_/ghu_/ghs_/pat_/xoxb-/AIza prefixes, Authorization: Bearer, common credential var assignments

Total unique blobs across full history: 745

### High-signal pattern hits in any historical blob

9 lines of hits — see /tmp/auraken-audit/high-signal-hits.txt for detail
Blob 1adae9fef2a2e27de62f36c2f9250a48fc9c57aa:
131:| `AURAKEN_LENS_API_KEY` | (none) | API key sent as `Authorization: Bearer ...` |

Blob 533cf720fda3ddca693ff8b2eeaba8a224cfe450:
112:| `AURAKEN_LENS_API_KEY` | (none) | API key sent as `Authorization: Bearer ...` |

Blob 7a77c95ce6de9d9ffec8ab3f46be01168d662c22:
112:| `AURAKEN_LENS_API_KEY` | (none) | API key sent as `Authorization: Bearer ...` |

```

**Hits triaged:** 9 lines / 3 blobs all map to the same source — INSTALL.md's environment-variable table that documents `AURAKEN_LENS_API_KEY` as being sent via `Authorization: Bearer ...` (literal ellipsis, not a credential). Three blob hashes because INSTALL.md evolved across F5 / F8 / F9 commits.

Concrete: `git cat-file -p 7a77c95 | sed -n '108,115p'`
```
| --- | --- | --- |
| `HERMES_HOME` | `$HOME/.hermes` | Where Hermes lives |
| `AURAKEN_PROFILE` | `auraken` | Skill name + slash command (changes `/auraken` to `/<name>`) |
| `AURAKEN_LENS_API_BASE` | `http://127.0.0.1:8317/v1` | OpenAI-compatible chat-completions endpoint |
| `AURAKEN_LENS_API_KEY` | (none) | API key sent as `Authorization: Bearer ...` |
| `AURAKEN_LENS_API_KEY_FILE` | `$HOME/.cli-proxy-api/local-api-key` | File to read the API key from when `AURAKEN_LENS_API_KEY` is unset |
| `AURAKEN_LENS_MODEL` | `claude-opus-4-7` | Model id; see `MANIFEST.yaml` `compatibility.models` for tested set |
| `AURAKEN_LENS_TIMEOUT_SEC` | `15` | Per-call timeout to the chat-completions endpoint |
```

**Verdict for Phase 4: clean.** No real credentials in any historical blob.

## 5. Provider-specific credential format sweep

More precise patterns (lower false-positive rate):
- Anthropic API keys: `sk-ant-[a-zA-Z0-9_-]{90,}`
- OpenAI API keys: `sk-proj-[a-zA-Z0-9_-]{40,}` / `sk-[a-zA-Z0-9]{48}` (legacy)
- Telegram bot tokens: `[0-9]{8,12}:[A-Za-z0-9_-]{30,}`
- AWS access keys: `AKIA[0-9A-Z]{16}`
- Google API keys: `AIza[a-zA-Z0-9_-]{35}`
- Slack tokens: `xox[abprs]-[a-zA-Z0-9-]+`
- GitHub PATs: `ghp_/gho_/ghu_/ghs_/ghr_/pat_[a-zA-Z0-9]{30,}`

```
(zero provider-specific credential hits across all 745 blobs)
```

## 6. Legacy daemon scan — src/auraken/ + config-shaped files

The pre-pivot Python daemon ran in production on sleeper-service with real Telegram + Anthropic credentials. Its source is still in the repo. Check that every credential reference is via `os.environ` / config loader, not hardcoded literals.

### src/auraken/ structure
```
__init__.py
__main__.py
__pycache__
agent.py
api.py
bridge.py
checkpoint.py
config.py
curriculum.py
db.py
deai.py
discrimination.py
extraction.py
forge.py
forge_code.py
gating.py
gmail_import
identity.py
intermute.py
lens_communities.json
lens_edges.json
lens_evolution.py
lens_graph.py
lens_library.json
lens_library_v2.json
lens_stacks.py
lenses.py
mcp_server.py
model_routing.py
models.py

Total Python files: 51
Total YAML / JSON configs: 4
```

### Credential lookups in legacy daemon (should ALL be env-var or config-loader patterns)
```
src/auraken/__main__.py:31:            env={**__import__("os").environ, "TELEGRAM_BOT_TOKEN": settings.telegram_bot_token},
src/auraken/agent.py:113:    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
src/auraken/config.py:20:    anthropic_api_key: str = ""  # Required for SDK mode, optional for CLI mode
src/auraken/config.py:33:    google_places_api_key: str = ""  # Optional — recs work without it (LLM knowledge only)
src/auraken/config.py:35:    deepgram_api_key: str = ""  # Optional — for voice note transcription
src/auraken/config.py:36:    openai_api_key: str = ""  # Optional — fallback STT via Whisper
src/auraken/gmail_import/auth.py:51:            client_secret=self._get_client_secret(),
src/auraken/gmail_import/auth.py:129:    def _get_client_secret(self) -> str:
src/auraken/gmail_import/auth.py:131:        return settings.gmail_client_secret
src/auraken/gmail_import/auth.py:142:                "client_secret": settings.gmail_client_secret,
src/auraken/stt.py:22:    if settings.deepgram_api_key:
src/auraken/stt.py:24:    if settings.openai_api_key:
src/auraken/stt.py:40:                        "Authorization": f"Token {settings.deepgram_api_key}",
src/auraken/stt.py:66:                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
```
### Any config-shaped JSON / YAML committed under src/?
```
src/auraken/lens_library.json
src/auraken/lens_library_v2.json
src/auraken/lens_communities.json
src/auraken/lens_edges.json
```

**Legacy daemon credential pattern: clean.** All API keys / tokens are loaded via `settings.<name>` (the pydantic-settings config loader), which reads from environment variables. No hardcoded credentials anywhere in src/auraken/.

## 7. IP exposure check — what becomes world-readable on flip?

Not a *security* concern but a *disclosure* concern. The user should know what proprietary content goes public.

### Lens library and graph data (Auraken's core IP)
```
src/auraken/lens_library.json               187004 bytes    4194 lines
src/auraken/lens_library_v2.json            654607 bytes    9383 lines
src/auraken/lens_communities.json             4658 bytes     126 lines
src/auraken/lens_edges.json                 802539 bytes   16012 lines
```

### data/ directory (calibration / training assets)
```
data/calibration/stack_patterns.json
data/calibration/near_miss_analysis.json
data/calibration/restructure_holdings.py
data/calibration/README.md
data/calibration/anchor_suite.json
data/calibration/analyze_near_misses.py
data/calibration/analyze_cookoff.py
data/calibration/cookoff_results.jsonl
data/calibration/daily_dilemmas.json
data/calibration/build_difficulty_ladder.py
data/calibration/cookoff_analysis.json
data/calibration/forge_stress_test_log.jsonl
data/calibration/lens_cookoff.py
data/calibration/build_anchor_suite.py
data/calibration/difficulty_ladder.json
data/calibration/near_miss_forge_ready.json
data/calibration/__pycache__/build_difficulty_ladder.cpython-312.pyc
data/calibration/__pycache__/restructure_holdings.cpython-312.pyc
data/calibration/__pycache__/enrich_near_miss.cpython-312.pyc
data/calibration/__pycache__/build_anchor_suite.cpython-312.pyc
```

### samples/, research/, tests/transcripts/ — corpora / personal content
```
samples/:
samples/README.md
samples/wikifeedia.json
research/:
research/hermes-agent/toolset_distributions.py
research/hermes-agent/LICENSE
research/hermes-agent/batch_runner.py
research/hermes-agent/README.md
research/hermes-agent/AGENTS.md
research/hermes-agent/toolsets.py
research/hermes-agent/cli.py
research/hermes-agent/.gitmodules
research/hermes-agent/run_agent.py
research/hermes-agent/requirements.txt
(no docs/conversations/)
tests/transcripts/:
tests/transcripts/v0.1-gpt-5.5.md
tests/transcripts/v0.1-gpt-5.4-mini.md
```

## 8. PII & personal-content findings

### 8.1 Personal Gmail address — RED (one remediation needed)

`a.r.r.qvs@gmail.com` appears **45 times** in `.beads/issues.jsonl` as the `owner` field of auraken-prefix beads.

```
$ grep -c "a.r.r.qvs@gmail.com" .beads/issues.jsonl
45
```

- All occurrences are in `.beads/issues.jsonl` (no other tracked file)
- The email is the user's personal Gmail — links `mistakeknot` (public alias) to a personal identity
- The blob is in current HEAD AND in every prior commit that touched issues.jsonl

**Remediation paths:**
1. **`bd update --owner <redacted-id>`** across all 45 beads, then `bd export` → fresh JSONL commit. Removes the email from HEAD but leaves it in earlier commits.
2. **History rewrite via `git filter-repo`** — strip the email from every historical version of `.beads/issues.jsonl`. Authoritative scrub; force-push required; any pre-flip clones still carry the original history.
3. **Squash the entire history into a single commit** before flipping. Loses commit archaeology but is the cleanest scrub for a personal-private → public flip when history doesn't need to travel.

### 8.2 Other emails — clean

Other emails in tracked content (`digital-no-reply@amazon.com`, `noreply@steampowered.com`, etc.) are **email-sender filter constants** in `src/auraken/gmail_import/parsers/*.py`. They are publicly-known noreply addresses used to identify the sender of receipt emails for parsing. Not PII.

`support@generalsystemsventures.com` and `privacy@generalsystemsventures.com` are the user's company domain — not personal Gmail. Acceptable disclosure (the connection to GSV is presumably intentional in a public release).

### 8.3 Personal paths — yellow (mild info disclosure)

References to `/home/mk/...` appear in:
- `docs/plans/2026-03-29-signal-first-foundation.md` (25 hits)
- `.claude/reviews/fd-plan-architecture.md` (13 hits)
- Various reflection / brainstorm docs (1-3 hits each)

These reveal the dev environment layout (`/home/mk/projects/Sylveste/apps/Auraken`). Not a security risk, but discloses that the dev box is Linux and the username is `mk`. Worth a sed-replace pass before flip if disclosure of dev environment is not desired.

### 8.4 Personal product disclosures — yellow

`docs/brainstorms/2026-04-05-gmail-purchase-import-brainstorm.md` references specific products the user owns ("AirPods Pro 3, Sony WH-1000XM6, MacBook Pro 14"). These are example items in a discussion of the Gmail purchase-import feature. Mild — equivalent to mentioning hardware in a blog post.

## 9. IP / disclosure surface

### 9.1 Auraken's proprietary 291-lens library — yellow (intentional disclosure?)

`src/auraken/lens_library.json`, `lens_library_v2.json`, `lens_communities.json`, `lens_edges.json` together encode the full lens dataset and its graph structure. This is **Auraken's product IP**. Flipping public means:
- Anyone can vendor the lens library
- Competitors can analyze the graph topology
- The 291-lens count claim in MANIFEST becomes verifiable

This is a product / licensing decision, not a security decision. The user should make it consciously. License options:
- Keep proprietary; ship only via the published distribution (private repo, public release attachments)
- MIT / Apache the whole repo
- Source-Available with a non-compete clause
- CC-BY for the lens content + MIT for the code

### 9.2 Pre-pivot Python daemon source — neutral

`src/auraken/` contains the legacy Telegram+Anthropic daemon. Going public exposes:
- The OODARC conversation engine implementation
- Gmail import OAuth flow code
- PostgreSQL + pgvector schema
- The architectural approach Auraken used pre-pivot

Code quality is dev-grade (working but not polished). Public exposure exposes design choices but not credentials.

## 10. Final verdict

**Status: 🟡 YELLOW — one remediation required before flip.**

**Blocker (must address):**
- The personal Gmail `a.r.r.qvs@gmail.com` in `.beads/issues.jsonl` (45 occurrences). Strip via one of the remediation paths in §8.1.

**Decisions the user should make consciously (not blockers, but acknowledgments):**
1. The 291-lens library + graph become world-readable (§9.1). Confirm intent + add a LICENSE file.
2. Dev environment paths (`/home/mk/...`) in docs are disclosed (§8.3). Optional sed pass.
3. Product disclosures in brainstorm doc (§8.4). Optional review.

**Confirmed clean:**
- ✅ Zero high-signal API key prefixes across all 745 historical blobs
- ✅ Zero provider-specific credentials (sk-ant-, sk-proj-, AKIA, AIza, xoxb, ghp/gho/ghu/ghs/ghr/pat) anywhere in history
- ✅ `.env` never committed at any point on any branch
- ✅ Every credential lookup in `src/auraken/` goes through `settings.<name>` (pydantic-settings)
- ✅ `.env.example` is properly sanitized (placeholder values, no real credentials)
- ✅ `research/hermes-agent/` is fully gitignored — 0 tracked files
- ✅ No committed `.bak`, `.backup`, `.orig`, `.swp` files
- ✅ No hardcoded passwords / bearer tokens / GitHub PATs

**Recommended next step:** decide on remediation path for §8.1, then schedule the flip. The audit corpus + this report live at `/tmp/auraken-audit/`.


---

## ADDENDUM (2026-05-27 — later that day)

While executing the §8.1 remediation (Path 1: HEAD-only scrub of personal Gmail in `.beads/issues.jsonl`), two findings the original audit missed surfaced. These materially change the verdict.

### A1. `.beads/.beads-credential-key` — tracked binary credential blob

A 32-byte binary file (`.beads/.beads-credential-key`) has been tracked since the `bd init` commit (`fa707c6`). It is the local key bd uses for Dolt sync auth.

- The regex sweep in §3-5 used text-shaped credential patterns (`sk-`, `ghp_`, etc.) and did not match binary blobs.
- The outer Sylveste `.gitignore` correctly ignores `.beads-credential-key`. The apps/Auraken `.gitignore` did not until commit `638092a` (this addendum's remediation).
- Current HEAD: the file is untracked going forward; local copy preserved so bd keeps working.
- History: the credential blob remains in every prior commit. Rotating the local key (`bd backup keygen` or equivalent) makes the historical blob inert, but defense-in-depth says scrub it.

**Lesson for future audits:** also flag any tracked file < 256 bytes with high-entropy binary content.

### A2. Git author / committer email on every commit — `MK <a.r.r.qvs@gmail.com>`

```
$ git log --all --format="%ae" | sort | uniq -c | sort -rn
    137 a.r.r.qvs@gmail.com
$ git config --local user.email
a.r.r.qvs@gmail.com
$ git config --global user.email
mistakeknot@vibeguider.org
```

The personal Gmail is the **local** git author email for this repo (overrides the global). Every one of the 137 commit objects in history carries it in both author and committer fields. This metadata travels with the repo on any clone/fork.

**This is the dominant exposure surface.** A HEAD-only scrub of `.beads/issues.jsonl` (which the commit `638092a` accomplished — HEAD blob now uses `mk@generalsystemsventures.com`) addresses one tracked-content vector and ignores the much bigger metadata vector. Any third party who clones the public repo gets the personal Gmail via `git log` immediately.

**This cannot be fixed without rewriting history.**

### Updated remediation matrix

The original audit listed three paths. Given findings A1 + A2:

| Path | Scrubs JSONL? | Scrubs credential blob? | Scrubs git author? | Effort | Force-push? |
|------|---|---|---|---|---|
| ~~1: bd update HEAD-only~~ | yes (HEAD) | no | **no** | low | no |
| 2: `git filter-repo --mailmap` + path-filter | yes (history) | yes | yes | medium | yes (destructive) |
| 3: Squash entire history to single commit | yes | yes | yes (set author at squash) | low-medium | yes (destructive) |
| **C (NEW): Fresh public repo** | n/a | n/a | n/a | low | none |

### Path C — fresh public repo (now the recommended default)

Don't flip `mistakeknot/auraken`. Keep it private. Create a new public repo `mistakeknot/auraken-public` (or `mistakeknot/auraken-distribution`) that contains:

- `integrations/hermes/dist/v0.1/` (the published bundle)
- `apps/Auraken/dist/{build-binaries,build-dist,install.sh.in,test-install}.sh` (the build tooling)
- A minimal LICENSE
- A README pointing back to the upstream private repo

Single commit, authored as `mk@generalsystemsventures.com`, no historical baggage, no IP-disclosure decisions for the legacy daemon, no need to rewrite history. The published GitHub Release attachments are already independent of the source repo — moving the release tag to the new public repo is a `gh release create` against the new repo with the existing tarball + checksums + install.sh.

INSTALL.md's `gh release download` and `curl -LO` commands change their repo path from `mistakeknot/auraken` to `mistakeknot/auraken-public`. That's it.

**Trade-offs of Path C:**
- + No history rewrite, no force-push, no destructive operations on the working repo
- + IP-disclosure decisions (§9.1) become per-file-add at the new-repo seeding step rather than a sweeping repo-wide call
- + The lens library can stay in the private repo; the public bundle ships the binary + MCP server + skill only
- − Loses the "see the source that built this" link for the public release
- − Two repos to keep in sync if future v0.x changes touch both code that lives in the private repo AND content that should be in the public release

### Updated verdict

**Status: 🔴 RED for in-place public flip of `mistakeknot/auraken`. 🟢 GREEN for Path C (fresh public repo).**

Phase 1.5 partial remediation (`638092a`) cleaned the JSONL in HEAD and untracked the credential key going forward. This is a reasonable hygiene improvement regardless of which final path the user picks. It does not resolve the in-place-flip blockers.


---

## Phase 2 — history rewrite complete (2026-05-27, later still)

Executed `git filter-repo` against `mistakeknot/auraken` with three coordinated passes:

```
git filter-repo \
  --mailmap <mailmap-file> \
  --invert-paths --path .beads/.beads-credential-key \
  --replace-text <replacement-file> \
  --force
```

- **Mailmap** rewrites all 137 commits' author + committer fields from `a.r.r.qvs@gmail.com` → `mk@generalsystemsventures.com`
- **Path removal** drops the `.beads/.beads-credential-key` blob from every commit's tree across history
- **Text replacement** substitutes the personal Gmail with the company email in any blob's contents (covers historical `.beads/issues.jsonl` snapshots where 45 records carried the email)

### Verification (post-rewrite, post-force-push)

| Check | Pre-rewrite | Post-rewrite |
|---|---|---|
| Commits authored by `a.r.r.qvs@gmail.com` | 137 | **0** |
| Commits authored by `mk@generalsystemsventures.com` | 0 | **137** |
| Blobs containing personal Gmail (across all history) | several | **0** |
| Commits with `.beads-credential-key` in their tree | 137 | **0** |
| `auraken-distribution-v0.1.0` tag | `7fb2545` → `ec099dd` | `f7a43b7` → `2baf9b58` |
| `mistakeknot/auraken/main` HEAD | `638092a` | `16271cf` |

### Release page impact

- **Tag re-pointed automatically** — GitHub Release page's tag-association follows the new SHA `2baf9b58`.
- **Three attachments unchanged** — tarball, checksums.txt, install.sh remained at their original SHA-256 digests because they're opaque blobs uploaded independently of the source tree.
- **End-user install path verified post-rewrite**: `gh release download` → `sha256sum -c checksums.txt --ignore-missing` returns `OK` → `tar -xzf` → `bash install.sh` succeeds against a fresh `$HERMES_HOME`.

### Local sync

The local `apps/Auraken` working copy was hard-reset to the new `origin/main`. Stashed parallel-session work (uv.lock, recon-spike SKILL.md edits, etc.) was preserved via `git stash pop` after the reset — no conflicts because filter-repo only modified files (`.beads/issues.jsonl`, `.beads/.beads-credential-key`) outside the stash's diff. Reflog + GC dropped the orphaned old commits from local storage.

Local git config (`apps/Auraken/.git/config`) updated:
- `user.email = mk@generalsystemsventures.com`
- `user.name = MK`

Going forward, every commit authored from this checkout uses the company email by default.

### Updated verdict — pre-flip state

**Status: 🟢 GREEN.** All findings from the original audit + the A1/A2 addendum are now resolved:

- ✅ Personal Gmail nowhere in the repo (HEAD or history)
- ✅ Credential-key blob removed from all history; gitignored going forward
- ✅ Git author metadata is `mk@generalsystemsventures.com` on every commit
- ✅ Release attachments unchanged; end-user install path verified

**Phase 3 (the actual `gh repo edit --visibility public --accept-visibility-change-consequences`) remains pending user authorization.** Pre-flip state is now clean.

### Insurance backup

A mirror clone of the pre-rewrite state was kept at `/tmp/auraken-backup` for the duration of the rewrite. Can be removed once Phase 3 lands and the new state is verified stable.

