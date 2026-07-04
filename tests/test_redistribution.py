"""Unit tests for the wing-redistribution helpers used by script 20."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck.features.projection import usage_rate
from fitcheck.features.shooting import (capped_split, expected_pps,
                                        pps_usage_penalty,
                                        usage_delta_for_volume)


class TestCappedSplit(unittest.TestCase):
    def test_proportional_when_no_cap_binds(self):
        alloc = capped_split(10.0, [3.0, 1.0], [100.0, 100.0])
        self.assertAlmostEqual(alloc[0], 7.5)
        self.assertAlmostEqual(alloc[1], 2.5)

    def test_allocations_sum_to_volume(self):
        # Brown-like case: 21.7 FGA/g over seven weighted slots with caps.
        weights = [14.4, 13.9, 13.8, 7.7, 4.3, 3.9, 3.3]
        caps = [min(4.5, 2.0 * w) for w in weights]
        alloc = capped_split(21.7, weights, caps)
        self.assertAlmostEqual(sum(alloc), 21.7, places=9)

    def test_caps_respected(self):
        weights = [14.4, 13.9, 13.8, 7.7, 4.3, 3.9, 3.3]
        caps = [min(4.5, 2.0 * w) for w in weights]
        for a, c in zip(capped_split(21.7, weights, caps), caps):
            self.assertLessEqual(a, c + 1e-9)

    def test_capped_excess_reflows_to_open_slots(self):
        # Slot 0 wants 8 but is capped at 2; the excess flows to slot 1.
        alloc = capped_split(10.0, [4.0, 1.0], [2.0, 100.0])
        self.assertAlmostEqual(alloc[0], 2.0)
        self.assertAlmostEqual(alloc[1], 8.0)

    def test_volume_beyond_caps_left_unallocated(self):
        alloc = capped_split(10.0, [1.0, 1.0], [3.0, 3.0])
        self.assertAlmostEqual(sum(alloc), 6.0)

    def test_zero_weight_slot_gets_nothing(self):
        alloc = capped_split(6.0, [1.0, 0.0], [10.0, 10.0])
        self.assertAlmostEqual(alloc[0], 6.0)
        self.assertAlmostEqual(alloc[1], 0.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            capped_split(1.0, [1.0], [1.0, 1.0])


class TestUsageDeltaForVolume(unittest.TestCase):
    TEAM = dict(tm_fga=90.0, tm_fta=18.0, tm_tov=12.0, tm_min=240.0)

    def test_matches_differenced_usage_rate(self):
        # Adding volume must shift USG% by exactly the closed-form delta.
        base = usage_rate(14.0, 3.0, 2.0, 34.0, **self.TEAM)
        bumped = usage_rate(14.0 + 3.0, 3.0 + 0.5, 2.0, 34.0, **self.TEAM)
        delta = usage_delta_for_volume(3.0, 0.5, 34.0, **self.TEAM)
        self.assertAlmostEqual(delta, bumped - base, places=9)

    def test_linear_in_extra_volume(self):
        one = usage_delta_for_volume(1.0, 0.0, 30.0, **self.TEAM)
        four = usage_delta_for_volume(4.0, 0.0, 30.0, **self.TEAM)
        self.assertAlmostEqual(four, 4.0 * one)

    def test_zero_minutes_is_nan(self):
        v = usage_delta_for_volume(1.0, 0.0, 0.0, **self.TEAM)
        self.assertNotEqual(v, v)


class TestPpsUsagePenalty(unittest.TestCase):
    def test_two_ts_points_per_pps_point(self):
        # +5 usage points at -0.4 TS pts each = -2 TS pts = -0.04 PPS.
        self.assertAlmostEqual(pps_usage_penalty(5.0, 0.4), 0.04)

    def test_zero_slope_no_penalty(self):
        self.assertAlmostEqual(pps_usage_penalty(7.0, 0.0), 0.0)


class TestRedistributionPricing(unittest.TestCase):
    def test_priced_at_receiver_mix(self):
        # A .800 three-rate receiver at 38%/55% prices redistributed shots
        # at 3*.8*.38 + 2*.2*.55 = 1.132 per shot.
        self.assertAlmostEqual(expected_pps(0.8, 0.38, 0.55), 1.132)

    def test_end_to_end_delta_sign(self):
        # Moving 2 shots from a 1.05 PPS shooter to a 1.132 mix gains
        # 2 * (1.132 - 1.05) = +0.164 pts before discounts.
        gain = 2.0 * (expected_pps(0.8, 0.38, 0.55) - 1.05)
        self.assertAlmostEqual(gain, 0.164)
        self.assertGreater(gain, 0)


if __name__ == "__main__":
    unittest.main()
