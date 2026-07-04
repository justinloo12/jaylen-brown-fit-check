"""Live-ball turnover classification and points-off-turnover walks (PBP V3).

Definitions (documented in outputs/live_ball_turnovers.md):
  * LIVE-BALL turnover = a steal was credited on the event. In PlayByPlayV3
    the steal is a separate row immediately after the turnover row (same
    clock) whose description contains "STEAL". Everything else — offensive
    fouls, travels, out-of-bounds, 3-second violations — is dead-ball.
  * POINTS OFF a live-ball turnover = opponent points scored from the steal
    until the turnover team next gains possession (their next shot attempt,
    free throw, turnover, rebound — including team rebounds — or the end of
    the period). Opponent offensive rebounds and and-1 free throws therefore
    stay inside the window, which is the intent.
  * FAST conversion = the opponent's first shot attempt (FG or FT trip)
    comes within ``fast_window`` seconds of the turnover, in the same
    period — the transition/easy-points flag.

All functions are pure frame-walkers so they can be unit-tested on toy
play-by-play frames (tests/test_turnovers.py).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

FAST_WINDOW_SECONDS = 8.0

_POSSESSION_TYPES = {"Made Shot", "Missed Shot", "Free Throw", "Turnover"}
_ATTEMPT_TYPES = {"Made Shot", "Missed Shot", "Free Throw"}


def clock_seconds(clock: str) -> float:
    """'PT11M29.00S' -> seconds remaining in the period."""
    m = re.match(r"PT(\d+)M([\d.]+)S", str(clock))
    if not m:
        return np.nan
    return 60.0 * int(m.group(1)) + float(m.group(2))


def _scores(pbp: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Forward-filled numeric (home, away) running scores."""
    h = pd.to_numeric(pbp["scoreHome"], errors="coerce").ffill().fillna(0)
    a = pd.to_numeric(pbp["scoreAway"], errors="coerce").ffill().fillna(0)
    return h, a


def is_live_ball(pbp: pd.DataFrame, pos: int) -> bool:
    """A turnover at positional index ``pos`` is live-ball iff one of the
    next two rows is a STEAL credited at the same clock."""
    to_clock = pbp.iloc[pos]["clock"]
    for j in range(pos + 1, min(pos + 3, len(pbp))):
        r = pbp.iloc[j]
        if "STEAL" in str(r["description"]).upper() and r["clock"] == to_clock:
            return True
    return False


def _team_regains(row: pd.Series, team_id: int, team_hint: str) -> bool:
    """Does this row mark the turnover team regaining possession?"""
    at = str(row["actionType"])
    if at == "period" and str(row["subType"]) == "end":
        return True
    if int(row["teamId"] or 0) == team_id and at in _POSSESSION_TYPES:
        return True
    if at == "Rebound":
        if int(row["teamId"] or 0) == team_id:
            return True
        # Team rebounds carry teamId 0; the team lives in the description.
        if int(row["teamId"] or 0) == 0 and team_hint.upper() in str(
                row["description"]).upper():
            return True
    return False


def points_off_turnover(pbp: pd.DataFrame, pos: int, team_id: int, *,
                        team_is_home: bool, team_hint: str,
                        fast_window: float = FAST_WINDOW_SECONDS) -> dict:
    """Walk forward from a turnover by ``team_id`` at positional index
    ``pos`` and price the opponent's ensuing possession.

    Returns dict(points=<opponent points before the team regains>,
                 fast=<first opponent attempt within fast_window seconds>).
    """
    home, away = _scores(pbp)
    opp_score = away if team_is_home else home
    to_row = pbp.iloc[pos]
    t0, period = clock_seconds(to_row["clock"]), to_row["period"]
    start_pts = float(opp_score.iloc[pos])

    fast = False
    seen_attempt = False
    end = pos
    for j in range(pos + 1, len(pbp)):
        r = pbp.iloc[j]
        if r["period"] != period or _team_regains(r, team_id, team_hint):
            break
        end = j
        if (not seen_attempt and str(r["actionType"]) in _ATTEMPT_TYPES
                and int(r["teamId"] or 0) != team_id):
            seen_attempt = True
            elapsed = t0 - clock_seconds(r["clock"])
            fast = bool(elapsed <= fast_window)
    points = float(opp_score.iloc[end]) - start_pts
    return {"points": max(points, 0.0), "fast": fast}


def turnover_ledger(pbp: pd.DataFrame, team_id: int, *, team_is_home: bool,
                    team_hint: str, player_id: int | None = None,
                    fast_window: float = FAST_WINDOW_SECONDS) -> pd.DataFrame:
    """One row per turnover committed by ``team_id`` (or by one player on
    it): live/dead classification plus the opponent's points off it.

    Team turnovers (shot-clock etc., personId == 0) are excluded when a
    ``player_id`` is given and included (personId 0) when it is None.
    """
    pbp = pbp.reset_index(drop=True)
    mask = (pbp["actionType"] == "Turnover") & (pbp["teamId"] == team_id)
    if player_id is not None:
        mask &= pbp["personId"] == player_id
    out = []
    for pos in np.flatnonzero(mask.to_numpy()):
        live = is_live_ball(pbp, pos)
        row = {"personId": int(pbp.iloc[pos]["personId"]),
               "period": int(pbp.iloc[pos]["period"]),
               "live_ball": live, "points_against": 0.0, "fast": False}
        if live:
            walk = points_off_turnover(pbp, pos, team_id,
                                       team_is_home=team_is_home,
                                       team_hint=team_hint,
                                       fast_window=fast_window)
            row["points_against"] = walk["points"]
            row["fast"] = walk["fast"]
        out.append(row)
    return pd.DataFrame(out, columns=["personId", "period", "live_ball",
                                      "points_against", "fast"])


def summarize_ledger(ledger: pd.DataFrame) -> dict:
    """Season-level aggregates for one player/team's turnover ledger."""
    if ledger.empty:
        return {"tov": 0, "live": 0, "live_share": np.nan,
                "pts_against": 0.0, "pts_per_live": np.nan,
                "fast_n": 0, "fast_share": np.nan}
    live = ledger[ledger["live_ball"]]
    scored_fast = live[live["fast"] & (live["points_against"] > 0)]
    return {
        "tov": int(len(ledger)),
        "live": int(len(live)),
        "live_share": len(live) / len(ledger),
        "pts_against": float(live["points_against"].sum()),
        "pts_per_live": (float(live["points_against"].mean())
                         if len(live) else np.nan),
        "fast_n": int(len(scored_fast)),
        "fast_share": (len(scored_fast) / len(live)) if len(live) else np.nan,
    }
