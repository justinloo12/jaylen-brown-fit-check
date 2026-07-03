"""Validate the exact lottery math against published anchor values."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np

from fitcheck.models.lottery import new_odds, old_odds, top4_odds


class TestNewLottery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.odds = new_odds()

    def test_rows_are_distributions(self):
        self.assertTrue(np.allclose(self.odds.sum(axis=1), 1.0))

    def test_seed1_first_pick_is_14pct(self):
        # 140/1000 by construction; the enumeration must reproduce it exactly.
        self.assertAlmostEqual(self.odds.loc[1, 1], 0.140, places=3)

    def test_worst_three_seeds_tied(self):
        self.assertAlmostEqual(self.odds.loc[1, 1], self.odds.loc[2, 1], places=12)
        self.assertAlmostEqual(self.odds.loc[2, 1], self.odds.loc[3, 1], places=12)

    def test_seed1_top4_anchor(self):
        # Published NBA figure: 52.1%
        self.assertAlmostEqual(top4_odds(self.odds).loc[1], 0.521, places=3)

    def test_seed14_anchors(self):
        # Published: 0.5% first pick, 2.4% top-4
        self.assertAlmostEqual(self.odds.loc[14, 1], 0.005, places=3)
        self.assertAlmostEqual(top4_odds(self.odds).loc[14], 0.024, places=3)

    def test_seed1_cannot_fall_past_pick5(self):
        # 4 drawn picks -> a seed falls at most 4 spots.
        self.assertEqual(self.odds.loc[1, 6:].sum(), 0.0)
        self.assertGreater(self.odds.loc[1, 5], 0.0)


class TestOldLottery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.odds = old_odds()

    def test_seed1_first_pick_25pct(self):
        self.assertAlmostEqual(self.odds.loc[1, 1], 0.250, places=3)

    def test_seed1_cannot_fall_past_pick4(self):
        self.assertEqual(self.odds.loc[1, 5:].sum(), 0.0)

    def test_reform_flattened_the_top(self):
        # The whole point of the 2019 reform: worse odds for the worst team,
        # better top-pick access for mid seeds.
        new = new_odds()
        self.assertLess(new.loc[1, 1], self.odds.loc[1, 1])
        self.assertGreater(top4_odds(new).loc[8], 3 * self.odds.loc[8, 1])


if __name__ == "__main__":
    unittest.main()
