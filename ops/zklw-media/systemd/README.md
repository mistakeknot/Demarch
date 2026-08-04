# systemd overrides on grey

Drop-ins live in `/etc/systemd/system/<unit>.d/override.conf`. Apply with
`systemctl daemon-reload && systemctl restart <timer>`.

## mdcheck: the monthly RAID scrub was landing in prime viewing time

Symptom: Jellyfin stuttered badly on 2026-08-03 at ~21:00 PT. The stream was
**DirectPlay** — no transcode, no network fault — so the cause was local I/O:

    md3   r_await 825 ms   w_await 853 ms   aqu-sz 5.94   %util 76
    load average 8.72

`/proc/mdstat` showed a RAID5 consistency check reading the whole 44 TB array
at 133 MB/s, `mismatch_cnt 0`, `degraded 0` — a healthy routine scrub, simply
running at the worst possible time.

### Why it was running then, which is the actual bug

`mdcheck` is not one job. `mdcheck_start.timer` begins a scrub monthly and
`mdcheck_continue.timer` resumes it **daily** until the array is covered, each
run bounded by `MDADM_CHECK_DURATION` (stock: 6 hours). On a 44 TB array that
is many consecutive days of scrubbing.

Stock schedule, and the trap:

    mdcheck_start      OnCalendar=Sun *-*-1..7 1:00:00   RandomizedDelaySec=24h
    mdcheck_continue   OnCalendar=daily                  RandomizedDelaySec=12h

The host is `Europe/Berlin`, so "daily" means midnight Berlin = **15:00 PT**,
and a 6-hour run covers 15:00-21:00 PT — squarely in the evening. Worse, the
randomised delay smears each trigger across a 12-24 hour spread, so the scrub
can begin at *any* hour and the configured time means nothing. Setting
`OnCalendar` without also zeroing `RandomizedDelaySec` does not fix it.

### The override

11:00 Berlin == 02:00 America/Los_Angeles. Pacific and Berlin both observe DST
and stay 9 hours apart year-round, so this holds without seasonal drift.

    [Timer]
    OnCalendar=
    OnCalendar=*-*-* 11:00:00        # continue; start uses Sun *-*-1..7 11:00:00
    RandomizedDelaySec=0

    [Service]
    Environment="MDADM_CHECK_DURATION=8 hours"

8 hours from 02:00 PT ends at 10:00 PT. The empty `OnCalendar=` is required —
it clears the inherited values rather than appending to them.

### Throttling is the wrong permanent lever

`dev.raid.speed_limit_max` (default 200000 KB/s) throttles the scrub and works
immediately — dropping it to 25000 took `%util` from 76 to 4.6. But the same
sysctl also caps **rebuild** speed after a real disk failure, and on 15 TB
members a throttled rebuild means days of degraded-array exposure. So use it as
a live fire extinguisher only, and leave it at the default. Fix the *schedule*,
not the speed.

To stop a scrub in progress: `echo idle > /sys/block/mdN/md/sync_action`.
`mdcheck --continue` resumes from `/var/lib/mdcheck/MD_UUID_*` on the next
timer fire, so nothing is lost. Do it for **every** array — md0-md3 share the
same four physical spindles, so pausing md3 alone just moves the load to md2.

## Jellyfin: trickplay generation is the same class of problem

`Generate Trickplay Images` (a `DailyTrigger` task) decodes every video to
build scrubbing thumbnails. On 4K HDR it also tone-maps:

    ffmpeg -i /data/movies/Parasite...UHD.2160p.DV.HDR.x265.mkv \
      -vf fps=0.1,...,tonemapx=tonemap=bt2390:... -f image2 .../%08d.jpg

That is the expensive path this box has no GPU for, and it ran for ~20 hours
against the library while the RAID scrub was already saturating the spindles.
Cancel a running task with `DELETE /ScheduledTasks/Running/{id}`; killing the
ffmpeg process alone is useless because Jellyfin immediately spawns the next
file.

`Generate Trickplay Images` and `Extract Chapter Images` were both moved to
05:00 America/New_York with an 8h cap. Note the Jellyfin **container** runs
`TZ=America/New_York` (from `.env`) while the host is `Europe/Berlin`, so task
triggers are in Eastern, not host time — 05:00 ET = 02:00 PT.

    curl -H 'Authorization: MediaBrowser Token="<key>"' \
      -X POST -H 'Content-Type: application/json' \
      -d '[{"Type":"DailyTrigger","TimeOfDayTicks":180000000000,"MaxRuntimeTicks":288000000000}]' \
      http://100.123.250.67:8096/ScheduledTasks/<id>/Triggers

Ticks are 100 ns units: hours x 3600 x 10^7. The `X-Emby-Token` header and
`api_key=` query param both return non-JSON on this build; the
`Authorization: MediaBrowser Token="..."` form is the one that works.

## Result

    before                          after
    load 8.72                       load 0.51
    md3 %util 76.1                  %util 0.20
    md3 w_await 853 ms              w_await 1.46 ms
    md3 aqu-sz 5.94                 aqu-sz 0.00
