"""Contract feature tests: money parsing and both BRef table shapes."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fitcheck.features.contract import _money_to_float, contract_aav, value_row


class TestMoneyParsing(unittest.TestCase):
    def test_dollar_string(self):
        self.assertEqual(_money_to_float("$53,142,264"), 53_142_264.0)

    def test_nan_passthrough(self):
        self.assertTrue(np.isnan(_money_to_float(np.nan)))

    def test_garbage_is_nan(self):
        self.assertTrue(np.isnan(_money_to_float("TBD")))


class TestContractAAV(unittest.TestCase):
    def test_long_form(self):
        df = pd.DataFrame({
            "Season": ["2024-25", "2025-26", "Career"],
            "Salary": ["$49,205,800", "$53,142,264", "$232,591,618"],
        })
        self.assertEqual(contract_aav(df, "2025-26"), 53_142_264.0)

    def test_long_form_missing_season(self):
        df = pd.DataFrame({"Season": ["2024-25"], "Salary": ["$1,000"]})
        self.assertTrue(np.isnan(contract_aav(df, "2028-29")))

    def test_wide_form(self):
        df = pd.DataFrame({"Team": ["BOS"], "2025-26": ["$53,142,264"]})
        self.assertEqual(contract_aav(df, "2025-26"), 53_142_264.0)

    def test_empty(self):
        self.assertTrue(np.isnan(contract_aav(pd.DataFrame(), "2025-26")))


class TestValueRow(unittest.TestCase):
    def test_cost_per_ws(self):
        row = value_row("Test", "2025-26", 50_000_000,
                        pd.Series({"WS": 5.0, "VORP": 2.0}))
        self.assertEqual(row["cost_per_WS"], 10_000_000)
        self.assertEqual(row["cost_per_VORP"], 25_000_000)

    def test_zero_ws_guard(self):
        row = value_row("Test", "2025-26", 50_000_000,
                        pd.Series({"WS": 0.0, "VORP": -0.5}))
        self.assertTrue(np.isnan(row["cost_per_WS"]))
        self.assertTrue(np.isnan(row["cost_per_VORP"]))


if __name__ == "__main__":
    unittest.main()
