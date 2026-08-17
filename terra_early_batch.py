#!/usr/bin/env python3
"""Stage and promote a balanced 1996–2015 Terra classification tranche."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from terra_pilot import safe_name, validate


ROOT = Path(__file__).parent
DATA = ROOT / "data"
SAMPLE = DATA / "sample_topn5_1996_2015_first50.csv"
BOOKS = DATA / "books_topn5_1996_2016.csv"
QUOTES = DATA / "quotes_topn5_1996_2016.csv"
BOOK_SOURCES = (BOOKS,)
QUOTE_SOURCES = (QUOTES,)
CLASSIFIED = DATA / "classified_topn5_1996_2015"
RUN_ID = "20260812_terra_early_first50_v2"
RUN = DATA / "terra_runs" / RUN_ID
JOBS = RUN / "jobs"
PROMPT = ROOT / "terra_prompt_v2.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_text(sample_id: str) -> str:
    return f"""# 1996–2015 Terra classification tranche

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one book. Use only these workspace
files: do not access parent directories, the network, or prior knowledge.

Write `results.json` with exactly this production-compatible shape:

```json
{{
  "sample_id": "{sample_id}",
  "quotes": [
    {{"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", "tense": "past|present|", "note": ""}}
  ],
  "narrating_situation": "retrospective|simultaneous|dual|unclear",
  "agent_note": ""
}}
```

Every input quote must appear exactly once and in input order. Every quote object
must include `tense`: use `past` or `present` only for `event`, otherwise `""`.
Only `dialogue` has `beat_tense`: add that key only for dialogue quotes, using
`past`, `present`, or `none`; omit it from every other bucket. Do not compute an
overall book label. Validate the file before responding.
"""


def prepare() -> None:
    if RUN.exists():
        raise SystemExit(f"run already exists: {RUN}")
    selection = list(csv.DictReader(SAMPLE.open(encoding="utf-8")))
    source_books = {
        row["sample_id"]: row
        for path in BOOK_SOURCES
        for row in csv.DictReader(path.open(encoding="utf-8"))
    }
    source_quotes: dict[str, list[dict[str, str]]] = {row["sample_id"]: [] for row in selection}
    for path in QUOTE_SOURCES:
        for row in csv.DictReader(path.open(encoding="utf-8")):
            if row["sample_id"] in source_quotes:
                source_quotes[row["sample_id"]].append(row)
    if missing := [sample_id for sample_id, rows in source_quotes.items() if not rows]:
        raise SystemExit(f"selected books without quotes: {missing}")
    targets = {row["sample_id"]: CLASSIFIED / f"{safe_name(row['sample_id'])}.json" for row in selection}
    if existing := [str(path) for path in targets.values() if path.exists()]:
        raise SystemExit(f"refusing to overwrite existing early classification files: {existing}")

    JOBS.mkdir(parents=True)
    shutil.copy2(ROOT / "METHODOLOGY.md", RUN / "METHODOLOGY.md")
    shutil.copy2(PROMPT, RUN / "terra_prompt_v2.md")
    for row in selection:
        sample_id = row["sample_id"]
        job = JOBS / safe_name(sample_id)
        job.mkdir()
        shutil.copy2(RUN / "METHODOLOGY.md", job / "METHODOLOGY.md")
        shutil.copy2(RUN / "terra_prompt_v2.md", job / "terra_prompt_v2.md")
        with (job / "quotes.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=("sample_id", "quote_id", "quote_text"))
            writer.writeheader()
            writer.writerows({key: quote[key] for key in writer.fieldnames} for quote in source_quotes[sample_id])
        (job / "TASK.md").write_text(task_text(sample_id), encoding="utf-8")

    manifest = {
        "run_id": RUN_ID,
        "created_at": datetime.now(UTC).isoformat(),
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "prompt": "terra_prompt_v2.md",
        "prompt_sha256": digest(PROMPT),
        "methodology_sha256": digest(ROOT / "METHODOLOGY.md"),
        "sample_source": str(SAMPLE),
        "quote_source": [str(path) for path in QUOTE_SOURCES],
        "selection_rule": "top two quote-yield books per year 1996–2015, plus third for odd years; minimum 15 quotes",
        "books": [
            {
                "sample_id": row["sample_id"], "title": source_books[row["sample_id"]]["title"],
                "author": source_books[row["sample_id"]]["author"], "year": row["year"],
                "quote_count": len(source_quotes[row["sample_id"]]),
                "quotes_sha256": digest(JOBS / safe_name(row["sample_id"]) / "quotes.csv"),
                "staged_result": str(JOBS / safe_name(row["sample_id"]) / "results.json"),
                "production_output": str(targets[row["sample_id"]]), "status": "staged",
            }
            for row in selection
        ],
    }
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"staged {len(selection)} early-period jobs in {RUN}")


def promote() -> None:
    manifest_path = RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validated = []
    for entry in manifest["books"]:
        result, destination = Path(entry["staged_result"]), Path(entry["production_output"])
        if destination.exists():
            raise SystemExit(f"refusing to overwrite existing output: {destination}")
        if not result.exists():
            raise SystemExit(f"missing staged result: {result}")
        payload = json.loads(result.read_text(encoding="utf-8"))
        for quote in payload.get("quotes", []):
            if quote.get("bucket") != "dialogue" and quote.get("beat_tense") in {"", "none"}:
                del quote["beat_tense"]
        ids = [row["quote_id"] for row in csv.DictReader((result.parent / "quotes.csv").open(encoding="utf-8"))]
        validate(entry["sample_id"], payload, ids)
        validated.append((entry, payload, destination))
    CLASSIFIED.mkdir(exist_ok=True)
    for entry, payload, destination in validated:
        temporary = destination.with_suffix(".json.terra-tmp")
        temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        entry["status"] = "promoted"
        entry["output_sha256"] = digest(destination)
        entry["promoted_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"validated and promoted {len(validated)} early-period classifications")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "promote"))
    args = parser.parse_args()
    {"prepare": prepare, "promote": promote}[args.command]()
