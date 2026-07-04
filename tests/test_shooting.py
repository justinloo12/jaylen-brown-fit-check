"""Unit tests for the shot-mix pricing helpers used by script 19."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck.features.shooting import (diet_swap_delta, expected_pps,
                                        fg2_pct, pps, three_rate)


class TestPps(unittest.TestCase):
    def test_free_throws_excluded(self):
        # 30 pts with 6 FTM on 20 FGA -> 24 field-goal points / 20 = 1.2.
        self.assertAlmostEqual(pps(30, 6, 20), 1.2)

    def test_zero_fga_is_nan(self):
        self.assertNotEqual(pps(0, 0, 0), pps(0, 0, 0))


class TestFg2Pct(unittest.TestCase):
    def test_splits_out_threes(self):
        # 10/20 overall with 2/8 from three -> 8/12 on twos.
        self.assertAlmostEqual(fg2_pct(10, 2, 20, 8), 8 / 12)

    def test_all_threes_is_nan(self):
        v = fg2_pct(5, 5, 10, 10)
        self.assertNotEqual(v, v)


class TestThreeRate(unittest.TestCase):
    def test_rate(self):
        self.assertAlmostEqual(three_rate(8, 20), 0.4)

    def test_zero_fga_is_nan(self):
        v = three_rate(0, 0)
        self.assertNotEqual(v, v)


class TestExpectedPps(unittest.TestCase):
    def test_the_15x_math(self):
        # A 36% three prices at 1.08; a 50% two at 1.00. A 40/60 mix:
        # 0.4*1.08 + 0.6*1.00 = 1.032.
        self.assertAlmostEqual(expected_pps(0.4, 0.36, 0.50), 1.032)

    def test_all_twos(self):
        self.assertAlmostEqual(expected_pps(0.0, 0.99, 0.55), 1.10)

    def test_all_threes(self):
        self.assertAlmostEqual(expected_pps(1.0, 0.40, 0.10), 1.20)


class TestDietSwapDelta(unittest.TestCase):
    def test_full_transfer(self):
        # 18 FGA/g moving from 1.10 to 1.15 PPS -> +0.9 pts/game.
        self.assertAlmostEqual(diet_swap_delta(18, 1.10, 1.15), 0.9)

    def test_transfer_discount_scales(self):
        self.assertAlmostEqual(diet_swap_delta(18, 1.10, 1.15, 0.5), 0.45)

    def test_downgrade_is_negative(self):
        self.assertLess(diet_swap_delta(18, 1.15, 1.10), 0)


if __name__ == "__main__":
    unittest.main()
