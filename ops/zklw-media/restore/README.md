# KG restore driver

`kg_restore.sh` lives on grey at `/root/grey-ops/` and is run by
`kg-restore.service`. It pulls the Karagarga cold backup from jarmusch one
folder at a time, resumable, into the seeding tree. The copy here is version
control for a script that otherwise exists on exactly one machine.

## The bandwidth window

The transfer is jarmusch -> grey, so it consumes the **home upload**, not the
server's. That is the whole reason for a cap: the driver picks an rsync
`--bwlimit` per film from the LA-local hour, uncapped overnight and gentle
during the day.

Widened 2026-07-29 from 01:00-07:00 to **00:00-08:00 America/Los_Angeles**.

Measured from the log before changing it (162 completed transfers with
matched START/DONE pairs):

| mode | films | mean | sustained |
|---|---|---|---|
| uncapped | 54 | 0.61 h/film | 39.1 films/day |
| 1200 KB/s | 108 | 1.10 h/film | 21.7 films/day |

So uncapped is ~1.8x the capped rate — real, but the window only covers a third
of the day, so widening it 6h -> 8h is worth about **+6%**: 27.0 -> 25.5 days
for the 496 films remaining. Observed throughput runs at ~70% of theory once
retries, service restarts and gaps are counted.

**The daytime cap is the dominant lever, not the window**, because it governs
16 of every 24 hours:

| daytime cap | films/day | days left |
|---|---|---|
| 1200 KB/s (current) | 19.4 | 25.5 |
| 2000 KB/s | 26.2 | 18.9 |
| 3000 KB/s | 34.7 | 14.3 |

That is a decision about how much home upload to give up during waking hours,
which is why it is documented here rather than changed.

## A wrinkle worth knowing

`bwlimit()` is evaluated **once per film, at START**, and rsync cannot change
`--bwlimit` mid-transfer. A long film starting at 07:5x therefore runs uncapped
well into the morning, and one starting at 23:5x stays capped all night. The
wider window makes the second case rarer, which is part of the point.

## Editing it safely

The service runs the script as a long-lived bash process, and bash reads its
script lazily by byte offset — editing in place mid-run can make a running
process execute garbage. Write a new file and `mv` it over (rename keeps the
old inode alive for the running process), then `systemctl restart
kg-restore.service`. Progress is tracked in `kg-restore-done.txt` and rsync
runs with `--partial`, so a restart costs only the in-flight file's remainder.
