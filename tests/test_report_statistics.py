import math
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

from build_report import trend, wilson_interval


class ReportStatisticsTests(unittest.TestCase):
    def test_trend_uses_count_weighted_year_center(self):
        rows = (
            [{"year": 2000, "label": "PAST", "frame": "test"}] * 1
            + [{"year": 2001, "label": "PRESENT", "frame": "test"}] * 3
            + [{"year": 2002, "label": "PAST", "frame": "test"}] * 7
        )
        result = trend(rows)

        counts = {2000: (0, 1), 2001: (3, 3), 2002: (0, 7)}
        total_present = sum(present for present, _ in counts.values())
        total = sum(n for _, n in counts.values())
        present_share = total_present / total
        mean_year = sum(year * n for year, (_, n) in counts.items()) / total
        numerator = sum(
            (year - mean_year) * (present - n * present_share)
            for year, (present, n) in counts.items()
        )
        denominator = sum(n * (year - mean_year) ** 2 for year, (_, n) in counts.items())

        self.assertAlmostEqual(result["slope"], numerator / denominator)
        expected_z = numerator / math.sqrt(present_share * (1 - present_share) * denominator)
        self.assertAlmostEqual(result["z"], expected_z)

    def test_wilson_is_non_degenerate_at_extremes(self):
        self.assertAlmostEqual(wilson_interval(0, 1)[1], 0.7934506856, places=9)
        self.assertAlmostEqual(wilson_interval(1, 1)[0], 0.2065493144, places=9)

    def test_wilson_matches_reference_case(self):
        low, high = wilson_interval(10, 25)
        self.assertAlmostEqual(low, 0.2340330238, places=9)
        self.assertAlmostEqual(high, 0.5926054264, places=9)


if __name__ == "__main__":
    unittest.main()
