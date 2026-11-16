import csv
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "carrier_annual_performance.csv"


class TestCarrierAnnualPerformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with DATA.open(newline="") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_expected_coverage(self):
        self.assertEqual(len(self.rows), 28)
        self.assertEqual({int(row["year"]) for row in self.rows}, set(range(2019, 2026)))
        self.assertEqual({row["ticker"] for row in self.rows}, {"AAL", "DAL", "LUV", "UAL"})

    def test_unique_ticker_year(self):
        keys = [(row["ticker"], row["year"]) for row in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_required_financial_values(self):
        for row in self.rows:
            self.assertTrue(row["revenue_usd"])
            self.assertTrue(row["operating_income_usd"])
            self.assertGreater(float(row["revenue_usd"]), 0)

    def test_load_factor_bounds(self):
        for row in self.rows:
            load_factor = float(row["load_factor"])
            self.assertTrue(math.isfinite(load_factor))
            self.assertGreaterEqual(load_factor, 0)
            self.assertLessEqual(load_factor, 1)

    def test_margin_recalculation(self):
        for row in self.rows:
            calculated = float(row["operating_income_usd"]) / float(row["revenue_usd"])
            self.assertAlmostEqual(calculated, float(row["operating_margin"]), places=10)


if __name__ == "__main__":
    unittest.main()

