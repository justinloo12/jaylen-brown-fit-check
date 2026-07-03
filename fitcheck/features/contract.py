"""Angle 3 features: contract value model.

Combines BRef Win Shares / VORP with contract AAV and the league cap to produce
cost-per-win-share and cost-per-VORP, then positions Brown against comp wings.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from fitcheck import config


def _money_to_float(x) -> float:
    if pd.isna(x):
        return np.nan
    s = re.sub(r"[^0-9.]", "", str(x))
    return float(s) if s else np.nan


def latest_season_value(adv_df: pd.DataFrame, season: str) -> pd.Series:
    """Pull WS / VORP / BPM for a given season from a BRef advanced table."""
    df = adv_df[adv_df["Season"].astype(str).str.startswith(season[:4])]
    if df.empty:
        return pd.Series(dtype=float)
    row = df.iloc[-1]  # last = combined/total row if multiple teams
    out = {}
    for col in ["WS", "WS/48", "BPM", "VORP", "OWS", "DWS"]:
        if col in row:
            out[col.replace("/", "_")] = pd.to_numeric(row[col], errors="coerce")
    return pd.Series(out)


def contract_aav(contract_df: pd.DataFrame, season: str) -> float:
    """Salary for a given season from a BRef salary/contract table.

    Handles the two BRef shapes:
      * long form — a 'Season' column with one row per year (the Salaries table)
      * wide form — season strings as column headers (the Contracts table)
    """
    if contract_df.empty:
        return np.nan

    # Long form: filter the Season row.
    if "Season" in contract_df.columns:
        sal_col = next((c for c in contract_df.columns
                        if "salary" in str(c).lower()), None)
        if sal_col is not None:
            row = contract_df[contract_df["Season"].astype(str) == season]
            if not row.empty:
                return _money_to_float(row.iloc[0][sal_col])
            return np.nan

    # Wide form: season string is a column header.
    for c in contract_df.columns:
        if season in str(c):
            return _money_to_float(contract_df.iloc[0][c])
    return np.nan


def value_row(name: str, season: str, salary: float,
              value_metrics: pd.Series) -> dict:
    """One player's cost-efficiency row for the comp scatter."""
    cap = config.SALARY_CAP.get(season, np.nan)
    ws = value_metrics.get("WS", np.nan)
    vorp = value_metrics.get("VORP", np.nan)
    return {
        "player": name,
        "season": season,
        "salary": salary,
        "cap_pct": salary / cap if cap and not np.isnan(salary) else np.nan,
        "WS": ws,
        "VORP": vorp,
        "cost_per_WS": salary / ws if ws and ws > 0 else np.nan,
        "cost_per_VORP": salary / vorp if vorp and vorp > 0 else np.nan,
    }


def build_value_table(rows: list[dict]) -> pd.DataFrame:
    """Assemble comp rows and rank cost efficiency (lower cost/WS = better)."""
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["cost_per_WS_rank"] = df["cost_per_WS"].rank()
    df["value_pctile"] = 1 - df["cost_per_WS"].rank(pct=True)  # 1.0 = best value
    return df.sort_values("cost_per_WS").reset_index(drop=True)
