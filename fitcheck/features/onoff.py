"""Angle 2 features: on/off impact and with-without-teammate lineup splits.

The headline product here is Brown's net-rating swing WITH Tatum vs WITHOUT
Tatum (and White, Holiday), built from 5-man lineup data so we can isolate
"Brown as a lead option" from "Brown next to the primary creator".
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


def parse_lineup_ids(group_id: str) -> set[int]:
    """LeagueDashLineups GROUP_ID looks like '-1627759-1628369-...-'."""
    return {int(x) for x in re.findall(r"\d+", str(group_id))}


def with_without_split(lineups: pd.DataFrame, subject_id: int,
                       teammate_id: int) -> pd.DataFrame:
    """Minute-weighted net rating for subject's lineups, split by whether a
    given teammate is also on the floor.

    Returns a 2-row frame: state in {"with", "without"} with aggregated MIN,
    minute-weighted OFF/DEF/NET rating, and possession share.

    Caveat: minute-weighting net rating across lineups approximates the true
    possession-weighted figure; it's directionally sound for these splits.
    """
    df = lineups.copy()
    ids = df["GROUP_ID"].apply(parse_lineup_ids)
    has_subject = ids.apply(lambda s: subject_id in s)
    has_mate = ids.apply(lambda s: teammate_id in s)

    df = df[has_subject].copy()
    df["state"] = np.where(has_mate[has_subject.values].values, "with", "without")

    def _agg(g: pd.DataFrame) -> pd.Series:
        w = g["MIN"].astype(float)
        tot = w.sum()
        wm = lambda col: float((g[col].astype(float) * w).sum() / tot) if tot else np.nan
        return pd.Series({
            "MIN": tot,
            "OFF_RATING": wm("OFF_RATING"),
            "DEF_RATING": wm("DEF_RATING"),
            "NET_RATING": wm("NET_RATING"),
            "n_lineups": len(g),
        })

    out = df.groupby("state", group_keys=False).apply(_agg, include_groups=False)
    out = out.reindex(["with", "without"])
    total_min = out["MIN"].sum()
    out["min_share"] = out["MIN"] / total_min if total_min else np.nan
    out["net_delta_vs_other"] = out["NET_RATING"] - out["NET_RATING"][::-1].values
    return out.reset_index()


def pair_configuration_split(lineups: pd.DataFrame, a_id: int,
                             b_id: int) -> pd.DataFrame:
    """Full 2x2 lineup configuration matrix for a pair of players.

    Splits ALL of a team's 5-man lineups into four cells — both on the
    floor, only A, only B, neither — and returns one row per cell with
    aggregated MIN and minute-weighted OFF/DEF/NET rating. The "neither"
    cell is the control group: it shows what the supporting cast does with
    no member of the pair on the floor.

    Same caveat as :func:`with_without_split`: minute-weighting across
    lineups approximates the possession-weighted figure.
    """
    df = lineups.copy()
    ids = df["GROUP_ID"].apply(parse_lineup_ids)
    has_a = ids.apply(lambda s: a_id in s).to_numpy()
    has_b = ids.apply(lambda s: b_id in s).to_numpy()
    df["state"] = np.select(
        [has_a & has_b, has_a & ~has_b, ~has_a & has_b],
        ["both", "a_only", "b_only"], default="neither")

    def _agg(g: pd.DataFrame) -> pd.Series:
        w = g["MIN"].astype(float)
        tot = w.sum()
        wm = lambda col: float((g[col].astype(float) * w).sum() / tot) if tot else np.nan
        return pd.Series({
            "MIN": tot,
            "OFF_RATING": wm("OFF_RATING"),
            "DEF_RATING": wm("DEF_RATING"),
            "NET_RATING": wm("NET_RATING"),
            "n_lineups": len(g),
        })

    out = df.groupby("state", group_keys=False).apply(_agg, include_groups=False)
    out = out.reindex(["both", "a_only", "b_only", "neither"])
    total_min = out["MIN"].sum()
    out["min_share"] = out["MIN"] / total_min if total_min else np.nan
    return out.reset_index()


def availability_cells(a_games: set, b_games: set,
                       team_games: set) -> dict[str, set]:
    """Classify a team's games into the four availability cells for a pair.

    ``a_games`` / ``b_games`` are the game IDs each player appeared in;
    ``team_games`` is every game the team played. Returns the 2x2 partition:
    ``both`` / ``a_only`` / ``b_only`` / ``neither``. Player game IDs outside
    ``team_games`` (e.g. games for another franchise) are ignored, so the
    four cells always partition ``team_games`` exactly.
    """
    a = set(a_games) & set(team_games)
    b = set(b_games) & set(team_games)
    return {
        "both": a & b,
        "a_only": a - b,
        "b_only": b - a,
        "neither": set(team_games) - a - b,
    }


def on_off_table(on_off_raw: pd.DataFrame, player_name: str | None = None) -> pd.DataFrame:
    """Tidy the TeamPlayerOnOffDetails stack into on-minus-off deltas per player."""
    df = on_off_raw.copy()
    key = "VS_PLAYER_NAME" if "VS_PLAYER_NAME" in df else "PLAYER_NAME"
    metrics = [c for c in ["OFF_RATING", "DEF_RATING", "NET_RATING"] if c in df]
    wide = df.pivot_table(index=key, columns="COURT_STATUS", values=metrics)
    wide.columns = [f"{m}_{s}" for m, s in wide.columns]
    for m in metrics:
        on, off = f"{m}_ON", f"{m}_OFF"
        if on in wide and off in wide:
            wide[f"{m}_DELTA"] = wide[on] - wide[off]
    wide = wide.reset_index()
    if player_name:
        wide = wide[wide[key] == player_name]
    return wide


def clutch_row(clutch_df: pd.DataFrame, player_id: int) -> pd.Series:
    """Pull one player's clutch line (FG%, TOV, +/-)."""
    row = clutch_df[clutch_df["PLAYER_ID"] == player_id]
    if row.empty:
        return pd.Series(dtype=float)
    keep = [c for c in ["PLAYER_NAME", "GP", "FG_PCT", "FG3_PCT", "TOV",
                        "PLUS_MINUS", "PTS"] if c in row]
    return row[keep].iloc[0]
