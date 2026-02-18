# Safety Review: intercore Implementation Plan

**Bead:** iv-ieh7
**Plan:** `/root/projects/Interverse/docs/plans/2026-02-17-intercore-state-database.md`
**PRD:** `/root/projects/Interverse/docs/prds/2026-02-17-intercore-state-database.md`
**Reviewer:** Flux-drive Safety Reviewer
**Date:** 2026-02-17

---

## Executive Summary

**Risk Level:** MEDIUM-HIGH
**Recommendation:** DO NOT PROCEED until critical issues are addressed

The intercore implementation plan contains **5 critical security vulnerabilities** and **3 high-impact deployment risks** that must be fixed before implementation. The most severe issue is **unrestricted `--db` path traversal** that allows attackers to overwrite arbitrary files on the system. Additionally, the migration strategy has **irreversible data loss scenarios** with no documented recovery path.

### Critical Findings (Fix Before Implementation)

1. **Path Traversal via `--db` Flag** (Security: CRITICAL)
2. **No JSON Payload Sanitization** (Security: HIGH)
3. **Irreversible Migration Failures** (Deployment: CRITICAL)
4. **Race Condition in Schema Migration** (Deployment: HIGH)
5. **Unsafe Temp File Patterns in Examples** (Security: MEDIUM)

---

## Threat Model Assessment

### System Architecture
- **Network Exposure:** Local-only CLI (no network-facing service)
- **Trust Boundary:** Same-user filesystem operations (root or claude-user)
- **Untrusted Inputs:**
  - `--db` flag (user-controlled file path)
  - JSON payloads via stdin (from hooks)
  - Scope IDs (session IDs from Claude Code)
  - Key names (hook-provided strings)
- **Credentials:** None stored in intercore (but `.clavain/` directory contains sensitive hook state)
- **Deployment:** Direct binary install to `~/.local/bin/` (no containerization, no CI/CD)

### Attack Vectors
1. **Malicious Claude Code session:** Compromised hook or skill passes crafted inputs
2. **Temp file races:** Attacker on same system exploits TOCTOU in temp file cleanup
3. **Path traversal:** `--db` flag abused to overwrite config files, SSH keys, or other binaries
4. **JSON injection:** Malicious payloads exploit downstream consumers (interline, hooks)

---

## Security Findings

### CRITICAL: Path Traversal via `--db` Flag

**Location:** Plan Task 1.3 (CLI framework), lines 87-90

**Vulnerable Code:**
```go
// DB path resolution: check `--db=<path>` flag,
// else look for `.clavain/intercore.db` by walking up from $PWD
```

**Exploit Scenario:**
```bash
# Attacker overwrites SSH authorized_keys
ic --db=/root/.ssh/authorized_keys state set dummy scope1 << EOF
ssh-rsa AAAAB3... attacker@evil.com
EOF

# Or overwrites the ic binary itself
ic --db=/root/.local/bin/ic state set dummy scope1 < /tmp/backdoor

# Or corrupts the beads database
ic --db=/root/projects/Interverse/.beads/.bv.db state set dummy scope1 < /dev/null
```

**Impact:**
- Arbitrary file overwrite with SQLite database format (file header: `SQLite format 3\0`)
- Can brick the system by overwriting critical binaries or config files
- No authentication required — any user who can run `ic` can exploit this
- Especially dangerous because:
  - Claude Code hooks run programmatically (not just interactive CLI)
  - Hooks can construct `ic` commands from untrusted inputs (session IDs, file paths)
  - The `lib-intercore.sh` library doesn't validate paths before passing to `ic`

**Mitigation (REQUIRED):**

1. **Strict path validation:**
   ```go
   func validateDBPath(path string) error {
       // Resolve to absolute path
       absPath, err := filepath.Abs(path)
       if err != nil {
           return fmt.Errorf("invalid path: %w", err)
       }

       // Must be under CWD or a .clavain directory
       cwd, _ := os.Getwd()
       if !strings.HasPrefix(absPath, cwd) && !strings.Contains(absPath, "/.clavain/") {
           return fmt.Errorf("DB path must be under current directory or in .clavain/")
       }

       // Must end with .db extension
       if filepath.Ext(absPath) != ".db" {
           return fmt.Errorf("DB path must have .db extension")
       }

       // Block paths with ".." (prevent escaping upward)
       if strings.Contains(path, "..") {
           return fmt.Errorf("relative paths with .. not allowed")
       }

       return nil
   }
   ```

2. **Environment variable override only (no CLI flag):**
   ```bash
   # Safer: require explicit opt-in via env var for non-standard paths
   export INTERCORE_DB="/tmp/intercore-test-$$.db"
   ic state set ...
   ```

3. **Add audit logging:**
   ```go
   if dbPath != defaultPath {
       log.Printf("WARN: non-default DB path: %s (from: %s)", dbPath, os.Getenv("USER"))
   }
   ```

**Test Cases (Add to Batch 1 acceptance criteria):**
```bash
# Should FAIL with clear error
ic --db=/etc/passwd state set dummy scope1
ic --db=../../../etc/shadow state set dummy scope1
ic --db=/root/.ssh/authorized_keys state set dummy scope1

# Should SUCCEED
ic --db=.clavain/intercore.db state set dummy scope1
ic --db=/root/projects/Interverse/.clavain/intercore.db state set dummy scope1
```

---

### HIGH: No JSON Payload Sanitization

**Location:** Plan Task 3.1 (State CRUD), lines 242-243

**Current Validation:**
```go
// Validate JSON payload (json.Valid()) — exit 2 on invalid
// Check payload size < 1MB — exit 2 on overflow
```

**Missing Validations:**

1. **Depth/nesting limits:** Attacker can send deeply nested JSON to cause stack overflow:
   ```bash
   # Generate 10,000-level nested object
   echo '{"a":' $(seq 1 10000 | xargs -I{} echo '{"b":') null $(seq 1 10000 | xargs -I{} echo '}') '}}' | ic state set deep scope1
   ```

2. **Key/value length limits:** 1MB total, but no per-field limits:
   ```bash
   # Single 900KB string (under 1MB total, but breaks downstream consumers)
   echo "{\"x\":\"$(head -c 900000 /dev/zero | tr '\0' 'a')\"}" | ic state set huge scope1
   ```

