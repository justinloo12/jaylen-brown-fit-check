"""Lottery-adjusted pick value: what the two firsts are worth if they convey
from a lottery team under the flattened (2019+) odds.

Chain:
  1. Exact pick distributions by seed, old vs new lottery (fitcheck.models.lottery).
  2. WS/season by draft slot from the scraped 2015-19 classes, smoothed with a
     log-decay fit (per-slot n=5 is noisy; the fit is monotone and labeled).
  3. E[WS/yr | lottery seed] = odds x slot value; convert to rookie-deal
     surplus at Brown's realized $/WS, alongside the late-first baseline.

Outputs:
  * data/processed/lottery_value.csv   (per-seed expected value, old vs new)
  * outputs/figures/lottery_value.png
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
from fitcheck.models import lottery

DRAFT_YEARS = [2015, 2016, 2017, 2018, 2019]
ROOKIE_DEAL_YEARS = 4
BROWN_COST_PER_WS = 7_701_777
LATE_FIRST_WS_YR = 1.69          # scripts/08 baseline, picks 15-30
# Rookie scale rises steeply at the top of the board (approx. AAVs).
ROOKIE_AAV_BY_PICK = {1: 12.5e6, 2: 11.2e6, 3: 10.1e6, 4: 9.1e6, 5: 8.2e6,
                      6: 7.5e6, 7: 6.9e6, 8: 6.3e6, 9: 5.8e6, 10: 5.5e6,
                      11: 5.2e6, 12: 5.0e6, 13: 4.7e6, 14: 4.5e6}


def slot_values() -> tuple[pd.Series, pd.DataFrame]:
    """WS/season by pick 1-30: raw slot means + smoothed log-decay fit."""
    frames = []
    for year in DRAFT_YEARS:
        html = bref._uncomment(bref._fetch_html(
            f"https://www.basketball-reference.com/draft/NBA_{year}.html",
            cache_name=f"draft_{year}"))
        t = BeautifulSoup(html, "lxml").find("table", id="stats")
        df = pd.read_html(io.StringIO(str(t)))[0]
        df.columns = ["_".join(str(x) for x in c if "Unnamed" not in str(x)).strip("_")
                      for c in df.columns]
        df["Pk"] = pd.to_numeric(df["Pk"], errors="coerce")
        df["WS"] = pd.to_numeric(df["Advanced_WS"], errors="coerce")
        df["Yrs"] = pd.to_numeric(df["Yrs"], errors="coerce")
        df = df.dropna(subset=["Pk"])
        df["ws_per_yr"] = (df["WS"] / df["Yrs"]).fillna(0.0)
        frames.append(df[["Pk", "ws_per_yr"]])
    picks = pd.concat(frames, ignore_index=True)
    picks = picks[picks.Pk <= 30]

    # log-decay fit: WS/yr ~ a + b*ln(pick), clipped at 0.
    X = np.log(picks.Pk.values)
    b, a = np.polyfit(X, picks.ws_per_yr.values, 1)
    fitted = pd.Series(
        np.clip(a + b * np.log(np.arange(1, 31)), 0, None),
        index=pd.RangeIndex(1, 31, name="pick"), name="ws_per_yr_fit")
    raw = picks.groupby("Pk")["ws_per_yr"].mean()
    return fitted, pd.DataFrame({"raw": raw, "fit": fitted})


def main() -> int:
    fitted, slot_table = slot_values()
    new = lottery.new_odds()
    old = lottery.old_odds()

    # Sanity anchors vs the published odds everyone can look up.
    p1_new = new.loc[1, 1]
    top4_new, top4_old = lottery.top4_odds(new), lottery.top4_odds(old)
    print(f"sanity: new seed1 P(#1)={p1_new:.3f} (published 0.140), "
          f"seed1 P(top4)={top4_new[1]:.3f} (published 0.521)")
    print(f"        old seed1 P(#1)={old.loc[1, 1]:.3f} (published 0.250)")

    ev_new = lottery.expected_value_by_seed(new, fitted.loc[1:14])
    ev_old = lottery.expected_value_by_seed(old, fitted.loc[1:14])
    exp_cost = lottery.expected_value_by_seed(
        new, pd.Series(ROOKIE_AAV_BY_PICK))

    out = pd.DataFrame({
        "seed": range(1, 15),
        "p_top4_new": top4_new.values,
        "p_top4_old": top4_old.values,
        "exp_ws_yr_new": ev_new.values,
        "exp_ws_yr_old": ev_old.values,
    }).set_index("seed")
    out["exp_ws_rookie_deal"] = out.exp_ws_yr_new * ROOKIE_DEAL_YEARS
    out["exp_rookie_cost_4yr"] = exp_cost.values * ROOKIE_DEAL_YEARS
    out["surplus_at_brown_rate"] = (out.exp_ws_rookie_deal * BROWN_COST_PER_WS
                                    - out.exp_rookie_cost_4yr)
    out.to_csv(config.PROCESSED_DIR / "lottery_value.csv")

    # ---- figure ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))
    seeds = out.index.values

    ax1.plot(seeds, out.p_top4_old * 100, "o--", color="#95a5a6",
             label="Old lottery (top-3 drawn)")
    ax1.plot(seeds, out.p_top4_new * 100, "o-", color="#007a33", lw=2,
             label="New lottery (top-4 drawn)")
    mid = (out.p_top4_new - out.p_top4_old).loc[5:14].idxmax()
    ax1.annotate("flattened odds lift\nthe mid-lottery",
                 (mid, out.p_top4_new[mid] * 100),
                 xytext=(mid + 1.2, out.p_top4_new[mid] * 100 + 12),
                 fontsize=9, color="#007a33", fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#007a33"))
    ax1.set_xlabel("Lottery seed (1 = worst record)")
    ax1.set_ylabel("P(top-4 pick), %")
    ax1.set_title("① Chance of a premium pick, old vs new odds",
                  fontsize=11.5, fontweight="bold", loc="left")
    ax1.legend(fontsize=9)

    ax2.plot(seeds, out.exp_ws_yr_new, "o-", color="#007a33", lw=2,
             label="Lottery pick (new odds)")
    ax2.axhline(LATE_FIRST_WS_YR, color="#c0392b", ls="--", lw=1.6,
                label=f"Late 1st baseline ({LATE_FIRST_WS_YR} WS/yr)")
    ax2.set_xlabel("Lottery seed (1 = worst record)")
    ax2.set_ylabel("Expected WS per season")
    ax2.set_title("② Expected production of the pick, by seed",
                  fontsize=11.5, fontweight="bold", loc="left")
    ax2.legend(fontsize=9)

    fig.suptitle("Lottery-adjusted pick value (exact odds, 2015-19 slot production)",
                 fontsize=13.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    p = config.FIG_DIR / "lottery_value.png"
    fig.savefig(p, dpi=155, bbox_inches="tight")
    plt.close(fig)

    mid_row = out.loc[8]
    print(f"\nseed 8 example: P(top4) {out.p_top4_old[8]:.1%} -> "
          f"{out.p_top4_new[8]:.1%} under new odds; "
          f"E[WS/yr]={mid_row.exp_ws_yr_new:.2f} vs late-1st {LATE_FIRST_WS_YR}")
    print(f"seed 8 surplus at Brown $/WS: ${mid_row.surplus_at_brown_rate:,.0f} "
          f"(late-1st was ~$38M)")
    print("wrote", config.PROCESSED_DIR / "lottery_value.csv", "and", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
