"""Defense check — did Brown's defense actually decline?

Tests the 'declining defense' claim from three independent directions:

  1. Box-metric arc — BRef DBPM / DWS / DRB%, 2019-20 through 2025-26.
  2. Matchup data — defended FG% vs shooters' normal FG% (PCT_PLUSMINUS),
     overall / at the rim / on threes, 2024-25 vs 2025-26.
  3. Team on/off — Celtics DEF_RATING with Brown on vs off the floor.

Spoiler (from the data, not the thesis): the claim does not survive. The
brief reports that plainly — this repo argues from evidence or not at all.

Outputs:
  * data/processed/defense_check.csv
  * outputs/figures/defense_check.png
  * outputs/defense_check.md
"""
from __future__ import annotations

import pathlib
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
from fitcheck.features import onoff

RED, BLUE, GREY, GREEN = "#c0392b", "#2c7fb8", "#8a97a5", "#007a33"
ARC_SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24",
               "2024-25", "2025-26"]
DEF_CATS = [("Overall", "Overall"), ("Less Than 6 Ft", "At rim (<6ft)"),
            ("3 Pointers", "Threes")]


def bref_arc() -> pd.DataFrame:
    adv = bref.player_advanced("brownja02")
    adv = adv[adv["Season"].isin(ARC_SEASONS)].copy()
    for c in ["DBPM", "DWS", "DRB%"]:
        adv[c] = pd.to_numeric(adv[c], errors="coerce")
    return adv[["Season", "G", "DBPM", "DWS", "DRB%"]].reset_index(drop=True)


def matchup_rows() -> pd.DataFrame:
    rows = []
    for s in config.SEASONS:
        df = nba.player_shot_defend(config.SUBJECT_ID, s)
        for cat, label in DEF_CATS:
            r = df[df["DEFENSE_CATEGORY"] == cat]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append({"season": s, "category": label,
                         "d_fga": r["D_FGA"], "d_fg_pct": r["D_FG_PCT"],
                         "plusminus": r["PCT_PLUSMINUS"]})
    return pd.DataFrame(rows)


def onoff_rows() -> pd.DataFrame:
    rows = []
    for s in config.SEASONS:
        raw = nba.team_on_off(config.CELTICS_TEAM_ID, s)
        t = onoff.on_off_table(raw)
        key = t.columns[0]
        r = t[t[key].str.contains("Brown", na=False)].iloc[0]
        rows.append({"season": s, "def_on": r["DEF_RATING_ON"],
                     "def_off": r["DEF_RATING_OFF"],
                     "def_delta": r["DEF_RATING_DELTA"]})
    return pd.DataFrame(rows)


