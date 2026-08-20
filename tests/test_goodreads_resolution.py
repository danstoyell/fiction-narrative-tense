import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from booktense.goodreads import _rank, title_match


class GoodreadsResolutionTests(unittest.TestCase):
    def test_same_author_wrong_title_is_rejected(self):
        matched, _, reason = title_match("The Rainmaker", "The Client", "John Grisham")
        self.assertFalse(matched)
        self.assertIn("title_mismatch", reason)

    def test_collection_containing_title_is_rejected(self):
        matched, _, reason = title_match(
            "Franny and Zooey",
            "The Catcher in the Rye/Franny and Zooey/Nine Stories/Raise High the Roof Beam",
            "J.D. Salinger",
        )
        self.assertFalse(matched)
        self.assertIn("title_mismatch", reason)

    def test_subtitle_and_author_listing_are_accepted(self):
        self.assertTrue(title_match("Daisy Jones & The Six", "Daisy Jones and The Six")[0])
        self.assertTrue(title_match(
            "Of Mice and Men", "Of Mice and Men Novella by John Steinbeck", "John Steinbeck"
        )[0])

    def test_one_character_title_requires_exact_candidate(self):
        candidates = [
            {"id": "wrong", "title": "The Surf Guru", "author": "Doug Dorst", "ratings": 1000},
            {"id": "right", "title": "S.", "author": "Doug Dorst", "ratings": 100},
        ]
        self.assertEqual([row["id"] for row in _rank(candidates, "S.", "Doug Dorst")], ["right"])


if __name__ == "__main__":
    unittest.main()
