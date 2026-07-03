"""Shot classification and termination-quality tests."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fitcheck.features.shot_profile import (classify_shots, shot_zone_profile,
                                            termination_quality)


def _shots():
    return pd.DataFrame({
        "SHOT_DISTANCE": [1, 10, 18, 25, 3],
        "SHOT_TYPE": ["2PT Field Goal", "2PT Field Goal", "2PT Field Goal",
                      "3PT Field Goal", "2PT Field Goal"],
        "SHOT_ZONE_BASIC": ["Restricted Area", "Mid-Range", "Mid-Range",
                            "Above the Break 3", "Restricted Area"],
        "SHOT_MADE_FLAG": [1, 0, 1, 1, 0],
    })


class TestClassifyShots(unittest.TestCase):
    def setUp(self):
        self.df = classify_shots(_shots())

    def test_zones_are_exclusive_and_exhaustive(self):
        zones = self.df[["is_rim", "is_short_mid", "is_long_two", "is_three"]]
        self.assertTrue((zones.sum(axis=1) == 1).all())

    def test_long_two_threshold(self):
        # 18 ft two -> long two; 10 ft two -> short mid.
        self.assertTrue(self.df.loc[2, "is_long_two"])
        self.assertTrue(self.df.loc[1, "is_short_mid"])

    def test_efficient_zone(self):
        self.assertEqual(self.df["is_efficient_zone"].sum(), 3)  # 2 rim + 1 three


class TestZoneProfile(unittest.TestCase):
    def test_rates_and_efg(self):
        prof = shot_zone_profile(_shots())
        self.assertEqual(prof["FGA"], 5)
        self.assertAlmostEqual(prof["three_rate"], 0.2)
        # eFG = (1 + 1 + 1.5) / 5
        self.assertAlmostEqual(prof["eFG"], 0.7)


class TestTerminationQuality(unittest.TestCase):
    def test_bad_shot_index_is_mean_of_components(self):
        zone = pd.Series({"long_two_rate": 0.10})
        creation = pd.Series({"iso_dribble_rate": 0.50,
                              "contested_rate": 0.40,
                              "late_clock_rate": 0.20})
        out = termination_quality(zone, creation)
        self.assertAlmostEqual(out["bad_shot_index"], np.mean([0.1, 0.5, 0.4, 0.2]))

    def test_missing_components_ignored(self):
        out = termination_quality(pd.Series({"long_two_rate": 0.2}), pd.Series())
        self.assertAlmostEqual(out["bad_shot_index"], 0.2)


if __name__ == "__main__":
    unittest.main()