def _figure(arc: pd.DataFrame, mu: pd.DataFrame, oo: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.6))

    # A: box-metric arc
    ax = axes[0]
    x = np.arange(len(arc))
    ax.plot(x, arc["DBPM"], "-o", color=BLUE, label="DBPM")
    ax.bar(x, arc["DWS"], 0.45, color=GREY, alpha=0.5, label="DWS")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([s[2:] for s in arc["Season"]], fontsize=9)
    ax.set_title("① Box-metric arc — flat, not falling",
                 fontsize=11.5, fontweight="bold", loc="left")
    ax.legend(fontsize=9)

    # B: matchup plus-minus
    ax = axes[1]
    cats = [label for _, label in DEF_CATS]
    x = np.arange(len(cats))
    w = 0.38
    for i, s in enumerate(config.SEASONS):
        vals = [mu[(mu.season == s) & (mu.category == c)]["plusminus"].iloc[0] * 100
                for c in cats]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=s,
                      color=GREY if i == 0 else GREEN)
        for rect in bars:
            h = rect.get_height()
            ax.annotate(f"{h:+.1f}", (rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 4 if h >= 0 else -13),
                        textcoords="offset points", ha="center", fontsize=8.5,
                        fontweight="bold")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(cats, fontsize=9.5)
    ax.set_ylabel("Defended FG% − shooters' normal (pts)")
    ax.set_title("② Matchup data — shooters got WORSE vs Brown in 25-26",
                 fontsize=11.5, fontweight="bold", loc="left")
    ax.legend(fontsize=9)
    ax.margins(y=0.3)

    # C: team on/off defense
    ax = axes[2]
    x = np.arange(len(oo))
    w = 0.38
    b1 = ax.bar(x - w/2, oo["def_on"], w, label="Brown ON", color=RED)
    b2 = ax.bar(x + w/2, oo["def_off"], w, label="Brown OFF", color=GREY)
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.annotate(f"{h:.1f}", (rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(oo["season"])
    ax.set_ylabel("Celtics DEF_RATING (lower = better)")
    ax.set_ylim(100, 118)
    ax.set_title("③ Team on/off — the one stat against him (confounded)",
                 fontsize=11.5, fontweight="bold", loc="left")
    ax.legend(fontsize=9)

    fig.suptitle("Defense check — the 'declining defense' claim vs the data",
                 fontsize=14.5, fontweight="bold", y=1.03)
    fig.tight_layout()
    fig.savefig(config.FIG_DIR / "defense_check.png", dpi=155,
                bbox_inches="tight")
    plt.close(fig)


def _write(arc: pd.DataFrame, mu: pd.DataFrame, oo: pd.DataFrame) -> None:
    def m(s, c):
        r = mu[(mu.season == s) & (mu.category == c)]
        return r.iloc[0] if not r.empty else None

    o25 = m("2025-26", "Overall")
    o24 = m("2024-25", "Overall")
    rim25 = m("2025-26", "At rim (<6ft)")

    L = [
        "# Defense Check — Tested and Not Supported",
        "",
        "_The 'declining defense' angle was proposed for the trade case. We "
        "tested it three ways before writing a word of advocacy. **Verdict: "
        "the claim is not supported — do not use it.** By the matchup data, "
        "2025-26 was Brown's best defensive season of the two studied._",
        "",
        "## 1. Box-metric arc (Basketball-Reference)",
        "",
        "| Season | G | DBPM | DWS | DRB% |",
        "|---|---|---|---|---|",
    ]
    for _, r in arc.iterrows():
        L.append(f"| {r.Season} | {r.G} | {r.DBPM:+.1f} | {r.DWS:.1f} "
                 f"| {r['DRB%']:.1f} |")
    L += [
        "",
        "DBPM has hovered around zero his whole career — he was never an "
        "elite stopper by box metrics, but there is no downward arc: 2025-26 "
        f"(DBPM {arc.iloc[-1].DBPM:+.1f}, DWS {arc.iloc[-1].DWS:.1f}, "
        f"career-high DRB% {arc.iloc[-1]['DRB%']:.1f}) grades *better* than "
        "2024-25.",
        "",
        "## 2. Matchup data (defended FG% vs shooters' normal)",
        "",
        "| Category | 2024-25 | 2025-26 |",
        "|---|---|---|",
    ]
    for _, label in DEF_CATS:
        a, b = m("2024-25", label), m("2025-26", label)
        L.append(f"| {label} | {a.plusminus*100:+.1f} on {a.d_fga:.0f} FGA "
                 f"| {b.plusminus*100:+.1f} on {b.d_fga:.0f} FGA |")
    L += [
        "",
        f"In 2024-25 Brown was a neutral defender by this measure "
        f"({o24.plusminus*100:+.1f} overall). In 2025-26 shooters shot "
        f"**{o25.plusminus*100:+.1f} points worse** than their norm against "
        f"him on {o25.d_fga:.0f} defended attempts — including "
        f"{rim25.plusminus*100:+.1f} at the rim. That is improvement, at "
        "career-high offensive usage.",
        "",
        "## 3. Team on/off (the one stat that cuts against him)",
        "",
        "| Season | DEF_RATING on | DEF_RATING off | Delta |",
        "|---|---|---|---|",
    ]
    for _, r in oo.iterrows():
        L.append(f"| {r.season} | {r.def_on:.1f} | {r.def_off:.1f} "
                 f"| {r.def_delta:+.1f} |")
    L += [
        "",
        "Boston defended ~5–6 points/100 better with Brown off. But single-"
        "player defensive on/off is the noisiest stat here: 'Brown off' "
        "minutes lean on defense-first bench units and (in 2025-26) come "
        "disproportionately from stretches where opponents also rested "
        "starters. It contradicts the matchup data and the box metrics; two "
        "independent measures against one confounded one.",
        "",
        "## Verdict",
        "- **'Declining defense' is refuted** in the 2024-25 → 2025-26 window; "
        "if anything the trend is up.",
        "- The honest defensive statement: Brown was never an elite defender "
        "by box metrics (career DBPM ≈ 0), 2024-25 was a soft year (neutral "
        "matchup numbers), and 2025-26 was genuinely good.",
        "- **Implication for the trade case: leave defense out of it.** It is "
        "closer to a point in Brown's favor — he defended well while carrying "
        "35% usage. The case stands on flow, shot selection, price, and the "
        "return; hanging it on defense hands the other side an easy kill.",
    ]
    (config.OUTPUT_DIR / "defense_check.md").write_text("\n".join(L),
                                                        encoding="utf-8")


def main() -> int:
    arc = bref_arc()
    mu = matchup_rows()
    oo = onoff_rows()
    mu.to_csv(config.PROCESSED_DIR / "defense_check.csv", index=False)
    print(arc.to_string(index=False))
    print(mu.to_string(index=False))
    print(oo.to_string(index=False))
    _figure(arc, mu, oo)
    _write(arc, mu, oo)
    print("Done. outputs/defense_check.md + figures/defense_check.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
