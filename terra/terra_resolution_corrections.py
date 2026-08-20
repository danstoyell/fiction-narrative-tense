#!/usr/bin/env python3
"""Stage and run blind Terra-medium jobs for Goodreads resolution corrections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from terra_pilot import safe_name, validate


HERE = Path(__file__).parent
ROOT = HERE.parent
AUDIT = ROOT / "raw_data" / "resolution_audit_20260819"
SOURCE_BOOKS = AUDIT / "corrected_books.csv"
SOURCE_QUOTES = AUDIT / "corrected_quotes.csv"
SAMPLE = AUDIT / "refetch_sample.csv"
RUN_ID = "20260820_terra_resolution_corrections_v1"
RUN = AUDIT / RUN_ID
JOBS = RUN / "jobs"
PROMPT = HERE / "terra_prompt_v2.md"
MODEL = "gpt-5.6-terra"
CONFIG = 'model_reasoning_effort="medium"'
BOOK_FIELDS = (
    "sample_id", "stratum", "title", "author", "year", "isbn", "gr_book_id",
    "gr_work_id", "gr_title", "gr_author", "gr_year", "gr_ratings",
    "resolve_method", "resolve_confidence", "resolve_notes", "pages_fetched",
    "quotes_raw", "quotes_dedup", "fetched_at",
)
QUOTE_FIELDS = (
    "quote_id", "sample_id", "gr_work_id", "page", "idx", "source_url",
    "quote_text", "bucket", "tense", "note",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_text(sample_id: str) -> str:
    return f"""# Goodreads resolution correction classification

Read `METHODOLOGY.md` and `terra_prompt_v2.md`, then classify every quote in
`quotes.csv`. This workspace contains exactly one unidentified book.

