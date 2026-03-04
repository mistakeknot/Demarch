# fd-mount-security-wiring -- Review Findings

## Summary

The mount security wiring has been correctly fixed: `main.rs` now calls `load_allowlist()` at daemon startup and passes it through `RunConfig` to both `process_group.rs` and `scheduler_wiring.rs`. The core allowlist logic in both Node and Rust implementations is functionally equivalent and well-tested. However, there are several findings around the exclude/tmpfs validation gap (P1), a silent behavioral divergence between Node and Rust when the allowlist is absent (P2), and the module-level cache in Node preventing runtime allowlist updates (P3).

## Findings

### [P1] Exclude values are passed unvalidated to Docker --mount destination

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/container-runner.ts:291-293` and `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/secrets.rs:153-159`
- **Issue**: The `exclude` array from `AdditionalMount` is passed through `validateAdditionalMounts` without any validation of its values. The raw strings are then interpolated directly into `--mount type=tmpfs,destination={containerPath}/{subdir},tmpfs-size=0`. A malicious or misconfigured `exclude` value containing `..` or `,` could perform path traversal out of the intended mount point or inject additional Docker `--mount` options (e.g., `exclude: ["../../etc"]` would produce `destination=/workspace/extra/project/../../etc`).
- **Scenario**: A group's `containerConfig` in Postgres contains `{"additionalMounts": [{"hostPath": "~/projects/foo", "exclude": ["../../etc"]}]}`. The tmpfs overlay targets `/workspace/extra/foo/../../etc` which resolves to `/etc` inside the container, potentially masking system directories or, more critically, allowing arbitrary tmpfs mounts at any container path. Similarly, an exclude value like `x,tmpfs-size=999999999` could inject mount options.
- **Fix**: Validate each `exclude` entry in both `validateAdditionalMounts` (Rust) and `validateAdditionalMounts` (Node) using the same rules as `isValidContainerPath`: reject values containing `..`, `/`, or `,`. Both implementations should add:
  ```
  // In validate_additional_mounts, before pushing to validated:
  for subdir in &mount.exclude {
      if subdir.contains("..") || subdir.contains('/') || subdir.contains(',') || subdir.is_empty() {
          warn!("Exclude value rejected: {}", subdir);
          continue; // or reject the entire mount
      }
  }
  ```

### [P2] Rust silently skips mounts when allowlist is None; Node blocks with a logged reason

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/mounts.rs:169-189` vs `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:249-257`
- **Issue**: When the allowlist is not loaded (file missing, parse error), the two implementations diverge in behavior and observability:
  - **Node**: `validateMount()` (line 249) calls `loadMountAllowlist()` internally on every validation. If it returns null, every mount is individually rejected with a clear reason: `"No mount allowlist configured at {path}"`. Each rejected mount is logged at WARN level with the group name and requested path.
  - **Rust**: `build_volume_mounts()` (line 169) checks `if let Some(allowlist) = allowlist` and if None, emits a single DEBUG-level log: `"Skipping additional mounts -- no allowlist loaded"`. The individual mounts are never enumerated or logged, so an operator cannot tell which mounts were requested but skipped.
- **Scenario**: An operator configures `additionalMounts` for a group in Postgres but the allowlist file is missing (e.g., after a fresh deploy, config directory not provisioned). On the Rust side, the operator sees only a debug-level message that mounts were skipped -- easily missed in production log levels (default: info). They have no indication which specific mounts were dropped, making troubleshooting difficult.
- **Fix**: Elevate the Rust log to `warn!` (matching Node behavior) and enumerate the skipped mount paths:
  ```rust
  } else {
      for m in &config.additional_mounts {
          warn!(
              group = %group.name,
              requested_path = %m.host_path,
              "Additional mount SKIPPED — no allowlist loaded"
          );
      }
  }
  ```

