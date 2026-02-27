#!/usr/bin/env python3
"""
Map docs/brainstorms and docs/plans markdown files to bead notes.

Behavior:
- Extract primary bead IDs from each doc's "**Bead:** ..." declaration.
- Optionally infer from first iv-* token near top when declaration is missing.
- Create placeholder beads for missing IDs (optional).
- Append idempotent doc-map note lines to each mapped bead.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ID_RE = re.compile(r"iv-[a-z0-9]+(?:\.[0-9]+)*", re.IGNORECASE)
DECL_RE = re.compile(r"^\*\*Bead:\*\*\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Mapping:
    doc_path: str
    doc_kind: str
    bead_id: str
    mode: str  # declared | inferred


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def bead_exists(bead_id: str) -> bool:
    return run(["bd", "show", bead_id]).returncode == 0


def bead_show_text(bead_id: str) -> str:
    result = run(["bd", "show", bead_id])
    if result.returncode != 0:
        return ""
    return result.stdout or ""


def normalize_slug(path: Path) -> str:
    name = path.name
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
    name = name.removesuffix(".md")
    name = name.replace("-brainstorm", "")
    return name


def title_from_doc(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in text[:40]:
        line = line.strip()
        if line.startswith("#"):
            title = re.sub(r"^#+\s*", "", line).strip()
            if title:
                return f"[recovered-doc] {title}"[:220]
    return f"[recovered-doc] {path.stem}"[:220]


def create_placeholder(bead_id: str, path: Path, kind: str, dry_run: bool) -> tuple[bool, str]:
    title = title_from_doc(path)
    desc = (
        "Recovered placeholder bead created while mapping brainstorm/plan docs to beads.\n\n"
        f"- Source doc: {path.as_posix()}\n"
        f"- Doc kind: {kind}\n"
        "- Reason: bead ID referenced by doc was missing from current beads database."
    )
    cmd = [
        "bd",
        "create",
        "--id",
        bead_id,
        "--type",
        "task",
        "--priority",
        "2",
        "--title",
        title,
        "--description",
        desc,
        "--labels",
        "recovered,placeholder,doc-map",
    ]
    if dry_run:
        return True, f"would_create {bead_id}"
    res = run(cmd)
    if res.returncode != 0:
        return False, (res.stderr or "").strip()
    return True, f"created {bead_id}"


def append_doc_note(bead_id: str, mapping: Mapping, dry_run: bool) -> tuple[str, str]:
    note = f"[doc-map] {mapping.doc_kind} ({mapping.mode}): {mapping.doc_path}"
    current = bead_show_text(bead_id)
    if mapping.doc_path in current:
        return "skip", "already mapped"
    cmd = ["bd", "update", bead_id, "--append-notes", note]
    if dry_run:
        return "would_map", note
    res = run(cmd)
    if res.returncode != 0:
        return "error", (res.stderr or "").strip()
    return "mapped", note


def extract_ids(path: Path, infer_missing: bool) -> list[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    # 1) Primary declaration.
    for line in lines:
        m = DECL_RE.match(line.strip())
        if m:
            ids = [i.lower() for i in ID_RE.findall(m.group(1))]
            if ids:
                return [(i, "declared") for i in ids]

    # 2) Fallback "Bead:" plain declaration.
    for line in lines:
        if "Bead:" in line:
            rhs = line.split("Bead:", 1)[1]
            ids = [i.lower() for i in ID_RE.findall(rhs)]
            if ids:
                return [(i, "declared") for i in ids]

    # 3) Inference fallback from early text.
    if infer_missing:
        full_text = "\n".join(lines)
        m = ID_RE.search(full_text)
        if m:
            return [(m.group(0).lower(), "inferred")]

    return []


def collect_mappings(repo_root: Path, infer_missing: bool) -> list[Mapping]:
    docs = sorted((repo_root / "docs" / "brainstorms").glob("*.md")) + sorted(
        (repo_root / "docs" / "plans").glob("*.md")
    )
    prds = sorted((repo_root / "docs" / "prds").glob("*.md")) if (repo_root / "docs" / "prds").exists() else []

    # Build sibling lookup from declared bead mappings across brainstorms/plans/prds.
    slug_to_ids: dict[str, set[str]] = {}
    for path in docs + prds:
        declared = extract_ids(path, infer_missing=False)
        if not declared:
            continue
        slug = normalize_slug(path)
        ids = {bead_id for bead_id, mode in declared if mode == "declared"}
        if not ids:
            continue
        slug_to_ids.setdefault(slug, set()).update(ids)

    mappings: list[Mapping] = []
    for path in docs:
        rel = path.relative_to(repo_root).as_posix()
        kind = "brainstorm" if "/brainstorms/" in rel else "plan"
        ids = extract_ids(path, infer_missing=infer_missing)
        if not ids:
            sibling_ids = sorted(slug_to_ids.get(normalize_slug(path), set()))
            if sibling_ids:
                ids = [(i, "inferred-sibling") for i in sibling_ids]
        for bead_id, mode in ids:
            mappings.append(Mapping(doc_path=rel, doc_kind=kind, bead_id=bead_id, mode=mode))
    # Dedup exact duplicates while preserving order.
    seen: set[tuple[str, str]] = set()
    unique: list[Mapping] = []
    for m in mappings:
        key = (m.doc_path, m.bead_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description="Map brainstorms/plans to beads.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only.")
    parser.add_argument(
        "--no-create-missing",
        action="store_true",
        help="Do not create placeholder beads for missing IDs.",
    )
    parser.add_argument(
        "--no-infer",
        action="store_true",
        help="Disable inference for docs without explicit Bead declaration.",
    )
    parser.add_argument(
        "--report-csv",
        default="/tmp/beads-recovery-122264884/brainstorm-plan-bead-map.csv",
        help="Path for mapping report CSV.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    mappings = collect_mappings(repo_root, infer_missing=not args.no_infer)

    report_path = Path(args.report_csv)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["doc_path", "doc_kind", "bead_id", "mode"])
        for m in mappings:
            w.writerow([m.doc_path, m.doc_kind, m.bead_id, m.mode])

    mapped = 0
    skipped = 0
    created = 0
    errors = 0
    missing_ids: set[str] = set()
    unresolved_inferred = 0
    known_existing: set[str] = set()

    for m in mappings:
        exists = m.bead_id in known_existing or bead_exists(m.bead_id)
        if not exists:
            missing_ids.add(m.bead_id)
            if m.mode == "inferred":
                unresolved_inferred += 1
                skipped += 1
                print(f"skip inferred-missing {m.bead_id} for {m.doc_path}")
                continue
            if args.no_create_missing:
                errors += 1
                print(f"error missing bead {m.bead_id} for {m.doc_path}", file=sys.stderr)
                continue
            ok, msg = create_placeholder(
                m.bead_id,
                repo_root / m.doc_path,
                m.doc_kind,
                dry_run=args.dry_run,
            )
            if not ok:
                errors += 1
                print(f"error create {m.bead_id}: {msg}", file=sys.stderr)
                continue
            created += 1
            known_existing.add(m.bead_id)
            print(msg)
        else:
            known_existing.add(m.bead_id)

        status, detail = append_doc_note(m.bead_id, m, dry_run=args.dry_run)
        if status in {"mapped", "would_map"}:
            mapped += 1
        elif status == "skip":
            skipped += 1
        else:
            errors += 1
            print(f"error map {m.bead_id} <- {m.doc_path}: {detail}", file=sys.stderr)

    print(
        "summary:",
        f"docs_mappings={len(mappings)}",
        f"created={created}",
        f"mapped={mapped}",
        f"skipped={skipped}",
        f"unresolved_inferred={unresolved_inferred}",
        f"errors={errors}",
        f"missing_ids_seen={len(missing_ids)}",
        f"dry_run={str(args.dry_run).lower()}",
    )
    print(f"report_csv: {report_path}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
