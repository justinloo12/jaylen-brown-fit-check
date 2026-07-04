"""with/without lineup-split tests on a toy lineup frame."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from fitcheck.features.onoff import (parse_lineup_ids,
                                     pair_configuration_split,
                                     with_without_split)

SUBJ, MATE, OTHER = 111, 222, 333


def _lineups():
    # Two lineups with subject+mate, one subject-only, one without subject.
    return pd.DataFrame({
        "GROUP_ID": [f"-{SUBJ}-{MATE}-1-2-3-",
                     f"-{SUBJ}-{MATE}-4-5-6-",
                     f"-{SUBJ}-{OTHER}-7-8-9-",
                     f"-{MATE}-{OTHER}-4-5-6-"],
        "MIN": [100.0, 50.0, 200.0, 80.0],
        "OFF_RATING": [120.0, 110.0, 100.0, 115.0],
        "DEF_RATING": [100.0, 105.0, 105.0, 110.0],
        "NET_RATING": [20.0, 5.0, -5.0, 5.0],
    })


class TestParseLineupIds(unittest.TestCase):
    def test_parses_all_ids(self):
        self.assertEqual(parse_lineup_ids("-111-222-1-2-3-"),
                         {111, 222, 1, 2, 3})


class TestWithWithoutSplit(unittest.TestCase):
    def setUp(self):
        self.out = with_without_split(_lineups(), SUBJ, MATE).set_index("state")

    def test_excludes_subject_off_lineups(self):
        # 80 mate-only minutes must not appear anywhere.
        self.assertAlmostEqual(self.out["MIN"].sum(), 350.0)

    def test_minute_weighted_net(self):
        # with: (20*100 + 5*50) / 150 = 15.0 ; without: -5.0
        self.assertAlmostEqual(self.out.loc["with", "NET_RATING"], 15.0)
        self.assertAlmostEqual(self.out.loc["without", "NET_RATING"], -5.0)

    def test_lineup_counts(self):
        self.assertEqual(self.out.loc["with", "n_lineups"], 2)
        self.assertEqual(self.out.loc["without", "n_lineups"], 1)

    def test_no_shared_minutes_yields_nan(self):
        solo = _lineups().iloc[[2]]  # subject never plays with mate
        out = with_without_split(solo, SUBJ, MATE).set_index("state")
        self.assertTrue(np.isnan(out.loc["with", "NET_RATING"]))


class TestPairConfigurationSplit(unittest.TestCase):
    def setUp(self):
        # Add a lineup with neither player so all four cells are populated.
        frame = pd.concat([_lineups(), pd.DataFrame({
            "GROUP_ID": ["-7-8-9-10-11-"], "MIN": [40.0],
            "OFF_RATING": [90.0], "DEF_RATING": [100.0],
            "NET_RATING": [-10.0],
        })], ignore_index=True)
        self.out = (pair_configuration_split(frame, SUBJ, MATE)
                    .set_index("state"))

    def test_all_minutes_accounted_for(self):
        self.assertAlmostEqual(self.out["MIN"].sum(), 470.0)

    def test_cell_assignment(self):
        self.assertAlmostEqual(self.out.loc["both", "MIN"], 150.0)
        self.assertAlmostEqual(self.out.loc["a_only", "MIN"], 200.0)
        self.assertAlmostEqual(self.out.loc["b_only", "MIN"], 80.0)
        self.assertAlmostEqual(self.out.loc["neither", "MIN"], 40.0)

    def test_minute_weighted_nets(self):
        # both: (20*100 + 5*50)/150 = 15.0 ; single-lineup cells pass through.
        self.assertAlmostEqual(self.out.loc["both", "NET_RATING"], 15.0)
        self.assertAlmostEqual(self.out.loc["a_only", "NET_RATING"], -5.0)
        self.assertAlmostEqual(self.out.loc["b_only", "NET_RATING"], 5.0)
        self.assertAlmostEqual(self.out.loc["neither", "NET_RATING"], -10.0)

    def test_missing_cell_is_nan_row(self):
        out = pair_configuration_split(_lineups(), SUBJ, MATE).set_index("state")
        self.assertTrue(np.isnan(out.loc["neither", "NET_RATING"]))


if __name__ == "__main__":
    unittest.main()
