"""Pure helpers for the three-point identity analysis (script 19).

Shot-mix pricing lives here so the diet-swap projection is auditable and
unit-tested. Nothing in this module touches the network.

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