3. **Array length limits:** Can create 100,000-element arrays:
   ```bash
   echo "{\"items\":[$(seq 1 100000 | xargs -I{} echo '1,')]}" | ic state set bigarray scope1
   ```

4. **Control character filtering:** JSON can contain `\u0000` or other problematic chars that break shell parsing.

**Impact:**
- **DoS against hooks:** A malicious session can write a 1MB payload that crashes hooks trying to parse it with `jq`
- **Shell injection in interline:** If interline doesn't properly quote the JSON when rendering, attacker can inject shell commands:
  ```json
  {"phase": "executing$(touch /tmp/pwned)"}
  ```
- **Memory exhaustion:** Hooks that `jq` parse unbounded arrays can OOM

**Mitigation (REQUIRED):**

```go
func validatePayload(payload json.RawMessage) error {
    // Existing checks
    if !json.Valid(payload) {
        return fmt.Errorf("invalid JSON")
    }
    if len(payload) > 1024*1024 {
        return fmt.Errorf("payload exceeds 1MB")
    }

    // NEW: Depth limit (prevent stack overflow)
    var depth int
    if err := checkDepth(payload, &depth, 20); err != nil {
        return fmt.Errorf("JSON nesting too deep (max 20 levels): %w", err)
    }

    // NEW: Key/value length limits
    var obj map[string]interface{}
    if err := json.Unmarshal(payload, &obj); err == nil {
        for k, v := range obj {
            if len(k) > 1000 {
                return fmt.Errorf("key too long (max 1000 chars)")
            }
            if str, ok := v.(string); ok && len(str) > 100000 {
                return fmt.Errorf("string value too long (max 100KB)")
            }
        }
    }

    // NEW: Array length limit
    var arr []interface{}
    if err := json.Unmarshal(payload, &arr); err == nil && len(arr) > 10000 {
        return fmt.Errorf("array too long (max 10,000 elements)")
    }

    // NEW: Control character filter
    for _, b := range payload {
        if b < 0x20 && b != '\t' && b != '\n' && b != '\r' {
            return fmt.Errorf("payload contains control characters")
        }
    }

    return nil
}

func checkDepth(data json.RawMessage, depth *int, max int) error {
    *depth++
    if *depth > max {
        return fmt.Errorf("depth limit exceeded")
    }

    var obj map[string]interface{}
    if err := json.Unmarshal(data, &obj); err == nil {
        for _, v := range obj {
            if child, err := json.Marshal(v); err == nil {
                if err := checkDepth(child, depth, max); err != nil {
                    return err
                }
            }
        }
    }
    *depth--
    return nil
}
```

**Test Cases (Add to Batch 3 acceptance criteria):**
```bash
# Should FAIL with clear error
echo '{"a":{"b":{"c":{...}}}}' | ic state set nested scope1  # 21 levels deep
echo '{"x":"'$(head -c 200000 /dev/zero | tr '\0' 'a')'"}' | ic state set bigstring scope1
echo '{"items":['$(seq 1 20000 | xargs -I{} echo '1,')']}"' | ic state set bigarray scope1
echo $'{"x":"\\u0000"}' | ic state set control scope1

# Should SUCCEED
echo '{"phase":"executing","depth":{"level":{"nested":{"ok":true}}}}' | ic state set valid scope1
```

---

### HIGH: Unsafe `intercore_available()` Health Check Distinction

**Location:** Plan Task 4.1 (lib-intercore.sh), lines 322-332

**Current Logic:**
```bash
intercore_available() {
    if [[ -n "$_INTERCORE_BIN" ]]; then return 0; fi
    _INTERCORE_BIN=$(command -v ic 2>/dev/null || command -v intercore 2>/dev/null)
    if [[ -z "$_INTERCORE_BIN" ]]; then return 1; fi
    # Check health — distinguish "unavailable" from "broken"
    if ! "$_INTERCORE_BIN" health >/dev/null 2>&1; then
        echo "ic: DB health check failed — run 'ic init' or 'ic health'" >&2
        return 1  # fail-loud: DB exists but broken
    fi
    return 0
}
```

**Problem: F5 PRD specifies different fail-safe semantics:**

From PRD lines 112-115:
```
- **Fail-safe with distinction:**
  - "DB unavailable" (no binary, no DB file): fail-safe, return 0, never block workflow
  - "DB available but broken" (schema mismatch, corruption): fail-loud, return 1, log error to stderr
```

**But the implementation contradicts this:**
- `if [[ -z "$_INTERCORE_BIN" ]]; then return 1` — returns 1 (fail-loud) when binary not found
- PRD says this should be "fail-safe, return 0, never block workflow"

**Impact:**
- Hooks will BLOCK if `ic` binary is not installed (violates fail-safe principle)
- During rollout, hooks on machines without `ic` will fail instead of gracefully degrading
- Contradicts the PRD's explicit requirement

**Mitigation (REQUIRED):**

```bash
intercore_available() {
    # Check if binary exists
    if [[ -n "$_INTERCORE_BIN" ]]; then
        # Cached from previous call
        return 0
    fi

    _INTERCORE_BIN=$(command -v ic 2>/dev/null || command -v intercore 2>/dev/null)
    if [[ -z "$_INTERCORE_BIN" ]]; then
        # Binary not found → fail-safe (return 0, allow hook to continue)
        return 0
    fi

    # Binary exists → check health
    if ! "$_INTERCORE_BIN" health >/dev/null 2>&1; then
        # DB broken → fail-loud (return 1, block workflow)
        echo "ic: DB health check failed — run 'ic init' or 'ic health'" >&2
        return 1
    fi

    return 0
}

intercore_state_set() {
    local key="$1" scope_id="$2" json="$3"
    if [[ -z "$_INTERCORE_BIN" ]]; then
        # Binary not found → fail-safe, skip write
        return 0
    fi
    if ! intercore_available; then
        # Health check failed → fail-loud
        return 1
    fi
    echo "$json" | "$_INTERCORE_BIN" state set "$key" "$scope_id" 2>/dev/null
    return 0  # fail-safe on write errors
}
```

**Test Cases (Add to Batch 4 acceptance criteria):**
```bash
# Scenario 1: Binary not on PATH (should succeed)
export PATH=/usr/bin:/bin  # Remove ~/.local/bin
source lib-intercore.sh
intercore_available  # Should return 0
intercore_state_set dispatch sess1 '{"phase":"x"}'  # Should succeed (no-op)

# Scenario 2: Binary exists but DB corrupt (should fail)
ic init
sqlite3 .clavain/intercore.db "DROP TABLE state;"  # Corrupt DB
intercore_available  # Should return 1 with error message

# Scenario 3: Binary exists and DB healthy (should succeed)
ic init
intercore_available  # Should return 0
```

