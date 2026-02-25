# Plan: CI Baseline — Go Repos

**Bead:** iv-be0ik.1
**Date:** 2026-02-24
**Complexity:** 2/5 (simple — repeating a template across repos)

## Scope

Add GitHub Actions CI to all 8 Go repos that currently have zero CI:
- `core/intercore`
- `core/intermute`
- `core/interbench`
- `core/interband`
- `interverse/intermap`
- `interverse/interlock`
- `interverse/intermux`
- `interverse/interserve`

Also add CI to `apps/autarch` (currently only has Gemini code review, no test CI).

## Tasks

### Task 1: Create Go CI workflow template
- [x] Write `.github/workflows/ci.yml` for Go repos with:
  - Trigger on push to main + PRs
  - Go setup (go 1.24)
  - `go build ./...`
  - `go test -race ./...`
  - `go vet ./...`
- [x] Keep it minimal — no caching, no matrix, no bells and whistles

### Task 2: Apply to core/ repos
- [x] `core/intercore` — add ci.yml, verify `go test -race ./...` passes
- [x] `core/intermute` — add ci.yml, verify tests pass
- [x] `core/interbench` — add ci.yml (may not have tests, build-only is fine)
- [x] `core/interband` — add ci.yml, verify tests pass

### Task 3: Apply to interverse/ Go repos
- [x] `interverse/intermap` — add ci.yml
- [x] `interverse/interlock` — add ci.yml
- [x] `interverse/intermux` — add ci.yml
- [x] `interverse/interserve` — add ci.yml

### Task 4: Apply to apps/autarch
- [x] Add ci.yml alongside existing Gemini workflows

### Task 5: Commit and push each repo
- [x] Commit each repo individually (they have independent .git)
- [x] Push all

## Template

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: "1.24"
      - run: go build ./...
      - run: go vet ./...
      - run: go test -race ./...
```

## Notes

- Each repo has its own `.git` — need individual commits
- Some repos have `replace` directives in go.mod pointing to sibling dirs — CI won't have those. Need to handle.
- `apps/autarch` has `replace github.com/mistakeknot/intermute => ../../core/intermute` — CI needs this checked out
