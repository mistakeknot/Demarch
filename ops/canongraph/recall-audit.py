#!/usr/bin/env python3
"""Recall-vs-auto-memory audit for the CanonGraph memory loop (goal mk-9qf.4).

Reads ~/.canongraph/recall-log.jsonl (written by the SessionStart recall hook on each
machine) and summarizes: hit rate, emission rate, decision coverage, top hit/miss
projects. Run on both machines (or pull zklw's log over ssh) after ~a week of sessions,
then tune: misses that SHOULD hit → backfill those projects; hits with 0 decisions →
decision archaeology targets; noisy hits → tighten the lane policy or the hook's
emission rule (memory-lanes.md is the policy home).
"""
import json, os, sys
from collections import Counter

path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.canongraph/recall-log.jsonl")
if not os.path.exists(path):
    sys.exit(f"no log at {path} — has the recall hook run?")

rows = [json.loads(l) for l in open(path) if l.strip()]
hits = [r for r in rows if r.get("hit")]
misses = [r for r in rows if not r.get("hit")]
emitted = [r for r in hits if r.get("emitted")]
with_dec = [r for r in hits if r.get("decisions")]

print(f"sessions logged : {len(rows)}  (since {rows[0]['ts'] if rows else '-'})")
print(f"graph hits      : {len(hits)}/{len(rows)}  ({100*len(hits)//max(1,len(rows))}%)")
print(f"context emitted : {len(emitted)}/{len(hits)} of hits")
print(f"hits w/decisions: {len(with_dec)}/{len(hits)}")
print("\ntop projects (hits):", Counter(r["project"] for r in hits).most_common(8))
print("misses (backfill candidates):", Counter(r["project"] for r in misses).most_common(8))
print("\nTune loop: misses→backfill | 0-decision hits→archaeology | noise→memory-lanes.md")
