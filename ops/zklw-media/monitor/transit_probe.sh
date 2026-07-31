#!/usr/bin/env bash
# Sample throughput across the transatlantic path grey depends on.
#
# Jellyfin buffering was traced to the Charter -> Lumen -> Colt -> Hetzner
# corridor, which degrades episodically. Three spot checks gave 0.085 Mbps,
# 17 Mbps and 84 Mbps, and each time a tidy causal story was built on two of
# them it was wrong -- transcoding, then congestion control, then peak-hour
# timing. What actually decides whether to migrate 10 TB and 475 seeding
# torrents to a US host is the *frequency and duration* of the bad periods,
# and no amount of spot-checking answers that.
#
# So: sample continuously, decide later. Cheap -- 20 MB every 15 min is
# ~1.9 GB/day on an unmetered port.
#
# Direction note: this measures grey pulling FROM the US, while streaming is
# grey pushing TO the US. Not identical, but the same transit corridor and the
# only end of it that is always powered on. Read it as a corridor health
# indicator, not as a Jellyfin bitrate prediction.
set -u
LOG=${LOG:-/root/grey-ops/transit-probe.log}
BYTES=${BYTES:-20971520}          # 20 MB
URL=${URL:-https://cachefly.cachefly.net/100mb.test}

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
la=$(TZ=America/Los_Angeles date +%H)

# %{speed_download} is bytes/sec averaged over the transfer. --max-time bounds a
# stall: a probe that cannot move 20 MB in 90 s is itself the signal we want, and
# curl still reports the (tiny) speed it managed rather than failing silently.
read -r speed code < <(curl -s -o /dev/null --max-time 90 \
    -r 0-$((BYTES - 1)) \
    -w '%{speed_download} %{http_code}' "$URL" 2>/dev/null || echo "0 000")

mbps=$(awk -v s="${speed:-0}" 'BEGIN{printf "%.2f", s*8/1000000}')
printf '%s la_hour=%s mbps=%s http=%s\n' "$ts" "$la" "$mbps" "${code:-000}" >> "$LOG"

# Keep the log bounded without needing logrotate: ~4 samples/hr * 24 * 90 days.
if [ "$(wc -l < "$LOG")" -gt 9000 ]; then
    tail -n 8000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
