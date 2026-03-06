---
artifact_type: plan
bead: iv-godia
stage: executing
---
# Routing Decisions as Kernel Facts — Implementation Plan

**Goal:** Persist routing decisions as replayable kernel facts so offline eval can build counterfactual rows directly from durable data.

**Architecture:** New v27 migration, new `internal/routing/decision.go` store, new CLI subcommands. Follows landed/session store pattern exactly.

**Bead:** iv-godia

---

### Task 1: v27 migration — `routing_decisions` table

- [x] Create migration file
- [x] Append to schema.sql
- [x] Bump currentSchemaVersion and maxSchemaVersion to 27

### Task 2: Decision store — `internal/routing/decision.go`

- [x] Decision struct
- [x] RecordOpts and ListOpts
- [x] Record method (INSERT)
- [x] Get method (SELECT by id)
- [x] List method (dynamic WHERE)
- [x] Tests: TestRecord, TestRecord_WithAllFields, TestGet_NotFound, TestList_Empty, TestList_ByAgent, TestList_ByModel, TestList_Limit, TestList_ByDispatchID

### Task 3: CLI — `ic route record` and `ic route list`

- [x] Add `record` case to cmdRoute switch
- [x] Add `list` case to cmdRoute switch
- [x] Update usage help text

### Task 4: Update db tests

- [x] Update version assertions (26→27, 13 occurrences)
- [x] Add routing_decisions to table existence check

### Task 5: Run tests and commit

- [x] `go test ./...` passes (807 passed, 2 pre-existing failures in event package)
- [ ] Commit from core/intercore directory
