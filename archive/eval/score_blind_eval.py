#!/usr/bin/env python3
"""Score blinded evaluator JSON against a frozen Sonnet production snapshot."""
import csv
import json
from collections import Counter
from pathlib import Path

from analyze_year import label, tally


ROOT = Path(__file__).parent
EVAL = ROOT / "data" / "evals" / "terra_sonnet_blind_20260811"
WORK = Path("/private/tmp/booktense-terra-blind-20260811")


def book_label(record):
    quotes = record["quotes"]
    event_past, event_present, beat_past, beat_present = tally(quotes, "include")
    verse = sum(
        "not prose fiction" in (quote.get("note") or "").lower() for quote in quotes
    ) > len(quotes) / 2
    return label(
        event_past + beat_past,
        event_present + beat_present,
        record.get("narrating_situation", ""),
        verse,
    )[0]


def rate(match, total):
    return f"{match}/{total} ({match / total:.1%})" if total else "n/a"


def job_id(sample_id):
    return "job_" + "".join(char if char.isalnum() else "_" for char in sample_id)


def main():
    manifest = json.loads((EVAL / "manifest.json").read_text(encoding="utf-8"))
    production = {}
    for entry in manifest["books"]:
        snapshot = EVAL / entry["snapshot"]
        production[entry["sample_id"]] = json.loads(snapshot.read_text(encoding="utf-8"))

    deviations = []
    totals = Counter()
    book_results = []
    for entry in manifest["books"]:
        sample_id = entry["sample_id"]
        agent_id = job_id(sample_id)
        result_path = WORK / "jobs" / agent_id / "results.json"
        if not result_path.exists():
            raise SystemExit(f"missing evaluator output: {result_path}")
        results = json.loads(result_path.read_text(encoding="utf-8"))
        if results.get("agent_id") != agent_id:
            raise SystemExit(f"agent ID mismatch in {result_path}")
        if len(results.get("books", [])) != 1:
            raise SystemExit(f"expected one book in {result_path}")
        for candidate in results["books"]:
            if candidate.get("sample_id") != sample_id:
                raise SystemExit(f"wrong sample ID in {result_path}: {candidate.get('sample_id')}")
            reference = production[sample_id]
            reference_quotes = {quote["quote_id"]: quote for quote in reference["quotes"]}
            candidate_quotes = {quote["quote_id"]: quote for quote in candidate.get("quotes", [])}
            if set(reference_quotes) != set(candidate_quotes):
                raise SystemExit(f"quote set mismatch for {sample_id} from {agent_id}")
            for quote_id, reference_quote in reference_quotes.items():
                candidate_quote = candidate_quotes[quote_id]
                totals["quotes"] += 1
                if candidate_quote.get("bucket") == reference_quote.get("bucket"):
                    totals["bucket_match"] += 1
                else:
                    deviations.append({
                        "level": "quote", "agent_id": agent_id, "sample_id": sample_id,
                        "quote_id": quote_id, "field": "bucket",
                        "sonnet": reference_quote.get("bucket", ""),
                        "terra": candidate_quote.get("bucket", ""),
                    })
                if reference_quote.get("bucket") == candidate_quote.get("bucket") == "event":
                    totals["event_tense_comparable"] += 1
                    if candidate_quote.get("tense") == reference_quote.get("tense"):
                        totals["event_tense_match"] += 1
                    else:
                        deviations.append({
                            "level": "quote", "agent_id": agent_id, "sample_id": sample_id,
                            "quote_id": quote_id, "field": "event_tense",
                            "sonnet": reference_quote.get("tense", ""),
                            "terra": candidate_quote.get("tense", ""),
                        })
                if reference_quote.get("bucket") == candidate_quote.get("bucket") == "dialogue":
                    totals["beat_comparable"] += 1
                    if candidate_quote.get("beat_tense") == reference_quote.get("beat_tense"):
                        totals["beat_match"] += 1
                    else:
                        deviations.append({
                            "level": "quote", "agent_id": agent_id, "sample_id": sample_id,
                            "quote_id": quote_id, "field": "beat_tense",
                            "sonnet": reference_quote.get("beat_tense", ""),
                            "terra": candidate_quote.get("beat_tense", ""),
                        })
            sonnet_label = book_label(reference)
            terra_label = book_label(candidate)
            situation_match = candidate.get("narrating_situation") == reference.get("narrating_situation")
            label_match = terra_label == sonnet_label
            totals["books"] += 1
            totals["situation_match"] += situation_match
            totals["label_match"] += label_match
            if not situation_match:
                deviations.append({
                    "level": "book", "agent_id": agent_id, "sample_id": sample_id,
                    "quote_id": "", "field": "narrating_situation",
                    "sonnet": reference.get("narrating_situation", ""),
                    "terra": candidate.get("narrating_situation", ""),
                })
            if not label_match:
                deviations.append({
                    "level": "book", "agent_id": agent_id, "sample_id": sample_id,
                    "quote_id": "", "field": "derived_label",
                    "sonnet": sonnet_label, "terra": terra_label,
                })
            book_results.append({
                "agent_id": agent_id, "sample_id": sample_id,
                "sonnet_situation": reference.get("narrating_situation", ""),
                "terra_situation": candidate.get("narrating_situation", ""),
                "sonnet_label": sonnet_label, "terra_label": terra_label,
            })

    expected = {entry["sample_id"] for entry in manifest["books"]}
    observed = {row["sample_id"] for row in book_results}
    if expected != observed:
        raise SystemExit(f"missing evaluator books: {sorted(expected - observed)}")

    with (EVAL / "book_comparison.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(book_results[0]))
        writer.writeheader()
        writer.writerows(sorted(book_results, key=lambda row: row["sample_id"]))
    with (EVAL / "deviations.csv").open("w", encoding="utf-8", newline="") as file:
        fields = ["level", "agent_id", "sample_id", "quote_id", "field", "sonnet", "terra"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(deviations)
    report = "\n".join([
        "# Terra vs. Sonnet blind evaluation",
        "",
        f"- Bucket agreement: {rate(totals['bucket_match'], totals['quotes'])}",
        f"- Event-tense agreement (when both called event): {rate(totals['event_tense_match'], totals['event_tense_comparable'])}",
        f"- Beat-tense agreement (when both called dialogue): {rate(totals['beat_match'], totals['beat_comparable'])}",
        f"- Narrating-situation agreement: {rate(totals['situation_match'], totals['books'])}",
        f"- Derived book-label agreement: {rate(totals['label_match'], totals['books'])}",
        f"- Explicit deviations: {len(deviations)} (see `deviations.csv`)",
        "",
    ])
    (EVAL / "REPORT.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