### [P2] Node allowlist cache prevents loading a newly created allowlist without restart

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:22-24,62-65`
- **Issue**: The module-level `cachedAllowlist` and `allowlistLoadError` variables create a one-shot cache. If the allowlist file does not exist when the Node process starts, `allowlistLoadError` is set to a non-null string (line 69), and all subsequent calls to `loadMountAllowlist()` return null immediately (line 62-65) without re-checking the filesystem. This means if an operator creates the allowlist file after the Node service is already running, all additional mounts remain blocked until the service is restarted.
- **Scenario**: During initial deployment, the operator starts the intercom Node service before running `setup/mounts.ts` to create the allowlist. All additional mounts are permanently blocked for the lifetime of the process. The operator adds the allowlist file and expects it to take effect, but mounts remain blocked with no indication that a restart is needed.
- **Fix**: Either (a) remove the negative cache (`allowlistLoadError`) so the file is re-checked on each call, or (b) add a TTL to the error cache (e.g., retry after 60 seconds), or (c) document prominently that the Node service must be restarted after creating the allowlist. Option (a) is simplest:
  ```typescript
  // Remove the allowlistLoadError early-return block (lines 62-65)
  // Only cache successful loads; failures are retried each call
  ```

### [P2] Rust loads allowlist once at daemon startup; allowlist changes require daemon restart

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/main.rs:364-366`
- **Issue**: The allowlist is loaded once in `serve()` and stored in `RunConfig`. This `RunConfig` is cloned into `build_process_messages_fn()` (line 383) and `build_task_callback()` (line 451). Changes to the allowlist file on disk are never picked up without restarting `intercomd`. This is a deliberate design choice (immutable config at startup is common in Rust services), but it is not documented and diverges from the Node side's behavior of calling `loadMountAllowlist()` on every mount validation (albeit with the caching issue noted above).
- **Scenario**: Operator updates `~/.config/intercom/mount-allowlist.json` to add a new allowed root. Node side picks it up on next restart (due to the cache), Rust side also requires restart. But if the Node cache bug above were fixed, they would diverge: Node would see updates immediately, Rust would not.
- **Fix**: Document in `docs/architecture/security.md` that both services must be restarted after allowlist changes. Alternatively, add a file-watcher or periodic reload (lower priority -- current behavior is safe, just operationally inconvenient).

### [P3] Blocked pattern substring matching can over-block legitimate paths

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:161-162` and `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/security.rs:187-188`
- **Issue**: Both implementations use substring matching (`part.includes(pattern)` in Node, `part.contains(pattern.as_str())` in Rust) when checking path components against blocked patterns. The blocked pattern `"credentials"` will match a path component named `my_credentials_backup` or `credentials_v2`. Similarly, `.env` matches `.env.example`, `.envrc`, or any component containing `.env` as a substring. The pattern `.secret` matches `.secretariat` or any directory with `.secret` embedded.
- **Scenario**: A legitimate project directory at `~/projects/credentials_manager/` or `~/projects/my-app/.env.d/configs/` would be blocked by the substring match against `credentials` or `.env`, even though these are not sensitive credential stores. The full-path check on line 168-169 (Node) / 193 (Rust) further broadens this: any occurrence of the pattern anywhere in the path string causes a block.
- **Fix**: This appears to be intentional defense-in-depth (over-block rather than under-block). The full-path substring check is the most aggressive and could be narrowed to exact component matching only if false positives become a user issue. No immediate change needed, but document the behavior in the allowlist template or security docs so users understand why legitimate paths may be blocked.

### [P3] containerPath defaults to basename(hostPath), which can be empty for root paths

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:260` and `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/security.rs:240-245`
- **Issue**: When `containerPath` is not specified, it defaults to `path.basename(mount.hostPath)` in Node and `Path::new(&mount.host_path).file_name()` in Rust. For a `hostPath` of `/` (root), Node's `path.basename("/")` returns an empty string `""`, which would fail the `isValidContainerPath` check (empty string rejected). The Rust side handles this more carefully with `.unwrap_or("mount")` as a fallback (line 244), producing `"mount"` instead. This is a minor divergence but both sides handle the edge case safely -- Node rejects, Rust falls back.
- **Scenario**: A misconfigured mount with `hostPath: "/"` and no `containerPath` would be rejected by Node (empty container path) but would proceed to the allowed-root check in Rust with container path `"mount"`. In practice, `/` would fail the allowed-root check in both cases since no sane allowlist includes `/` as an allowed root.
- **Fix**: No action needed -- both implementations are safe. The Rust fallback to `"mount"` is slightly more permissive but the allowed-root check prevents any real exposure. For consistency, consider having Rust also reject when `file_name()` returns None, but this is cosmetic.

