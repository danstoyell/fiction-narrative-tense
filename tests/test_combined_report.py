import collections
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_combined_report", ROOT / "analysis" / "build_combined_report.py"
)
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


class CombinedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.books = REPORT.load_data()
        cls.eligible = [
            book
            for book in cls.books
            if book["person"] in REPORT.PERSON_LABELS
            and book["tense"] in REPORT.TENSE_LABELS
        ]

    def test_overlap_matches_completed_person_panel(self):
        summary = REPORT.summarize(self.books)
        self.assertEqual(581, len(self.eligible))
        self.assertEqual(len(self.eligible), summary["eligible"])
        self.assertEqual(
            dict(collections.Counter(book["person"] for book in self.eligible)),
            summary["persons"],
        )
        self.assertEqual(
            dict(collections.Counter(book["tense"] for book in self.eligible)),
            summary["tenses"],
        )

    def test_combinations_partition_the_overlap(self):
        summary = REPORT.summarize(self.books)
        self.assertEqual(summary["eligible"], sum(summary["combinations"].values()))

    def test_render_is_standalone_and_has_interactive_area_chart(self):
        page = REPORT.render(self.books)
        self.assertNotIn("<script src=", page)
        self.assertNotIn("<link rel=", page)
        self.assertIn("Interactive stacked area chart", page)
        self.assertIn('id="denominator"', page)
        self.assertIn('value="combined"', page)
        self.assertIn('value="person"', page)
        self.assertIn('value="tense"', page)
        self.assertIn('class="area"', page)
        self.assertIn('id="figTitle"', page)
        self.assertIn('id="figSub"', page)
        self.assertLess(page.index('id="tenseChecks"'), page.index('id="figTitle"'))
        self.assertLess(page.index('id="figTitle"'), page.index('<svg id="chart"'))
        match = re.search(
            r'<script id="data" type="application/json">(.*?)</script>', page, re.DOTALL
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(len(self.books), len(payload["books"]))


if __name__ == "__main__":
    unittest.main()