---

### MEDIUM: Unsafe Temp File Pattern in Example

**Location:** Plan Task 5.3 (Example hook migration), lines 488-500

**Vulnerable Pattern:**
```bash
# Legacy fallback
STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
if [[ -f "$STOP_SENTINEL" ]]; then exit 0; fi
touch "$STOP_SENTINEL"
```

**Known Vulnerability (documented in existing codebase):**

From `hub/clavain/docs/research/safety-review-of-f3-f4.md`:
```
Attack scenario: Symlink /tmp/clavain-discovery-brief-_root_projects_Clavain.cache to /etc/passwd

Mitigation: Use O_EXCL in file creation (mkdir, not touch)
```

**Why `touch` is unsafe:**
1. **TOCTOU race:** Check (`[[ -f ]]`) and create (`touch`) are separate syscalls
2. **Symlink attack:** Attacker creates symlink before `touch` runs:
   ```bash
   ln -s /etc/passwd /tmp/clavain-stop-sess1
   # Hook runs: touch /tmp/clavain-stop-sess1 → overwrites /etc/passwd
   ```

**Impact:**
- Example code in MIGRATION.md will be copy-pasted by users
- Propagates insecure pattern to all hooks during migration
- Can overwrite arbitrary files with empty content (or append junk to append-only files)

**Mitigation (REQUIRED):**

Change Task 5.3 example to use safe pattern:

```bash
# SAFE: Use mkdir with atomic O_EXCL
if ! mkdir "/tmp/clavain-stop-${SESSION_ID}" 2>/dev/null; then
    # Directory already exists → sentinel fired
    exit 0
fi
# Sentinel created atomically
```

Or better, use `set -C` (noclobber):
```bash
(
    set -C  # Fail if file exists (atomic O_EXCL behavior)
    > "/tmp/clavain-stop-${SESSION_ID}"
) 2>/dev/null || exit 0  # Already exists → exit
```

**Add to MIGRATION.md:**
```markdown
## Security Notes

### DO NOT use `touch` for sentinels

**WRONG (vulnerable to symlink attacks):**
```bash
if [[ -f "$SENTINEL" ]]; then exit 0; fi
touch "$SENTINEL"
```

**CORRECT (atomic O_EXCL):**
```bash
if ! mkdir "$SENTINEL" 2>/dev/null; then exit 0; fi
```

See: `docs/research/safety-review-of-f3-f4.md` for details.
```

---

## Deployment & Migration Findings

### CRITICAL: Irreversible Migration Failures

**Location:** Plan Batch 1 (Schema Migration), Task 1.2, lines 70-83

**Vulnerable Design:**
```go
// Migrate() error — applies schema.sql in BEGIN IMMEDIATE transaction,
// sets PRAGMA user_version
```

**Missing Failure Modes:**

1. **Partial migration (transaction rollback):**
   - If `CREATE INDEX` fails (e.g., disk full, corrupt DB), transaction rolls back
   - User is left with no DB and no clear recovery path
   - No documentation on how to recover from failed migration

2. **Schema version mismatch (forward compatibility):**
   - User runs `ic` v2 (schema version 2), creates DB
   - Rolls back to `ic` v1 (schema version 1)
   - Plan line 92: "if user_version > max supported, exit 2 with upgrade message"
   - But this leaves user STUCK — can't run commands, can't downgrade schema
   - No `ic migrate --downgrade` or `ic migrate --force-version=1` escape hatch

