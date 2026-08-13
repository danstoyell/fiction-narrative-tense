#!/usr/bin/env python3
"""Confirm a backfill pass added beat_tense and changed NOTHING else."""
import json, glob, os, sys
PRE, POST = "data/classified_pre_beat", "data/classified"
bad = checked = filled = 0
for post in sorted(glob.glob(os.path.join(POST, "*.json"))):
    pre = os.path.join(PRE, os.path.basename(post))
    if not os.path.exists(pre):
        continue
    a, b = json.load(open(pre)), json.load(open(post))
    qa = {x["quote_id"]: x for x in a.get("quotes", [])}
    qb = {x["quote_id"]: x for x in b.get("quotes", [])}
    if set(qa) != set(qb):
        print(f"  QUOTE SET CHANGED: {os.path.basename(post)}"); bad += 1; continue
    if a.get("narrating_situation") != b.get("narrating_situation"):
        print(f"  SITUATION CHANGED: {os.path.basename(post)}"); bad += 1
    touched = False
    for k in qa:
        for f in ("bucket", "tense", "note"):
            if (qa[k].get(f) or "") != (qb[k].get(f) or ""):
                print(f"  {f.upper()} CHANGED: {os.path.basename(post)} {k}"); bad += 1
        if qb[k].get("bucket") == "dialogue" and "beat_tense" in qb[k]:
            touched = True
    checked += 1
    if touched:
        filled += 1
print(f"\n  {checked} files compared · {filled} carry beat_tense · {bad} integrity violations")
sys.exit(1 if bad else 0)
