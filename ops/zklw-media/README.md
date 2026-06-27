# zklw media server

A private, Tailscale-only Jellyfin media stack with one-click movie requests,
driven by the *arr automation suite and an optional Claude/Hermes ops agent.

**Server:** zklw (Ryzen 9 5950X, 121 GB RAM, Ubuntu 24.04, Tailscale `100.78.63.67`)
**Access model:** tailnet-only. No public ports. Reach UIs at `http://100.78.63.67:<port>`.
**Player:** Jellyfin (free, no account).

---

## How a movie request flows

```
You open Jellyseerr → search a title → click Request
        │
        ▼
   Radarr finds the best release on YOUR indexers (private tracker + Usenet)
        │
        ▼
   qBittorrent / SABnzbd downloads it under /data/downloads
        │
        ▼
   Radarr hardlinks + renames it into /data/movies   (instant, no copy)
        │
        ▼
   Jellyfin shows it, ready to play on your TV / phone / iPad
```

You configure the indexers + credentials **once** (step 4). After that it is
one click per movie. **You** hold the tracker accounts and make the requests;
the stack just automates the mechanics of *your* request.

---

## Setup (run on zklw)

### 1. Attach + mount the 20TB volume

Attach the volume in the ReliableSite panel (may need a reboot), then confirm
it appears as a new block device:

```bash
lsblk            # look for a new ~20T disk, e.g. /dev/sdb or /dev/nvme1n1
```

Format (only if brand new — DESTROYS any data on the device) and mount:

```bash
DEV=/dev/sdb                      # <-- set to the real device from lsblk
sudo mkfs.ext4 -L media "$DEV"
sudo mkdir -p /mnt/media
echo "LABEL=media /mnt/media ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
sudo mount -a
df -h /mnt/media                  # confirm ~20T available
```

> **Interim option (no waiting):** to demo on the existing NVMe first, set
> `MEDIA_ROOT=/srv/media` in `.env` and `sudo mkdir -p /srv/media`. Migrate to
> `/mnt/media` later by stopping the stack, `rsync -a` the tree across, and
> flipping the one `MEDIA_ROOT` line. **Keep downloads + library on the same
> root** so hardlinks keep working.

### 2. Configure environment

```bash
cd ops/zklw-media
cp .env.example .env
id -u; id -g                      # put these in .env as PUID / PGID
$EDITOR .env                      # set MEDIA_ROOT, PUID, PGID, TZ
```

### 3. Create the directory layout + bring up the stack

```bash
sudo ./bootstrap-dirs.sh
docker compose up -d
docker compose ps                 # all should be Up
```

### 4. Wire it together (one-time, in the web UIs over Tailscale)

Order matters — each step feeds the next:

1. **qBittorrent** `http://100.78.63.67:8080`
   Default login `admin` / (temp password printed in `docker compose logs qbittorrent`).
   Change the password. Set default save path to `/data/downloads`.
2. **SABnzbd** `http://100.78.63.67:8081` — add your Usenet provider + an indexer
   API key. Set the completed-download folder to `/data/downloads/complete`.
3. **Prowlarr** `http://100.78.63.67:9696` — **this is where you add your private
   tracker and Usenet indexers.** Settings → Indexers → add. Then Settings →
   Apps → add Radarr (and Sonarr) so indexers sync automatically.
4. **Radarr** `http://100.78.63.67:7878`
   - Settings → Media Management → root folder `/data/movies`, enable hardlinks.
   - Settings → Download Clients → add qBittorrent (host `qbittorrent`, port 8080)
     and SABnzbd (host `sabnzbd`, port 8080).
   - Quality profiles come from Prowlarr/Recyclarr.
5. **Jellyfin** `http://100.78.63.67:8096` — first-run wizard; add a Movies
   library pointing at `/data/movies` and a Shows library at `/data/tv`.
6. **Jellyseerr** `http://100.78.63.67:5055` — connect it to Jellyfin (for users)
   and to Radarr/Sonarr (for fulfillment). **This is the URL you share with
   family** — the friendly request portal.

### 5. (Optional) Invite users

In Tailscale, share the tailnet or use Tailscale's user-sharing so family
devices can reach `100.78.63.67`. They only ever need Jellyseerr (to request)
and Jellyfin (to watch).

---

## The agent layer (Claude Code / Hermes)

The *arr stack handles the deterministic grab loop. The agent handles the
fuzzy ops around it — see `agent/README.md`. Examples:

- "Why is the Dune request stuck?" → reads Radarr queue + qBittorrent status.
- "This film imported with the wrong year." → fixes the Radarr movie + refreshes.
- "Audit the library for duplicate or misnamed folders."
- "What got added this week?" → summarizes Jellyfin recently-added.

---

## Backups to your home NAS

Config is small and lives under `${CONFIG_ROOT}` (default `/opt/zklw-media/config`).
Back THAT up to your 24TB NAS (it's the irreplaceable part — the media can be
re-fetched). A `restic`/`rsync` job over Tailscale to the NAS is the clean path;
ask the agent to set one up once the stack is live.

## Deferred next-actions (file as beads from the main checkout)

These can't be done until you've acted on the hardware/bring-up, so they're
tracked here for the workstation to file as beads:

1. **[P1] Attach + mount the 20TB volume** — not yet visible on zklw (only the
   1.8TB NVMe is present). Attach in the ReliableSite panel, then format/mount
   at `/mnt/media` (step 1). *Blocks everything below.*
2. **[P2] Bring up the stack + wire indexers** — `bootstrap-dirs.sh`,
   `docker compose up -d`, then the one-time UI wiring in step 4 (Prowlarr
   indexers incl. your private tracker + Usenet; Radarr clients + root folder;
   Jellyfin libraries; Jellyseerr connect).
3. **[P3] Agent env + NAS backup** — populate `~/.config/zklw-media/agent.env`
   with API keys, verify `mediactl.py health`, then set up a nightly restic/rsync
   of `CONFIG_ROOT` to the 24TB home NAS over Tailscale.

## Stop / update / logs

```bash
docker compose logs -f radarr        # follow one service
docker compose pull && docker compose up -d   # update all images
docker compose down                  # stop everything (data persists)
```
