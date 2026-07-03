"""Trade-return analysis: Paul George (+ two firsts) vs Jaylen Brown.

Answers three questions with real data:
  1. Fit — whose shot diet fits a movement-3 offense better?
  2. Production — what to expect from George vs Brown (WS / VORP / cost-per-WS)?
  3. Cap — what the one-year-earlier contract expiry unlocks.

Outputs:
  * outputs/paul_george_comparison.md
  * outputs/figures/george_vs_brown.png

Runs off cache after the pulls below are warmed once.
"""
from __future__ import annotations

import pathlib
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import bref_scraper as bref
from fitcheck.data import nba_client as nba
from fitcheck.features import contract, shot_profile

PLAYERS = {"Jaylen Brown": (1627759, "brownja02"),
           "Paul George": (202331, "georgpa01")}
RED, BLUE, GREY, GREEN = "#c0392b", "#2c7fb8", "#95a5a6", "#27ae60"


def _money(x) -> float:
    if pd.isna(x):
        return np.nan
    s = re.sub(r"[^0-9.]", "", str(x))
    return float(s) if s else np.nan


# ---------------------------------------------------------------------------
# 1. Fit profile
# ---------------------------------------------------------------------------
def fit_profile(pid: int, season: str) -> pd.Series:
    zone = shot_profile.shot_zone_profile(nba.shot_chart(pid, season))
    creation = shot_profile.self_creation_profile(
        nba.player_tracking_shots(pid, season, split="dribble"),
        nba.player_tracking_shots(pid, season, split="touchtime"),
        nba.player_tracking_shots(pid, season, split="closestdef"),
        nba.player_tracking_shots(pid, season, split="shotclock"),
    )
    return shot_profile.termination_quality(zone, creation)


# ---------------------------------------------------------------------------
# 3. Cap timeline
# ---------------------------------------------------------------------------
def cap_timeline() -> pd.DataFrame:
    rows = {}
    for name, (_pid, slug) in PLAYERS.items():
        fc = bref.future_contract(slug)
        year_cols = [c for c in fc.columns if re.match(r"\d{4}-\d{2}", str(c))]
        rows[name] = {y: _money(fc.iloc[0][y]) for y in year_cols}
    df = pd.DataFrame(rows).sort_index()
    df.index.name = "season"
    return df


def main() -> int:
    seasons = config.SEASONS

    # ---- fit + production ----
    fit_rows, prod_rows = [], []
    for name, (pid, slug) in PLAYERS.items():
        adv = bref.player_advanced(slug)
        for s in seasons:
            fp = fit_profile(pid, s)
            fp = fp.rename(lambda k: k)
            fit_rows.append({"player": name, "season": s, **fp.to_dict()})

            metrics = contract.latest_season_value(adv, s)
            fc = bref.future_contract(slug)
            year_cols = [c for c in fc.columns if str(c) == s]
            salary = _money(fc.iloc[0][year_cols[0]]) if year_cols else np.nan
            prod_rows.append(contract.value_row(name, s, salary, metrics))

    fit_df = pd.DataFrame(fit_rows)
    prod_df = pd.DataFrame(prod_rows)
    fit_df.to_csv(config.PROCESSED_DIR / "george_vs_brown_fit.csv", index=False)
    prod_df.to_csv(config.PROCESSED_DIR / "george_vs_brown_value.csv", index=False)

    cap = cap_timeline()
    cap.to_csv(config.PROCESSED_DIR / "george_vs_brown_cap.csv")

    # ---- figure ----
    _make_figure(fit_df, prod_df, cap)

    # ---- writeup ----
    _write_report(fit_df, prod_df, cap)
    print("Done. See outputs/paul_george_comparison.md and figures/george_vs_brown.png")
    return 0


