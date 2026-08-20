#!/usr/bin/env python3
"""Advance one isolated final-early-period Terra job per invocation."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

import terra_pilot as pilot


HERE = Path(__file__).parent
ROOT = HERE.parent
RUN = ROOT / "raw_data" / "terra_runs" / "20260812_terra_early_rest_v2"
MODEL = "gpt-5.6-terra"
CONFIG = 'model_reasoning_effort="medium"'


def session_id(job: Path) -> str | None:
    for log in (job / "codex.log", job / "codex-resume.log", job / "codex-repair.log"):
        if log.exists() and (match := re.search(r"session id: ([^\s]+)", log.read_text(encoding="utf-8", errors="ignore"))):
            return match.group(1)
    return None


def validate(job: Path, sample_id: str) -> str:
    result = job / "results.json"
    if not result.exists():
        return "missing"
    try:
        payload = json.loads(result.read_text(encoding="utf-8"))
        for quote in payload.get("quotes", []):
            if quote.get("bucket") != "dialogue":
                quote.pop("beat_tense", None)
        result.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        quote_ids = [row["quote_id"] for row in csv.DictReader((job / "quotes.csv").open(encoding="utf-8"))]
        pilot.validate(sample_id, payload, quote_ids)
    except Exception:
        return "invalid"
    return "valid"


def invoke(job: Path, command: list[str], log_name: str) -> None:
    with (job / log_name).open("a", encoding="utf-8") as log:
        subprocess.run(command, cwd=job, stdout=log, stderr=subprocess.STDOUT, check=False)


def main() -> None:
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    states = []
    for entry in manifest["books"]:
        job = Path(entry["staged_result"]).parent
        states.append((validate(job, entry["sample_id"]), entry, job))
    for desired in ("invalid", "missing"):
        for state, entry, job in states:
            if state != desired:
                continue
            session = session_id(job)
            if desired == "invalid":
                instruction = (
                    "Immediately rewrite results.json as one valid JSON object using direct Python or shell "
                    "serialization, not apply_patch. Preserve substantive classifications and quote order; "
                    "strictly follow TASK.md. Do not return prose."
                )
            else:
                instruction = (
                    "Read TASK.md, METHODOLOGY.md, terra_prompt_v2.md, and quotes.csv. Classify solely "
                    "from supplied quote text. Write complete results.json directly with Python or shell JSON "
                    "serialization, not apply_patch. Do not inspect parent directories or use network."
                )
            if session:
                command = ["codex", "exec", "resume", session, "--skip-git-repo-check", "-m", MODEL, "-c", CONFIG, instruction]
                invoke(job, command, "codex-repair.log" if desired == "invalid" else "codex-resume.log")
            else:
                command = ["codex", "exec", "--skip-git-repo-check", "-m", MODEL, "-c", CONFIG, "--ignore-user-config", "--ignore-rules", instruction]
                invoke(job, command, "codex.log")
            if validate(job, entry["sample_id"]) == "missing" and (session := session_id(job)):
                command = ["codex", "exec", "resume", session, "--skip-git-repo-check", "-m", MODEL, "-c", CONFIG, "Immediately write complete schema-valid results.json now with direct Python or shell JSON serialization, not apply_patch. No prose."]
                invoke(job, command, "codex-resume.log")
            print(f"processed {entry['year']}: {entry['title']} ({validate(job, entry['sample_id'])})")
            return
    print("all staged results validate")


if __name__ == "__main__":
    main()
