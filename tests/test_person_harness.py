import argparse
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from person.person_harness import (
    SCHEMA,
    ValidationError,
    codex_command,
    export,
    prepare,
    promote,
    safe_name,
    transient_capacity_error,
    validate_payload,
)


def valid_first_payload(sample_id="book:1"):
    return {
        "schema_version": 1,
        "sample_id": sample_id,
        "quotes": [
            {"quote_id": "q1", "person_signal": "first", "note": "Narratorial I."},
            {"quote_id": "q2", "person_signal": "unmarked", "note": "Another character."},
        ],
        "person_label": "FIRST",
        "person_confidence": "high",
        "web_evidence": [
            {
                "url": "https://publisher.example/excerpt",
                "title": "Official excerpt",
                "tier": "A",
                "scope": "interior",
                "supports": "FIRST",
                "note": "Sustained participating narration.",
            }
        ],
        "search_log": ["title author excerpt", "title first person narrator"],
        "person_note": "The participating narrator controls the book.",
    }


def write_csv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class PersonHarnessTests(unittest.TestCase):
    def test_usage_limit_is_a_resumable_capacity_error(self):
        message = (
            "ERROR: You've hit your usage limit. Upgrade or try again at "
            "Aug 26th, 2026 2:06 AM."
        )
        self.assertEqual(
            transient_capacity_error(message),
            "Codex usage limit reached; try again at Aug 26th, 2026 2:06 AM",
        )

    def test_output_schema_types_const_and_enum_fields(self):
        schema = json.loads(SCHEMA.read_text())

        def visit(value):
            if isinstance(value, dict):
                if "const" in value or "enum" in value:
                    self.assertIn("type", value)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(schema)

    def test_validates_supported_high_label(self):
        validate_payload(valid_first_payload(), "book:1", ["q1", "q2"])

    def test_rejects_named_character_as_unsupported_third_label(self):
        payload = valid_first_payload()
        payload["person_label"] = "THIRD"
        payload["person_confidence"] = "med"
        payload["quotes"][0]["person_signal"] = "unmarked"
        payload["web_evidence"][0]["supports"] = "none"
        with self.assertRaisesRegex(ValidationError, "lacks diagnostic"):
            validate_payload(payload, "book:1", ["q1", "q2"])

    def test_rejects_quote_reordering(self):
        with self.assertRaisesRegex(ValidationError, "input order"):
            validate_payload(valid_first_payload(), "book:1", ["q2", "q1"])

    def test_codex_command_pins_sol_medium_and_live_search(self):
        command = codex_command(Path("/tmp/person-job"))
        self.assertIn("gpt-5.6-sol", command)
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn('web_search="live"', command)
        self.assertIn("--output-schema", command)

    def test_codex_command_includes_validation_feedback_on_retry(self):
        command = codex_command(
            Path("/tmp/person-job"), validation_feedback="high confidence requires Tier A/B"
        )
        self.assertIn("high confidence requires Tier A/B", command[-1])

    def test_codex_command_explains_exact_support_for_no_quote_high_retry(self):
        command = codex_command(
            Path("/tmp/person-job"),
            validation_feedback=(
                "high confidence without quote support requires two Tier A/B sources"
            ),
        )
        self.assertIn("supports field exactly matches the final label", command[-1])
        self.assertIn("use med confidence", command[-1])

    def test_safe_name_is_stable_and_collision_resistant(self):
        self.assertEqual(safe_name("top2025:A|B"), safe_name("top2025:A|B"))
        self.assertNotEqual(safe_name("top2025:A|B"), safe_name("top2025:A:B"))

    def test_prepare_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            books = root / "books.csv"
            quotes = root / "quotes.csv"
            runs = root / "runs"
            classified = root / "classified"
            output = root / "output"
            write_csv(
                books,
                ["sample_id", "frame", "year", "title", "author", "raw_label", "confidence"],
                [{
                    "sample_id": "book:1", "frame": "test", "year": "2000",
                    "title": "A Book", "author": "A Writer", "raw_label": "PAST",
                    "confidence": "high",
                }],
            )
            write_csv(
                quotes,
                ["sample_id", "quote_id", "bucket", "tense", "beat_tense", "note", "quote_text"],
                [
                    {"sample_id": "book:1", "quote_id": "q1", "bucket": "event", "tense": "past", "beat_tense": "", "note": "", "quote_text": "I walked."},
                    {"sample_id": "book:1", "quote_id": "q2", "bucket": "event", "tense": "past", "beat_tense": "", "note": "", "quote_text": "Maria followed."},
                ],
            )
            args = argparse.Namespace(
                books_csv=books,
                quotes_csv=quotes,
                all=False,
                sample_id=["book:1"],
                sample_file=None,
                limit=None,
                run_id="test-run",
                runs_dir=runs,
                classified_dir=classified,
            )
            prepare(args)
            manifest = json.loads((runs / "test-run" / "manifest.json").read_text())
            self.assertEqual(manifest["model"], "gpt-5.6-sol")
            self.assertEqual(manifest["reasoning_effort"], "medium")
            self.assertEqual(manifest["web_search"], "live")
            self.assertEqual(manifest["books"][0]["quote_count"], 2)

            classified.mkdir()
            payload = valid_first_payload()
            payload["provenance"] = {
                "run_id": "test-run", "model": "gpt-5.6-sol", "reasoning_effort": "high"
            }
            (classified / f"{safe_name('book:1')}.json").write_text(json.dumps(payload))
            export(argparse.Namespace(
                books_csv=books,
                quotes_csv=quotes,
                classified_dir=classified,
                out_dir=output,
            ))
            with (output / "person_books.csv").open(encoding="utf-8") as file:
                book_rows = list(csv.DictReader(file))
            with (output / "person_quotes.csv").open(encoding="utf-8") as file:
                quote_rows = list(csv.DictReader(file))
            self.assertEqual(book_rows[0]["person_label"], "FIRST")
            self.assertEqual(book_rows[0]["tense_label"], "PAST")
            self.assertEqual([row["person_signal"] for row in quote_rows], ["first", "unmarked"])

    def test_promote_preserves_models_in_resumed_mixed_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "mixed"
            run_dir.mkdir()
            entries = []
            for index in range(2):
                sample_id = f"book:{index}"
                job = run_dir / str(index)
                job.mkdir()
                write_csv(job / "quotes.csv", ["quote_id"],
                          [{"quote_id": "q1"}, {"quote_id": "q2"}])
                result = job / "results.json"
                result.write_text(json.dumps(valid_first_payload(sample_id)))
                entry = {
                    "sample_id": sample_id, "job_dir": str(job),
                    "staged_result": str(result), "status": "valid",
                    "production_output": str(root / "classified" / f"{index}.json"),
                    "quotes_sha256": "quote-hash",
                }
                if index:
                    entry.update(model="gpt-5.6-sol", reasoning_effort="medium")
                entries.append(entry)
            manifest = {
                "run_id": "mixed", "model": "gpt-6-astra",
                "reasoning_effort": "medium", "web_search": "live",
                "methodology_sha256": "method-hash", "prompt_sha256": "prompt-hash",
                "books": entries,
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest))
            promote(argparse.Namespace(run_id="mixed", runs_dir=root))
            for index, model in enumerate(("gpt-6-astra", "gpt-5.6-sol")):
                result = json.loads((root / "classified" / f"{index}.json").read_text())
                self.assertEqual(result["provenance"]["model"], model)
                self.assertEqual(result["provenance"]["reasoning_effort"], "medium")

    def test_prepare_selects_first_n_per_year_in_source_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            books = root / "books.csv"
            quotes = root / "quotes.csv"
            rows = [
                {
                    "sample_id": f"book:{year}:{index}", "frame": "test", "year": str(year),
                    "title": f"Book {year}-{index}", "author": "A Writer",
                    "raw_label": "PAST", "confidence": "high",
                }
                for year in (1999, 2000, 2001) for index in range(3)
            ]
            write_csv(
                books,
                ["sample_id", "frame", "year", "title", "author", "raw_label", "confidence"],
                rows,
            )
            write_csv(
                quotes,
                ["sample_id", "quote_id", "bucket", "tense", "beat_tense", "note", "quote_text"],
                [],
            )
            prepare(argparse.Namespace(
                books_csv=books, quotes_csv=quotes, all=False, sample_id=None,
                sample_file=None, per_year=2, year_from=2000, year_to=2001, limit=None,
                run_id="per-year", runs_dir=root / "runs", classified_dir=root / "classified",
            ))
            manifest = json.loads((root / "runs" / "per-year" / "manifest.json").read_text())
            self.assertEqual(
                [book["sample_id"] for book in manifest["books"]],
                ["book:2000:0", "book:2000:1", "book:2001:0", "book:2001:1"],
            )
            self.assertEqual(manifest["selection"]["mode"], "per_year_in_source_order")


if __name__ == "__main__":
    unittest.main()
