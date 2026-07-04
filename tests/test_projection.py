"""Unit tests for the pure projection helpers used by script 16."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck.features.projection import (
    intervals_overlap,
    net_to_wins,
    possessions,
    shrink_gap,
    true_shooting,
    ts_after_usage_shift,
    usage_rate,
    wilson_interval,
)


class TestTrueShooting(unittest.TestCase):
    def test_known_value(self):
        # 30 pts on 20 FGA, 10 FTA: TS = 30 / (2*(20+4.4)) = 0.61475...
        self.assertAlmostEqual(true_shooting(30, 20, 10), 30 / 48.8)

    def test_zero_attempts_is_nan(self):
        self.assertNotEqual(true_shooting(0, 0, 0), true_shooting(0, 0, 0))


class TestUsageRate(unittest.TestCase):
    def test_player_who_is_whole_team(self):
        # One player takes every team true-shot attempt while on the floor
        # the entire game -> usage 100% by construction.
        u = usage_rate(fga=80, fta=20, tov=10, minutes=48,
                       tm_fga=80, tm_fta=20, tm_tov=10, tm_min=240)
        self.assertAlmostEqual(u, 100.0)

    def test_scales_with_share(self):
        # Same floor time, half the true-shot attempts -> 50%.
        u = usage_rate(fga=40, fta=10, tov=5, minutes=48,
                       tm_fga=80, tm_fta=20, tm_tov=10, tm_min=240)
        self.assertAlmostEqual(u, 50.0)

    def test_zero_minutes_is_nan(self):
        u = usage_rate(10, 2, 1, 0, 80, 20, 10, 240)
        self.assertNotEqual(u, u)


class TestPossessions(unittest.TestCase):
    def test_formula(self):
        self.assertAlmostEqual(possessions(fga=90, oreb=10, tov=12, fta=25),
                               90 - 10 + 12 + 0.44 * 25)


class TestNetToWins(unittest.TestCase):
    def test_rule_of_thumb(self):
        self.assertAlmostEqual(net_to_wins(1.0), 2.7)
        self.assertAlmostEqual(net_to_wins(-2.0), -5.4)


class TestShrinkGap(unittest.TestCase):
    def test_default_range(self):
        lo, hi = shrink_gap(4.3)
        self.assertAlmostEqual(lo, 1.72)
        self.assertAlmostEqual(hi, 2.58)

    def test_negative_gap_keeps_order(self):
        lo, hi = shrink_gap(-4.3)
        self.assertLess(lo, hi)
        self.assertAlmostEqual(lo, -2.58)
        self.assertAlmostEqual(hi, -1.72)


class TestWilsonInterval(unittest.TestCase):
    def test_known_value(self):
        # Classic reference case: 8/10 at z=1.96 -> (0.4902, 0.9433).
        lo, hi = wilson_interval(8, 10)
        self.assertAlmostEqual(lo, 0.4902, places=4)
        self.assertAlmostEqual(hi, 0.9433, places=4)

    def test_contains_point_estimate(self):
        lo, hi = wilson_interval(13, 16)
        self.assertLess(lo, 13 / 16)
        self.assertGreater(hi, 13 / 16)

    def test_bounded_at_extremes(self):
        lo, hi = wilson_interval(0, 5)
        self.assertAlmostEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        lo, hi = wilson_interval(5, 5)
        self.assertLess(lo, 1.0)
        self.assertAlmostEqual(hi, 1.0)

    def test_narrows_with_n(self):
        small = wilson_interval(8, 10)
        big = wilson_interval(80, 100)
        self.assertLess(big[1] - big[0], small[1] - small[0])

    def test_zero_n_is_nan(self):
        lo, hi = wilson_interval(0, 0)
        self.assertNotEqual(lo, lo)
        self.assertNotEqual(hi, hi)


class TestIntervalsOverlap(unittest.TestCase):
    def test_overlapping(self):
        self.assertTrue(intervals_overlap((0.5, 0.8), (0.7, 0.9)))

    def test_touching_counts_as_overlap(self):
        self.assertTrue(intervals_overlap((0.5, 0.7), (0.7, 0.9)))

    def test_disjoint(self):
        self.assertFalse(intervals_overlap((0.1, 0.3), (0.4, 0.6)))
        self.assertFalse(intervals_overlap((0.4, 0.6), (0.1, 0.3)))


class TestTsAfterUsageShift(unittest.TestCase):
    def test_midpoint_slope(self):
        # 61.0 TS% at 30 usage -> 32.5 usage at -0.45 TS pts per usage pt:
        # 0.610 - 2.5 * 0.0045 = 0.59875
        self.assertAlmostEqual(
            ts_after_usage_shift(0.610, 30.0, 32.5, 0.45), 0.59875)

    def test_no_shift_no_change(self):
        self.assertAlmostEqual(ts_after_usage_shift(0.6, 30, 30, 0.45), 0.6)


if __name__ == "__main__":
    unittest.main()
