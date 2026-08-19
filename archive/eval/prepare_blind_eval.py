#!/usr/bin/env python3
"""Create a stratified, blinded Terra-vs-Sonnet evaluation fixture."""
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).parent
DATA = ROOT / "data"
YEARS = range(2016, 2026)
SEED = 20260811
BOOKS_PER_YEAR = 3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_quotes():
    with (DATA / "quotes_topn.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    quotes = defaultdict(list)
    for row in rows:
        quotes[row["sample_id"]].append(row)
    return quotes


def valid_production_records(quotes_by_book):
    candidates = defaultdict(list)
    for path in sorted((DATA / "classified").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        sample_id = record.get("sample_id", "")
        if not sample_id.startswith("top"):
            continue
        try:
            year = int(sample_id[3:7])
        except ValueError:
            continue
        if year not in YEARS:
            continue
        source_quotes = quotes_by_book.get(sample_id, [])
        result_quotes = record.get("quotes", [])
        if not source_quotes or {row["quote_id"] for row in source_quotes} != {
            row.get("quote_id") for row in result_quotes
        }:
            continue
        if record.get("narrating_situation") not in {
            "retrospective", "simultaneous", "dual", "unclear"
        }:
            continue
        if any(
            row.get("bucket") == "dialogue" and row.get("beat_tense") not in {
                "past", "present", "none"
            }
            for row in result_quotes
        ):
            continue
        candidates[year].append((sample_id, path, record))
    return candidates


def main():
    eval_root = DATA / "evals" / "terra_sonnet_blind_20260811"
    work_root = Path("/private/tmp/booktense-terra-blind-20260811")
    if eval_root.exists() or work_root.exists():
        raise SystemExit(f"refusing to overwrite existing evaluation fixture: {eval_root}")

    quotes_by_book = load_quotes()
    candidates = valid_production_records(quotes_by_book)
    short = {year: len(candidates[year]) for year in YEARS if len(candidates[year]) < BOOKS_PER_YEAR}
    if short:
        raise SystemExit(f"not enough complete production records: {short}")

    rng = random.Random(SEED)
    selected = {}
    for year in YEARS:
        selected[year] = rng.sample(candidates[year], BOOKS_PER_YEAR)

    eval_root.mkdir(parents=True)
    snapshot_root = eval_root / "sonnet_snapshot"
    snapshot_root.mkdir()
    work_root.mkdir()
    manifest = {
        "seed": SEED,
        "books_per_year": BOOKS_PER_YEAR,
        "years": list(YEARS),
        "model": "gpt-5.6-terra",
        "reasoning_effort": "medium",
        "books": [],
    }
    assignments = {f"agent_{number}": [] for number in range(1, 4)}

    for year in YEARS:
        for index, (sample_id, source_path, record) in enumerate(selected[year]):
            agent_id = f"agent_{index + 1}"
            snapshot_path = snapshot_root / f"{sample_id.replace(':', '_').replace('|', '_')}.json"
            shutil.copyfile(source_path, snapshot_path)
            entry = {
                "sample_id": sample_id,
                "year": year,
                "agent_id": agent_id,
                "production_source": str(source_path.relative_to(ROOT)),
                "production_sha256": digest(source_path),
                "snapshot": str(snapshot_path.relative_to(eval_root)),
                "quote_count": len(record["quotes"]),
            }
            manifest["books"].append(entry)
            assignments[agent_id].append(entry)

    for agent_id, assigned in assignments.items():
        workspace = work_root / agent_id
        workspace.mkdir()
        shutil.copyfile(ROOT / "METHODOLOGY.md", workspace / "METHODOLOGY.md")
        with (workspace / "quotes.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["sample_id", "quote_id", "quote_text"])
            writer.writeheader()
            for entry in assigned:
                for quote in quotes_by_book[entry["sample_id"]]:
                    writer.writerow({
                        "sample_id": quote["sample_id"],
                        "quote_id": quote["quote_id"],
                        "quote_text": quote["quote_text"],
                    })
        (workspace / "TASK.md").write_text(
            "# Blind narrative-tense evaluation\n\n"
            "Read `METHODOLOGY.md` and classify every quote in `quotes.csv`.\n\n"
            "You have only pull-quote text. Do not access the network, parent directories, "
            "or any external metadata, and do not infer labels from prior knowledge.\n\n"
            "Write exactly one `results.json` with this shape:\n\n"
            "```json\n"
            "{\n"
            f'  "agent_id": "{agent_id}",\n'
            '  "books": [{\n'
            '    "sample_id": "topYYYY:...",\n'
            '    "narrating_situation": "retrospective|simultaneous|dual|unclear",\n'
            '    "agent_note": "",\n'
            '    "quotes": [{"quote_id": "q00001", "bucket": "dialogue|gnomic|event|paratext|unclear", '
            '"tense": "past|present|", "beat_tense": "past|present|none", "note": ""}]\n'
            "  }]\n"
            "}\n"
            "```\n\n"
            "Every input quote must appear exactly once. `tense` must be blank unless `bucket` is `event`; "
            "`beat_tense` must be `past`, `present`, or `none` only for dialogue, and blank otherwise. "
            "Do not calculate a final book label.\n",
            encoding="utf-8",
        )

    (eval_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (eval_root / "README.md").write_text(
        "# Blind Terra vs. Sonnet evaluation\n\n"
        "This directory contains a frozen production snapshot and evaluation metadata. "
        "Blind agent inputs live separately in `/private/tmp/booktense-terra-blind-20260811/` "
        "and contain quote text and methodology only.\n",
        encoding="utf-8",
    )
    print(f"created {eval_root}")
    print(f"created {work_root}")
    for agent_id, assigned in assignments.items():
        print(f"{agent_id}: {len(assigned)} books")


if __name__ == "__main__":
    main()
