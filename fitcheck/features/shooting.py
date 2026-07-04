"""Pure helpers for the three-point identity analyses (scripts 19 and 20).

Shot-mix pricing lives here so the diet-swap and wing-redistribution
projections are auditable and unit-tested. Nothing in this module touches
the network.

Conventions:
  * PPS (points per shot) is measured on FGA only: (PTS - FTM) / FGA.
    Free throws are deliberately excluded — the diet swap re-prices field
    goal attempts; FT generation is a separate (caveated) channel.
  * A "shot mix" is summarized by the 3PT attempt rate (FG3A / FGA); the
    remainder is twos. Expected PPS prices a mix with accuracy by type:
    E[PPS] = r3 * 3 * FG3% + (1 - r3) * 2 * FG2%.
  * FG2% must be computed from the two-point split, not overall FG%:
    FG2% = (FGM - FG3M) / (FGA - FG3A).
"""
from __future__ import annotations


def pps(pts: float, ftm: float, fga: float) -> float:
    """Realized points per field-goal attempt (free throws excluded)."""
    return (pts - ftm) / fga if fga else float("nan")


def fg2_pct(fgm: float, fg3m: float, fga: float, fg3a: float) -> float:
    """Two-point FG% from overall and three-point counting totals."""
    den = fga - fg3a
    return (fgm - fg3m) / den if den else float("nan")


def three_rate(fg3a: float, fga: float) -> float:
    """3PT attempt rate: share of FGA taken from three."""
    return fg3a / fga if fga else float("nan")


def expected_pps(rate3: float, fg3_pct: float, fg2_pct_: float) -> float:
    """Expected points per FGA for a shot mix priced at given accuracy.

    ``rate3`` is the 3PT attempt rate (0-1); ``fg3_pct`` / ``fg2_pct_`` are
    make rates by type (0-1). This is the 1.5x math made explicit: a 36%
    three (1.08 PPS) outscores a 50% two (1.00 PPS).
    """
    return rate3 * 3.0 * fg3_pct + (1.0 - rate3) * 2.0 * fg2_pct_


def diet_swap_delta(fga_pg: float, own_pps: float, target_pps: float,
                    transfer: float = 1.0) -> float:
    """Points-per-game delta from re-pricing a player's shot volume.

    ``fga_pg`` shots per game move from ``own_pps`` to ``target_pps``;
    ``transfer`` (0-1) discounts for the share of that volume the offense
    can actually regenerate at the target mix — self-created shots do not
    convert 1:1 into catch-and-shoot looks someone else must create.
    """
    return fga_pg * (target_pps - own_pps) * transfer


# ---------------------------------------------------------------------------
# Wing-redistribution helpers (script 20)
# ---------------------------------------------------------------------------
def capped_split(volume: float, weights: list[float],
                 caps: list[float]) -> list[float]:
    """Split ``volume`` across slots proportional to ``weights`` with per-slot
    ``caps``, waterfall style: any share a cap refuses re-flows to the still-
    open slots in proportion to their weights, until the volume is placed.

    Returns allocations summing to ``min(volume, sum(caps))`` — if the caps
    cannot absorb everything, the remainder is deliberately left unallocated
    (the caller must notice and say so). Zero-weight or zero-cap slots get 0.
    """
    n = len(weights)
    if n != len(caps):
        raise ValueError("weights and caps must be the same length")
    alloc = [0.0] * n
    remaining = min(volume, sum(caps))
    open_ = [i for i in range(n) if caps[i] > 0 and weights[i] > 0]
    while remaining > 1e-12 and open_:
        wsum = sum(weights[i] for i in open_)
        clamped = [i for i in open_
                   if remaining * weights[i] / wsum >= caps[i] - alloc[i] - 1e-12]
        if not clamped:                      # everyone fits: place and finish
            for i in open_:
                alloc[i] += remaining * weights[i] / wsum
            remaining = 0.0
            break
        for i in clamped:                    # fill the binding slots, loop
            room = caps[i] - alloc[i]
            alloc[i] += room
            remaining -= room
        open_ = [i for i in open_ if i not in clamped]
    return alloc


def usage_delta_for_volume(extra_fga: float, extra_fta: float, minutes: float,
                           tm_fga: float, tm_fta: float, tm_tov: float,
                           tm_min: float) -> float:
    """Usage-point increase from adding shot volume, turnovers held flat.

    This is the standard boxscore USG% formula (see
    ``fitcheck.features.projection.usage_rate``) differenced in its numerator:
    Δusg = 100 * (ΔFGA + 0.44*ΔFTA) * (TmMIN/5) / (MIN * (TmFGA +
    0.44*TmFTA + TmTOV)). All inputs on a consistent time basis (per-game
    values with ``tm_min`` ≈ 240 team minutes work).
    """
    den = minutes * (tm_fga + 0.44 * tm_fta + tm_tov)
    if not den:
        return float("nan")
    return 100.0 * (extra_fga + 0.44 * extra_fta) * (tm_min / 5.0) / den


def pps_usage_penalty(delta_usg: float, ts_slope_per_pt: float) -> float:
    """PPS penalty implied by a usage-driven TS% decline.

    ``ts_slope_per_pt`` is TS *points* lost per +1 usage point (pass a
    positive number from the 0.3-0.6 rule-of-thumb range used by script 16).
    TS is points per two shooting possessions, so a ΔTS of x percentage
    points prices to ≈ 2x/100 points per shot: ΔPPS = 2 * Δusg * slope / 100.
    """
    return 2.0 * delta_usg * ts_slope_per_pt / 100.0
