# Agent ops layer — the "organize movies with Claude/Hermes" part

This is where an LLM agent earns its keep on a media server. The *arr stack
already does the deterministic grab loop (search → score → download → import).
An agent is the **mechanic and dispatcher** around it — the fuzzy work that a
fixed script can't do well.

## The division of labor (read this first)

| Job | Owner | Why |
|---|---|---|
| Decide a release is "good enough" and download it | **Radarr** | Deterministic scoring; ms-fast; no hallucination |
| Pick *what* movie to get | **You** (via Jellyseerr) | It's your call + your tracker accounts |
| Diagnose *why* a request is stuck | **Agent** | Reads queue + logs, reasons over messy error text |
| Fix a wrong year / poster / merged folder | **Agent** | Fuzzy matching + API edits |
| Audit library hygiene, summarize what's new | **Agent** | Cross-references multiple APIs, writes a digest |
| Set up backups, write new automation | **Agent** | Generates + tests the glue code |

**Why not let the agent do the downloading?** Acquisition is a tight,
repeatable state machine — exactly what purpose-built software does better and
cheaper than an LLM making live torrent decisions every loop. And keeping the
agent out of the grab loop keeps the "what to acquire" decision firmly with
you, against your accounts. The agent observes and repairs; it does not acquire.

## Tooling

`mediactl.py` is a dependency-free (stdlib-only) control surface:

```bash
./mediactl.py health          # are all services up?
./mediactl.py queue           # downloads + WHY anything is stuck
./mediactl.py movie "Dune"    # a title's status across Radarr + Jellyfin
./mediactl.py audit           # monitored-but-missing + duplicate titles
./mediactl.py recent          # what landed recently
```

It prints JSON so the agent reasons over structure, not scraped HTML. It is
deliberately **read-mostly** — it surfaces problems; you approve the fixes.

## Setup

```bash
mkdir -p ~/.config/zklw-media
cat > ~/.config/zklw-media/agent.env <<'EOF'
RADARR_URL=http://100.78.63.67:7878
RADARR_API_KEY=...        # Radarr → Settings → General → API Key
SONARR_URL=http://100.78.63.67:8989
SONARR_API_KEY=...
JELLYFIN_URL=http://100.78.63.67:8096
JELLYFIN_API_KEY=...      # Jellyfin → Dashboard → API Keys
QBIT_URL=http://100.78.63.67:8080
QBIT_USER=admin
QBIT_PASS=...
EOF
chmod 600 ~/.config/zklw-media/agent.env
```

## Example agent prompts (run Claude Code on zklw)

- *"Run mediactl queue and tell me what's stuck and why, in plain English."*
- *"The Blade Runner 1982 import has the wrong year. Find it in Radarr and fix it."*
- *"Audit the library and give me a cleanup list, worst offenders first."*
- *"Summarize what got added this week as a short note I can send the family."*
- *"Set up a nightly restic backup of the config dir to my home NAS over Tailscale."*

## Extending it

`mediactl.py` is intentionally small. To add a capability (e.g. trigger a
Radarr re-search, or talk to qBittorrent), add a `cmd_*` function and register
it in `COMMANDS`. Keep write-actions explicit and few — the agent should
*propose* destructive actions and let you confirm, not fire them blind.
