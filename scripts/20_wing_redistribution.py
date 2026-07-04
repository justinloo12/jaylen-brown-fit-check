"""Wing redistribution: spread Brown's shot volume across the OTHER wings.

Script 19 asked "what if Brown's volume were re-priced at George's mix or
the team-average non-Brown mix?" This script asks the more realistic
version: Brown leaves, George arrives, and Brown's 21.7 FGA/g are spread
across the whole remaining wing rotation — each redistributed shot priced
at the *receiving* player's own mix and accuracy. Three numbers, clearly
labeled:

  1. NAIVE CEILING — current efficiencies held constant. A ceiling because
     efficiency does not fully survive a volume increase.
  2. USAGE-ADJUSTED ESTIMATE — the same redistribution with (a) the
     -0.3 to -0.6 TS-points-per-usage-point tradeoff from script 16 applied
     to every receiver's added volume and (b) a 50% creation-transfer
     discount on the share of Brown's volume that was self-created
     (his 3+ dribble rate).
  3. GEORGE-ONLY swap under the same adjustments — so the reader can see
     why spreading beats a 1-for-1 replacement.

Honesty requirements printed with the numbers, not under them: the
Hauser/Scheierman low-usage caveat, the usage-adjusted number being small,
and the double-counting warning against the hierarchy projection
(tatum_first_option.md) — the two projections overlap and are NOT additive.

Outputs:
  * data/processed/wing_redistribution.csv
  * outputs/figures/wing_redistribution.png
  * outputs/wing_redistribution.md
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
from fitcheck.data import nba_client as nba
from fitcheck.features.projection import net_to_wins
from fitcheck.features.shooting import (capped_split, expected_pps, fg2_pct,
                                        pps, pps_usage_penalty, three_rate,
                                        usage_delta_for_volume)
from fitcheck.features.shot_profile import self_creation_profile

SEASON = "2025-26"
BROWN = config.SUBJECT_ID
GEORGE_ID = 202331                     # Paul George (see scripts 06 and 19)
RED, GREEN, GREY, DARK = "#c0392b", "#007A33", "#b5b8b1", "#4a4f4a"

MIN_FLOOR = 1000                       # same rotation floor as script 19
# The receiving pool = every non-Brown perimeter Celtic above the floor,
# plus George. Tatum's injury-shortened 2025-26 (16 games) falls under the
# floor; his usage rise is modeled separately in script 16 — see the
# double-counting warning below. Bigs are excluded: absorbing wing volume
# is not a center's job (same split as script 19).
BIGS = {"Luka Garza", "Nikola Vucevic", "Neemias Queta", "Kristaps Porzingis",
        "Al Horford", "Luke Kornet", "Xavier Tillman", "Robert Williams III"}

# --- redistribution + adjustment assumptions (all quoted in the memo) -----
MAX_EXTRA_FGA = 4.5     # nobody absorbs more than +4.5 FGA/g
MAX_GAIN_MULT = 2.0     # nobody more than triples volume (gain <= 2x current)
TS_SLOPE_LO, TS_SLOPE_HI = 0.3, 0.6  # TS pts lost per +1 usage pt (script 16)
CREATION_TRANSFER = 0.5  # transfer rate on Brown's self-created volume (s19)
AGE_HAIRCUT_3PT = 0.02   # up to -2pp on George's 3P% (36 in '26, same as s19)


def _is_big(name: str) -> bool:
    import unicodedata
    plain = "".join(c for c in unicodedata.normalize("NFKD", name)
                    if not unicodedata.combining(c))
    return plain in BIGS


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
def player_row(pl: pd.DataFrame, pid: int) -> dict:
    r = pl[pl["PLAYER_ID"] == pid].iloc[0]
    return {
        "player": r["PLAYER_NAME"], "player_id": pid,
        "fga_pg": float(r["FGA"]), "fta_pg": float(r["FTA"]),
        "min_pg": float(r["MIN"]), "gp": int(r["GP"]),
        "rate3": three_rate(r["FG3A"], r["FGA"]),
        "fg3_pct": r["FG3M"] / r["FG3A"] if r["FG3A"] else np.nan,
        "fg2_pct": fg2_pct(r["FGM"], r["FG3M"], r["FGA"], r["FG3A"]),
        "pps": pps(r["PTS"], r["FTM"], r["FGA"]),
    }


def brown_iso_share(season: str = SEASON) -> float:
    """Brown's self-created share = his 3+ dribble rate (tracking, cached).

    Same definition and pipeline as scripts 02/11/16
    (outputs/tatum_vs_brown.md quotes 0.639 for 2025-26).
    """
    dribble = nba.player_tracking_shots(BROWN, season, split="dribble")
    empty = pd.DataFrame()
    prof = self_creation_profile(dribble, empty, empty, empty)
    return float(prof["iso_dribble_rate"])


def receiving_pool(pl: pd.DataFrame) -> list[dict]:
    bos = pl[pl["TEAM_ID"] == config.CELTICS_TEAM_ID].copy()
    bos["MIN_TOT"] = bos["MIN"] * bos["GP"]
    bos = bos[(bos["MIN_TOT"] >= MIN_FLOOR) & (bos["PLAYER_ID"] != BROWN)]
    wings = [player_row(pl, int(r["PLAYER_ID"]))
             for _, r in bos.iterrows() if not _is_big(r["PLAYER_NAME"])]
    wings.append(player_row(pl, GEORGE_ID))     # George joins the pool
    return sorted(wings, key=lambda w: -w["fga_pg"])


# ---------------------------------------------------------------------------
# Redistribution + pricing
# ---------------------------------------------------------------------------
def build_table(wings: list[dict], brown: dict, team: dict) -> pd.DataFrame:
    """Who absorbs what, and at what price.

    Weights = current FGA/g share (shot-takers absorb shots in proportion to
    how much they already shoot — a minutes-share weighting moves volume
    toward low-usage players even faster and would only flatter the result).
    Caps: gain <= MAX_EXTRA_FGA and gain <= MAX_GAIN_MULT x current FGA.
    """
    weights = [w["fga_pg"] for w in wings]
    caps = [min(MAX_EXTRA_FGA, MAX_GAIN_MULT * w["fga_pg"]) for w in wings]
    gains = capped_split(brown["fga_pg"], weights, caps)
    assert abs(sum(gains) - brown["fga_pg"]) < 1e-9, "caps swallowed volume"

    rows = []
    for w, g in zip(wings, gains):
        epps = expected_pps(w["rate3"], w["fg3_pct"], w["fg2_pct"])
        extra_fta = g * (w["fta_pg"] / w["fga_pg"])   # FTs at own draw rate
        dusg = usage_delta_for_volume(
            g, extra_fta, w["min_pg"], team["fga"], team["fta"],
            team["tov"], team["min5"])
        rows.append({**w, "gain_fga": g, "epps": epps, "dusg": dusg,
                     "naive_pts": g * (epps - brown["pps"])})
    return pd.DataFrame(rows)


def scenario_deltas(tab: pd.DataFrame, brown: dict, iso_share: float,
                    george_id: int = GEORGE_ID) -> dict:
    """The three labeled numbers (pts/game deltas)."""
    transfer = 1.0 - iso_share * (1.0 - CREATION_TRANSFER)
    naive = float(tab["naive_pts"].sum())

    def adjusted(slope: float, haircut: bool) -> float:
        total = 0.0
        for _, r in tab.iterrows():
            epps = r["epps"]
            if haircut and r["player_id"] == george_id:
                epps -= 3.0 * r["rate3"] * AGE_HAIRCUT_3PT
            pen = pps_usage_penalty(r["dusg"], slope)
            total += r["gain_fga"] * (epps - pen - brown["pps"])
        return total * transfer

    return {
        "transfer": transfer, "naive": naive,
        "adj_hi": adjusted(TS_SLOPE_LO, haircut=False),
        "adj_lo": adjusted(TS_SLOPE_HI, haircut=True),
    }


def george_only(pl: pd.DataFrame, brown: dict, team: dict,
                iso_share: float) -> dict:
    """1-for-1 swap: George takes all of Brown's volume at Brown's minutes.

    His whole re-priced volume carries the usage penalty because his usage
    moves from his 2025-26 level to Brown's — the same marginal-pricing rule
    used above, applied to a much larger usage jump concentrated on one
    36-year-old. Same transfer discount and aging haircut as the spread.
    """
    g = player_row(pl, GEORGE_ID)
    transfer = 1.0 - iso_share * (1.0 - CREATION_TRANSFER)
    epps = expected_pps(g["rate3"], g["fg3_pct"], g["fg2_pct"])
    extra_fga = brown["fga_pg"] - g["fga_pg"]
    extra_fta = extra_fga * (g["fta_pg"] / g["fga_pg"])
    dusg = usage_delta_for_volume(extra_fga, extra_fta, brown["min_pg"],
                                  team["fga"], team["fta"], team["tov"],
                                  team["min5"])
    naive = brown["fga_pg"] * (epps - brown["pps"])
    hi = (brown["fga_pg"]
          * (epps - pps_usage_penalty(dusg, TS_SLOPE_LO) - brown["pps"])
          * transfer)
    lo = (brown["fga_pg"]
          * (epps - 3.0 * g["rate3"] * AGE_HAIRCUT_3PT
             - pps_usage_penalty(dusg, TS_SLOPE_HI) - brown["pps"])
          * transfer)
    return {"naive": naive, "adj_lo": lo, "adj_hi": hi, "dusg": dusg,
            "epps": epps, "george": g}


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def _figure(tab: pd.DataFrame, sc: dict, go: dict, brown: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16.6, 5.8),
                             gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Left: where the shots go.
    ax = axes[0]
    t = tab.sort_values("gain_fga")
    names = list(t["player"]) + ["Jaylen Brown"]
    vals = list(t["gain_fga"]) + [-brown["fga_pg"]]
    colors = [GREEN] * len(t) + [RED]
    bars = ax.barh(names, vals, color=colors, height=0.62)
    for rect, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}",
                    (v, rect.get_y() + rect.get_height() / 2),
                    textcoords="offset points",
                    xytext=(5 if v >= 0 else -5, 0),
                    ha="left" if v >= 0 else "right", va="center",
                    fontsize=11.5, fontweight="bold")
    ax.axvline(0, color="black", lw=0.9)
    ax.set_xlabel("FGA/game redistributed (2025-26 baseline)", fontsize=12)
    ax.set_title(f"Where Brown's {brown['fga_pg']:.1f} FGA/g go —\n"
                 "proportional to current volume, capped at "
                 f"+{MAX_EXTRA_FGA:.1f}", fontsize=13, fontweight="bold",
                 loc="left")
    ax.margins(x=0.18)
    ax.tick_params(axis="y", labelsize=11.5)

    # Right: the three labeled numbers.
    ax = axes[1]
    labels = ["Naive ceiling\n(efficiency held\nconstant)",
              "Usage-adjusted\nestimate",
              "George-only\n1-for-1 swap\n(usage-adjusted)"]
    mids = [sc["naive"],
            (sc["adj_lo"] + sc["adj_hi"]) / 2,
            (go["adj_lo"] + go["adj_hi"]) / 2]
    los = [sc["naive"], sc["adj_lo"], go["adj_lo"]]
    his = [sc["naive"], sc["adj_hi"], go["adj_hi"]]
    err = [[m - a for m, a in zip(mids, los)],
           [b - m for m, b in zip(mids, his)]]
    ax.bar(np.arange(3), mids, 0.52, color=[GREY, GREEN, RED], alpha=0.88)
    ax.errorbar(np.arange(3), mids, yerr=err, fmt="none", ecolor=DARK,
                capsize=6, lw=1.6)
    for i, (a, b) in enumerate(zip(los, his)):
        txt = (f"{a:+.1f} pts/g\n({net_to_wins(a):+.1f} W)" if a == b else
               f"{a:+.1f} to {b:+.1f} pts/g\n({net_to_wins(a):+.1f} to "
               f"{net_to_wins(b):+.1f} W)")
        ax.annotate(txt, (i, max(b, 0)), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=11,
                    fontweight="bold")
    ax.set_xticks(np.arange(3))
    ax.set_xticklabels(labels, fontsize=10.5)
    ax.axhline(0, color="black", lw=0.9)
    ax.set_ylabel("Projected pts/game delta", fontsize=12)
    ax.set_title("PROJECTION: three numbers, honestly labeled",
                 fontsize=13, fontweight="bold", loc="left")
    ax.margins(y=0.42)

    fig.suptitle("Redistributing Brown's shot volume across the other wings "
                 "(incl. George), each shot priced at the receiver's own mix",
                 fontsize=15.5, fontweight="bold", y=1.02)
    fig.text(0.005, -0.09,
             "Ceiling assumes efficiency survives the volume increase — it "
             "won't fully (Hauser/Scheierman shoot at low usage).\nAdjusted "
             f"= -{TS_SLOPE_LO}..-{TS_SLOPE_HI} TS pts per +1 usage pt, "
             f"{CREATION_TRANSFER:.0%} transfer on Brown's self-created "
             "share, up to -2pp on George's 3P%. NOT additive with the "
             "hierarchy projection (tatum_first_option.md).",
             fontsize=9.5, style="italic", color=DARK)
    fig.tight_layout()
    out = config.FIG_DIR / "wing_redistribution.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


# ---------------------------------------------------------------------------
# Memo
# ---------------------------------------------------------------------------
def _write(tab: pd.DataFrame, sc: dict, go: dict, brown: dict,
           iso_share: float) -> None:
    naive_w = net_to_wins(sc["naive"])
    adj_lo_w, adj_hi_w = net_to_wins(sc["adj_lo"]), net_to_wins(sc["adj_hi"])
    go_lo_w, go_hi_w = net_to_wins(go["adj_lo"]), net_to_wins(go["adj_hi"])

    L = [
        "# Wing Redistribution — Spreading Brown's Volume Across the Other "
        "Wings (incl. George)",
        "",
        "_Companion to [three_point_identity.md](three_point_identity.md) "
        "(which re-priced Brown's volume at a single target mix) and "
        "[tatum_first_option.md](tatum_first_option.md) (the hierarchy "
        "projection this one partially overlaps — see the double-counting "
        "warning in §3). **Everything here is a projection** built on "
        "observed 2025-26 shot mixes._",
        "",
        "## 1. The scenario and who absorbs what",
        "",
        f"Brown's 2025-26 volume ({brown['fga_pg']:.1f} FGA/g, plus "
        f"{brown['fta_pg']:.1f} FTA/g handled only through the usage math — "
        "the pricing itself is FT-excluded, same as script 19) is spread "
        "across the remaining perimeter rotation plus Paul George. "
        "**Weighting: proportional to each wing's current FGA/g** (shot "
        "volume flows to players in proportion to how much they already "
        "shoot; a minutes-share weighting would push even more volume onto "
        "the lowest-usage shooters and flatter the result). **Caps:** no "
        f"one gains more than {MAX_EXTRA_FGA:.1f} FGA/g and no one more "
        f"than triples their volume (gain ≤ {MAX_GAIN_MULT:.0f}× current "
        "FGA); capped excess re-flows to the open slots. Tatum is not in "
        "the pool — his 16-game 2025-26 falls under the rotation floor, and "
        "his usage rise is already the subject of the script-16 projection.",
        "",
        "| Player | FGA/g now | Gain | New FGA/g | 3PT rate | Exp. PPS "
        "| Δ usage (pts) | Naive Δpts/g |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for _, r in tab.iterrows():
        L.append(f"| {r['player']} | {r['fga_pg']:.1f} "
                 f"| +{r['gain_fga']:.1f} "
                 f"| {r['fga_pg'] + r['gain_fga']:.1f} | {r['rate3']:.3f} "
                 f"| {r['epps']:.3f} | +{r['dusg']:.1f} "
                 f"| {r['naive_pts']:+.2f} |")
    L += [
        f"| **Jaylen Brown** | {brown['fga_pg']:.1f} "
        f"| −{brown['fga_pg']:.1f} | 0.0 | {brown['rate3']:.3f} "
        f"| {brown['pps']:.3f} (realized) | — | — |",
        "",
        f"Every redistributed shot is priced at the receiver's own mix and "
        "accuracy: E[PPS] = 3PT rate × 3 × 3P% + 2PT share × 2 × 2P% "
        "(`expected_pps`, unit-tested). Brown's shots are removed at his "
        f"realized {brown['pps']:.3f} PPS. George is priced in the Boston "
        "environment at his 2025-26 Philadelphia mix, accuracy, and minutes.",
        "",
        "## 2. Three numbers, clearly labeled",
        "",
        f"1. **NAIVE CEILING: {sc['naive']:+.1f} pts/game "
        f"(~{naive_w:+.1f} wins).** Ceiling — assumes efficiency survives "
        "the volume increase, because it won't fully. **Printed with this "
        "number, not under it: Hauser and Scheierman post those PPS "
        "figures at 7.7 and 4.3 FGA/g of curated, low-usage looks — "
        "their .84/.74 three-point rates are exactly what makes their "
        "expected PPS high, and exactly what a defense starts taking away "
        "when their volume jumps ~40%.** Also visible in the table: "
        "White's 2025-26 pricing (0.979 expected PPS) is *below* Brown's "
        "realized 1.046 — the spread is not uniformly upgrade.",
        "",
        f"2. **USAGE-ADJUSTED ESTIMATE: {sc['adj_lo']:+.1f} to "
        f"{sc['adj_hi']:+.1f} pts/game (~{adj_lo_w:+.1f} to "
        f"{adj_hi_w:+.1f} wins).** Two documented adjustments: "
        f"(a) the −{TS_SLOPE_LO} to −{TS_SLOPE_HI} TS-points-per-+1-usage-"
        "point tradeoff — the same rule-of-thumb range script 16 applies "
        "to Tatum (Goldman/Rao skill-curve literature) — converted to PPS "
        "(ΔPPS ≈ 2×ΔTS) and charged to each receiver's *added* shots at "
        "their own usage bump (charging their existing volume too would "
        "push this lower still); "
        f"(b) a {CREATION_TRANSFER:.0%} creation-transfer discount on the "
        f"{iso_share:.3f} share of Brown's volume that was self-created "
        "(his 3+ dribble rate, tracking data — same figure quoted in "
        "tatum_vs_brown.md), i.e. an effective transfer of "
        f"{sc['transfer']:.3f}. That volume needs a creator; in practice "
        "the creator is Tatum, whose usage rise is what script 16 already "
        "projects — the discount here prices the interaction instead of "
        "double-counting the gain. The low corner also takes "
        f"{AGE_HAIRCUT_3PT * 100:.0f}pp off George's 3P% (36 in 2026).",
        "",
        f"3. **GEORGE-ONLY 1-FOR-1 SWAP: {go['adj_lo']:+.1f} to "
        f"{go['adj_hi']:+.1f} pts/game (~{go_lo_w:+.1f} to {go_hi_w:+.1f} "
        f"wins) usage-adjusted; {go['naive']:+.1f} naive.** Why spreading "
        "beats the 1-for-1: George alone must jump "
        f"+{go['dusg']:.1f} usage points at age 36 to absorb all of "
        "Brown's volume at his .497 three rate, while the spread hands "
        "each wing a small bump (+4.4 to +7.0 usage points) and routes "
        "shots to .576/.844 three-rate players. Same math, same "
        "discounts — concentration is what kills the 1-for-1.",
        "",
        "**If the honest number looks small, say so: it is.** The "
        f"usage-adjusted estimate is {adj_lo_w:+.1f} to {adj_hi_w:+.1f} "
        "wins — a rounding error on a season, and the low corner is "
        "negative. The shot-mix channel by itself does not carry the "
        "trade case; it never did (script 19 reached the same verdict "
        "from a different angle).",
        "",
        "## 3. DOUBLE-COUNTING WARNING — read before citing any number "
        "above",
        "",
        "**This projection overlaps the hierarchy projection in "
        "[tatum_first_option.md](tatum_first_option.md) (+4.7 to +7.0 "
        "wins). They are NOT additive.** What overlaps: the hierarchy "
        "number is built from observed without-Brown lineup nets — and "
        "those lineups were *already running* the three-heavier mix this "
        "script prices shot-by-shot. The better mix is one of the "
        "mechanisms *inside* the lineup gap, not a separate effect on top "
        "of it. The creation-transfer discount here and the usage-tax on "
        "Tatum there are two views of the same possession. What is "
        "genuinely incremental here: George's arrival (his mix is priced "
        "into this pool but not into the historical lineups) and the "
        "explicit caps on how much low-usage shooters can absorb.",
        "",
        f"**Combined honest range: roughly +4 to +8 wins total** — the "
        "hierarchy range (+4.7 to +7.0) widened by this script's "
        f"uncertainty ({adj_lo_w:+.1f} to {adj_hi_w:+.1f}), **not** the "
        "sum (which would double-count to +5 to +10 and should not be "
        "quoted). If a single number must survive, quote the hierarchy "
        "range and treat this memo as the shot-level mechanism check "
        "on it.",
        "",
        "## 4. Assumptions, constants, and method notes",
        "",
        f"- Redistribution: proportional to current FGA/g, caps "
        f"min(+{MAX_EXTRA_FGA:.1f} FGA/g, {MAX_GAIN_MULT:.0f}× current); "
        "waterfall re-flow (`capped_split`, unit-tested: allocations sum "
        "to Brown's volume, caps respected).",
        "- Usage math: standard boxscore USG% differenced "
        "(`usage_delta_for_volume`), Boston 2025-26 team totals, added "
        "FTs at each receiver's own FTA/FGA rate, turnovers held flat.",
        f"- Win conversion: pts/game × {net_to_wins(1.0):.1f} wins per "
        "point of per-game differential — the same Pythagorean rule of "
        "thumb as scripts 16 and 19; defense assumed unchanged.",
        "- Free throws excluded from pricing on both sides (Brown's rim "
        "pressure drew 7.5 FTA/g; a three-heavier diet returns some of "
        "that — this memo, like script 19, does not credit either side).",
        "- Constants live at the top of `scripts/20_wing_redistribution.py`; "
        "pure helpers in `fitcheck/features/shooting.py`, tested in "
        "`tests/test_redistribution.py` and `tests/test_shooting.py`.",
    ]
    out = config.OUTPUT_DIR / "wing_redistribution.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  ✓ memo -> {out}")


# ---------------------------------------------------------------------------
def main() -> int:
    pl = nba.league_player_stats(SEASON, measure="Base")
    tm = (nba.league_team_stats(SEASON, measure="Base")
          .set_index("TEAM_ID").loc[config.CELTICS_TEAM_ID])
    team = {"fga": float(tm["FGA"]), "fta": float(tm["FTA"]),
            "tov": float(tm["TOV"]), "min5": float(tm["MIN"]) * 5.0}

    brown = player_row(pl, BROWN)
    iso_share = brown_iso_share()
    wings = receiving_pool(pl)
    tab = build_table(wings, brown, team)
    sc = scenario_deltas(tab, brown, iso_share)
    go = george_only(pl, brown, team, iso_share)

    print(f"  ✓ pool: {len(tab)} wings absorb {tab['gain_fga'].sum():.1f} "
          f"FGA/g (Brown iso share {iso_share:.3f}, transfer "
          f"{sc['transfer']:.3f})")
    for _, r in tab.iterrows():
        print(f"    {r['player']:<18} +{r['gain_fga']:.1f} FGA/g "
              f"(epps {r['epps']:.3f}, +{r['dusg']:.1f} usg)")
    print(f"  ✓ NAIVE CEILING       {sc['naive']:+.2f} pts/g "
          f"({net_to_wins(sc['naive']):+.1f} W) — ceiling: assumes "
          "efficiency survives the volume increase; it won't fully "
          "(Hauser/Scheierman shoot at low usage)")
    print(f"  ✓ USAGE-ADJUSTED      {sc['adj_lo']:+.2f} to "
          f"{sc['adj_hi']:+.2f} pts/g ({net_to_wins(sc['adj_lo']):+.1f} to "
          f"{net_to_wins(sc['adj_hi']):+.1f} W) — small; say so plainly")
    print(f"  ✓ GEORGE-ONLY 1-for-1 {go['adj_lo']:+.2f} to "
          f"{go['adj_hi']:+.2f} pts/g ({net_to_wins(go['adj_lo']):+.1f} to "
          f"{net_to_wins(go['adj_hi']):+.1f} W) — concentration loses to "
          "spreading")
    print("  ! DOUBLE-COUNTING WARNING: overlaps the hierarchy projection "
          "(+4.7 to +7.0 W, tatum_first_option.md) — NOT additive; "
          "combined honest range ~+4 to +8 W, not the sum.")

    tab.to_csv(config.PROCESSED_DIR / "wing_redistribution.csv", index=False)
    _figure(tab, sc, go, brown)
    _write(tab, sc, go, brown, iso_share)
    print("Done. outputs/wing_redistribution.md + "
          "figures/wing_redistribution.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
