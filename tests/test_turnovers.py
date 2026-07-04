"""Live-ball turnover classification / points-off walks on toy PBP frames."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd

from fitcheck.features.turnovers import (clock_seconds, is_live_ball,
                                         points_off_turnover,
                                         summarize_ledger, turnover_ledger)

US, THEM = 10, 20          # our team id, opponent team id
P_STAR, P_OPP = 1, 2       # our player, their player


def _row(action, clock, *, team=0, person=0, desc="", sub="",
         sh="", sa="", period=1):
    return {"actionType": action, "subType": sub, "description": desc,
            "clock": clock, "period": period, "teamId": team,
            "personId": person, "scoreHome": sh, "scoreAway": sa}


def _frame(rows):
    return pd.DataFrame(rows)


def _steal_sequence(*, elapsed=6.0, opp_points=2, and_one=False):
    """TO by our star at 10:00, steal, opponent attempt `elapsed` sec later."""
    rows = [
        _row("period", "PT12M00.00S", sub="start"),
        _row("Turnover", "PT10M00.00S", team=US, person=P_STAR,
             desc="Star Lost Ball Turnover", sub="Lost Ball"),
        _row("", "PT10M00.00S", team=THEM, person=P_OPP,
             desc="Opp STEAL (1 STL)"),
    ]
    attempt_clock_s = 600.0 - elapsed
    m, s = int(attempt_clock_s // 60), attempt_clock_s % 60
    clk = f"PT{m:02d}M{s:05.2f}S"
    if opp_points:
        rows.append(_row("Made Shot", clk, team=THEM, person=P_OPP,
                         desc="Opp Layup (2 PTS)", sa=str(opp_points)))
        if and_one:
            rows.append(_row("Free Throw", clk, team=THEM, person=P_OPP,
                             desc="Opp Free Throw 1 of 1 (3 PTS)",
                             sa=str(opp_points + 1)))
    else:
        rows.append(_row("Missed Shot", clk, team=THEM, person=P_OPP,
                         desc="MISS Opp Jump Shot"))
        rows.append(_row("Rebound", f"PT{m:02d}M{max(s-2, 0):05.2f}S",
                         desc="CELTICS Rebound"))
    rows.append(_row("Made Shot", "PT09M30.00S", team=US, person=P_STAR,
                     desc="Star Jump Shot (2 PTS)", sh="2"))
    return _frame(rows)


class TestClockSeconds(unittest.TestCase):
    def test_parses(self):
        self.assertAlmostEqual(clock_seconds("PT11M29.00S"), 689.0)
        self.assertAlmostEqual(clock_seconds("PT00M03.50S"), 3.5)


class TestIsLiveBall(unittest.TestCase):
    def test_steal_next_row_is_live(self):
        self.assertTrue(is_live_ball(_steal_sequence(), 1))

    def test_dead_ball_without_steal(self):
        pbp = _frame([
            _row("Turnover", "PT10M00.00S", team=US, person=P_STAR,
                 desc="Star Offensive Foul Turnover"),
            _row("Made Shot", "PT09M50.00S", team=THEM, person=P_OPP,
                 desc="Opp Jump Shot (2 PTS)", sa="2"),
        ])
        self.assertFalse(is_live_ball(pbp, 0))

    def test_steal_at_different_clock_not_matched(self):
        pbp = _frame([
            _row("Turnover", "PT10M00.00S", team=US, person=P_STAR,
                 desc="Star Bad Pass Turnover"),
            _row("", "PT08M00.00S", team=THEM, person=P_OPP,
                 desc="Opp STEAL (1 STL)"),
        ])
        self.assertFalse(is_live_ball(pbp, 0))


class TestPointsOffTurnover(unittest.TestCase):
    def test_fast_score_counted(self):
        out = points_off_turnover(_steal_sequence(elapsed=6, opp_points=2), 1,
                                  US, team_is_home=True, team_hint="CELTIC")
        self.assertAlmostEqual(out["points"], 2.0)
        self.assertTrue(out["fast"])

    def test_slow_score_not_fast(self):
        out = points_off_turnover(_steal_sequence(elapsed=15, opp_points=2), 1,
                                  US, team_is_home=True, team_hint="CELTIC")
        self.assertAlmostEqual(out["points"], 2.0)
        self.assertFalse(out["fast"])

    def test_and_one_free_throw_stays_in_window(self):
        out = points_off_turnover(
            _steal_sequence(elapsed=6, opp_points=2, and_one=True), 1,
            US, team_is_home=True, team_hint="CELTIC")
        self.assertAlmostEqual(out["points"], 3.0)

    def test_empty_possession_via_team_rebound(self):
        out = points_off_turnover(_steal_sequence(elapsed=6, opp_points=0), 1,
                                  US, team_is_home=True, team_hint="CELTIC")
        self.assertAlmostEqual(out["points"], 0.0)


class TestLedgerAndSummary(unittest.TestCase):
    def test_ledger_and_summary(self):
        ledger = turnover_ledger(_steal_sequence(elapsed=6, opp_points=2),
                                 US, team_is_home=True, team_hint="CELTIC",
                                 player_id=P_STAR)
        self.assertEqual(len(ledger), 1)
        s = summarize_ledger(ledger)
        self.assertEqual(s["tov"], 1)
        self.assertEqual(s["live"], 1)
        self.assertAlmostEqual(s["pts_against"], 2.0)
        self.assertEqual(s["fast_n"], 1)

    def test_empty_ledger(self):
        s = summarize_ledger(turnover_ledger(
            _steal_sequence(), US, team_is_home=True, team_hint="CELTIC",
            player_id=999))
        self.assertEqual(s["tov"], 0)
        self.assertNotEqual(s["live_share"], s["live_share"])


if __name__ == "__main__":
    unittest.main()
