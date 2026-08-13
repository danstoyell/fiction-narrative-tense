#!/usr/bin/env python3
"""Stage, validate, and atomically promote a small Terra classification pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).parent
DATA = ROOT / "data"
RUN_ID = "20260811_terra_prod_pilot_v2"
RUN = DATA / "terra_runs" / RUN_ID
JOBS = RUN / "jobs"
PROMPT = ROOT / "terra_prompt_v2.md"
SAMPLE_IDS = (
    "top2025:DUNGEON CRAWLER CARL|Matt Dinniman",
    "top2018:7239",
    "top2019:3883",
)
VALID_BUCKETS = {"dialogue", "gnomic", "event", "paratext", "unclear"}
VALID_SITUATIONS = {"retrospective", "simultaneous", "dual", "unclear"}


def safe_name(sample_id: str) -> str:
    return sample_id.translate(str.maketrans({"/": "_", ":": "_", "|": "_", "'": "_"}))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_quotes() -> dict[str, list[dict[str, str]]]:
    quotes: dict[str, list[dict[str, str]]] = {sample_id: [] for sample_id in SAMPLE_IDS}
    with (DATA / "quotes_topn.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row["sample_id"] in quotes:
                quotes[row["sample_id"]].append(row)
    if missing := [sample_id for sample_id, rows in quotes.items() if not rows]:
        raise SystemExit(f"missing quotes for: {missing}")
    return quotes


def load_books() -> dict[str, dict[str, str]]:
    with (DATA / "books_topn.csv").open(encoding="utf-8", newline="") as file:
        books = {row["sample_id"]: row for row in csv.DictReader(file)}
    return {sample_id: books[sample_id] for sample_id in SAMPLE_IDS}


def task_text(sample_id: str) -> str:
    return f"""# Terra production classification pilot

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one book.

Use only the files in this workspace. Do not use the network, parent directories,
or knowledge of the title. Write `results.json` with the production-compatible
shape below. Do not calculate an overall book label.

```json
{{
  "sample_id": "{sample_id}",
  "quotes": [
    {{"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", "tense": "past|present|", "beat_tense": "past|present|none (dialogue only)", "note": ""}}
  ],
  "narrating_situation": "retrospective|simultaneous|dual|unclear",
  "agent_note": ""
}}
```

Every input quote must appear exactly once and in input order. `tense` is required
only for `event` and must otherwise be empty. `beat_tense` is required only for
`dialogue` and must not be included for other buckets. Before responding, validate
the JSON against those conditions.
"""


def prepare() -> None:
    if RUN.exists():
        raise SystemExit(f"run already exists: {RUN}")
    quotes = load_quotes()
    books = load_books()
    destinations = {sample_id: DATA / "classified" / f"{safe_name(sample_id)}.json" for sample_id in SAMPLE_IDS}
    existing = [str(path) for path in destinations.values() if path.exists()]
    if existing:
        raise SystemExit(f"refusing to overwrite existing production files: {existing}")

    JOBS.mkdir(parents=True)
    shutil.copy2(ROOT / "METHODOLOGY.md", RUN / "METHODOLOGY.md")
    shutil.copy2(PROMPT, RUN / "terra_prompt_v2.md")
    for sample_id, rows in quotes.items():
        job = JOBS / safe_name(sample_id)
        job.mkdir()
        shutil.copy2(RUN / "METHODOLOGY.md", job / "METHODOLOGY.md")
        shutil.copy2(RUN / "terra_prompt_v2.md", job / "terra_prompt_v2.md")
        with (job / "quotes.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=("sample_id", "quote_id", "quote_text"))
            writer.writeheader()
            writer.writerows({key: row[key] for key in writer.fieldnames} for row in rows)
        (job / "TASK.md").write_text(task_text(sample_id), encoding="utf-8")

    manifest = {
        "run_id": RUN_ID,
        "created_at": datetime.now(UTC).isoformat(),
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "prompt": "terra_prompt_v2.md",
        "prompt_sha256": digest(PROMPT),
        "methodology_sha256": digest(ROOT / "METHODOLOGY.md"),
        "books": [
            {
                "sample_id": sample_id,
                "title": books[sample_id]["title"],
                "author": books[sample_id]["author"],
                "year": books[sample_id]["year"],
                "quote_count": len(quotes[sample_id]),
                "quotes_sha256": digest(JOBS / safe_name(sample_id) / "quotes.csv"),
                "staged_result": str(JOBS / safe_name(sample_id) / "results.json"),
                "production_output": str(destinations[sample_id]),
                "status": "staged",
            }
            for sample_id in SAMPLE_IDS
        ],
    }
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"staged {len(SAMPLE_IDS)} jobs in {RUN}")


def validate(sample_id: str, payload: dict, expected_ids: list[str]) -> None:
    if set(payload) != {"sample_id", "quotes", "narrating_situation", "agent_note"}:
        raise ValueError(f"{sample_id}: unexpected top-level keys")
    if payload["sample_id"] != sample_id:
        raise ValueError(f"{sample_id}: sample_id mismatch")
    if payload["narrating_situation"] not in VALID_SITUATIONS:
        raise ValueError(f"{sample_id}: invalid narrating_situation")
    if not isinstance(payload["agent_note"], str):
        raise ValueError(f"{sample_id}: agent_note must be a string")
    quotes = payload["quotes"]
    if [quote.get("quote_id") for quote in quotes] != expected_ids:
        raise ValueError(f"{sample_id}: quote IDs are not complete and ordered")
    for quote in quotes:
        bucket = quote.get("bucket")
        if bucket not in VALID_BUCKETS or not isinstance(quote.get("note"), str):
            raise ValueError(f"{sample_id}: invalid bucket or note for {quote.get('quote_id')}")
        if bucket == "event":
            if quote.get("tense") not in {"past", "present"} or "beat_tense" in quote:
                raise ValueError(f"{sample_id}: invalid event fields for {quote['quote_id']}")
        elif bucket == "dialogue":
            if quote.get("tense") != "" or quote.get("beat_tense") not in {"past", "present", "none"}:
                raise ValueError(f"{sample_id}: invalid dialogue fields for {quote['quote_id']}")
        elif quote.get("tense") != "" or "beat_tense" in quote:
            raise ValueError(f"{sample_id}: invalid non-evidence fields for {quote['quote_id']}")


def promote() -> None:
    manifest_path = RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validated: list[tuple[dict, dict, Path]] = []
    for entry in manifest["books"]:
        sample_id = entry["sample_id"]
        result = Path(entry["staged_result"])
        destination = Path(entry["production_output"])
        expected_ids = [row["quote_id"] for row in csv.DictReader((result.parent / "quotes.csv").open(encoding="utf-8"))]
        if destination.exists():
            raise SystemExit(f"refusing to overwrite active or existing file: {destination}")
        if not result.exists():
            raise SystemExit(f"missing staged result: {result}")
        payload = json.loads(result.read_text(encoding="utf-8"))
        validate(sample_id, payload, expected_ids)
        validated.append((entry, payload, destination))

    for entry, payload, destination in validated:
        temporary = destination.with_suffix(".json.terra-tmp")
        temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        entry["status"] = "promoted"
        entry["output_sha256"] = digest(destination)
        entry["promoted_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"validated and promoted {len(validated)} production-compatible Terra files")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "promote"))
    args = parser.parse_args()
    {"prepare": prepare, "promote": promote}[args.command]()


if __name__ == "__main__":
    main()
