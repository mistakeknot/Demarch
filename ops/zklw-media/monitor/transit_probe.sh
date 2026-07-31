#!/usr/bin/env bash
# Sample the corridor between grey (Hetzner DE) and the house.
#
# HISTORY, because the first version of this script was wrong and its own output
# caught it. It probed cachefly, reasoning that a US CDN would exercise the
# transatlantic path. It does not: cachefly anycasts, and from grey it resolves
# to a European edge 5 ms away. The second sample read 624 Mbps -- grey to
# Frankfurt, never crossing the Atlantic, measuring nothing this estate cares
# about. A probe whose numbers look great is not thereby a working probe.
#
# The right target is jarmusch, the NAS at the house: it is always on, grey
# already has key access for the Karagarga restore, and Tailscale routes it
# direct over the home public IP -- the same corridor Jellyfin streams through.
#
#   grey -> european cachefly edge      5 ms      (irrelevant)
#   grey -> jarmusch                  176 ms      (the corridor)
#
# WHAT IS MEASURED, and why both halves are needed:
#
#   loss/jitter  ping is nearly free, but on its own it is not sufficient. When
#                the corridor collapsed to 0.085 Mbps, RTT to the house barely
#                moved (250 -> 251 ms). Latency alone would have reported
#                "healthy" through the worst outage observed. Loss and jitter
#                are the parts that plausibly move; they are recorded because
#                they are cheap, not because they are trusted.
#
#   throughput   the ground truth, and pushed grey -> jarmusch deliberately.
#                That direction is the home connection's DOWNLOAD, which is what
#                Jellyfin streaming actually consumes. Pulling instead would
#                measure home upload -- a different, much smaller pipe on an
#                asymmetric line, and the one the restore is already using.
#
# THE NUMBER IS A FLOOR, NOT THE LINK CAPACITY. Two effects hold it under the
# true figure, and both were measured rather than assumed:
#
#   slow start   at 176 ms RTT a small transfer is mostly congestion-window
#                ramp. Measured on this exact path:
#                     8 MB -> 16.9 Mbps      32 MB -> 43.4 Mbps
#                Same link, same minute -- the payload size was the variable.
#                Hence 32 MB. (jarmusch was ruled out as the cause: it is a
#                Ryzen V1500B with AES-NI, not a weak NAS CPU.)
#
#   ssh window   per-channel flow control (~2 MB) caps throughput near
#                window/RTT = 2 MB / 0.176 s ~= 91 Mbps regardless of the link.
#
# So treat a reading as "at least this much". That is sufficient for the actual
# question -- telling a healthy corridor from one delivering 0.085 Mbps is not a
# close call -- but never quote these as bandwidth figures. What matters is that
# the number is produced identically every time, so samples are comparable to
# each other even where they understate the link.
set -u
LOG=${LOG:-/root/grey-ops/transit-probe.log}
PEER=${PEER:-jarmusch}
PEER_IP=${PEER_IP:-100.108.23.82}
MB=${MB:-32}           # 1.5 GB/day at one sample per 30 min

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
la=$(TZ=America/Los_Angeles date +%H)

# --- loss / latency / jitter -------------------------------------------------
p=$(ping -c 30 -i 0.3 -W 2 "$PEER_IP" 2>/dev/null)
loss=$(printf '%s' "$p" | sed -n 's/.*, \([0-9.]*\)% packet loss.*/\1/p')
rtt=$(printf  '%s' "$p" | sed -n 's|.*= [0-9.]*/\([0-9.]*\)/.*|\1|p')
jit=$(printf  '%s' "$p" | awk -F/ '/rtt min/{print $NF}')

# --- throughput, grey -> house (the streaming direction) ---------------------
# /dev/zero is fine: ssh compression is off by default, so this is not a
# compressible-payload illusion. Bound it so a dead corridor cannot wedge cron.
start=$(date +%s.%N)
sent=$(timeout 120 dd if=/dev/zero bs=1M count="$MB" 2>/dev/null \
       | timeout 120 ssh -o BatchMode=yes -o ConnectTimeout=15 \
             -o StrictHostKeyChecking=accept-new "$PEER" \
             'cat > /dev/null && echo ok' 2>/dev/null)
end=$(date +%s.%N)

if [ "${sent:-}" = "ok" ]; then
    mbps=$(awk -v m="$MB" -v a="$start" -v b="$end" \
           'BEGIN{d=b-a; printf "%.2f", (d>0)? m*8.388608/d : 0}')
else
    mbps=FAIL          # distinct from 0.00: the transfer never completed
fi

printf '%s la_hour=%s loss=%s rtt=%s jitter=%s mbps=%s\n' \
    "$ts" "$la" "${loss:-NA}" "${rtt:-NA}" "${jit:-NA}" "$mbps" >> "$LOG"

if [ "$(wc -l < "$LOG")" -gt 9000 ]; then
    tail -n 8000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
