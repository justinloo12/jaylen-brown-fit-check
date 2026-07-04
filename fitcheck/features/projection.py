"""Pure helpers for the 'Tatum as sole first option' projection (script 16).

Every formula the projection memo quotes lives here so it can be unit-tested
and audited in one place. Nothing in this module touches the network.

Conventions / sources:
  * True shooting: TS% = PTS / (2 * (FGA + 0.44 * FTA)) — the standard
    free-throw-possession approximation (Basketball-Reference glossary).
  * Usage: the standard boxscore formula (Basketball-Reference glossary):
    USG% = 100 * (FGA + 0.44*FTA + TOV) * (TmMIN / 5)
               / (MIN * (TmFGA + 0.44*TmFTA + TmTOV))
  * Possessions: POSS ≈ FGA - OREB + TOV + 0.44*FTA (team-side estimate).
  * Net-rating-to-wins: ~2.7 wins per point of season net rating over 82
    games — the widely used rule of thumb from Pythagorean-expectation fits.
  * Usage-efficiency tradeoff: roughly −0.3 to −0.6 TS points per +1 usage
    point, a rule-of-thumb range consistent with the skill-curve literature
    (Goldman/Rao and Darryl Blackport's public work). An assumption, not a
    measurement — callers must label it as such.
"""
from __future__ import annotations

WINS_PER_NET_POINT = 2.7  # wins per +1.0 season net rating, 82-game season


def true_shooting(pts: float, fga: float, fta: float) -> float:
    """TS% (as a fraction, e.g. 0.61) from counting totals."""
    denom = 2.0 * (fga + 0.44 * fta)
    return pts / denom if denom else float("nan")


def usage_rate(fga: float, fta: float, tov: float, minutes: float,
               tm_fga: float, tm_fta: float, tm_tov: float,
               tm_min: float) -> float:
    """Standard boxscore USG% (0-100). ``tm_min`` is total team minutes
    (≈ 240 per regulation game across five players)."""
    num = (fga + 0.44 * fta + tov) * (tm_min / 5.0)
    den = minutes * (tm_fga + 0.44 * tm_fta + tm_tov)
    return 100.0 * num / den if den else float("nan")


def possessions(fga: float, oreb: float, tov: float, fta: float) -> float:
    """Team-side possession estimate for a game or a set of games."""
    return fga - oreb + tov + 0.44 * fta


def net_to_wins(net_points: float,
                wins_per_point: float = WINS_PER_NET_POINT) -> float:
    """Convert a season-level net-rating delta into a win delta."""
    return net_points * wins_per_point


def shrink_gap(gap: float, low: float = 0.4, high: float = 0.6) -> tuple[float, float]:
    """Apply a regression discount to a lineup-level net gap.

    Lineup nets are noisier and more contaminated (bench/garbage minutes)
    than season team nets, so we keep only 40-60% of the observed gap.
    Returns (low_estimate, high_estimate) of the surviving team-level gap.
    """
    lo, hi = sorted((gap * low, gap * high))
    return lo, hi


def ts_after_usage_shift(ts0: float, usg0: float, usg1: float,
                         slope_per_usg_pt: float) -> float:
    """Project TS% (fraction) after a usage change.

    ``slope_per_usg_pt`` is TS *points* (percentage points) lost per +1
    usage point — pass a positive number, e.g. 0.45 for the midpoint of the
    0.3-0.6 rule-of-thumb range.
    """
    return ts0 - (usg1 - usg0) * slope_per_usg_pt / 100.0
