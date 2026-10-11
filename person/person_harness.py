#!/usr/bin/env python3
"""Stage, run, validate, promote, and export base-narration person labels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOKS = ROOT / "dataset" / "books.csv"
DEFAULT_QUOTES = ROOT / "dataset" / "quotes.csv"
DEFAULT_RUNS = ROOT / "raw_data" / "person_runs"
DEFAULT_CLASSIFIED = ROOT / "raw_data" / "person_classified"
DEFAULT_EXPORT = ROOT / "dataset"
METHODOLOGY = ROOT / "PERSON_METHODOLOGY.md"
PROMPT = Path(__file__).with_name("PROMPT.md")
SCHEMA = Path(__file__).with_name("result_schema.json")

MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "medium"
SCHEMA_VERSION = 1

PERSON_SIGNALS = {"first", "second", "third", "unmarked", "non_base", "unclear"}
PERSON_LABELS = {"FIRST", "SECOND", "THIRD", "ALTERNATING", "UNCLEAR", "INSUFFICIENT", "EXCLUDED"}
SUBSTANTIVE_LABELS = {"FIRST", "SECOND", "THIRD", "ALTERNATING"}
CONFIDENCES = {"high", "med", "CONFLICT", ""}
TIERS = {"A", "B", "C", "D"}
SCOPES = {"whole_book", "named_section", "opening", "interior", "unknown"}
WEB_SUPPORTS = {"FIRST", "SECOND", "THIRD", "ALTERNATING", "none"}

CORE_KEYS = {
    "schema_version", "sample_id", "quotes", "person_label", "person_confidence",
    "web_evidence", "search_log", "person_note",
}
QUOTE_KEYS = {"quote_id", "person_signal", "note"}
WEB_KEYS = {"url", "title", "tier", "scope", "supports", "note"}


class ValidationError(ValueError):
    """A staged person-classification result is structurally invalid."""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S_person_sol_medium")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(sample_id: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9._-]+", "_", sample_id).strip("_")[:96] or "book"
    suffix = hashlib.sha256(sample_id.encode("utf-8")).hexdigest()[:10]
    return f"{readable}_{suffix}"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_sources(
    books_path: Path,
    quotes_path: Path,
) -> tuple[list[dict[str, str]], dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    books = read_csv(books_path)
    quotes = read_csv(quotes_path)
    if not books or "sample_id" not in books[0]:
        raise SystemExit(f"books input lacks sample_id rows: {books_path}")
    if quotes and not {"sample_id", "quote_id", "quote_text"}.issubset(quotes[0]):
        raise SystemExit(f"quotes input lacks sample_id/quote_id/quote_text: {quotes_path}")

    by_id: dict[str, dict[str, str]] = {}
    for book in books:
        sample_id = book.get("sample_id", "")
        if not sample_id:
            raise SystemExit(f"blank sample_id in {books_path}")
        if sample_id in by_id:
            raise SystemExit(f"duplicate book sample_id in {books_path}: {sample_id}")
        by_id[sample_id] = book

    by_book: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_quote_ids: dict[str, set[str]] = defaultdict(set)
    for quote in quotes:
        sample_id = quote.get("sample_id", "")
        quote_id = quote.get("quote_id", "")
        if sample_id not in by_id:
            raise SystemExit(f"quote references unknown sample_id: {sample_id}")
        if not quote_id or quote_id in seen_quote_ids[sample_id]:
            raise SystemExit(f"blank or duplicate quote_id for {sample_id}: {quote_id!r}")
        seen_quote_ids[sample_id].add(quote_id)
        by_book[sample_id].append(quote)
    return books, by_id, by_book


def sample_ids_from_file(path: Path) -> list[str]:
    if not path.exists():
        raise SystemExit(f"missing sample file: {path}")
    if path.suffix.lower() == ".csv":
        rows = read_csv(path)
        if rows and "sample_id" not in rows[0]:
            raise SystemExit(f"CSV sample file needs a sample_id column: {path}")
        return [row["sample_id"].strip() for row in rows if row.get("sample_id", "").strip()]
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def selected_sample_ids(
    args: argparse.Namespace,
    books: list[dict[str, str]],
    by_id: dict[str, dict[str, str]],
    classified_dir: Path,
) -> list[str]:
    if args.all:
        requested = [book["sample_id"] for book in books
                     if not (classified_dir / f"{safe_name(book['sample_id'])}.json").exists()]
    elif getattr(args, "per_year", None) is not None:
        requested = []
        counts: Counter[int] = Counter()
        for book in books:
            try:
                year = int(book.get("year", ""))
            except ValueError:
                continue
            if args.year_from <= year <= args.year_to and counts[year] < args.per_year:
                requested.append(book["sample_id"])
                counts[year] += 1
        short = {year: counts[year] for year in range(args.year_from, args.year_to + 1)
                 if counts[year] < args.per_year}
        if short:
            raise SystemExit(
                f"not enough books for --per-year {args.per_year}; available counts: {short}"
            )
    elif args.sample_file:
        requested = sample_ids_from_file(args.sample_file)
    else:
        requested = args.sample_id or []

    ordered = list(dict.fromkeys(requested))
    if missing := [sample_id for sample_id in ordered if sample_id not in by_id]:
        raise SystemExit(f"sample_ids not found in books input: {missing}")
    existing = [sample_id for sample_id in ordered
                if (classified_dir / f"{safe_name(sample_id)}.json").exists()]
    if existing and not args.all:
        raise SystemExit(f"person classifications already exist: {existing}")
    if args.limit is not None:
        ordered = ordered[:args.limit]
    if not ordered:
        raise SystemExit("no unclassified books selected")
    return ordered


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in rows)


def task_text(book: dict[str, str]) -> str:
    return f"""# Person classification task

