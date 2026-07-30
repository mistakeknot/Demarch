# Backup restore runbook

> Written 2026-07-29 (**mk-7vej**). Every procedure here has been executed and
> verified, not transcribed from documentation. Where something was only believed,
> it says so.
>
> This file exists because the one constraint that would actually have stopped a
> restore — the Postgres dumps needing PG17 — existed nowhere except inside a
> container image and a comment in a systemd unit. A restore instruction that
> lives only on the machine you are restoring *from* is not an instruction.

## 0. Before anything: do you have the repository password?

**Every restic repository below is encrypted with one password, and if you do not
have it nothing else in this document matters.** The copies live in
`~/.config/restic/` on Clavain — `PASSWORD.txt`, and inline in `env-b2` and
`env-synology`.

As of 2026-07-29 those were the **only three copies anywhere**. 1Password held the
Synology *SMB* credential (item `Synology NAS`) but not the repository password.
If that has since been escrowed, look there first; if it has not, this is the
single highest-priority gap in the whole backup strategy, because both
repositories survive an SSD failure as ciphertext no one can open.

Backing the password up *into* the repositories does not help. It is circular.

## 1. Clavain → Backblaze B2 (off-site, never stopped)

```bash
set -a; . ~/.config/restic/env-b2; set +a     # RESTIC_REPOSITORY=rclone:b2:sma-mac-backup
restic snapshots --latest 1
restic restore <id> --target /tmp/restore --include '/Users/sma/projects/…'
```

Covers `~/projects`, `~/Downloads`, `~/Pictures/Photo Archive`, and — since
2026-07-29 — `~/.config/restic` and `~/scripts`.

**Verified:** `install-macos.sh` restored from snapshot `21b7153a`, sha256
identical to the live file, `bash -n` parses.

## 2. Clavain → Synology (local, over Tailscale)

The share is **not** at `/Volumes/Jarmusch`. `/Volumes` is root-owned, so an
unprivileged agent cannot create a mountpoint there; that is why the old mount
only existed while someone had connected in Finder. It now mounts under `$HOME`:

```bash
mkdir -p ~/mnt/jarmusch
PW="$(security find-internet-password -s jarmusch -a mistakenot -w)"
# percent-encode PW, then:
/sbin/mount_smbfs "//mistakenot:<encoded>@jarmusch/Jarmusch" ~/mnt/jarmusch
```

`backup-synology.sh` does exactly this on every run, so in practice just let the
LaunchAgent mount it. `jarmusch` resolves through Tailscale MagicDNS
(`jarmusch.tail1c1ab6.ts.net`, 100.108.23.82) and **SMB works from anywhere on the
tailnet** — this is not a home-network-only destination.

```bash
set -a; . ~/.config/restic/env-synology; set +a
restic snapshots --latest 1
```

**Verified 2026-07-29:** 361 snapshots (2026-03-26 → 2026-07-08), `restic check`
clean on all 361. A 22.9 MiB Olympus RAW (`P5270011.ORF`) restored from snapshot
`f6a8b7bc` — sha256 identical to live, `cmp` reports no differences, `sips`
decodes it at 5184×3888 and renders a JPEG. A shell script restored from the same
snapshot was byte-identical to the live file.

### If restic says `wrong password or no key found` here

**It probably is not the password.** That message is what restic prints when SMB
I/O stalls while listing `keys/`: the retry "succeeds" with an empty listing and
restic truthfully reports finding no key. Check the mount first — `/sbin/mount |
grep jarmusch` — and look for `fdopendir …/keys: operation timed out` in
`~/.config/restic/synology.log`. This cost this project a wrong diagnosis and a
spurious key-reconciliation task.

### If restic refuses with `repository is already locked`

A lock naming a PID **on this same host** can survive a reboot and then have its
PID reused by an unrelated live process, at which point restic cannot tell it is
stale and will refuse indefinitely. This cost the Synology repository 95 days.

`restic unlock` clears genuinely stale locks. Both backup scripts pass
`--retry-lock 15m`, which handles contention but deliberately does **not**
self-clear orphans — a script that deletes locks it does not understand will
eventually delete a live one.

