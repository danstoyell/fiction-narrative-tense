import importlib.util
import collections
import copy
import csv
import json
import re
import unittest
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_person_report", ROOT / "analysis" / "build_person_report.py"
)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


class PersonReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.books = REPORT.load_data()

    def test_panel_has_five_eligible_books_per_year(self):
        eligible = [book for book in self.books if book["person"] in REPORT.ELIGIBLE_LABELS]
        for year in range(1996, 2026):
            self.assertGreaterEqual(sum(book["year"] == year for book in eligible), 5, year)
        self.assertGreaterEqual(len(eligible), 150)

    def test_summary_counts_match_reviewed_exports(self):
        summary = REPORT.summarize(self.books)
        in_scope = [
            book for book in self.books
            if book["person"] in REPORT.ELIGIBLE_LABELS
            and book["tense"] in REPORT.SUBSTANTIVE_TENSE_LABELS
        ]
        self.assertEqual(dict(collections.Counter(book["person"] for book in in_scope)), summary["labels"])
        self.assertEqual(
            dict(collections.Counter(book["confidence"] for book in in_scope)),
            summary["confidence"],
        )
        self.assertEqual(len(in_scope), summary["eligible"])
        self.assertEqual(582, summary["target_total"])
        self.assertEqual(1, summary["excluded"])
        self.assertEqual(sum(book["n_quotes"] for book in in_scope), summary["quotes"])

    def test_render_is_standalone_and_embeds_all_records(self):
        page = REPORT.render(self.books)
        self.assertNotIn("<script src=", page)
        self.assertNotIn("<link rel=", page)
        match = re.search(
            r'<script id="data" type="application/json">(.*?)</script>', page, re.DOTALL
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(len(self.books), len(payload["books"]))
        self.assertEqual(
            sum(len(book["quotes"]) for book in self.books),
            sum(len(book["quotes"]) for book in payload["books"]),
        )
        self.assertIn("Narrative person in NYT bestsellers", page)

    def test_abstentions_load_and_stay_out_of_person_denominators(self):
        with REPORT.BOOKS_CSV.open() as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            original = list(reader)
        for label in REPORT.ABSTENTION_LABELS:
            rows = copy.deepcopy(original)
            row = next(r for r in rows if r['person_label'] in REPORT.ELIGIBLE_LABELS
                       and r['tense_label'] in REPORT.SUBSTANTIVE_TENSE_LABELS)
            row['person_label'], row['person_confidence'] = label, ''
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'books.csv'
                with path.open('w', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                loaded = REPORT.load_data(path, REPORT.QUOTES_CSV)
            before, after = REPORT.summarize(self.books), REPORT.summarize(loaded)
            self.assertEqual(after['eligible'], before['eligible'] - 1)
            self.assertEqual(after['abstained_target'], before['abstained_target'] + 1)
            self.assertEqual(after['reviewed_target'], before['reviewed_target'])
            self.assertEqual(sum(after['labels'].values()), after['eligible'])
            page = REPORT.render(loaded)
            self.assertIn('abstentions (unclear or insufficient evidence)', page)
            self.assertIn(label, page)


if __name__ == "__main__":
    unittest.main()