3. **Concurrent migration (WAL mode doesn't help):**
   - Plan line 561: "Migration wrapped in BEGIN IMMEDIATE — only one process can migrate at a time"
   - But if migration process is killed (kill -9, OOM, power loss), lock is released
   - Next `ic` invocation sees `user_version=0` (migration incomplete) and tries again
   - If schema changes are NOT idempotent, second migration corrupts DB

**Impact:**
- **Data loss:** If migration fails after user has written data, rollback deletes all state
- **Service outage:** If schema version mismatch occurs, `ic` is unusable until binary downgraded/upgraded
- **Corruption:** Concurrent migrations can create inconsistent schema

**Mitigation (REQUIRED):**

1. **Add pre-migration backup:**
   ```go
   func Migrate() error {
       // Before migration, copy DB to .intercore.db.backup
       if exists(dbPath) {
           backup := dbPath + ".backup-" + time.Now().Format("20060102-150405")
           copyFile(dbPath, backup)
           log.Printf("Backup created: %s", backup)
       }

       tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
       if err != nil {
           return fmt.Errorf("begin migration: %w", err)
       }
       defer tx.Rollback()

       // Apply schema
       if _, err := tx.Exec(schemaSQL); err != nil {
           return fmt.Errorf("apply schema (backup: %s): %w", backup, err)
       }

       // Set version
       if _, err := tx.Exec("PRAGMA user_version = ?", targetVersion); err != nil {
           return fmt.Errorf("set schema version: %w", err)
       }

       return tx.Commit()
   }
   ```

2. **Add schema downgrade command:**
   ```bash
   ic migrate --downgrade --to=1
   # Drops indexes, drops new columns, resets user_version
   # Only works if no data dependencies on new schema
   ```

3. **Idempotent migrations (already in schema.sql, but document WHY):**
   ```sql
   -- CORRECT: idempotent (safe to run multiple times)
   CREATE TABLE IF NOT EXISTS state (...);
   CREATE INDEX IF NOT EXISTS idx_state_scope ...;

   -- WRONG: not idempotent (fails on second run)
   CREATE TABLE state (...);
   ALTER TABLE state ADD COLUMN new_col;
   ```

4. **Add recovery documentation:**
   ```markdown
   ## Migration Failure Recovery

   ### If migration fails with "disk full"
   1. Free disk space: `df -h .clavain/`
   2. Restore from backup: `cp .clavain/intercore.db.backup-* .clavain/intercore.db`
   3. Retry: `ic health`

   ### If stuck with "Upgrade intercore to v2"
   Option 1: Upgrade binary
   Option 2: Downgrade schema: `ic migrate --downgrade --to=1`
   Option 3: Delete and reinit (LOSES ALL DATA): `rm .clavain/intercore.db && ic init`
   ```

**Test Cases (Add to Batch 1 acceptance criteria):**
```bash
# Scenario 1: Disk full during migration
dd if=/dev/zero of=/tmp/fill bs=1M count=1000  # Fill disk
ic init  # Should fail with clear error + backup path

# Scenario 2: Concurrent migration (kill -9 during migration)
ic init &  # Start migration in background
PID=$!
sleep 0.1
kill -9 $PID  # Kill mid-migration
ic init  # Should detect incomplete migration and retry safely

# Scenario 3: Schema version mismatch
ic init  # v1 schema
# Simulate v2 schema by manually bumping version
sqlite3 .clavain/intercore.db "PRAGMA user_version = 2;"
ic state get dispatch sess1  # Should fail with "Upgrade intercore to v2"
ic migrate --downgrade --to=1  # Should succeed
```

---

### HIGH: Race Condition in Schema Migration

**Location:** Plan Task 1.2 (Schema DDL), lines 70-76

**Vulnerable Sequence:**
```go
func Open(path string, timeout time.Duration) (*DB, error)
    // Opens with DSN params (?_journal_mode=WAL&_busy_timeout=<ms>)
    // Uses SetMaxOpenConns(1) — CLI is single-command, single-writer
    // Migrate() error — applies schema.sql in BEGIN IMMEDIATE transaction
```

**Race Condition:**

1. Two `ic` processes start simultaneously (e.g., two hooks fire at the same time)
2. Both call `Open()` → both get a DB connection
3. Both call `Migrate()` → first one acquires `BEGIN IMMEDIATE` lock
4. Second one waits up to `busy_timeout` (100ms default)
5. If first migration takes >100ms, second one gets `SQLITE_BUSY` and fails

**Compounding Factor: WAL Mode Persistence**

Plan line 74: "Uses `SetMaxOpenConns(1)` — CLI is single-command, single-writer"

But WAL mode is **persistent** (line 40 in PRD):
```sql
PRAGMA journal_mode = WAL;  -- Sticky, survives DB close
```

**Problem:**
- First `ic init` enables WAL mode
- Subsequent `ic` commands assume WAL is already enabled
- But if someone manually deletes `-wal` and `-shm` files, WAL mode is lost
- Next `ic` command silently falls back to DELETE journal mode
- Concurrent writes corrupt DB (DELETE mode is not multi-writer safe)

**Impact:**
- DB corruption if `-wal` files deleted while `ic` commands are running
- No detection or recovery path

**Mitigation (REQUIRED):**

1. **Verify WAL mode on every Open():**
   ```go
   func Open(path string, timeout time.Duration) (*DB, error) {
       db, err := sql.Open("sqlite", dsn)
       if err != nil {
           return nil, err
       }

       // Force WAL mode (idempotent)
       if _, err := db.Exec("PRAGMA journal_mode = WAL;"); err != nil {
           return nil, fmt.Errorf("enable WAL mode: %w", err)
       }

       // Verify WAL is actually active
       var mode string
       if err := db.QueryRow("PRAGMA journal_mode;").Scan(&mode); err != nil {
           return nil, err
       }
       if mode != "wal" {
           return nil, fmt.Errorf("WAL mode failed to enable (got: %s)", mode)
       }

       return &DB{db: db}, nil
   }
   ```

2. **Increase busy_timeout for migration operations:**
   ```go
   func Migrate() error {
       // Migration can take longer than 100ms (index creation on large DB)
       ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
       defer cancel()

       tx, err := db.BeginTx(ctx, &sql.TxOptions{Isolation: sql.LevelSerializable})
       // ...
   }
   ```

3. **Add migration lock file (filesystem-level):**
   ```go
   func Migrate() error {
       lockPath := dbPath + ".migrate.lock"
       lockFile, err := os.OpenFile(lockPath, os.O_CREATE|os.O_EXCL, 0600)
       if err != nil {
           if os.IsExist(err) {
               return fmt.Errorf("migration already in progress (lock: %s)", lockPath)
           }
           return err
       }
       defer os.Remove(lockPath)
       defer lockFile.Close()

       // Proceed with migration...
   }
   ```

**Test Cases (Add to Batch 1 acceptance criteria):**
```bash
# Scenario 1: Concurrent migrations
for i in {1..10}; do ic init & done
wait
ic health  # Should succeed, DB should be consistent

# Scenario 2: WAL files deleted
ic init
rm .clavain/intercore.db-wal .clavain/intercore.db-shm
ic state set dispatch sess1 < payload.json  # Should re-enable WAL
sqlite3 .clavain/intercore.db "PRAGMA journal_mode;"  # Should output "wal"

# Scenario 3: Migration timeout
# (Simulate slow migration by creating DB with 1M rows, then migrate)
```

---

### MEDIUM: Missing `.clavain/` Directory Permission Handling

**Location:** Plan Task 1.2, line 560 (Risk Mitigations table)

**Current Mitigation:**
```
`.clavain/` dir doesn't exist | `ic init` creates it via `os.MkdirAll`. Also check in `Open()`.
```

**Missing Considerations:**

1. **Permission conflicts with beads:**
   - `.clavain/` is created by beads (`bd init`) with mode 0700
   - `ic init` tries to create with `os.MkdirAll` (mode 0755 default?)
   - If permissions differ, one tool can't access the other's files
   - Especially critical for claude-user ACLs (see CLAUDE.md ACL setup)

2. **Ownership conflicts (root vs claude-user):**
   - Root's Claude Code runs `ic init` → creates `.clavain/` owned by root:root
   - claude-user's Claude Code (via `cc` wrapper) can't access → permission denied
   - Even with ACLs, initial `mkdir` doesn't inherit default ACLs

3. **Atomic directory creation (TOCTOU):**
   - `os.MkdirAll` is not atomic if parent dirs don't exist
   - Attacker can race to create `.clavain/` as symlink to `/etc/`
   - Subsequent `ic init` writes `intercore.db` to `/etc/intercore.db`

**Impact:**
- Permission denied errors when switching between root and claude-user sessions
- Symlink attack can write DB to unintended location

**Mitigation (REQUIRED):**

1. **Strict directory creation:**
   ```go
   func ensureClavainDir() error {
       dir := ".clavain"

       // Check if exists and is a directory (not symlink)
       info, err := os.Lstat(dir)  // Lstat doesn't follow symlinks
       if err == nil {
           if !info.IsDir() {
               return fmt.Errorf("%s exists but is not a directory", dir)
           }
           if info.Mode()&os.ModeSymlink != 0 {
               return fmt.Errorf("%s is a symlink (security risk)", dir)
           }
           return nil  // Already exists and is a real directory
       }

       if !os.IsNotExist(err) {
           return err
       }

       // Create with restrictive permissions (user-only)
       if err := os.Mkdir(dir, 0700); err != nil {
           return fmt.Errorf("create .clavain: %w", err)
       }

       return nil
   }
   ```

2. **Check ownership consistency:**
   ```go
   func checkClavainOwnership() error {
       info, _ := os.Stat(".clavain")
       stat := info.Sys().(*syscall.Stat_t)

       currentUID := os.Getuid()
       if int(stat.Uid) != currentUID {
           return fmt.Errorf(".clavain owned by UID %d, but running as UID %d (permission conflict)", stat.Uid, currentUID)
       }

       return nil
   }
   ```

3. **Document multi-user ACL setup in AGENTS.md:**
   ```markdown
   ## Multi-User Setup (root + claude-user)

   If running ic as both root and claude-user, set ACLs on .clavain/:

   ```bash
   setfacl -R -m u:claude-user:rwX /root/projects/*/.clavain
   setfacl -R -m d:u:claude-user:rwX /root/projects/*/.clavain
   ```

   This allows both users to read/write intercore.db without permission errors.
   ```

**Test Cases (Add to Batch 1 acceptance criteria):**
```bash
# Scenario 1: .clavain is a symlink (should fail)
ln -s /etc .clavain
ic init  # Should fail with "is a symlink (security risk)"

# Scenario 2: .clavain owned by different user (should fail)
sudo chown nobody:nobody .clavain
ic init  # Should fail with "permission conflict"

# Scenario 3: Normal case (should succeed)
rm -rf .clavain
ic init  # Should create .clavain with mode 0700
ls -ld .clavain  # Should be drwx------
```

---

### MEDIUM: Read-Fallback Migration Can Cause Incorrect Behavior

**Location:** Plan Batch 5 (Read-Fallback Migration), Task 5.3, lines 479-500

**Migration Strategy:**
```bash
if intercore_available; then
    intercore_sentinel_check stop "$SESSION_ID" 0 || exit 0
else
    # Legacy fallback
    STOP_SENTINEL="/tmp/clavain-stop-${SESSION_ID}"
    if [[ -f "$STOP_SENTINEL" ]]; then exit 0; fi
    touch "$STOP_SENTINEL"
fi
```

**Problem: Stale Legacy Files Cause State Divergence**

1. **Scenario:** User upgrades hook to use intercore, but legacy files still exist
2. **Execution:**
   - Hook checks `ic sentinel check stop sess1 --interval=0` → returns "allowed" (first time)
   - Hook creates sentinel in DB
   - But legacy file `/tmp/clavain-stop-sess1` also exists from previous session
3. **Bug:** If `ic` becomes unavailable (binary removed, DB corrupted), fallback logic triggers:
   - `intercore_available` returns false → fallback to legacy
   - Legacy check sees stale file from 3 days ago → blocks execution
   - But intercore DB has no sentinel (was cleared by auto-prune after 7 days)
4. **Result:** Hook behaves differently depending on whether intercore is available, even though state should be consistent

**Impact:**
- Non-deterministic behavior during migration period
- Hard-to-debug issues where "hook works with ic but fails without it"
- Violates expectation that fallback is semantically equivalent

**Mitigation (REQUIRED):**

1. **Add cleanup step to migration guide:**
   ```markdown
   ## Phase 1: Read-Fallback Deployment

   Before enabling read-fallback in hooks:

   1. Clear all legacy temp files:
      ```bash
      rm -f /tmp/clavain-stop-*
      rm -f /tmp/clavain-compound-last-*
      rm -f /tmp/clavain-drift-last-*
      rm -f /tmp/clavain-handoff-*
      rm -f /tmp/clavain-dispatch-*.json
      rm -f /tmp/clavain-bead-*.json
      ```

   2. Restart all active sessions (to clear in-memory state)

   3. Deploy hooks with read-fallback enabled
   ```

2. **Add staleness detection to `ic compat status`:**
   ```bash
   ic compat status
   # Output:
   # key              legacy_exists  legacy_age  db_exists  recommendation
   # stop             yes            72h         no         STALE: rm /tmp/clavain-stop-*
   # dispatch         yes            5m          yes        OK (migrated)
   # compound_throttle no            n/a         yes        OK (fully migrated)
   ```

3. **Add `ic compat clean` command:**
   ```bash
   ic compat clean --dry-run  # Show what would be deleted
   ic compat clean --older-than=24h  # Delete legacy files older than 24h
   ```

4. **Change fallback logic to prefer DB state:**
   ```bash
   # WRONG: checks legacy first, DB second
   if [[ -f "$STOP_SENTINEL" ]]; then exit 0; fi
   if intercore_available; then
       intercore_sentinel_check stop "$SESSION_ID" 0 || exit 0
   fi

   # CORRECT: checks DB first, legacy only if DB unavailable
   if intercore_available; then
       intercore_sentinel_check stop "$SESSION_ID" 0 || exit 0
   else
       # Legacy fallback ONLY if ic unavailable
       if [[ -f "$STOP_SENTINEL" ]]; then exit 0; fi
       touch "$STOP_SENTINEL"
   fi
   ```

**Test Cases (Add to Batch 5 acceptance criteria):**
```bash
# Scenario 1: Stale legacy file exists
touch /tmp/clavain-stop-sess1  # Simulate old session
ic init
ic sentinel check stop sess1 --interval=0  # Should be "allowed" (DB has no record)

# Scenario 2: Compat status detects staleness
touch /tmp/clavain-stop-sess1
sleep 2
ic sentinel check stop sess1 --interval=0  # Fires sentinel
ic compat status  # Should show "STALE: legacy file exists but DB migrated"

# Scenario 3: Clean removes only stale files
touch /tmp/clavain-stop-old
touch /tmp/clavain-dispatch-recent.json
ic compat clean --older-than=1s --dry-run
# Should only list clavain-stop-old, not dispatch-recent
```

---

### LOW: No Disk Space Pre-Check for Writes

**Location:** Plan Task 1.2 (Health check), line 74

**Current Health Check:**
```go
// Health() error — checks DB readable, schema version current, disk space >10MB
```

**Gap:** Health check runs on-demand, but writes don't check disk space before attempting

**Scenario:**
1. Hook calls `ic state set` with 900KB payload
2. Disk has only 5MB free
3. SQLite tries to write to WAL
4. Runs out of space mid-transaction → DB left in inconsistent state
5. Error message: "SQLITE_FULL: database or disk is full"
6. User has no guidance on recovery

**Impact:**
- LOW severity because:
  - Disk full is rare on modern systems
  - SQLite WAL mode is designed to handle this gracefully (transaction rollback)
  - But error message is not actionable

**Mitigation (OPTIONAL, nice-to-have):**

1. **Pre-write disk space check:**
   ```go
   func (s *Store) Set(ctx context.Context, key, scopeID string, payload json.RawMessage, ttl time.Duration) error {
       // Check disk space before write
       if free, err := getDiskFree(".clavain"); err == nil && free < 10*1024*1024 {
           return fmt.Errorf("insufficient disk space (free: %d MB, min: 10 MB)", free/(1024*1024))
       }

       // Proceed with write...
   }
   ```

2. **Better error messages:**
   ```go
   if sqliteErr.Code == sqlite3.ErrFull {
       return fmt.Errorf("disk full: free space on .clavain/ partition, then run 'ic state prune'")
   }
   ```

---

## Input Validation & Sanitization Summary

### Trust Boundaries

| Input Source | Trust Level | Validation Required |
|--------------|-------------|---------------------|
| `--db` flag | UNTRUSTED | Path validation (prefix, extension, no ..) |
| JSON payloads (stdin) | UNTRUSTED | Size, depth, key/value length, control chars |
| Scope IDs | SEMI-TRUSTED | Length limit, charset validation (no path separators) |
| Key names | SEMI-TRUSTED | Length limit, charset validation (alphanumeric + _ - only) |
| `--interval` flag | UNTRUSTED | Range validation (0-86400 seconds) |
| `--ttl` flag | UNTRUSTED | Range validation (1s-365d) |

**SEMI-TRUSTED rationale:** Scope IDs and key names come from hooks, which are controlled by plugin authors (not end users). But hooks can have bugs or be compromised, so basic validation is still required.

### Recommended Validation Functions

```go
// Validate scope_id (session IDs, bead IDs)
func validateScopeID(s string) error {
    if len(s) > 256 {
        return fmt.Errorf("scope_id too long (max 256 chars)")
    }
    if !regexp.MustCompile(`^[a-zA-Z0-9_-]+$`).MatchString(s) {
        return fmt.Errorf("scope_id contains invalid characters (allowed: a-z A-Z 0-9 _ -)")
    }
    return nil
}

// Validate key name
func validateKey(s string) error {
    if len(s) > 100 {
        return fmt.Errorf("key too long (max 100 chars)")
    }
    if !regexp.MustCompile(`^[a-z][a-z0-9_]*$`).MatchString(s) {
        return fmt.Errorf("key must start with lowercase letter, contain only a-z 0-9 _")
    }
    return nil
}

// Validate interval (seconds)
func validateInterval(n int) error {
    if n < 0 || n > 86400 {
        return fmt.Errorf("interval out of range (0-86400 seconds)")
    }
    return nil
}
```

### SQL Injection Risk: LOW

**Assessment:** Plan uses parameterized queries throughout (`?` placeholders), which are safe from SQL injection.

**Example (Task 2.1, lines 141-165):**
```go
err = tx.QueryRowContext(ctx, `
    WITH claim AS (
        UPDATE sentinels
        SET last_fired = unixepoch()
        WHERE name = ? AND scope_id = ?  -- Parameterized, safe
    ...
    name, scopeID, intervalSec, intervalSec, intervalSec,
).Scan(&allowed)
```

**No findings:** All database operations use parameterized queries correctly.

---

## Rollback & Recovery Analysis

### Rollback Scenarios

| Scenario | Rollback Feasible? | Data Loss Risk | Recovery Path |
|----------|-------------------|----------------|---------------|
| Code rollback (v2 → v1) | NO | HIGH | Need schema downgrade or manual DB deletion |
| DB corruption | PARTIAL | MEDIUM | Restore from `.backup` file if migration failed |
| Sentinel fired incorrectly | YES | NONE | `ic sentinel reset <name> <scope_id>` |
| State write failed | YES | NONE | Retry write (idempotent) |
| Migration failed (disk full) | YES | LOW | Free space, restore backup, retry |
| Schema version mismatch | NO | NONE | Binary upgrade or schema downgrade required |

### Missing Rollback Documentation

**Required additions to AGENTS.md:**

```markdown
## Rollback Procedures

### Code Rollback (ic binary)

If you need to roll back to an older ic version:

1. **Check schema compatibility:**
   ```bash
   sqlite3 .clavain/intercore.db "PRAGMA user_version;"
   # If version > old binary's max version, downgrade required
   ```

2. **Option A: Downgrade schema (preserves data):**
   ```bash
   ic migrate --downgrade --to=1
   git checkout main~1 -- ~/.local/bin/ic
   ic health
   ```

3. **Option B: Delete and reinit (LOSES DATA):**
   ```bash
   rm .clavain/intercore.db*
   git checkout main~1 -- ~/.local/bin/ic
   ic init
   # All sentinels and state lost, hooks will recreate as needed
   ```

### DB Corruption Recovery

If ic health fails with "DB corrupt":

1. **Check for backup:**
   ```bash
   ls -lh .clavain/intercore.db.backup-*
   ```

2. **Restore latest backup:**
   ```bash
   cp .clavain/intercore.db.backup-20260217-120000 .clavain/intercore.db
   ic health
   ```

3. **If no backup, try SQLite recovery:**
   ```bash
   sqlite3 .clavain/intercore.db ".recover" | sqlite3 .clavain/intercore-recovered.db
   mv .clavain/intercore-recovered.db .clavain/intercore.db
   ic health
   ```

4. **Last resort: reinit (data loss):**
   ```bash
   rm .clavain/intercore.db*
   ic init
   ```

### Sentinel Reset (if hook blocked incorrectly)

If a sentinel fired but the action didn't complete:

```bash
# Reset specific sentinel
ic sentinel reset <name> <scope_id>

# Or clear all sentinels (nuclear option)
sqlite3 .clavain/intercore.db "DELETE FROM sentinels;"
```

### State Corruption (invalid JSON)

If ic state get returns corrupt JSON:

```bash
# Manual fix
sqlite3 .clavain/intercore.db "UPDATE state SET payload = '{\"fixed\":true}' WHERE key = 'bad_key' AND scope_id = 'scope1';"

# Or delete the bad entry
sqlite3 .clavain/intercore.db "DELETE FROM state WHERE key = 'bad_key' AND scope_id = 'scope1';"
```
```

---

## Operational Safety Checklist

### Pre-Deploy Checks (REQUIRED)

- [ ] Path validation prevents `--db` flag from writing outside `.clavain/`
- [ ] JSON payload validation enforces depth/size/key limits
- [ ] `intercore_available()` returns 0 (fail-safe) when binary not found
- [ ] Migration creates backup before modifying schema
- [ ] Schema DDL is idempotent (`IF NOT EXISTS` everywhere)
- [ ] `.clavain/` directory creation checks for symlinks
- [ ] WAL mode is verified on every `Open()`, not just `init`
- [ ] Migration lock file prevents concurrent migrations
- [ ] Example migration code uses `mkdir` (not `touch`) for sentinels
- [ ] All legacy temp files cleared before read-fallback rollout

### Post-Deploy Monitoring (RECOMMENDED)

- [ ] Monitor `ic` error logs for `SQLITE_BUSY` (indicates lock contention)
- [ ] Track DB file size growth (should be <10KB/day)
- [ ] Monitor sentinel prune rate (auto-prune runs after every check)
- [ ] Check for stale legacy temp files (`ls -lh /tmp/clavain-* | wc -l`)
- [ ] Verify WAL file cleanup (`.db-wal` should be <1MB typically)
- [ ] Track migration backup accumulation (`.backup-*` files can be deleted after 7 days)

### Incident Response Runbook

**Symptom: "ic: DB health check failed"**
1. Check disk space: `df -h .clavain/`
2. Check DB permissions: `ls -l .clavain/intercore.db`
3. Check schema version: `sqlite3 .clavain/intercore.db "PRAGMA user_version;"`
4. If corrupt: restore from backup (see Rollback Procedures)

**Symptom: "permission denied" on .clavain/intercore.db**
1. Check ownership: `ls -l .clavain/intercore.db`
2. If root owns file but running as claude-user: `setfacl -m u:claude-user:rw .clavain/intercore.db`
3. If directory unreadable: `setfacl -m u:claude-user:rx .clavain/`

**Symptom: Hook blocks after sentinel fired, but action didn't complete**
1. Reset sentinel: `ic sentinel reset <name> <scope_id>`
2. Check DB state: `ic state get <key> <scope_id>` (verify action state)
3. Manually complete action, then re-fire hook

---

## Risk Prioritization Matrix

| Finding | Exploitability | Blast Radius | Priority | Must Fix Before Launch? |
|---------|---------------|--------------|----------|------------------------|
| Path traversal via --db | HIGH (trivial to exploit) | HIGH (arbitrary file overwrite) | P0 | YES |
| No JSON validation (depth/size) | MEDIUM (requires malicious session) | HIGH (DoS hooks, shell injection) | P0 | YES |
| Irreversible migration failures | LOW (requires disk full or kill -9) | CRITICAL (data loss, service outage) | P0 | YES |
| Unsafe intercore_available() logic | HIGH (triggers on every deployment) | MEDIUM (blocks hooks during rollout) | P1 | YES |
| Schema migration race condition | MEDIUM (requires concurrent init) | HIGH (DB corruption) | P1 | YES |
| Unsafe temp file example (touch) | LOW (requires local attacker) | MEDIUM (symlink attack) | P1 | YES |
| Stale legacy files (migration) | MEDIUM (triggers post-rollout) | MEDIUM (non-deterministic behavior) | P2 | RECOMMENDED |
| Missing .clavain/ symlink check | LOW (requires local attacker setup) | MEDIUM (DB written to wrong location) | P2 | RECOMMENDED |
| No disk space pre-check | LOW (rare on modern systems) | LOW (clear error message) | P3 | OPTIONAL |

**Launch Blockers (Must fix):** 6 findings (P0-P1)
**Recommended Before Launch:** 2 findings (P2)
**Nice-to-Have:** 1 finding (P3)

---

## Recommendations

### Immediate Actions (Before Implementation)

1. **Fix path traversal (P0):**
   - Add `validateDBPath()` to Task 1.3
   - Enforce `.db` extension, no `..`, must be under CWD or in `.clavain/`
   - Add test cases to Batch 1 acceptance criteria

2. **Fix JSON validation (P0):**
   - Add `validatePayload()` with depth/size/key limits to Task 3.1
   - Add test cases to Batch 3 acceptance criteria

3. **Fix migration backup (P0):**
   - Add pre-migration backup creation to Task 1.2
   - Document recovery procedures in AGENTS.md

4. **Fix intercore_available() logic (P1):**
   - Change to return 0 (fail-safe) when binary not found
   - Add test cases to Batch 4 acceptance criteria

5. **Fix schema migration race (P1):**
   - Add WAL mode verification to `Open()`
   - Add migration lock file to `Migrate()`
   - Increase busy_timeout for migration operations

6. **Fix unsafe temp file example (P1):**
   - Change Task 5.3 example to use `mkdir` (not `touch`)
   - Add security notes to MIGRATION.md

### Design Changes (Before Implementation)

1. **Remove `--db` flag entirely:**
   - Replace with env var: `INTERCORE_DB=/path/to/db ic state set ...`
   - Easier to validate (env var has same scope as process)
   - Harder to exploit (can't inject via command-line parsing bugs)

2. **Add schema downgrade command:**
   - `ic migrate --downgrade --to=1`
   - Prevents "upgrade required" lock-in

3. **Add `ic compat clean` command:**
   - Automates legacy temp file cleanup
   - Reduces migration risk from stale files

### Testing Requirements (Add to Plan)

1. **Adversarial test suite:**
   ```bash
   # Add to test-integration.sh
   test_path_traversal() {
       ic --db=/etc/passwd state set attack scope1 <<< '{}' && fail "path traversal not blocked"
   }

   test_json_depth_limit() {
       echo '{"a":{"b":{"c":{...}}}}' | ic state set deep scope1 && fail "depth limit not enforced"
   }

   test_concurrent_migration() {
       for i in {1..10}; do ic init & done
       wait
       ic health || fail "concurrent migration corrupted DB"
   }
   ```

2. **Fuzzing (post-v1, but document intent):**
   ```bash
   # Fuzz JSON payloads
   go-fuzz -func=FuzzStateSet -workdir=/tmp/fuzz

   # Fuzz scope IDs
   go-fuzz -func=FuzzScopeID -workdir=/tmp/fuzz
   ```

### Documentation Requirements (Add to AGENTS.md)

1. **Security Model section:**
   - Threat model (local-only, same-user trust boundary)
   - Input validation rules
   - Path traversal protections
   - Multi-user ACL setup

2. **Rollback Procedures section:**
   - Code rollback (schema downgrade)
   - DB corruption recovery
   - Sentinel reset
   - Migration failure recovery

3. **Operational Runbook section:**
   - Monitoring checks
   - Common error signatures
   - Incident response steps

---

## Residual Risks (After Mitigations)

Even with all mitigations applied, these risks remain:

### Acceptable Residual Risks

1. **SQLite bugs/vulnerabilities:**
   - Risk: modernc.org/sqlite may have undiscovered bugs
   - Mitigation: Keep dependency updated, monitor CVEs
   - Likelihood: LOW (SQLite is well-audited)

2. **Filesystem race conditions:**
   - Risk: Between permission check and file open, attacker modifies file
   - Mitigation: Use `O_EXCL`, validate after open
   - Likelihood: LOW (requires local attacker with precise timing)

3. **Disk corruption (hardware failure):**
   - Risk: WAL mode protects against crashes, not disk failure
   - Mitigation: Backups during migration, `ic health` checks
   - Likelihood: VERY LOW (modern SSDs have internal ECC)

### Unacceptable Residual Risks (Block Launch If Not Fixed)

1. **Path traversal if validation bypassed:**
   - If `validateDBPath()` has a bug (e.g., forgets to check symlinks in parent dirs)
   - **Requires:** Security review of path validation code by second engineer
   - **Test:** Adversarial test suite covering edge cases

2. **JSON injection if validation incomplete:**
   - If depth limit doesn't catch all recursion patterns
   - **Requires:** Fuzzing with go-fuzz for 1M iterations
   - **Test:** Known-bad payloads from OWASP, NVD

3. **Migration data loss if backup fails silently:**
   - If backup creation succeeds but backup file is corrupted
   - **Requires:** Backup verification step (checksum or test restore)
   - **Test:** Simulate disk-full during backup

---

## Conclusion

The intercore implementation plan is **not ready for implementation** until critical security and deployment issues are addressed. The most severe issues are:

1. **Path traversal (P0):** Trivially exploitable, leads to arbitrary file overwrite
2. **No JSON validation (P0):** Enables DoS and potential shell injection
3. **Irreversible migrations (P0):** Data loss with no recovery path

**Recommended Next Steps:**

1. Fix all P0 and P1 findings (6 items)
2. Add adversarial test suite to Batch 4 acceptance criteria
3. Document security model and rollback procedures in AGENTS.md
4. Schedule security review of path validation and JSON validation code
5. Re-review plan after fixes before proceeding to implementation

**Estimated Rework:** 1-2 days to integrate mitigations into plan, 1 day for security review

**Sign-off Required From:**
- Security reviewer (validation logic correct?)
- Deployment engineer (rollback procedures tested?)
- Plugin author (migration strategy sound?)

---

## Appendix: Attack Scenario Walkthrough

### Scenario 1: Path Traversal → SSH Key Overwrite

**Attacker goal:** Gain SSH access to server

**Steps:**
1. Attacker controls a Clavain hook (either by exploiting a skill or by submitting a malicious plugin to marketplace)
2. Hook generates `ic` command with crafted `--db` path:
   ```bash
   ic --db=/root/.ssh/authorized_keys state set dummy scope1 <<EOF
   ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... attacker@evil.com
   EOF
   ```
3. `ic` writes SQLite database header to `authorized_keys` (corrupts file)
4. SSH daemon can't parse `authorized_keys`, blocks all logins
5. Or worse: if SQLite happens to write attacker's key in a valid location, attacker gains access

**Defense (current plan):** NONE — `--db` is unchecked user input

**Defense (after mitigation):** `validateDBPath()` blocks paths outside `.clavain/`

---

### Scenario 2: JSON Injection → Shell Command Execution in interline

**Attacker goal:** Execute arbitrary code via statusline rendering

**Steps:**
1. Attacker session writes malicious dispatch state:
   ```bash
   ic state set dispatch sess1 <<EOF
   {"phase":"executing","bead":"iv-1234$(touch /tmp/pwned)"}
   EOF
   ```
2. Interline plugin reads state:
   ```bash
   bead=$(ic state get dispatch sess1 | jq -r '.bead')
   # interline doesn't quote properly:
   bd show $bead  # BOOM: shell interprets $(touch /tmp/pwned)
   ```
3. Attacker's command executes in hook context

**Defense (current plan):** Partial — `json.Valid()` checks syntax, but doesn't sanitize content

**Defense (after mitigation):** JSON validation blocks control characters, interline must quote all variables

---

### Scenario 3: Migration Failure → Service Outage

**Attacker goal:** DoS the Clavain hook system

**Steps:**
1. Attacker fills disk to 95% capacity:
   ```bash
   dd if=/dev/zero of=/root/fill bs=1M count=5000
   ```
2. Victim runs `ic init` (or any ic command that triggers migration)
3. Migration starts, tries to create indexes (requires temp space)
4. Disk fills to 100%, migration fails:
   ```
   SQLITE_FULL: database or disk is full
   ```
5. Transaction rolls back, `intercore.db` is deleted (or left corrupt)
6. All subsequent hooks fail with "Run 'ic init'" error
7. Victim runs `ic init`, hits same disk-full error
8. System is bricked until disk space freed

**Defense (current plan):** Partial — `ic health` checks disk space, but migration doesn't pre-check

**Defense (after mitigation):** Pre-migration backup + disk space check + recovery docs

---

**End of Review**