def _make_figure(fit_df, prod_df, cap) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))

    # Panel A: fit (2025-26) — shorter bars = better fit for the "avoid" metrics
    keys = ["three_rate", "catch_shoot_rate", "iso_dribble_rate", "long_two_rate"]
    labels = ["3PT\nrate", "Catch &\nshoot", "Iso\n(3+ dr)", "Long-2\nrate"]
    ax = axes[0]
    cur = fit_df[fit_df["season"] == "2025-26"].set_index("player")
    x = np.arange(len(keys)); w = 0.38
    ax.bar(x - w/2, [cur.loc["Jaylen Brown", k] for k in keys], w,
           label="Jaylen Brown", color=RED)
    ax.bar(x + w/2, [cur.loc["Paul George", k] for k in keys], w,
           label="Paul George", color=BLUE)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("① Fit: George's diet is more catch-&-shoot, less iso (2025-26)",
                 fontsize=11, fontweight="bold", loc="left")
    ax.set_ylabel("Share of FGA"); ax.legend(fontsize=9)

    # Panel B: production WS both seasons
    ax = axes[1]
    seasons = config.SEASONS
    x = np.arange(len(seasons)); w = 0.38
    b_ws = [prod_df[(prod_df.player=="Jaylen Brown")&(prod_df.season==s)]["WS"].iloc[0] for s in seasons]
    g_ws = [prod_df[(prod_df.player=="Paul George")&(prod_df.season==s)]["WS"].iloc[0] for s in seasons]
    ax.bar(x - w/2, b_ws, w, label="Jaylen Brown", color=RED)
    ax.bar(x + w/2, g_ws, w, label="Paul George", color=BLUE)
    for i,(a,b) in enumerate(zip(b_ws,g_ws)):
        ax.annotate(f"{a:.1f}", (x[i]-w/2, a), ha="center", va="bottom", fontsize=9)
        ax.annotate(f"{b:.1f}", (x[i]+w/2, b), ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(seasons)
    ax.set_title("② Production: Brown out-produces George in raw WS",
                 fontsize=11, fontweight="bold", loc="left")
    ax.set_ylabel("Win Shares"); ax.legend(fontsize=9)

    # Panel C: cap timeline
    ax = axes[2]
    yrs = list(cap.index)
    xb = np.arange(len(yrs))
    brown = cap["Jaylen Brown"].values/1e6
    george = cap["Paul George"].reindex(yrs).values/1e6
    ax.bar(xb - 0.2, brown, 0.38, label="Brown owed", color=RED)
    ax.bar(xb + 0.2, np.nan_to_num(george), 0.38, label="George owed", color=BLUE)
    # highlight the free year
    for i,y in enumerate(yrs):
        if np.isnan(george[i]) and not np.isnan(brown[i]):
            ax.annotate("George:\noff books\n(~$65M free)", (xb[i]+0.2, 2),
                        ha="center", va="bottom", fontsize=8.5, color=GREEN,
                        fontweight="bold")
    ax.set_xticks(xb); ax.set_xticklabels(yrs, fontsize=8, rotation=20)
    ax.set_title("③ Cap: George expires a year earlier",
                 fontsize=11, fontweight="bold", loc="left")
    ax.set_ylabel("Salary owed ($M)"); ax.legend(fontsize=9)

    fig.suptitle("Trade return — Paul George (+2 firsts) vs Jaylen Brown",
                 fontsize=15, fontweight="bold", y=1.03)
    fig.tight_layout()
    out = config.FIG_DIR / "george_vs_brown.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)


def _write_report(fit_df, prod_df, cap) -> None:
    def g(player, season, col):
        r = prod_df[(prod_df.player==player)&(prod_df.season==season)]
        return r[col].iloc[0] if not r.empty else float("nan")
    def f(player, season, col):
        r = fit_df[(fit_df.player==player)&(fit_df.season==season)]
        return r[col].iloc[0] if not r.empty else float("nan")

    brown_free = cap["Jaylen Brown"].dropna().iloc[-1]
    remaining_brown = cap["Jaylen Brown"].loc["2026-27":].sum()
    remaining_george = cap["Paul George"].loc["2026-27":].sum()

    lines = [
        "# Trade Return: Paul George (+ picks) vs Jaylen Brown",
        "",
        "_**The trade is real:** on July 1, 2026 Boston sent Brown to "
        "Philadelphia for George, a 2028 first (may convert to a favorable "
        "swap), a 2031 unprotected first, and two seconds. This brief was "
        "modeled as a hypothetical days earlier with nearly identical terms. "
        "It argues Boston's side on purpose, from real Fit Check pipeline "
        "data, includes a weakest-point section — and note the media "
        "consensus graded the deal for Philadelphia. George's numbers are "
        "his real recent production in Philadelphia._",
        "",
        "## The one-line case",
        "You trade a ball-dominant, iso-heavy, long-contract wing for (a) a "
        "better *stylistic* fit who spaces and defends, (b) **a year of extra "
        "cap flexibility**, and (c) **two first-round picks** — cheap, "
        "controllable, tradeable assets. You lose raw production; you buy fit, "
        "flexibility, and optionality.",
        "",
        "## 1. Fit — George is the cleaner fit for a movement-3 offense",
        "",
        "| Metric (2025-26) | Jaylen Brown | Paul George | Edge |",
        "|---|---|---|---|",
    ]
    for k, lab in [("three_rate","3PT rate"),("catch_shoot_rate","Catch-&-shoot rate"),
                   ("iso_dribble_rate","Iso / 3+ dribble rate"),
                   ("long_two_rate","Long-2 rate"),("contested_rate","Contested rate"),
                   ("bad_shot_index","Bad-shot index")]:
        b, p = f("Jaylen Brown","2025-26",k), f("Paul George","2025-26",k)
        better_low = k in ("iso_dribble_rate","long_two_rate","contested_rate","bad_shot_index")
        edge = "George" if ((p<b) == better_low) else "Brown"
        lines.append(f"| {lab} | {b:.3f} | {p:.3f} | {edge} |")
    lines += [
        "",
        "George takes a higher share of catch-and-shoot looks and fewer "
        "iso/long-two shots — the exact shot mix Boston's system is built to "
        "generate. He plugs into the offense instead of stopping it.",
        "",
        "## 2. Production — expect *less* raw output from George",
        "",
        "| | Brown 24-25 | Brown 25-26 | George 24-25 | George 25-26 |",
        "|---|---|---|---|---|",
        f"| Win Shares | {g('Jaylen Brown','2024-25','WS'):.1f} | "
        f"{g('Jaylen Brown','2025-26','WS'):.1f} | "
        f"{g('Paul George','2024-25','WS'):.1f} | "
        f"{g('Paul George','2025-26','WS'):.1f} |",
        f"| VORP | {g('Jaylen Brown','2024-25','VORP'):.1f} | "
        f"{g('Jaylen Brown','2025-26','VORP'):.1f} | "
        f"{g('Paul George','2024-25','VORP'):.1f} | "
        f"{g('Paul George','2025-26','VORP'):.1f} |",
        "",
        "**Be honest: this is where the trade costs you.** George is 35 and "
        "declining; Brown out-produces him in raw Win Shares and VORP. The case "
        "is *not* 'George is better' — it's 'George is good enough as a "
        "connective piece, and the fit + flexibility + picks clear the bar.'",
        "",
        "## 3. Cap — the year-earlier expiry is the real prize",
        "",
        "| Season | Brown owed | George owed |",
        "|---|---|---|",
    ]
    for s in cap.index:
        b = cap["Jaylen Brown"].get(s, float("nan"))
        p = cap["Paul George"].get(s, float("nan"))
        pstr = f"${p:,.0f}" if not pd.isna(p) else "**— (off books)**"
        lines.append(f"| {s} | ${b:,.0f} | {pstr} |")
    lines += [
        "",
        f"- George is **cheaper every remaining year** and comes **off the books "
        f"a full season earlier**. In 2028-29 Boston owes Brown "
        f"**${brown_free:,.0f}**; it owes George **$0** — an open near-max slot "
        f"to reload, or hard tax relief, a year sooner.",
        f"- Committed dollars from 2026-27 on: Brown **${remaining_brown:,.0f}** "
        f"vs George **${remaining_george:,.0f}** — about "
        f"**${remaining_brown-remaining_george:,.0f} less** locked up.",
        "",
        "## 4. The two first-round picks (the tiebreaker)",
        "- Rookie-scale contracts are the cheapest production in the league; even "
        "average late firsts return positive surplus value (production >> pay) "
        "over four controllable years. _Estimate: ~$3-5M/yr each vs mid-rotation "
        "output = elite cost-per-win, and both are tradeable._",
        "- For a team whose stars eat the cap, cheap controllable talent + trade "
        "ammo is exactly the currency Boston lacks with Brown's deal on the books.",
        "",
        "## Where this argument is weakest",
        "- **Raw talent/production favors Brown**, clearly (§2). If the goal is "
        "'best player in the deal,' Boston loses that line.",
        "- **George's age is a cliff risk** — a 35/36-year-old's decline can be "
        "non-linear; the fit edge means nothing if he can't stay on the floor.",
        "- **Two firsts are a range, not a guarantee** — late picks bust often; "
        "the surplus-value claim is an expectation, not a floor.",
        "- The clean, defensible version of this brief is: **fit + one extra year "
        "of flexibility + two cheap assets**, *accepting* a real production "
        "downgrade — not 'George is the better player.'",
    ]
    out = config.OUTPUT_DIR / "paul_george_comparison.md"
    out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
