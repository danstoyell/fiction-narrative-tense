#!/usr/bin/env python3
"""Restore an out-of-range duplicate row touched by the first integration pass."""

import csv
import json
import os
from pathlib import Path


RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[2]
BACKUP = RUN / "integration_backup"
SAMPLE_ID = "top1995:6096"


def read(path):
    return list(csv.DictReader(path.open(encoding="utf-8")))


def write(path, rows, fields):
    temporary = path.with_suffix(path.suffix + ".scope-tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def restore_rows(relative_path):
    active = ROOT / relative_path
    backup = BACKUP / relative_path
    current = read(active)
    original = [row for row in read(backup) if row["sample_id"] == SAMPLE_ID]
    restored = []
    inserted = False
    for row in current:
        if row["sample_id"] == SAMPLE_ID:
            if not inserted:
                restored.extend(original)
                inserted = True
        else:
            restored.append(row)
    if not inserted:
        restored.extend(original)
    write(active, restored, list(current[0]))


restore_rows(Path("raw_data/books_topn.csv"))
restore_rows(Path("raw_data/quotes_topn.csv"))
(ROOT / "raw_data/classified/top1995_6096.json").unlink(missing_ok=True)

manifest_path = RUN / "integration_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
for change in manifest["changes"]:
    if change["sample_id"] == SAMPLE_ID:
        change["source_files"] = [path for path in change["source_files"] if path != "raw_data/books_topn.csv"]
        change["classification_files"] = [
            path for path in change["classification_files"]
            if path != "raw_data/classified/top1995_6096.json"
        ]
        change["scope_repair"] = "restored out-of-range modern duplicate from integration backup"
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

for source_path in sorted({path for change in manifest["changes"] for path in change["source_files"]}):
    path = ROOT / source_path
    rows = read(path)
    write(path, rows, list(rows[0]))
    quote_path = path.with_name(path.name.replace("books_", "quotes_"))
    quote_rows = read(quote_path)
    write(quote_path, quote_rows, list(quote_rows[0]))
print("restored out-of-range modern duplicate for top1995:6096")
