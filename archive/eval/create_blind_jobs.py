#!/usr/bin/env python3
"""Split a frozen blind-evaluation manifest into one isolated job per book."""
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).parent
EVAL = ROOT / "data" / "evals" / "terra_sonnet_blind_20260811"
WORK = Path("/private/tmp/booktense-terra-blind-20260811")


def job_id(sample_id):
    return "job_" + "".join(char if char.isalnum() else "_" for char in sample_id)


def main():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    jobs = WORK / "jobs"
    if jobs.exists():
        raise SystemExit(f"refusing to overwrite {jobs}")
    with (ROOT / "data" / "quotes_topn.csv").open(encoding="utf-8", newline="") as file:
        quotes = defaultdict(list)
        for row in csv.DictReader(file):
            quotes[row["sample_id"]].append(row)

    jobs.mkdir()
    for entry in manifest["books"]:
        workspace = jobs / job_id(entry["sample_id"])
        workspace.mkdir()
        shutil.copyfile(ROOT / "METHODOLOGY.md", workspace / "METHODOLOGY.md")
        with (workspace / "quotes.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["sample_id", "quote_id", "quote_text"])
            writer.writeheader()
            for quote in quotes[entry["sample_id"]]:
                writer.writerow({key: quote[key] for key in writer.fieldnames})
        (workspace / "TASK.md").write_text(
            "# Blind narrative-tense evaluation\n\n"
            "Read `METHODOLOGY.md`, then classify every quote in `quotes.csv`. "
            "This workspace contains one book only.\n\n"
            "Use only these workspace files. Do not access the network, parent directories, "
            "repository files, or external metadata. Do not infer anything from prior knowledge.\n\n"
            "Use Python's CSV reader to inspect the input; do not dump the whole file to the terminal.\n\n"
            "Before ending, write exactly one valid `results.json` with this shape:\n\n"
            "```json\n"
            "{\n"
            f'  "agent_id": "{job_id(entry["sample_id"])}",\n'
            '  "books": [{\n'
            f'    "sample_id": "{entry["sample_id"]}",\n'
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
    print(f"created {len(manifest['books'])} isolated jobs in {jobs}")


if __name__ == "__main__":
    main()
