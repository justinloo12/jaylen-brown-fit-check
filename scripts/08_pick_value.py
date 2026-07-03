"""Quantify the two first-round picks in the trade return.

Method (all real data, assumptions labeled):
  1. Scrape BRef draft pages for the 2015-2019 classes (careers mature enough
     to measure) and compute average Win Shares per season by draft slot.
  2. A contender's outgoing firsts land late — model picks in the 15-30 range.
  3. Rookie-scale cost for that range is ~$2.5-4.5M/yr (CBA scale); we use a
     $3.5M/yr midpoint over a 4-year deal.
  4. Surplus value = (expected WS on rookie deal x market $/WS) - salary paid,
     where market $/WS is what Boston actually paid Brown per win share.

Outputs:
  * data/processed/pick_value.csv
  * outputs/figures/pick_value.png
"""
from __future__ import annotations

import io
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import bref_scraper as bref

DRAFT_YEARS = [2015, 2016, 2017, 2018, 2019]
PICK_RANGE = (15, 30)          # where a contender's firsts typically land
ROOKIE_DEAL_YEARS = 4
ROOKIE_AAV = 3_500_000         # midpoint of late-first rookie scale (approx.)
BROWN_COST_PER_WS = 7_701_777  # from value_table_2025-26.csv — what BOS paid


def draft_class(year: int) -> pd.DataFrame:
    html = bref._uncomment(bref._fetch_html(
        f"https://www.basketball-reference.com/draft/NBA_{year}.html",
        cache_name=f"draft_{year}"))
    t = BeautifulSoup(html, "lxml").find("table", id="stats")
    df = pd.read_html(io.StringIO(str(t)))[0]
    df.columns = ["_".join(str(x) for x in c if "Unnamed" not in str(x)).strip("_")
                  for c in df.columns]
    df = df.rename(columns={"Advanced_WS": "WS", "Round 1_Player": "Player"})
    df["Pk"] = pd.to_numeric(df["Pk"], errors="coerce")
    df["WS"] = pd.to_numeric(df["WS"], errors="coerce")
    df["Yrs"] = pd.to_numeric(df["Yrs"], errors="coerce")
    df = df.dropna(subset=["Pk"])
    df["draft_year"] = year
    # WS per season played; unplayed busts count as 0 (that's the risk, keep it)
    df["ws_per_yr"] = (df["WS"] / df["Yrs"]).fillna(0.0)
    return df[["draft_year", "Pk", "Player", "WS", "Yrs", "ws_per_yr"]]


def main() -> int:
    frames = [draft_class(y) for y in DRAFT_YEARS]
    picks = pd.concat(frames, ignore_index=True)
    lo, hi = PICK_RANGE
    late = picks[(picks.Pk >= lo) & (picks.Pk <= hi)]

    ws_yr = late["ws_per_yr"].mean()             # expected WS/season, picks 15-30
    hit_rate = (late["ws_per_yr"] >= 2.0).mean() # share who become real rotation+
    bust_rate = (late["ws_per_yr"] < 0.5).mean()

    exp_ws_deal = ws_yr * ROOKIE_DEAL_YEARS
    cost_deal = ROOKIE_AAV * ROOKIE_DEAL_YEARS
    cost_per_ws = cost_deal / exp_ws_deal
    surplus = exp_ws_deal * BROWN_COST_PER_WS - cost_deal

    summary = pd.DataFrame([{
        "sample": f"picks {lo}-{hi}, drafts {DRAFT_YEARS[0]}-{DRAFT_YEARS[-1]}",
        "n_picks": len(late),
        "ws_per_yr": ws_yr,
        "exp_ws_4yr_deal": exp_ws_deal,
        "rookie_cost_4yr": cost_deal,
        "cost_per_ws": cost_per_ws,
        "brown_cost_per_ws": BROWN_COST_PER_WS,
        "surplus_value_per_pick": surplus,
        "surplus_two_picks": 2 * surplus,
        "hit_rate_ws2plus": hit_rate,
        "bust_rate_ws_under_half": bust_rate,
    }])
    summary.to_csv(config.PROCESSED_DIR / "pick_value.csv", index=False)

    # ---- figure: cost per WS, picks vs Brown ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5))

    bars = ax1.bar(["Late 1st\n(rookie deal)", "Jaylen Brown\n(2025-26)"],
                   [cost_per_ws / 1e6, BROWN_COST_PER_WS / 1e6],
                   color=["#27ae60", "#c0392b"], width=0.55)
    for b in bars:
        ax1.annotate(f"${b.get_height():.1f}M", (b.get_x() + b.get_width() / 2,
                     b.get_height()), ha="center", va="bottom",
                     fontsize=12, fontweight="bold")
    ax1.set_ylabel("Cost per Win Share ($M)")
    ax1.set_title("① A late first buys wins ~"
                  f"{BROWN_COST_PER_WS / cost_per_ws:.0f}x cheaper",
                  fontsize=12, fontweight="bold", loc="left")

    binned = picks.groupby(pd.cut(picks.Pk, [0, 5, 14, 30],
                                  labels=["1-5", "6-14", "15-30"]),
                           observed=True)["ws_per_yr"].mean()
    ax2.bar([str(i) for i in binned.index], binned.values,
            color=["#2c7fb8", "#7fb3d3", "#95a5a6"], width=0.55)
    ax2.axhline(ws_yr, color="#27ae60", ls="--", lw=1.2)
    ax2.set_ylabel("Avg WS per season (careers to date)")
    ax2.set_xlabel("Draft slot")
    ax2.set_title("② What draft slots actually produce (2015-19 classes)",
                  fontsize=12, fontweight="bold", loc="left")

    fig.suptitle("Pricing the two first-round picks", fontsize=14,
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    out = config.FIG_DIR / "pick_value.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)

    print(f"picks {lo}-{hi} (n={len(late)}): {ws_yr:.2f} WS/yr, "
          f"~{exp_ws_deal:.1f} WS over rookie deal")
    print(f"cost/WS: picks ${cost_per_ws:,.0f} vs Brown ${BROWN_COST_PER_WS:,.0f}")
    print(f"surplus per pick at Brown's $/WS: ${surplus:,.0f}  "
          f"(two picks: ${2*surplus:,.0f})")
    print(f"hit rate (>=2 WS/yr): {hit_rate:.0%}   bust rate (<0.5): {bust_rate:.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
