"""NBA draft lottery math — exact pick probabilities by lottery seed.

Two regimes, both computed exactly from the official ball-combination counts
(no simulation, no copied odds tables):

  * NEW (2019-present, "flattened"): 4 picks drawn; worst three seeds tied at
    140/1000 combinations. Designed to de-incentivize tanking — which is what
    raises mid-lottery seeds' chances of landing a top pick.
  * OLD (1994-2018): 3 picks drawn; worst seed held 250/1000.

Seeds not drawn receive the remaining picks in inverse-record order, which is
why a seed can fall at most 4 spots (new) / 3 spots (old).

The draw of k winners without replacement over weighted seeds is enumerated
over ordered k-permutations (14P4 = 24,024 terms — trivial).
"""
from __future__ import annotations

from itertools import permutations

import numpy as np
import pandas as pd

# Combinations (out of 1000) by inverse-record seed (1 = worst team).
NEW_COMBOS = [140, 140, 140, 125, 105, 90, 75, 60, 45, 30, 20, 15, 10, 5]
OLD_COMBOS = [250, 199, 156, 119, 88, 63, 43, 28, 17, 11, 8, 7, 6, 5]


def pick_probabilities(combos: list[int], n_drawn: int) -> pd.DataFrame:
    """Exact P(seed s receives pick p) for one lottery regime.

    Returns a 14x14 DataFrame: rows = seed (1..14), cols = pick (1..14).
    """
    n = len(combos)
    w = np.asarray(combos, dtype=float)
    prob = np.zeros((n, n))

    # Enumerate ordered draws of the n_drawn winners.
    for perm in permutations(range(n), n_drawn):
        p, remaining = 1.0, w.sum()
        for seed in perm:
            p *= w[seed] / remaining
            remaining -= w[seed]
        for pick_idx, seed in enumerate(perm):
            prob[seed, pick_idx] += p
        # Non-winners fill picks n_drawn+1..14 in inverse-record order.
        losers = sorted(set(range(n)) - set(perm))
        for offset, seed in enumerate(losers):
            prob[seed, n_drawn + offset] += p

    df = pd.DataFrame(prob,
                      index=pd.RangeIndex(1, n + 1, name="seed"),
                      columns=pd.RangeIndex(1, n + 1, name="pick"))
    assert np.allclose(df.sum(axis=1), 1.0), "rows must be distributions"
    return df


def new_odds() -> pd.DataFrame:
    return pick_probabilities(NEW_COMBOS, n_drawn=4)


def old_odds() -> pd.DataFrame:
    return pick_probabilities(OLD_COMBOS, n_drawn=3)


def top4_odds(odds: pd.DataFrame) -> pd.Series:
    """P(top-4 pick) by seed."""
    return odds.loc[:, 1:4].sum(axis=1)


def expected_value_by_seed(odds: pd.DataFrame, value_by_pick: pd.Series) -> pd.Series:
    """E[value | seed] = sum_p P(pick=p | seed) * value(p).

    ``value_by_pick`` is indexed by pick number (1..14+); e.g. WS/season.
    """
    v = value_by_pick.reindex(odds.columns).astype(float)
    return odds.mul(v, axis=1).sum(axis=1)