Use only the files in this workspace. Do not use the network, parent directories,
the book title, or any prior classification. Write `results.json` with exactly:

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
`dialogue` and must be omitted for other buckets. Do not compute an overall book
label. Validate the complete JSON before responding.
"""


def write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)


def normalized_inputs() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    expected = [row["sample_id"] for row in csv.DictReader(SAMPLE.open(encoding="utf-8"))]
    fetched = list(csv.DictReader(SOURCE_BOOKS.open(encoding="utf-8")))
    latest: dict[str, dict[str, str]] = {}
    for row in fetched:
        sample_id = row["sample_id"]
        if sample_id not in latest or row.get("fetched_at", "") >= latest[sample_id].get("fetched_at", ""):
            latest[sample_id] = row
    if missing := [sample_id for sample_id in expected if sample_id not in latest]:
        raise SystemExit(f"refetches are incomplete; missing book rows: {missing}")

    source_quotes = list(csv.DictReader(SOURCE_QUOTES.open(encoding="utf-8")))
    normalized_quotes = []
    for sample_id in expected:
        book = latest[sample_id]
        work_id = book.get("gr_work_id", "")
        seen_text = set()
        rows = []
        for quote in source_quotes:
            if quote["sample_id"] != sample_id or quote.get("gr_work_id", "") != work_id:
                continue
            text_key = " ".join(quote["quote_text"].split())
            if not text_key or text_key in seen_text:
                continue
            seen_text.add(text_key)
            rows.append(dict(quote))
        for index, quote in enumerate(rows, 1):
            quote["quote_id"] = f"q{index:05d}"
            normalized_quotes.append(quote)
        book["quotes_dedup"] = str(len(rows))
        book["pages_fetched"] = str(max((int(row["page"]) for row in rows), default=0))
    return [latest[sample_id] for sample_id in expected], normalized_quotes


def prepare() -> None:
    if RUN.exists():
        raise SystemExit(f"run already exists: {RUN}")
    books, quotes = normalized_inputs()
    by_sample: dict[str, list[dict[str, str]]] = {book["sample_id"]: [] for book in books}
    for quote in quotes:
        by_sample[quote["sample_id"]].append(quote)

    JOBS.mkdir(parents=True)
    shutil.copy2(ROOT / "METHODOLOGY.md", RUN / "METHODOLOGY.md")
    shutil.copy2(PROMPT, RUN / "terra_prompt_v2.md")
    write_csv(RUN / "corrected_books.csv", BOOK_FIELDS, books)
    write_csv(RUN / "corrected_quotes.csv", QUOTE_FIELDS, quotes)
    entries = []
    for book in books:
        sample_id = book["sample_id"]
        rows = by_sample[sample_id]
        entry = {
            "sample_id": sample_id,
            "title": book["title"],
            "author": book["author"],
            "year": book["year"],
            "gr_book_id": book["gr_book_id"],
            "gr_work_id": book["gr_work_id"],
            "gr_title": book["gr_title"],
            "quote_count": len(rows),
            "status": "no_quotes" if not rows else "staged",
        }
        if rows:
            job = JOBS / safe_name(sample_id)
            job.mkdir()
            shutil.copy2(RUN / "METHODOLOGY.md", job / "METHODOLOGY.md")
            shutil.copy2(RUN / "terra_prompt_v2.md", job / "terra_prompt_v2.md")
            write_csv(job / "quotes.csv", ("sample_id", "quote_id", "quote_text"), rows)
            (job / "TASK.md").write_text(task_text(sample_id), encoding="utf-8")
            entry["quotes_sha256"] = digest(job / "quotes.csv")
            entry["staged_result"] = str(job / "results.json")
        entries.append(entry)

    manifest = {
        "run_id": RUN_ID,
        "created_at": datetime.now(UTC).isoformat(),
        "model": MODEL,
        "reasoning_effort": "medium",
        "blind_to": ["title", "author", "year", "prior classifications", "network"],
        "prompt_sha256": digest(PROMPT),
        "methodology_sha256": digest(ROOT / "METHODOLOGY.md"),
        "books": entries,
    }
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"staged {sum(bool(by_sample[b['sample_id']]) for b in books)} jobs; "
          f"{sum(not bool(by_sample[b['sample_id']]) for b in books)} books have no corrected quotes")


def result_state(entry: dict) -> str:
    if entry["status"] == "no_quotes":
        return "no_quotes"
    result = Path(entry["staged_result"])
    if not result.exists():
        return "missing"
    try:
        payload = json.loads(result.read_text(encoding="utf-8"))
        for quote in payload.get("quotes", []):
            if quote.get("bucket") == "dialogue" and quote.get("beat_tense") == "":
                quote["beat_tense"] = "none"
            elif quote.get("bucket") != "dialogue":
                quote.pop("beat_tense", None)
        result.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        expected_ids = [
            row["quote_id"]
            for row in csv.DictReader((result.parent / "quotes.csv").open(encoding="utf-8"))
        ]
        validate(entry["sample_id"], payload, expected_ids)
    except Exception:
        return "invalid"
    return "valid"


def session_id(job: Path) -> str | None:
    for name in ("codex.log", "codex-resume.log", "codex-repair.log"):
        path = job / name
        if path.exists() and (match := re.search(r"session id: ([^\s]+)", path.read_text(errors="ignore"))):
            return match.group(1)
    return None


def invoke(job: Path, command: list[str], log_name: str) -> None:
    with (job / log_name).open("a", encoding="utf-8") as log:
        subprocess.run(command, cwd=job, stdout=log, stderr=subprocess.STDOUT, check=False)


def step() -> None:
    manifest_path = RUN / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for desired in ("invalid", "missing"):
        for entry in manifest["books"]:
            if result_state(entry) != desired:
                continue
            job = Path(entry["staged_result"]).parent
            session = session_id(job)
            instruction = (
                "Rewrite results.json as one complete schema-valid JSON object using only TASK.md, "
                "METHODOLOGY.md, terra_prompt_v2.md, and quotes.csv. Preserve quote order. No prose."
                if desired == "invalid" else
                "Read TASK.md, METHODOLOGY.md, terra_prompt_v2.md, and quotes.csv. Classify solely "
                "from supplied quote text and write complete results.json directly. No prose."
            )
            if session:
                command = ["codex", "exec", "resume", session, "--skip-git-repo-check", "-m", MODEL,
                           "-c", CONFIG, "-c", 'sandbox_mode="workspace-write"', instruction]
                log_name = "codex-repair.log" if desired == "invalid" else "codex-resume.log"
            else:
                command = ["codex", "exec", "--skip-git-repo-check", "-m", MODEL, "-c", CONFIG,
                           "-s", "workspace-write", "--ignore-user-config", "--ignore-rules", instruction]
                log_name = "codex.log"
            invoke(job, command, log_name)
            state = result_state(entry)
            entry["status"] = "classified" if state == "valid" else state
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"processed {entry['sample_id']}: {state}")
            return
    print("all staged results validate")


def status() -> None:
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for entry in manifest["books"]:
        state = result_state(entry)
        counts[state] = counts.get(state, 0) + 1
        print(f"{state:10s} {entry['year']} {entry['title']} ({entry['quote_count']} quotes)")
    print(counts)


def run_all() -> None:
    for _ in range(40):
        manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
        pending = [entry for entry in manifest["books"] if result_state(entry) in {"missing", "invalid"}]
        if not pending:
            print("all staged results validate")
            return
        step()
    raise SystemExit("classification run exceeded 40 attempts")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "step", "run", "status"))
    args = parser.parse_args()
    {"prepare": prepare, "step": step, "run": run_all, "status": status}[args.command]()


if __name__ == "__main__":
    main()
