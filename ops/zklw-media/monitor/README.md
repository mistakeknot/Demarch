# Transit probe

`transit_probe.sh`, every 30 min from grey's root crontab, appending to
`/root/grey-ops/transit-probe.log`:

    2026-07-31T04:34:15Z la_hour=21 loss=0 rtt=177.062 jitter=5.336 ms mbps=43.22

## Why this exists

Jellyfin buffering was eventually traced to the corridor between the house's
ISP and Hetzner — Charter → Lumen → **Colt** → Hetzner, breaking at the
Lumen→Colt handoff (63 ms → 326 ms). Not the codec chain, not the CPU, not the
client, not congestion control. All four were checked and cleared:

| suspect | measurement | verdict |
|---|---|---|
| GPU-less transcoding | 66 fps, **2.74× realtime** | innocent |
| disk | **613 MB/s** cold read | innocent |
| client | Shield Pro on Auto, correct bitrate choice | innocent |
| TCP `cubic` | interleaved A/B vs `bbr`: **identical** | innocent |

## What it is actually for

Spot checks of the corridor gave **0.085**, **17**, and **84 Mbps**. Each time a
causal story was built from two of them it turned out wrong — transcoding, then
congestion control, then "peak-hour congestion", which died when 21:20 LA
(deeper into prime time than the bad sample) measured 84 Mbps.

Two points always define a trend; they just don't define a true one. On a
channel that swings three orders of magnitude, spot checks cannot separate a
rare transient from a nightly outage — and that distinction *is* the migration
decision. Moving ~10 TB and 475 seeding torrents to a US host is clearly right
if the corridor dies every evening and clearly wrong if it drops for two hours
a month. So: sample continuously, decide on data.

## The first version was wrong, and its own output caught it

It probed cachefly, on the reasoning that a US CDN exercises the transatlantic
path. It does not — cachefly anycasts, and from grey it resolves to a European
edge **5 ms** away. The second sample read **624 Mbps**: grey to Frankfurt,
never crossing the Atlantic, measuring nothing this estate cares about.

Worth keeping as a caution. The broken probe did not look broken; it looked
*excellent*, because the number it produced was large. A probe reporting good
health is not thereby a working probe, and the failure was only visible because
624 Mbps was too good to be true for a residential link.

The target is now **jarmusch**, the NAS at the house — always on, already
key-accessible from grey for the Karagarga restore, and routed by Tailscale
direct over the home public IP. Same corridor Jellyfin streams through.

    grey -> european cachefly edge      5 ms      (irrelevant)
    grey -> jarmusch                  176 ms      (the corridor)

## What is measured, and why both halves

**loss / rtt / jitter** — nearly free, but *not sufficient alone*. When the
corridor collapsed to 0.085 Mbps, RTT to the house barely moved (250 → 251 ms).
Latency would have reported "healthy" straight through the worst outage
observed. Loss and jitter are recorded because they are cheap and might move,
not because they can be trusted to.

**throughput** — the ground truth, pushed grey → jarmusch *deliberately*. That
direction is the home connection's **download**, which is what Jellyfin
streaming consumes. Pulling instead would measure home upload — a different and
much smaller pipe on an asymmetric line, and the one the restore already uses.

## The number is a floor, not the link capacity

Two effects hold it under the true figure, both measured rather than assumed:

* **Slow start.** At 176 ms RTT a small transfer is mostly window ramp. On this
  exact path, same minute, payload size the only variable:

      8 MB  -> 16.9 Mbps
      32 MB -> 43.4 Mbps

  Hence 32 MB. jarmusch was ruled out as the cause — Ryzen V1500B with AES-NI,
  not a weak NAS CPU.
* **ssh channel window** (~2 MB) caps throughput near `window/RTT` ≈ **91 Mbps**
  regardless of the link.

So read every value as "at least this much", and never quote them as bandwidth.
That is fine for the question being asked — telling a healthy corridor from one
delivering 0.085 Mbps is not a close call — and what matters is that the number
is produced identically each time, so samples are comparable to one another.

## Reading it

    # bad periods
    awk '{split($6,m,"="); if (m[2]=="FAIL" || m[2]+0 < 10) print}' \
        /root/grey-ops/transit-probe.log

    # profile by hour of day, LA time
    awk '{split($2,h,"="); split($6,m,"=");
          if (m[2]!="FAIL") {s[h[2]]+=m[2]; n[h[2]]++}}
         END{for(i=0;i<24;i++) if(n[i]) printf "%02d  %6.1f Mbps  (n=%d)\n", i, s[i]/n[i], n[i]}' \
        /root/grey-ops/transit-probe.log

`mbps=FAIL` is distinct from a low number: the transfer never completed at all,
rather than completing slowly.

Decide after a week or two, not after one bad evening.

## Cost and removal

32 MB per sample, one sample per 30 min ≈ **1.5 GB/day** of home download —
negligible against a link measured at 94-176 Mbps, and in the opposite
direction from the restore, which consumes home upload.

Remove with `crontab -e`; the pre-probe crontab is backed up at
`/root/grey-ops/crontab.bak-20260731`. The invalid cachefly-era samples were set
aside as `transit-probe.log.cachefly-invalid` rather than mixed into the log,
since the two formats are not comparable.
