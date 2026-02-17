---
module: interkasten
date: 2026-02-16
problem_type: security_pattern
component: sync/engine
symptoms:
  - "Path traversal possible when guard condition evaluates to null/false"
  - "Validation only runs inside positive branch, negative branch proceeds unchecked"
  - "4 independent review agents all flagged the same code"
root_cause: guard_fallthrough
resolution_type: pattern
severity: high
tags: [path-traversal, validation, guard-clause, null-safety, security, typescript]
---

# Guard Fallthrough: Validation That Silently Skips on Null

## Problem

A path validation guard in `processPullOperation()` only ran when `findProjectDir()` returned a value. When it returned `null`, the entire validation was skipped and the pull operation proceeded with an unchecked `entity.localPath`.

## Anti-Pattern

```typescript
const projectDir = this.findProjectDir(entity.localPath);
if (projectDir) {
  // Validation only runs here
  const resolved = resolve(projectDir, basename(entity.localPath));
  if (!resolved.startsWith(projectDir + "/")) {
    return; // Abort on traversal
  }
}
// Falls through here when projectDir is null — NO validation
```

The logic reads naturally ("if we have a project dir, validate against it") but the implicit else branch is dangerous: it assumes that a null projectDir is safe, when in fact it means we have *less* information and should be *more* cautious.

## Correct Pattern

```typescript
const projectDir = this.findProjectDir(entity.localPath);
if (!projectDir) {
  // Fail closed: no project context means we can't validate
  appendSyncLog(this.db, {
    entityMapId: entity.id,
    operation: "error",
    detail: { error: "No project directory found — aborting pull" },
  });
  return;
}
// Now projectDir is guaranteed non-null
const resolved = resolve(projectDir, basename(entity.localPath));
if (!resolved.startsWith(projectDir + "/")) {
  return; // Abort on traversal
}
```

## General Rule

**Fail closed on missing context.** When a validation depends on a lookup that can fail (return null/undefined), the null case should abort the operation, not skip the validation. The guard clause should invert: check for the *absence* of the prerequisite first.

This applies broadly:
- Path validation requiring a project root
- Permission checks requiring a user context
- Rate limiting requiring a client identifier
- Input sanitization requiring a schema definition

## Detection Signal

Look for this code shape:
```
const context = lookup();
if (context) {
  validate(input, context);
}
// input used here without validation when context is null
```

The fix is always: flip the condition to `if (!context) { abort; }` then proceed with validation unconditionally.

## Cross-Reference

- All 4 quality-gates agents (architecture, quality, correctness, safety) independently flagged this same code — strong convergence signal for real issues
- See also: `docs/solutions/patterns/set-e-with-fallback-paths-20260216.md` for a similar "silent skip" pattern in shell scripts