### [P3] Dotfile container paths are not explicitly blocked

- **File**: `/home/mk/projects/Demarch/apps/intercom/src/mount-security.ts:214-231` and `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/security.rs:226-228`
- **Issue**: `isValidContainerPath` validates that the container path is non-empty, relative, and does not contain `..`. It does not reject dotfile names like `.bashrc` or `.profile`. Since additional mounts are placed under `/workspace/extra/{containerPath}`, a dotfile name is not directly dangerous (it becomes `/workspace/extra/.bashrc` which does not shadow any system config). However, if the mount prefix were ever changed or the container's working directory were set to `/workspace/extra/`, dotfiles could become executable config.
- **Scenario**: `containerPath: ".bashrc"` produces mount at `/workspace/extra/.bashrc`. Not currently exploitable since the container does not use `/workspace/extra/` as a home directory, but it represents a latent assumption.
- **Fix**: No immediate action needed. The `/workspace/extra/` prefix provides sufficient isolation. If mount points are ever restructured, this should be revisited.

### [P3] Rust hard-blocked path check does not canonicalize before comparison

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/container/security.rs:201-206`
- **Issue**: `is_hard_blocked()` checks the path against `HARD_BLOCKED_ROOTS` using string comparison on the lossy path representation without canonicalizing first. However, the function is called twice: once on the expanded (uncanonicalized) path (line 262) and once on the canonicalized `real` path (line 289). The first call could miss a symlink pointing into a hard-blocked root, but the second call (after `real_path()` canonicalizes) catches it. The Node implementation mirrors this pattern exactly (lines 272, 288).
- **Scenario**: A symlink `~/link-to-wm -> /wm/secret` would pass the first `is_hard_blocked` check (expanded path is `~/link-to-wm`, not under `/wm`) but would be caught by the second check after `realpathSync` resolves it to `/wm/secret`. The double-check pattern is correct and safe.
- **Fix**: No action needed. The defense-in-depth (pre- and post-canonicalization checks) correctly handles symlink bypass attempts.

### [P3] containerConfig flows correctly from Postgres through to runner

- **File**: `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/process_group.rs:181-184` and `/home/mk/projects/Demarch/apps/intercom/rust/intercomd/src/scheduler_wiring.rs:125-132`
- **Issue**: No issue found. Both `process_group_messages()` and `run_scheduled_task()` deserialize `container_config` from the `RegisteredGroup`'s `serde_json::Value` into `ContainerConfig` using `serde_json::from_value`. If deserialization fails (malformed JSON), `.ok()` produces `None`, and `build_volume_mounts` treats `None` as "no additional mounts" -- a safe default. The `RunConfig.allowlist` field is passed correctly from `main.rs:364-366` through both call chains.
- **Scenario**: N/A -- this path is correct.
- **Fix**: N/A.

## Verification Summary

| Check | Node | Rust | Status |
|-------|------|------|--------|
| Allowlist file path | `~/.config/intercom/mount-allowlist.json` | `~/.config/intercom/mount-allowlist.json` | Consistent |
| Allowlist load timing | On first validation call (cached) | At daemon startup (in RunConfig) | Divergent but safe |
| Missing allowlist behavior | Block all, warn per mount | Skip all, debug log once | **Divergent severity** (P2) |
| Blocked patterns | Substring match, merged with defaults | Substring match, merged with defaults | Consistent |
| containerPath validation | Reject `..`, absolute, empty | Reject `..`, absolute, empty | Consistent |
| Symlink resolution | `fs.realpathSync` | `std::fs::canonicalize` | Consistent |
| Hard-blocked roots | `/wm` pre- and post-canonicalization | `/wm` pre- and post-canonicalization | Consistent |
| Exclude validation | **None** | **None** | **Both missing** (P1) |
| containerConfig deserialization | TypeScript interface | `serde_json::from_value` with `.ok()` | Safe |
| validate_additional_mounts called before docker args | Yes (container-runner.ts:204) | Yes (mounts.rs:170) | Correct |
