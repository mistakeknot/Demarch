#!/bin/bash
# 4K/UHD sync driver: pulls the UHD tier from jarmusch into /data/movies-4k,
# one film at a time, resumable. Managed by uhd-sync.service.
#
# WHY THIS EXISTS. The migration to grey brought the 1080p tier only.
# /data/movies-4k was created but never filled (0 files), and radarr-4k has all
# 39 of its titles monitored=false, so it has never searched for anything. The
# 32 UHD files therefore sat on jarmusch while Jellyfin served the only copy it
# had -- 1080p. This closes that gap.
#
# BWLIMIT IS THE INVERSE OF kg_restore.sh, DELIBERATELY. Both scripts pull
# jarmusch -> grey, which is the home connection's UPLOAD -- one small, shared,
# asymmetric pipe. kg_restore runs uncapped 00:00-08:00 LA and throttled to
# 1200 KB/s the rest of the day. This one does the opposite: uncapped 08:00-
# 24:00, throttled 00:00-08:00. So whichever one is uncapped, the other is
# gentle, and neither needs to know the other exists. No coordination, no
# pausing, no shared lock -- just complementary schedules.
#
# Consequence worth knowing: this is SLOWER than kg_restore would be, because
# daytime is the worse window. That is the correct trade. The KG restore has
# ~3.3 TB left and this has 648 GB; the small job should yield the good window.
OPS=/root/grey-ops
SRC=/volume1/Jarmusch/Multimedia/Movies
DST=/data/movies-4k
ORDER=$OPS/uhd-sync-order.txt
PROG=$OPS/uhd-sync-done.txt
LOG=$OPS/uhd-sync.log
MIN_FREE=2199023255552   # 2 TiB, same floor as kg_restore

[ -f $OPS/webhooks.env ] && source $OPS/webhooks.env

exec 9>/run/uhd-sync.lock
flock -n 9 || exit 0
[ -e $OPS/uhd-sync-complete ] && exit 0
touch "$PROG"

log(){ echo "$(date -Is) $*" >> "$LOG"; }
discord(){ [ -n "${FEED_WEBHOOK:-}" ] && curl -sf -X POST -H "Content-Type: application/json" \
    -d "{\"content\":\"$1\"}" "$FEED_WEBHOOK" >/dev/null 2>&1; }

bwlimit(){
  # Mirror image of kg_restore.sh's window. See the header note.
  local h=$(TZ=America/Los_Angeles date +%-H)
  if [ "$h" -ge 8 ]; then echo 0; else echo 1200; fi
}

total=$(wc -l < "$ORDER")
log "driver start (done $(wc -l < "$PROG")/$total)"

while IFS= read -r d; do
  [ -z "$d" ] && continue
  grep -qxF "$d" "$PROG" && continue

  free=$(df --output=avail -B1 /data | tail -1)
  if [ "$free" -lt "$MIN_FREE" ]; then
    log "STOP low disk: ${free}B free"
    exit 0
  fi

  bw=$(bwlimit)
  n=$(( $(wc -l < "$PROG") + 1 ))
  log "START [$n/$total] bw=${bw}KB/s: $d"

  ok=0
  for attempt in 1 2 3; do
    # -s (--protect-args) matters here: these titles contain spaces, commas,
    # apostrophes and an ampersand ("Deadpool & Wolverine").
    rsync -a -s --partial --timeout=300 --bwlimit=$bw \
      --chown=1001:1001 --chmod=D755,F644 \
      -e "ssh -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6" \
      "jarmusch:$SRC/$d/" "$DST/$d/" >> "$LOG" 2>&1
    rc=$?
    [ $rc -eq 0 ] && { ok=1; break; }
    log "attempt $attempt rc=$rc: $d"
    sleep $(( attempt * 120 ))
  done

  if [ "$ok" = 1 ]; then
    echo "$d" >> "$PROG"
    log "DONE [$n/$total]: $d"
  else
    log "FAIL after 3 attempts: $d — exiting for service restart"
    exit 1
  fi
done < "$ORDER"

touch $OPS/uhd-sync-complete
log "ALL DONE $(wc -l < "$PROG")/$total"
discord "✅ **4K sync complete** — all $total UHD films pulled from jarmusch into /data/movies-4k (648 GB). Trigger a Radarr-4K rescan to import."
