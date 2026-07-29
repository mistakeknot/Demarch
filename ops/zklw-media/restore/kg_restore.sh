#!/bin/bash
# KG restore driver: pulls cold-backup-only KG folders from jarmusch into
# /data/Movies, one dir at a time, resumable, LA-time-aware bwlimit so the
# home upload stays usable. Managed by kg-restore.service.
OPS=/root/grey-ops
SRC=/volume1/Jarmusch/Multimedia/Movies
DST=/data/Movies
ORDER=$OPS/kg-restore-order.txt
PROG=$OPS/kg-restore-done.txt
LOG=$OPS/kg-restore.log
MIN_FREE=2199023255552   # 2 TiB

source $OPS/webhooks.env

exec 9>/run/kg-restore.lock
flock -n 9 || exit 0
[ -e $OPS/kg-restore-complete ] && exit 0

log(){ echo "$(date -Is) $*" >> "$LOG"; }
discord(){ curl -sf -X POST -H "Content-Type: application/json" -d "{\"content\":\"$1\"}" "$FEED_WEBHOOK" >/dev/null 2>&1; }

bwlimit(){
  # 00:00-08:00 America/Los_Angeles: uncapped (0 = no rsync bwlimit) per mk;
  # daytime stays gentle so home upload is usable. Widened from 01:00-07:00
  # on 2026-07-29: 8h instead of 6h of full-rate transfer.
  #
  # NOTE this is evaluated ONCE per film, at START, and rsync cannot change
  # bwlimit mid-transfer. So a long film starting at 07:5x runs uncapped well
  # into the morning, and one starting at 23:5x stays capped all night. The
  # wider window makes the second case rarer, which is the point.
  local h=$(TZ=America/Los_Angeles date +%-H)
  if [ "$h" -lt 8 ]; then echo 0; else echo 1200; fi
}

touch "$PROG"
total=$(wc -l < "$ORDER")
log "driver start (done $(wc -l < "$PROG")/$total)"

while IFS= read -r d; do
  [ -z "$d" ] && continue
  grep -qxF "$d" "$PROG" && continue
  free=$(df --output=avail -B1 /data | tail -1)
  if [ "$free" -lt "$MIN_FREE" ]; then
    log "STOP low disk: ${free}B free"
    if [ ! -e $OPS/kg-restore-lowdisk-alerted ]; then
      touch $OPS/kg-restore-lowdisk-alerted
      discord "⛔ **KG restore paused** — /data under 2 TiB free. Free space, then: systemctl start kg-restore"
    fi
    exit 0
  fi
  rm -f $OPS/kg-restore-lowdisk-alerted
  bw=$(bwlimit)
  n=$(( $(wc -l < "$PROG") + 1 ))
  log "START [$n/$total] bw=${bw}KB/s: $d"
  ok=0
  for attempt in 1 2 3; do
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

touch $OPS/kg-restore-complete
log "ALL DONE $(wc -l < "$PROG")/$total"
discord "✅ **KG restore transfer complete** — all $total cold-backup folders pulled from jarmusch (5.9 TiB). Tonight's adoption run imports the final batch and regenerates the review list."
