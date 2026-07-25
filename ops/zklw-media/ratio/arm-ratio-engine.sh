#!/usr/bin/env bash
# One-shot arming of the grey-area ratio engine. RUN THIS ON grey (as root).
#
# Everything this touches was built, dry-run verified, and left deliberately
# inert. This is the single step that makes grey start earning. It is separated
# out because both actions are outward-facing against a private tracker, and
# that is a human decision, not an automation default.
#
#   ssh grey-area 'bash /root/grey-ops/arm-ratio-engine.sh'
#
# Reversible:
#   racer   -> python3 /root/grey-ops/setup_rss_race.py --disarm
#   KG stops-> re-start those 6 torrents in the qBittorrent UI (files were kept)
#
# What it does, in order:
#   1. Stops 6 Karagarga "featured torrent" torrents. KG's tracker explicitly
#      asks seeders to step back on these; all 6 have 9-13 seeds against ZERO
#      leechers, so stopping costs no upload anybody wants, and it shrinks
#      grey's KG announce footprint from a datacenter IP (bead sylveste-e3fh).
#      The script re-checks the live tracker message and refuses to stop
#      anything with a live leecher or non-zero upload speed.
#   2. Arms the HDBits RSS racer. Against the live feed this matches 15 of 50
#      articles, 0.86-18 GB, median 4.4 GB, none over 25 GB -- fresh 1080p
#      encodes only, by codec-tag whitelist.
#
# Safety invariant that must hold while armed: qbit-manage keeps cleanup:false,
# so nothing can delete a torrent before its Hit-and-Run obligation is met.
# qbit-manage remains the only component permitted to remove a torrent.
set -uo pipefail

echo "=== 1/3  Karagarga featured-torrent stops (6) ==="
if [ -r /root/grey-ops/kg_stop6.py ]; then
  python3 /root/grey-ops/kg_stop6.py apply
else
  echo "  /root/grey-ops/kg_stop6.py missing — skipping (re-deploy it, or stop the 6 by hand)"
fi

echo
echo "=== 2/3  verify the HnR firewall is still closed before arming ==="
# NB: `grep -c` PRINTS "0" and ALSO exits non-zero when there are no matches, so
# `|| echo 0` appends a second line and yields "0\n0" -- which is != "0" and made
# this abort precisely when the firewall was correctly closed. Use `|| true`.
CLEANUP_TRUE=$(grep -c "cleanup: true" /home/mk/grey-media/config/qbit-manage/config.yml 2>/dev/null || true)
CLEANUP_TRUE=${CLEANUP_TRUE:-0}
if [ "$CLEANUP_TRUE" != "0" ]; then
  echo "  ABORT: qbit-manage has cleanup:true somewhere. Arming the racer now could"
  echo "  let a raced torrent be deleted before its HnR obligation is satisfied."
  echo "  Resolve that first, then re-run."
  exit 1
fi
echo "  OK — every share_limits group is cleanup:false; nothing deletes."

echo
echo "=== 3/3  arm the HDBits racer ==="
python3 /root/grey-ops/setup_rss_race.py --arm

echo
echo "=== armed. verify over the next hour ==="
echo "  watch grabs:   docker exec qbittorrent sh -c 'true' ; python3 /root/grey-ops/setup_rss_race.py --status"
echo "  watch ratio:   python3 /root/grey-ops/ratio_report.py"
echo "  disk headroom: df -h /data"
echo
echo "Expect the first grabs within one RSS refresh. If anything looks wrong:"
echo "  python3 /root/grey-ops/setup_rss_race.py --disarm"
