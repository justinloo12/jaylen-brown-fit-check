"""Angle 1 features: does the shot diet fit a movement-3 offense?

Turns raw shot-chart + tracking data into an auditable "possession termination
quality" profile: bad-shot rate, iso frequency, contested rate, late-clock rate,
assisted-make rate, and a self-created score.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from fitcheck import config


# ---------------------------------------------------------------------------
# Shot-chart derived features
# ---------------------------------------------------------------------------
def classify_shots(shots: pd.DataFrame) -> pd.DataFrame:
    """Add shot-type flags to a ShotChartDetail frame.

    Expects columns: SHOT_DISTANCE, SHOT_TYPE, SHOT_ZONE_BASIC, SHOT_MADE_FLAG.
    """
    df = shots.copy()
    dist = df["SHOT_DISTANCE"].astype(float)
    is_three = df["SHOT_TYPE"].str.contains("3PT", na=False)

    df["is_three"] = is_three
    df["is_rim"] = (~is_three) & (dist <= 4)
    df["is_short_mid"] = (~is_three) & (dist > 4) & (dist < config.LONG_TWO_MIN_FT)
    df["is_long_two"] = (~is_three) & (dist >= config.LONG_TWO_MIN_FT)
    # "Healthy" shots in a modern offense: rim + threes. Long twos are the tax.
    df["is_efficient_zone"] = df["is_rim"] | df["is_three"]
    return df


def shot_zone_profile(shots: pd.DataFrame) -> pd.Series:
    """Rate breakdown of where a player's FGA come from."""
    df = classify_shots(shots)
    n = len(df)
    if n == 0:
        return pd.Series(dtype=float)
    return pd.Series({
        "FGA": n,
        "rim_rate": df["is_rim"].mean(),
        "short_mid_rate": df["is_short_mid"].mean(),
        "long_two_rate": df["is_long_two"].mean(),
        "three_rate": df["is_three"].mean(),
        "efficient_zone_rate": df["is_efficient_zone"].mean(),
        "eFG": (df["SHOT_MADE_FLAG"] * np.where(df["is_three"], 1.5, 1.0)).sum()
               / max(n, 1),
    })


# ---------------------------------------------------------------------------
# Tracking-derived "how the shot was created" features
# ---------------------------------------------------------------------------
def _weighted_rate(df: pd.DataFrame, mask: pd.Series, weight_col: str = "FGA") -> float:
    """Share of attempts (weighted by FGA) satisfying a category mask."""
    w = df[weight_col].astype(float)
    total = w.sum()
    return float(w[mask].sum() / total) if total else np.nan


def self_creation_profile(dribble_df: pd.DataFrame,
                          touch_df: pd.DataFrame,
                          defender_df: pd.DataFrame,
                          shotclock_df: pd.DataFrame) -> pd.Series:
    """Combine the four tracking splits into self-creation / bad-shot signals.

    Each input is a PlayerDashPtShots table with a categorical label column and
    an FGA (FGA_FREQUENCY / FGA) column. Column names on stats.nba.com:
      dribble: DRIBBLE_RANGE
      touch:   TOUCH_TIME_RANGE
      defender:CLOSE_DEF_DIST_RANGE
      shotclock: SHOT_CLOCK_RANGE
    We match on label substrings so we're robust to exact bucket text.
    """
    out: dict[str, float] = {}

    if not dribble_df.empty:
        col = "DRIBBLE_RANGE"
        iso_mask = dribble_df[col].str.contains(r"3-6|7\+", regex=True, na=False)
        out["iso_dribble_rate"] = _weighted_rate(dribble_df, iso_mask)
        catch_mask = dribble_df[col].str.contains("0 Dribbles", na=False)
        out["catch_shoot_rate"] = _weighted_rate(dribble_df, catch_mask)

    if not touch_df.empty:
        col = "TOUCH_TIME_RANGE"
        holds_mask = touch_df[col].str.contains(r"6\+", regex=True, na=False)
        out["holds_ball_rate"] = _weighted_rate(touch_df, holds_mask)

    if not defender_df.empty:
        col = "CLOSE_DEF_DIST_RANGE"
        tight_mask = defender_df[col].str.contains(r"0-2|2-4", regex=True, na=False)
        out["contested_rate"] = _weighted_rate(defender_df, tight_mask)

    if not shotclock_df.empty:
        col = "SHOT_CLOCK_RANGE"
        late_mask = shotclock_df[col].str.contains(r"4-0|7-4", regex=True, na=False)
        out["late_clock_rate"] = _weighted_rate(shotclock_df, late_mask)

    return pd.Series(out)


def termination_quality(zone: pd.Series, creation: pd.Series,
                        assisted_make_rate: float | None = None) -> pd.Series:
    """Roll everything into one 'possession termination quality' scorecard.

    A higher `bad_shot_index` = more of the diet is the stuff a movement
    offense is trying to avoid (long twos, contested self-created jumpers).
    """
    parts = pd.concat([zone, creation]).to_dict()
    if assisted_make_rate is not None:
        parts["assisted_make_rate"] = assisted_make_rate

    # Composite bad-shot index: equal-weighted, all "avoid" categories.
    components = [
        parts.get("long_two_rate", np.nan),
        parts.get("iso_dribble_rate", np.nan),
        parts.get("contested_rate", np.nan),
        parts.get("late_clock_rate", np.nan),
    ]
    parts["bad_shot_index"] = float(np.nanmean(components))
    return pd.Series(parts)


def passes_per_touch(passing_df: pd.DataFrame) -> float:
    """Ball-movement proxy: passes made per touch (higher = keeps it moving)."""
    if passing_df.empty:
        return np.nan
    passes = passing_df.get("PASS")
    touches = passing_df.get("TOUCHES") if "TOUCHES" in passing_df else None
    if passes is None:
        return np.nan
    total_passes = float(passes.sum())
    # PlayerDashPtPass rows are per-teammate; touches live on a summary elsewhere.
    if touches is not None and touches.sum():
        return total_passes / float(touches.sum())
    return total_passes  # fall back to raw pass volume if touches absent