## 3. zklw → B2: Postgres dumps

```bash
set -a; . ~/projects/ops/pg-backup/jawnverse-pg-backup.env; set +a
restic snapshots --tag jawnverse-pg --latest 1
restic restore <id> --target /tmp/pg --tag jawnverse-pg
```

Covers the cluster app DBs: `oodacademy`, `jawnbase`, `agmodb`.

### ⚠ THE DUMPS REQUIRE PG17 TOOLING TO RESTORE

The dumps are `--format=custom`, written by **PostgreSQL 17** `pg_dump` running
**inside the `jawnverse-postgres` container**. They are *not* corrupt, but:

```
$ pg_restore --list oodacademy-20260729.dump
pg_restore: error: unsupported version (1.16) in file header
```

zklw's **host** `pg_restore` is 16.14 and rejects them outright. A fresh machine
with a distro Postgres will hit the same wall, and the error says nothing about
versions being the cause of the *restore* failing rather than the dump being bad.

Restore through PG17 tooling instead — either the running container:

```bash
docker exec -i jawnverse-postgres pg_restore -U postgres -d <db> < dump
```

or, on a bare machine with no container, any PG17 client:

```bash
docker run --rm -i -v /tmp/pg:/dumps postgres:17 \
  pg_restore -h <host> -U postgres -d <db> /dumps/<file>.dump
```

**Verified:** 18 dumps, 26.8 MiB, snapshot `847d1687`; `pg_restore --list` inside
the container returns 63 TOC entries with `dbname: jawnbase`, format CUSTOM.

## 4. zklw → B2: CanonGraph event log

Same repository, `--tag canongraph`. Restores `log.sqlite`, `topology.yaml`,
`profile.json`.

**Verified:** `PRAGMA integrity_check` → `ok`; the log replays 765 rows in
`event_log` (the table is `event_log`, **not** `events`), yielding 316 entities,
335 relationships, 40 documents. YAML and JSON both parse.

Never run CanonGraph CLI graph commands against the live service — Kùzu holds an
exclusive lock. Restore to a scratch path and inspect there.

## 5. Clavain → B2 rclone mirror

`~/scripts/backup-to-b2.sh` mirrors `~/.claude/projects` and `~/.codex` to
`b2:ethics-gradient-backup/mac` with `rclone sync`. **This is a mirror, not a
backup**: delete a file locally and the next run deletes it remotely.

Its only history is a B2 lifecycle rule, `daysFromHidingToDeleting: 30`, so
superseded and deleted versions are recoverable for 30 days and no longer. That
rule is now asserted by `rig-backup-freshness.py` on every run, because it lives
in a web console where one cost-cleanup edit would silently reduce the window to
zero with nothing local changing.

To recover a deleted or superseded file:

```bash
rclone lsjson --b2-versions b2:ethics-gradient-backup/mac/claude-sessions/…
rclone copy --b2-versions b2:ethics-gradient-backup/mac/<file>-v2026-07-08-… /tmp/
```

**Verified:** one session `.jsonl` restored, bytes identical, valid JSONL.

## Retention at a glance

| destination | depth | notes |
|---|---|---|
| Clavain → B2 | hourly 24, daily 7, weekly 4, monthly 6 | 85 snapshots from 2026-03-26 |
| Clavain → Synology | same | 361 snapshots, 2026-03-26 → 2026-07-08 |
| zklw → B2, both tags | daily 7, weekly 4, **monthly 12** | monthly tier added 2026-07-29; before that, max depth was ~5 weeks |
| rclone mirror | 30 days of versions | lifecycle rule, now asserted by the rig |

## Related

- `ops/rig-self-checks.md` § *Backups: proven restorable* — the diagnosis, the
  four faults, and what each instrument did and did not see
- `dotfiles/macos/.config/rig/backup-repos.conf` — what is covered, what is
  excluded, and why
- `dotfiles/macos/.config/restic/backup-synology.sh` — each fault answered beside
  the line that fixes it
