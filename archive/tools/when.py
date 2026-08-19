#!/usr/bin/env python3
"""Show when each turn in a Claude Code session happened.

Usage:  python3 when.py [N]      # last N exchanges (default 15)
"""
import json, sys, glob, os, datetime

PROJ = os.path.expanduser("~/.claude/projects")
here = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
cands = glob.glob(os.path.join(PROJ, "*booktense*", "*.jsonl"))
if not cands:
    sys.exit("no transcript found")
path = max(cands, key=os.path.getmtime)

n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
rows = []
for line in open(path):
    try:
        d = json.loads(line)
    except Exception:
        continue
    ts, msg = d.get("timestamp"), d.get("message")
    if not ts or not isinstance(msg, dict):
        continue
    role = msg.get("role")
    if role not in ("user", "assistant"):
        continue
    c = msg.get("content")
    if isinstance(c, list):
        text = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    else:
        text = c if isinstance(c, str) else ""
    text = " ".join(text.split())
    if not text or text.startswith("[SYSTEM NOTIFICATION"):
        continue
    rows.append((ts, role, text))

local = datetime.datetime.now().astimezone().tzinfo
prev = None
for ts, role, text in rows[-n:]:
    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(local)
    gap = ""
    if prev:
        m = (t - prev).total_seconds() / 60
        if m >= 60:
            gap = f"  (+{m/60:.1f}h)"
        elif m >= 1:
            gap = f"  (+{m:.0f}m)"
    prev = t
    who = "YOU " if role == "user" else "CLDE"
    print(f"{t:%a %H:%M}  {who}  {text[:88]}{gap}")
