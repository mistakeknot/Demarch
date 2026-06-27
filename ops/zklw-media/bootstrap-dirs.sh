#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Creates the hardlink-friendly media layout under $MEDIA_ROOT and the
# config root. Idempotent — safe to re-run. Run on zklw AFTER the 20TB
# volume is mounted and AFTER you've set MEDIA_ROOT in .env.
#
#   The layout (single root so imports = instant hardlinks):
#
#   $MEDIA_ROOT/
#   ├── downloads/        <- qBittorrent + SABnzbd write here
#   │   ├── complete/
#   │   └── incomplete/
#   ├── movies/           <- Radarr library (Jellyfin reads here)
#   └── tv/               <- Sonarr library
#
# Inside containers this whole tree appears at /data, so Radarr sees
# /data/downloads and /data/movies on ONE filesystem → hardlinks work.
# ----------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")"
if [[ ! -f .env ]]; then
  echo "ERROR: no .env found. Copy .env.example to .env and edit it first." >&2
  exit 1
fi
# shellcheck disable=SC1091
set -a; source .env; set +a

echo "MEDIA_ROOT  = $MEDIA_ROOT"
echo "CONFIG_ROOT = $CONFIG_ROOT"
echo "PUID:PGID   = $PUID:$PGID"
echo

# Sanity: refuse to run if MEDIA_ROOT isn't a real mountpoint with space.
# (Catches the classic "wrote 2TB to the unmounted placeholder dir" disaster.)
if ! mountpoint -q "$MEDIA_ROOT" 2>/dev/null; then
  echo "WARNING: $MEDIA_ROOT is not a separate mountpoint." >&2
  echo "         If you meant to use the 20TB volume, mount it first." >&2
  echo "         (For an intentional NVMe proof-of-concept, ignore this.)" >&2
  read -r -p "Continue anyway? [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 1
fi

avail_gb=$(df -BG --output=avail "$MEDIA_ROOT" | tail -1 | tr -dc '0-9')
echo "Available on $MEDIA_ROOT: ${avail_gb}G"
echo

mkdir -p \
  "$MEDIA_ROOT/downloads/complete" \
  "$MEDIA_ROOT/downloads/incomplete" \
  "$MEDIA_ROOT/movies" \
  "$MEDIA_ROOT/tv" \
  "$CONFIG_ROOT"/{jellyfin,jellyseerr,radarr,sonarr,prowlarr,qbittorrent,sabnzbd}

# Ownership so the containers (running as PUID:PGID) can write.
chown -R "$PUID:$PGID" "$MEDIA_ROOT" "$CONFIG_ROOT"

echo "Layout ready:"
find "$MEDIA_ROOT" -maxdepth 2 -type d | sort | sed "s|^|  |"
echo
echo "Next: docker compose up -d   (then follow README step 4: add indexers)"