Classify the base narrative person of **{book.get('title', '')}** by
**{book.get('author', '')}** ({book.get('year', '')}), sample ID
`{book['sample_id']}`.

Read `PERSON_METHODOLOGY.md`, `PROMPT.md`, `book.json`, and `quotes.csv`.
Use live web search as required. Return exactly one JSON object matching
`result_schema.json`; the harness captures that final object as `results.json`.
Do not edit the input files and do not return prose outside the JSON.
"""


def prepare(args: argparse.Namespace) -> None:
    books_path = args.books_csv.resolve()
    quotes_path = args.quotes_csv.resolve()
    runs_dir = args.runs_dir.resolve()
    classified_dir = args.classified_dir.resolve()
    books, by_id, quotes_by_book = load_sources(books_path, quotes_path)
    sample_ids = selected_sample_ids(args, books, by_id, classified_dir)

    run_id = args.run_id or default_run_id()
    run_dir = runs_dir / run_id
    if run_dir.exists():
        raise SystemExit(f"run already exists: {run_dir}")
    jobs_dir = run_dir / "jobs"
    jobs_dir.mkdir(parents=True)

    shutil.copy2(METHODOLOGY, run_dir / METHODOLOGY.name)
    shutil.copy2(PROMPT, run_dir / PROMPT.name)
    shutil.copy2(SCHEMA, run_dir / SCHEMA.name)

    entries: list[dict[str, Any]] = []
    quote_fields = ["sample_id", "quote_id", "bucket", "tense", "beat_tense", "note", "quote_text"]
    for sample_id in sample_ids:
        book = by_id[sample_id]
        job = jobs_dir / safe_name(sample_id)
        job.mkdir()
        shutil.copy2(run_dir / METHODOLOGY.name, job / METHODOLOGY.name)
        shutil.copy2(run_dir / PROMPT.name, job / PROMPT.name)
        shutil.copy2(run_dir / SCHEMA.name, job / SCHEMA.name)
        book_input = {key: book.get(key, "") for key in ("sample_id", "frame", "year", "title", "author")}
        (job / "book.json").write_text(json.dumps(book_input, indent=2) + "\n", encoding="utf-8")
        write_csv(job / "quotes.csv", quote_fields, quotes_by_book.get(sample_id, []))
        (job / "TASK.md").write_text(task_text(book), encoding="utf-8")
        entries.append({
            "sample_id": sample_id,
            "frame": book.get("frame", ""),
            "year": book.get("year", ""),
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "quote_count": len(quotes_by_book.get(sample_id, [])),
            "quotes_sha256": digest(job / "quotes.csv"),
            "job_dir": str(job),
            "staged_result": str(job / "results.json"),
            "production_output": str(classified_dir / f"{safe_name(sample_id)}.json"),
            "attempts": 0,
            "status": "staged",
            "last_error": "",
        })

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": now_iso(),
        "model": MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "web_search": "live",
        "methodology_sha256": digest(METHODOLOGY),
        "prompt_sha256": digest(PROMPT),
        "result_schema_sha256": digest(SCHEMA),
        "source_books": str(books_path),
        "source_books_sha256": digest(books_path),
        "source_quotes": str(quotes_path),
        "source_quotes_sha256": digest(quotes_path),
        "selection": (
            {
                "mode": "per_year_in_source_order",
                "per_year": args.per_year,
                "year_from": args.year_from,
                "year_to": args.year_to,
            }
            if getattr(args, "per_year", None) is not None
            else {"mode": "all" if args.all else "explicit"}
        ),
        "books": entries,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"staged {len(entries)} books in {run_dir}")


def require_type(value: Any, expected: type, path: str) -> None:
    if not isinstance(value, expected):
        raise ValidationError(f"{path} must be {expected.__name__}")


def validate_payload(payload: dict[str, Any], sample_id: str, expected_quote_ids: list[str]) -> None:
    require_type(payload, dict, "result")
    allowed_keys = CORE_KEYS | {"provenance"}
    if set(payload) - allowed_keys or not CORE_KEYS.issubset(payload):
        raise ValidationError(f"unexpected or missing top-level keys: {sorted(set(payload) ^ CORE_KEYS)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION}")
    if payload["sample_id"] != sample_id:
        raise ValidationError(f"sample_id mismatch: {payload['sample_id']!r} != {sample_id!r}")

    quotes = payload["quotes"]
    require_type(quotes, list, "quotes")
    if [quote.get("quote_id") for quote in quotes if isinstance(quote, dict)] != expected_quote_ids:
        raise ValidationError("quote IDs must be complete, unique, and in input order")
    for index, quote in enumerate(quotes):
        require_type(quote, dict, f"quotes[{index}]")
        if set(quote) != QUOTE_KEYS:
            raise ValidationError(f"quotes[{index}] must contain exactly {sorted(QUOTE_KEYS)}")
        if quote["person_signal"] not in PERSON_SIGNALS:
            raise ValidationError(f"invalid person_signal for {quote['quote_id']}")
        require_type(quote["note"], str, f"quotes[{index}].note")

    label = payload["person_label"]
    confidence = payload["person_confidence"]
    if label not in PERSON_LABELS:
        raise ValidationError(f"invalid person_label: {label!r}")
    if confidence not in CONFIDENCES:
        raise ValidationError(f"invalid person_confidence: {confidence!r}")
    if label in SUBSTANTIVE_LABELS and not confidence:
        raise ValidationError(f"{label} requires confidence")
    if label not in SUBSTANTIVE_LABELS and confidence:
        raise ValidationError(f"{label} must have blank confidence")
    require_type(payload["person_note"], str, "person_note")
    if not payload["person_note"].strip():
        raise ValidationError("person_note must explain the book decision")

    web_evidence = payload["web_evidence"]
    require_type(web_evidence, list, "web_evidence")
    for index, source in enumerate(web_evidence):
        require_type(source, dict, f"web_evidence[{index}]")
        if set(source) != WEB_KEYS:
            raise ValidationError(f"web_evidence[{index}] must contain exactly {sorted(WEB_KEYS)}")
        if not isinstance(source["url"], str) or not source["url"].startswith(("http://", "https://")):
            raise ValidationError(f"web_evidence[{index}].url must be HTTP(S)")
        if not isinstance(source["title"], str) or not source["title"].strip():
            raise ValidationError(f"web_evidence[{index}].title is required")
        if source["tier"] not in TIERS or source["scope"] not in SCOPES:
            raise ValidationError(f"invalid tier or scope in web_evidence[{index}]")
        if source["supports"] not in WEB_SUPPORTS:
            raise ValidationError(f"invalid supports in web_evidence[{index}]")
        if not isinstance(source["note"], str) or not source["note"].strip():
            raise ValidationError(f"web_evidence[{index}].note is required")

    search_log = payload["search_log"]
    require_type(search_log, list, "search_log")
    if not search_log or any(not isinstance(item, str) or not item.strip() for item in search_log):
        raise ValidationError("search_log must record at least one nonblank query or dead end")

    if label in SUBSTANTIVE_LABELS:
        expected_signal = label.lower() if label != "ALTERNATING" else None
        quote_signals = {quote["person_signal"] for quote in quotes}
        quote_support = expected_signal in quote_signals if expected_signal else \
            len(quote_signals & {"first", "second", "third"}) >= 2
        web_support = [source for source in web_evidence
                       if source["supports"] == label and source["tier"] in {"A", "B", "C"}]
        if not quote_support and not web_support:
            raise ValidationError(f"{label} lacks diagnostic quote or web support")
        if confidence == "high":
            strong_web = [source for source in web_support if source["tier"] in {"A", "B"}]
            if not strong_web:
                raise ValidationError("high confidence requires Tier A/B web evidence")
            if not quote_support and len(strong_web) < 2:
                raise ValidationError("high confidence without quote support requires two Tier A/B sources")

    if "provenance" in payload:
        require_type(payload["provenance"], dict, "provenance")


def expected_quote_ids(entry: dict[str, Any]) -> list[str]:
    path = Path(entry["job_dir"]) / "quotes.csv"
    return [row["quote_id"] for row in read_csv(path)]


def result_state(entry: dict[str, Any]) -> tuple[str, str]:
    if entry.get("status") == "promoted" and Path(entry["production_output"]).exists():
        return "promoted", ""
    result = Path(entry["staged_result"])
    if not result.exists():
        return "missing", ""
    try:
        payload = json.loads(result.read_text(encoding="utf-8"))
        validate_payload(payload, entry["sample_id"], expected_quote_ids(entry))
    except (OSError, json.JSONDecodeError, ValidationError, TypeError) as exc:
        return "invalid", str(exc)
    return "valid", ""


def codex_command(
    job: Path,
    codex_bin: str = "codex",
    validation_feedback: str = "",
) -> list[str]:
    instruction = (
        "The user has updated the execution standard to GPT-5.6 Sol with medium reasoning "
        "effort; this supersedes the older model requirement in PERSON_METHODOLOGY.md. "
        "Read TASK.md, PERSON_METHODOLOGY.md, PROMPT.md, book.json, and quotes.csv. "
        "Perform the required live web research. Return only the complete schema-valid JSON object."
    )
    if validation_feedback:
        instruction += (
            " Your previous output was rejected by the deterministic validator for this reason: "
            f"{validation_feedback}. Correct that issue using the methodology and evidence; do not "
            "merely preserve the previous confidence or support claim."
        )
        if "high confidence without quote support requires two Tier A/B sources" in validation_feedback:
            instruction += (
                " Specifically: if quote evidence does not support the final label, high confidence "
                "requires at least two Tier A/B web_evidence entries whose supports field exactly "
                "matches the final label. Component evidence does not count—for example, a THIRD "
                "opening plus one ALTERNATING source is only one ALTERNATING source. If that exact "
                "two-source threshold is not met, use med confidence."
            )
    return [
        codex_bin, "exec", "--skip-git-repo-check", "--ephemeral",
        "-m", MODEL,
        "-c", f'model_reasoning_effort="{REASONING_EFFORT}"',
        "-c", 'web_search="live"',
        "-c", 'tools.web_search={ context_size = "high" }',
        "-s", "read-only",
        "--ignore-user-config", "--ignore-rules",
        "--output-schema", str(job / SCHEMA.name),
        "--output-last-message", str(job / "results.json"),
        instruction,
    ]


def transient_capacity_error(log_text: str) -> str:
    """Return a resumable capacity error without charging a result attempt."""
    if "You've hit your usage limit" in log_text:
        match = re.search(r"try again at ([^.\n]+)", log_text)
        retry = f"; try again at {match.group(1)}" if match else ""
        return f"Codex usage limit reached{retry}"
    return ""


def run_one(entry: dict[str, Any], codex_bin: str, timeout_seconds: int) -> dict[str, Any]:
    job = Path(entry["job_dir"])
    attempt = int(entry.get("attempts", 0)) + 1
    result = Path(entry["staged_result"])
    if result.exists():
        backup = job / f"results.invalid.attempt-{attempt - 1}.json"
        os.replace(result, backup)
    command = codex_command(job, codex_bin, entry.get("last_error", ""))
    log_path = job / f"codex-attempt-{attempt}.log"
    try:
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                command,
                cwd=job,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout_seconds,
            )
        returncode = completed.returncode
    except subprocess.TimeoutExpired:
        with log_path.open("a", encoding="utf-8") as log:
            log.write(f"\nHARNESS TIMEOUT after {timeout_seconds} seconds\n")
        returncode = 124
    except OSError as exc:
        log_path.write_text(str(exc) + "\n", encoding="utf-8")
        returncode = 127
    state, error = result_state({**entry, "attempts": attempt})
    if state == "missing":
        capacity_error = transient_capacity_error(log_path.read_text(encoding="utf-8", errors="replace"))
        if capacity_error:
            return {"sample_id": entry["sample_id"], "attempt": attempt,
                    "state": "deferred", "error": capacity_error, "returncode": returncode}
    return {"sample_id": entry["sample_id"], "attempt": attempt, "state": state,
            "error": error, "returncode": returncode}


def load_manifest(runs_dir: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    manifest_path = runs_dir.resolve() / run_id / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing run manifest: {manifest_path}")
    return manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.person-tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(args: argparse.Namespace) -> None:
    manifest_path, manifest = load_manifest(args.runs_dir, args.run_id)
    entries = {entry["sample_id"]: entry for entry in manifest["books"]}

    while True:
        pending = []
        for entry in manifest["books"]:
            state, error = result_state(entry)
            entry["status"] = state
            entry["last_error"] = error
            if state in {"missing", "invalid"} and int(entry.get("attempts", 0)) < args.max_attempts:
                pending.append(entry)
        save_manifest(manifest_path, manifest)
        if not pending:
            break
        if args.dry_run:
            for entry in pending:
                print(shlex.join(codex_command(Path(entry["job_dir"]), args.codex_bin)))
            return

        capacity_error = ""
        for offset in range(0, len(pending), args.workers):
            wave = pending[offset:offset + args.workers]
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = {
                    executor.submit(
                        run_one, entry, args.codex_bin, args.job_timeout
                    ): entry["sample_id"]
                           for entry in wave}
                for future in as_completed(futures):
                    outcome = future.result()
                    entry = entries[outcome["sample_id"]]
                    if outcome["state"] != "deferred":
                        entry["attempts"] = outcome["attempt"]
                        entry["model"] = MODEL
                        entry["reasoning_effort"] = REASONING_EFFORT
                    entry["status"] = (
                        "missing" if outcome["state"] == "deferred" else outcome["state"]
                    )
                    entry["last_error"] = outcome["error"]
                    entry["last_returncode"] = outcome["returncode"]
                    entry["updated_at"] = now_iso()
                    save_manifest(manifest_path, manifest)
                    print(f"{outcome['state']:8s} {entry['year']} {entry['title']} "
                          f"(attempt {outcome['attempt']}, exit {outcome['returncode']})")
                    if outcome["state"] == "deferred":
                        capacity_error = outcome["error"]
            if capacity_error:
                raise SystemExit(f"batch paused safely: {capacity_error}")

    counts = Counter(result_state(entry)[0] for entry in manifest["books"])
    print(dict(counts))
    failed = [entry for entry in manifest["books"] if result_state(entry)[0] in {"missing", "invalid"}]
    if failed:
        raise SystemExit(f"{len(failed)} jobs did not validate within {args.max_attempts} attempts")


def status(args: argparse.Namespace) -> None:
    _, manifest = load_manifest(args.runs_dir, args.run_id)
    counts: Counter[str] = Counter()
    for entry in manifest["books"]:
        state, error = result_state(entry)
        counts[state] += 1
        suffix = f" — {error}" if error else ""
        print(f"{state:8s} {entry['year']} {entry['title']} ({entry['quote_count']} quotes){suffix}")
    print(dict(counts))


def promote(args: argparse.Namespace) -> None:
    manifest_path, manifest = load_manifest(args.runs_dir, args.run_id)
    failures = [(entry, *result_state(entry)) for entry in manifest["books"]
                if result_state(entry)[0] not in {"valid", "promoted"}]
    if failures:
        detail = [f"{entry['sample_id']}: {state} {error}" for entry, state, error in failures]
        raise SystemExit("cannot promote invalid run:\n" + "\n".join(detail))

    destinations = [Path(entry["production_output"]) for entry in manifest["books"]
                    if entry.get("status") != "promoted"]
    if existing := [str(path) for path in destinations if path.exists()]:
        raise SystemExit(f"refusing to overwrite person classifications: {existing}")
    for path in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)

    promoted = 0
    for entry in manifest["books"]:
        if entry.get("status") == "promoted":
            continue
        source = Path(entry["staged_result"])
        payload = json.loads(source.read_text(encoding="utf-8"))
        validate_payload(payload, entry["sample_id"], expected_quote_ids(entry))
        payload["provenance"] = {
            "run_id": manifest["run_id"],
            "model": entry.get("model", manifest["model"]),
            "reasoning_effort": entry.get("reasoning_effort", manifest["reasoning_effort"]),
            "web_search": manifest["web_search"],
            "classified_at": now_iso(),
            "methodology_sha256": manifest["methodology_sha256"],
            "prompt_sha256": manifest["prompt_sha256"],
            "quotes_sha256": entry["quotes_sha256"],
        }
        destination = Path(entry["production_output"])
        temporary = destination.with_suffix(".json.person-tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        entry["status"] = "promoted"
        entry["promoted_at"] = now_iso()
        entry["output_sha256"] = digest(destination)
        promoted += 1
    save_manifest(manifest_path, manifest)
    print(f"promoted {promoted} books to {Path(manifest['books'][0]['production_output']).parent}")


def write_csv_atomic(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".person-tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def export(args: argparse.Namespace) -> None:
    books, by_id, quotes_by_book = load_sources(args.books_csv.resolve(), args.quotes_csv.resolve())
    results: dict[str, dict[str, Any]] = {}
    for path in sorted(args.classified_dir.resolve().glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sample_id = payload.get("sample_id", "")
        if sample_id not in by_id:
            raise SystemExit(f"person result not present in current books input: {sample_id}")
        ids = [row["quote_id"] for row in quotes_by_book.get(sample_id, [])]
        validate_payload(payload, sample_id, ids)
        if sample_id in results:
            raise SystemExit(f"duplicate promoted person result: {sample_id}")
        results[sample_id] = payload

    book_rows: list[dict[str, Any]] = []
    quote_rows: list[dict[str, Any]] = []
    for book in books:
        sample_id = book["sample_id"]
        if sample_id not in results:
            continue
        payload = results[sample_id]
        signals = Counter(quote["person_signal"] for quote in payload["quotes"])
        provenance = payload.get("provenance", {})
        book_rows.append({
            "sample_id": sample_id,
            "frame": book.get("frame", ""),
            "year": book.get("year", ""),
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "tense_label": book.get("raw_label", book.get("label", "")),
            "tense_confidence": book.get("confidence", ""),
            "person_label": payload["person_label"],
            "person_confidence": payload["person_confidence"],
            "person_note": payload["person_note"],
            "n_quotes": len(payload["quotes"]),
            **{f"signal_{signal}": signals[signal] for signal in
               ("first", "second", "third", "unmarked", "non_base", "unclear")},
            "web_evidence_count": len(payload["web_evidence"]),
            "web_evidence_json": json.dumps(payload["web_evidence"], ensure_ascii=False),
            "search_log_json": json.dumps(payload["search_log"], ensure_ascii=False),
            "model": provenance.get("model", ""),
            "reasoning_effort": provenance.get("reasoning_effort", ""),
            "run_id": provenance.get("run_id", ""),
        })
        signal_by_id = {quote["quote_id"]: quote for quote in payload["quotes"]}
        for source_quote in quotes_by_book.get(sample_id, []):
            signal = signal_by_id[source_quote["quote_id"]]
            quote_rows.append({
                "sample_id": sample_id,
                "frame": book.get("frame", ""),
                "year": book.get("year", ""),
                "title": book.get("title", ""),
                "quote_id": source_quote["quote_id"],
                "bucket": source_quote.get("bucket", ""),
                "tense": source_quote.get("tense", ""),
                "beat_tense": source_quote.get("beat_tense", ""),
                "person_signal": signal["person_signal"],
                "person_note": signal["note"],
                "quote_text": source_quote.get("quote_text", ""),
            })

    book_fields = [
        "sample_id", "frame", "year", "title", "author", "tense_label", "tense_confidence",
        "person_label", "person_confidence", "person_note", "n_quotes",
        "signal_first", "signal_second", "signal_third", "signal_unmarked",
        "signal_non_base", "signal_unclear", "web_evidence_count", "web_evidence_json",
        "search_log_json", "model", "reasoning_effort", "run_id",
    ]
    quote_fields = [
        "sample_id", "frame", "year", "title", "quote_id", "bucket", "tense",
        "beat_tense", "person_signal", "person_note", "quote_text",
    ]
    out_dir = args.out_dir.resolve()
    write_csv_atomic(out_dir / "person_books.csv", book_fields, book_rows)
    write_csv_atomic(out_dir / "person_quotes.csv", quote_fields, quote_rows)
    print(f"wrote {out_dir / 'person_books.csv'} ({len(book_rows)} books)")
    print(f"wrote {out_dir / 'person_quotes.csv'} ({len(quote_rows)} quotes)")


def batch(args: argparse.Namespace) -> None:
    """Run prepare -> classify -> promote -> export as one guarded bulk command."""
    prepare(args)
    run(argparse.Namespace(
        run_id=args.run_id,
        runs_dir=args.runs_dir,
        workers=args.workers,
        max_attempts=args.max_attempts,
        codex_bin=args.codex_bin,
        job_timeout=args.job_timeout,
        dry_run=False,
    ))
    promote(argparse.Namespace(run_id=args.run_id, runs_dir=args.runs_dir))
    if not args.skip_export:
        export(argparse.Namespace(
            books_csv=args.books_csv,
            quotes_csv=args.quotes_csv,
            classified_dir=args.classified_dir,
            out_dir=args.out_dir,
        ))


def add_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--books-csv", type=Path, default=DEFAULT_BOOKS)
    parser.add_argument("--quotes-csv", type=Path, default=DEFAULT_QUOTES)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="stage an immutable bulk run")
    add_source_args(prepare_parser)
    selection = prepare_parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true", help="all books without promoted person output")
    selection.add_argument("--sample-id", action="append", help="repeat for specific books")
    selection.add_argument("--sample-file", type=Path, help="text IDs or CSV with sample_id")
    selection.add_argument(
        "--per-year", type=int, metavar="N",
        help="first N books per year in source order (requires --year-from/--year-to)",
    )
    prepare_parser.add_argument("--year-from", type=int)
    prepare_parser.add_argument("--year-to", type=int)
    prepare_parser.add_argument("--limit", type=int)
    prepare_parser.add_argument("--run-id")
    prepare_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    prepare_parser.add_argument("--classified-dir", type=Path, default=DEFAULT_CLASSIFIED)
    prepare_parser.set_defaults(func=prepare)

    run_parser = subparsers.add_parser("run", help="run all missing/invalid jobs")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    run_parser.add_argument("--workers", type=int, default=1)
    run_parser.add_argument("--max-attempts", type=int, default=2)
    run_parser.add_argument("--codex-bin", default="codex")
    run_parser.add_argument(
        "--job-timeout", type=int, default=900,
        help="maximum seconds for one Codex job before it is stopped (default: 900)",
    )
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.set_defaults(func=run)

    status_parser = subparsers.add_parser("status", help="validate and summarize a staged run")
    status_parser.add_argument("--run-id", required=True)
    status_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    status_parser.set_defaults(func=status)

    promote_parser = subparsers.add_parser("promote", help="atomically publish a valid run")
    promote_parser.add_argument("--run-id", required=True)
    promote_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    promote_parser.set_defaults(func=promote)

    export_parser = subparsers.add_parser("export", help="build flat person book/quote CSVs")
    add_source_args(export_parser)
    export_parser.add_argument("--classified-dir", type=Path, default=DEFAULT_CLASSIFIED)
    export_parser.add_argument("--out-dir", type=Path, default=DEFAULT_EXPORT)
    export_parser.set_defaults(func=export)

    batch_parser = subparsers.add_parser(
        "batch", help="prepare, run, promote, and export in one command"
    )
    add_source_args(batch_parser)
    batch_selection = batch_parser.add_mutually_exclusive_group(required=True)
    batch_selection.add_argument("--all", action="store_true")
    batch_selection.add_argument("--sample-id", action="append")
    batch_selection.add_argument("--sample-file", type=Path)
    batch_selection.add_argument("--per-year", type=int, metavar="N")
    batch_parser.add_argument("--year-from", type=int)
    batch_parser.add_argument("--year-to", type=int)
    batch_parser.add_argument("--limit", type=int)
    batch_parser.add_argument("--run-id", required=True)
    batch_parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    batch_parser.add_argument("--classified-dir", type=Path, default=DEFAULT_CLASSIFIED)
    batch_parser.add_argument("--out-dir", type=Path, default=DEFAULT_EXPORT)
    batch_parser.add_argument("--workers", type=int, default=1)
    batch_parser.add_argument("--max-attempts", type=int, default=2)
    batch_parser.add_argument("--codex-bin", default="codex")
    batch_parser.add_argument("--job-timeout", type=int, default=900)
    batch_parser.add_argument("--skip-export", action="store_true")
    batch_parser.set_defaults(func=batch)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if getattr(args, "limit", None) is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if getattr(args, "workers", 1) <= 0 or getattr(args, "max_attempts", 1) <= 0:
        raise SystemExit("--workers and --max-attempts must be positive")
    if getattr(args, "job_timeout", 1) <= 0:
        raise SystemExit("--job-timeout must be positive")
    per_year = getattr(args, "per_year", None)
    year_from = getattr(args, "year_from", None)
    year_to = getattr(args, "year_to", None)
    if per_year is not None:
        if per_year <= 0:
            raise SystemExit("--per-year must be positive")
        if year_from is None or year_to is None:
            raise SystemExit("--per-year requires --year-from and --year-to")
        if year_from > year_to:
            raise SystemExit("--year-from must be no later than --year-to")
    elif year_from is not None or year_to is not None:
        raise SystemExit("--year-from/--year-to require --per-year")
    args.func(args)


if __name__ == "__main__":
    main()
