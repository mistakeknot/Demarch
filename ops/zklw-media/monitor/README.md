# Transit probe

`transit_probe.sh`, every 15 min from grey's root crontab, appending to
`/root/grey-ops/transit-probe.log`:

    2026-07-31T04:21:52Z la_hour=21 mbps=84.73 http=206

## Why this exists

Jellyfin buffering was eventually traced to the transatlantic corridor between
the house's ISP and Hetzner — Charter → Lumen → **Colt** → Hetzner, breaking at
the Lumen→Colt handoff (63 ms → 326 ms). Not the codec chain, not the CPU, not
the client, not congestion control. All four of those were checked and cleared:

| suspect | measurement | verdict |
|---|---|---|
| GPU-less transcoding | 66 fps, **2.74× realtime** | innocent |
| disk | **613 MB/s** cold read | innocent |
| client | Shield Pro on Auto, correct bitrate choice | innocent |
| TCP `cubic` | interleaved A/B vs `bbr`: **identical** | innocent |

## What it is actually for

Three spot checks of the corridor gave **0.085**, **17**, and **84 Mbps**. Each
time a causal story was built from two of them it turned out wrong — first
transcoding, then congestion control, then "peak-hour congestion", which died
when 21:20 LA (deeper into prime time than the bad sample) measured 84 Mbps.

Two points always define a trend; they just don't define a true one. On a
channel that swings three orders of magnitude, spot checks cannot distinguish
a rare transient from a nightly outage — and that distinction is the entire
migration decision. Moving ~10 TB and 475 seeding torrents to a US host is
obviously right if the corridor collapses every evening and obviously wrong if
it drops out for two hours a month.

So this samples continuously and the decision waits for data. ~1.9 GB/day on an
unmetered port.

## Reading it

    # bad periods
    awk -F'mbps=' '$2+0 < 10' /root/grey-ops/transit-probe.log

    # profile by hour of the day, LA time
    awk '{split($2,h,"="); split($3,m,"="); s[h[2]]+=m[2]; n[h[2]]++}
         END{for(i=0;i<24;i++) if(n[i]) printf "%02d  %6.1f Mbps  (n=%d)\n", i, s[i]/n[i], n[i]}' \
        /root/grey-ops/transit-probe.log

Decide after a week or two, not after one bad evening.

## Caveats worth keeping in mind

* **Direction.** This measures grey pulling *from* a US CDN; streaming is grey
  pushing *to* the house. Same corridor, opposite direction — a health
  indicator, not a Jellyfin bitrate prediction.
* **Endpoint.** cachefly, not the house. It cannot see problems local to the
  home connection. The home side was separately measured healthy (94-176 Mbps
  to that same CDN) while Hetzner sat at 0.085, which is what isolated the
  fault to the corridor in the first place.
* **A stalled probe is data.** `--max-time 90` bounds it, and curl still
  reports the little it managed rather than failing silently — so a bad period
  shows up as a low `mbps`, not a gap in the log.

Removal: `crontab -e` and delete the line; a dated backup of the previous
crontab sits in `/root/grey-ops/crontab.bak-*`.
