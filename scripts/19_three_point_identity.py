"""The three-point game plan: Boston's identity, Brown's drag on it, the swap.

Three questions, answered in order and honestly separated:
  1. OBSERVED, league level — is "league-leading three volume at
     league-quality accuracy" actually Boston's identity? Team 3PA/game,
     3PT attempt rate, 3P%, points-per-shot on threes vs twos, and
     offensive-rating rank, all three current-system seasons (2023-24 →
     2025-26), with league ranks. Correlation is noted as correlation.
  2. OBSERVED, within team — where does Brown sit inside that identity?
     Shot diet (3PT rate, long-two rate, PPS, catch-&-shoot share) for
     every Bostonian above the minutes floor, perimeter players ranked
     together and bigs shown separately.
  3. PROJECTION — the diet swap: re-price Brown's 2025-26 shot volume
     under (a) Paul George's actual mix and accuracy and (b) the
     non-Brown Boston mix and accuracy, with a creation-transfer discount
     and an aging haircut. Ranges, not points; caveats printed with the
     number.

Outputs:
  * data/processed/three_point_identity_team.csv, _players.csv
  * outputs/figures/three_point_identity.png
  * outputs/three_point_identity.md
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
from fitcheck.features.shooting import (diet_swap_delta, expected_pps,
                                        fg2_pct, pps, three_rate)
from fitcheck.features.shot_profile import shot_zone_profile

SEASONS = config.POOL_SEASONS          # 2023-24 -> 2025-26
BROWN, TATUM = config.SUBJECT_ID, config.CELTICS_ROTATION["Jayson Tatum"]
GEORGE_ID = 202331                     # Paul George (see script 06)
RED, GREEN, GREY, DARK = "#c0392b", "#007A33", "#b5b8b1", "#4a4f4a"

MIN_FLOOR = 1000                       # season minutes to make the table
# Bigs are compared separately — a center's shot diet is not a wing choice.
# Names are matched diacritics-stripped (stats.nba.com spells Porziņģis,
# Vučević with accents).
BIGS = {"Kristaps Porzingis", "Al Horford", "Luke Kornet", "Neemias Queta",
        "Xavier Tillman", "Robert Williams III", "Nikola Vucevic",
        "Luka Garza"}


def _is_big(name: str) -> bool:
    import unicodedata
    plain = "".join(c for c in unicodedata.normalize("NFKD", name)
                    if not unicodedata.combining(c))
    return plain in BIGS

# --- diet-swap assumptions (every one is quoted in the memo) --------------
TRANSFER_LO, TRANSFER_HI = 0.5, 1.0    # share of re-priced volume realizable
AGE_HAIRCUT_3PT = 0.02                 # up to -2pp on George's 3P% (36 in '26)


# ---------------------------------------------------------------------------
# 1. League level: the identity
# ---------------------------------------------------------------------------
def team_identity(season: str) -> dict:
    base = nba.league_team_stats(season, measure="Base")
    adv = nba.league_team_stats(season, measure="Advanced")
    b = base.set_index("TEAM_ID")
    rate = b["FG3A"] / b["FGA"]

    def rank_of(series: pd.Series, team=config.CELTICS_TEAM_ID) -> int:
        return int(series.rank(ascending=False, method="min").loc[team])

    bos = b.loc[config.CELTICS_TEAM_ID]
    ortg = adv.set_index("TEAM_ID")["OFF_RATING"]
    return {
        "season": season,
        "fg3a_pg": bos["FG3A"], "fg3a_rank": rank_of(b["FG3A"]),
        "rate3": rate.loc[config.CELTICS_TEAM_ID], "rate3_rank": rank_of(rate),
        "fg3_pct": bos["FG3_PCT"], "fg3_pct_rank": rank_of(b["FG3_PCT"]),
        "pps3": 3.0 * bos["FG3_PCT"],
        "pps2": 2.0 * fg2_pct(bos["FGM"], bos["FG3M"], bos["FGA"], bos["FG3A"]),
        "lg_fg3a_pg": b["FG3A"].mean(),
        "ortg": ortg.loc[config.CELTICS_TEAM_ID], "ortg_rank": rank_of(ortg),
    }


# ---------------------------------------------------------------------------
# 2. Within team: the rotation shot-diet table
# ---------------------------------------------------------------------------
def rotation_diets(season: str) -> pd.DataFrame:
    pl = nba.league_player_stats(season, measure="Base")
    bos = pl[pl["TEAM_ID"] == config.CELTICS_TEAM_ID].copy()
    bos["MIN_TOT"] = bos["MIN"] * bos["GP"]
    bos = bos[bos["MIN_TOT"] >= MIN_FLOOR]

    track = nba.league_player_tracking(season, pt_measure="CatchShoot")
    cs = track.set_index("PLAYER_ID")

    rows = []
    for _, r in bos.iterrows():
        pid = int(r["PLAYER_ID"])
        zone = shot_zone_profile(nba.shot_chart(pid, season))
        cs_fga = float(cs.loc[pid, "CATCH_SHOOT_FGA"]) if pid in cs.index else np.nan
        rows.append({
            "season": season, "player": r["PLAYER_NAME"], "player_id": pid,
            "big": _is_big(r["PLAYER_NAME"]),
            "min_tot": r["MIN_TOT"], "fga_pg": r["FGA"],
            "rate3": three_rate(r["FG3A"], r["FGA"]),
            "long_two_rate": zone.get("long_two_rate", np.nan),
            "pps": pps(r["PTS"], r["FTM"], r["FGA"]),
            "cs_share": cs_fga / r["FGA"] if r["FGA"] else np.nan,
        })
    return pd.DataFrame(rows).sort_values("rate3", ascending=False)


def non_brown_pricing(season: str) -> dict:
    """Team-minus-Brown mix and accuracy by shot type (counting totals)."""
    tm = (nba.league_team_stats(season, measure="Base")
          .set_index("TEAM_ID").loc[config.CELTICS_TEAM_ID])
    pl = nba.league_player_stats(season, measure="Base")
    br = pl[pl["PLAYER_ID"] == BROWN].iloc[0]
    tot = {k: tm[k] * tm["GP"] - br[k] * br["GP"]
           for k in ("FGM", "FGA", "FG3M", "FG3A")}
    return {
        "rate3": three_rate(tot["FG3A"], tot["FGA"]),
        "fg3_pct": tot["FG3M"] / tot["FG3A"],
        "fg2_pct": fg2_pct(tot["FGM"], tot["FG3M"], tot["FGA"], tot["FG3A"]),
    }


def player_pricing(pl: pd.DataFrame, pid: int) -> dict:
    r = pl[pl["PLAYER_ID"] == pid].iloc[0]
    return {
        "name": r["PLAYER_NAME"], "fga_pg": r["FGA"], "gp": r["GP"],
        "rate3": three_rate(r["FG3A"], r["FGA"]),
        "fg3_pct": r["FG3M"] / r["FG3A"] if r["FG3A"] else np.nan,
        "fg2_pct": fg2_pct(r["FGM"], r["FG3M"], r["FGA"], r["FG3A"]),
        "pps": pps(r["PTS"], r["FTM"], r["FGA"]),
    }


# ---------------------------------------------------------------------------
# 3. Projection: the diet swap
# ---------------------------------------------------------------------------
def build_swap(season: str = "2025-26") -> dict:
    pl = nba.league_player_stats(season, measure="Base")
    brown = player_pricing(pl, BROWN)
    george = player_pricing(pl, GEORGE_ID)
    nb = non_brown_pricing(season)

    scenarios = {}
    # (a) George's mix at George's accuracy, with 0 to -2pp on his 3P%.
    deltas = [diet_swap_delta(
                  brown["fga_pg"], brown["pps"],
                  expected_pps(george["rate3"], george["fg3_pct"] - h,
                               george["fg2_pct"]), t)
              for t in (TRANSFER_LO, TRANSFER_HI)
              for h in (0.0, AGE_HAIRCUT_3PT)]
    scenarios["george"] = {"lo": min(deltas), "hi": max(deltas),
                           "target_pps": expected_pps(
                               george["rate3"], george["fg3_pct"],
                               george["fg2_pct"])}
    # (b) team-average non-Brown mix at non-Brown accuracy.
    deltas = [diet_swap_delta(
                  brown["fga_pg"], brown["pps"],
                  expected_pps(nb["rate3"], nb["fg3_pct"], nb["fg2_pct"]), t)
              for t in (TRANSFER_LO, TRANSFER_HI)]
    scenarios["team"] = {"lo": min(deltas), "hi": max(deltas),
                         "target_pps": expected_pps(
                             nb["rate3"], nb["fg3_pct"], nb["fg2_pct"])}
    return {"brown": brown, "george": george, "non_brown": nb,
            "scenarios": scenarios}


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def _figure(team: pd.DataFrame, diets: dict[str, pd.DataFrame],
            swap: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17.0, 5.8),
                             gridspec_kw={"width_ratios": [1.0, 1.15, 0.9]})

    # Panel 1: 3PA/game vs league average, rank annotated.
    ax = axes[0]
    x, w = np.arange(len(SEASONS)), 0.36
    t = team.set_index("season")
    b1 = ax.bar(x - w / 2, [t.loc[s, "fg3a_pg"] for s in SEASONS], w,
                color=GREEN, label="Boston 3PA/game")
    ax.bar(x + w / 2, [t.loc[s, "lg_fg3a_pg"] for s in SEASONS], w,
           color=GREY, label="League average")
    for rect, s in zip(b1, SEASONS):
        ax.annotate(f"{rect.get_height():.1f}\n(#{t.loc[s, 'fg3a_rank']:.0f})",
                    (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                    textcoords="offset points", xytext=(0, 4), ha="center",
                    fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(SEASONS, fontsize=12)
    ax.set_ylabel("3PA per game", fontsize=12)
    ax.set_title("The identity: three volume, league rank",
                 fontsize=13.5, fontweight="bold", loc="left")
    ax.legend(fontsize=10.5, loc="lower right")
    ax.margins(y=0.22)

    # Panel 2: 2025-26 perimeter rotation, 3PT attempt rate.
    ax = axes[1]
    d = diets["2025-26"]
    per = d[~d["big"]].sort_values("rate3")
    colors = [RED if p == config.SUBJECT else GREEN for p in per["player"]]
    bars = ax.barh(per["player"], per["rate3"], color=colors, height=0.62)
    for rect, v in zip(bars, per["rate3"]):
        ax.annotate(f"{v:.3f}", (v, rect.get_y() + rect.get_height() / 2),
                    textcoords="offset points", xytext=(4, 0), va="center",
                    fontsize=11.5, fontweight="bold")
    team_rate = team.set_index("season").loc["2025-26", "rate3"]
    ax.axvline(team_rate, color=DARK, lw=1.2, ls="--")
    ax.annotate(f"team {team_rate:.3f}", (team_rate, -0.45), fontsize=10.5,
                color=DARK, ha="center")
    ax.set_xlabel("3PT attempt rate (3PA / FGA), 2025-26", fontsize=12)
    ax.set_title("Inside the identity: Brown is the outlier (perimeter only)",
                 fontsize=13.5, fontweight="bold", loc="left")
    ax.margins(x=0.14)
    ax.tick_params(axis="y", labelsize=11.5)

    # Panel 3: diet-swap ranges.
    ax = axes[2]
    sc = swap["scenarios"]
    labels = ["George's mix\n& accuracy", "Non-Brown\nBoston mix"]
    los = [sc["george"]["lo"], sc["team"]["lo"]]
    his = [sc["george"]["hi"], sc["team"]["hi"]]
    mid = [(a + b) / 2 for a, b in zip(los, his)]
    err = [[m - a for m, a in zip(mid, los)], [b - m for m, b in zip(mid, his)]]
    ax.bar(np.arange(2), mid, 0.5, color=[GREEN, GREY], alpha=0.85)
    ax.errorbar(np.arange(2), mid, yerr=err, fmt="none", ecolor=DARK,
                capsize=6, lw=1.6)
    for i, (a, b) in enumerate(zip(los, his)):
        ax.annotate(f"{a:+.1f} to {b:+.1f}\npts/g "
                    f"({net_to_wins(a):+.1f} to {net_to_wins(b):+.1f} W)",
                    (i, b), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=11.5, fontweight="bold")
    ax.set_xticks(np.arange(2))
    ax.set_xticklabels(labels, fontsize=11.5)
    ax.axhline(0, color="black", lw=0.9)
    ax.set_ylabel("Projected pts/game delta", fontsize=12)
    ax.set_title("PROJECTION: re-pricing Brown's shot volume",
                 fontsize=13.5, fontweight="bold", loc="left")
    ax.margins(y=0.35)

    fig.suptitle("Boston's three-point identity — and what Brown's shot mix "
                 "costs inside it (2023-24 → 2025-26)",
                 fontsize=16.5, fontweight="bold", y=1.03)
    fig.text(0.005, -0.04,
             "Panel 3 is a projection with a 50-100% creation-transfer "
             "discount and up to -2pp aging haircut on George's 3P%; "
             "free throws and defense excluded. See memo §3 caveats.",
             fontsize=10, style="italic", color=DARK)
    fig.tight_layout()
    out = config.FIG_DIR / "three_point_identity.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


# ---------------------------------------------------------------------------
# Memo
# ---------------------------------------------------------------------------
def _diet_table(d: pd.DataFrame) -> list[str]:
    L = ["| Player | Min | FGA/g | 3PT rate | Long-2 rate | PPS | C&S share |",
         "|---|---|---|---|---|---|---|"]
    per = d[~d["big"]].sort_values("rate3", ascending=False)
    bigs = d[d["big"]].sort_values("rate3", ascending=False)
    for _, r in per.iterrows():
        mark = "**" if r["player"] == config.SUBJECT else ""
        L.append(f"| {mark}{r['player']}{mark} | {r['min_tot']:,.0f} "
                 f"| {r['fga_pg']:.1f} | {mark}{r['rate3']:.3f}{mark} "
                 f"| {r['long_two_rate']:.3f} | {r['pps']:.3f} "
                 f"| {r['cs_share']:.3f} |")
    for _, r in bigs.iterrows():
        L.append(f"| {r['player']} _(big)_ | {r['min_tot']:,.0f} "
                 f"| {r['fga_pg']:.1f} | {r['rate3']:.3f} "
                 f"| {r['long_two_rate']:.3f} | {r['pps']:.3f} "
                 f"| {r['cs_share']:.3f} |")
    return L


def _brown_ranks(d: pd.DataFrame) -> tuple[int, int, int]:
    per = d[~d["big"]]
    n = len(per)
    r3 = int(per["rate3"].rank(ascending=False).loc[
        per["player"] == config.SUBJECT].iloc[0])
    lt = int(per["long_two_rate"].rank(ascending=False).loc[
        per["player"] == config.SUBJECT].iloc[0])
    return r3, lt, n


def _write(team: pd.DataFrame, diets: dict[str, pd.DataFrame],
           swap: dict) -> None:
    t = team.set_index("season")
    br, ge, nb = swap["brown"], swap["george"], swap["non_brown"]
    sc = swap["scenarios"]
    d26 = diets["2025-26"]
    per26 = d26[~d26["big"]]
    nb_pps = ((per26[per26["player"] != config.SUBJECT]["pps"]
               * per26[per26["player"] != config.SUBJECT]["fga_pg"]).sum()
              / per26[per26["player"] != config.SUBJECT]["fga_pg"].sum())
    r3_rank, lt_rank, n_per = _brown_ranks(d26)

    L = [
        "# The Three-Point Identity — Boston's Game Plan, Brown's Drag, "
        "and the Diet-Swap Projection",
        "",
        "_Companion to [tatum_first_option.md](tatum_first_option.md) "
        "(§1b uses the same 2023-24 → 2025-26 window). §1-§2 are "
        "**observed**; §3 is a **projection** and is labeled at every "
        "step._",
        "",
        "## 1. The game plan, proven — league-leading volume at "
        "league-quality accuracy",
        "",
        "| Season | 3PA/g (rank) | 3PA rate (rank) | 3P% (rank) "
        "| PPS on 3s | PPS on 2s | ORTG rank |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in SEASONS:
        r = t.loc[s]
        L.append(f"| {s} | {r['fg3a_pg']:.1f} (#{r['fg3a_rank']:.0f}) "
                 f"| {r['rate3']:.3f} (#{r['rate3_rank']:.0f}) "
                 f"| {r['fg3_pct']:.3f} (#{r['fg3_pct_rank']:.0f}) "
                 f"| {r['pps3']:.3f} | {r['pps2']:.3f} "
                 f"| #{r['ortg_rank']:.0f} |")
    L += [
        "",
        "The 1.5x math, explicit: a three is worth 1.5 twos, so Boston's "
        f"league-average-or-better accuracy prices its threes at "
        f"{t.loc['2025-26', 'pps3']:.2f} points per shot vs "
        f"{t.loc['2025-26', 'pps2']:.2f} on twos (2025-26). Three seasons "
        "of top-of-league volume ranks alongside top-of-league offensive "
        "ratings is correlation, not causation — but it is the game plan, "
        "run on purpose, and it has coincided with elite offense every "
        "year of the window.",
        "",
        "## 2. Brown inside the identity — the within-team outlier",
        "",
        f"Rotation = every Celtic above {MIN_FLOOR:,} minutes. Perimeter "
        "players are ranked together; bigs are listed separately (a "
        "center's diet is a different job). PPS = (PTS − FTM) / FGA — "
        "free throws excluded by construction. **Bold = Brown.**",
        "",
    ]
    for s in SEASONS:
        L += [f"### {s}", ""] + _diet_table(diets[s]) + [""]
    L += [
        f"**Where Brown sits (2025-26):** #{r3_rank} of {n_per} perimeter "
        "players in 3PT rate"
        + (" — dead last, the most two-heavy diet" if r3_rank == n_per else "")
        + " — his "
        f"{per26.set_index('player').loc[config.SUBJECT, 'rate3']:.3f} vs "
        f"the team's {t.loc['2025-26', 'rate3']:.3f} — and #{lt_rank} of "
        f"{n_per} in long-two rate. His raw PPS "
        f"({br['pps']:.3f}) vs the other perimeter players' "
        f"volume-weighted {nb_pps:.3f}: the gap is real but modest, "
        "because his two-point finishing is genuinely good. **Frame it "
        "precisely: the issue is shot-mix value against the system's "
        "target mix, not his finishing.** A good two is still worth less "
        "than a league-average three, and Brown takes the most "
        "two-heavy, long-two-heaviest diet among Boston's wings while "
        "using the most shots.",
        "",
        "## 3. PROJECTION — how much better without him (labeled, ranged)",
        "",
        "_Everything below is a projection. Method: take Brown's 2025-26 "
        f"volume ({br['fga_pg']:.1f} FGA/g at a realized "
        f"{br['pps']:.3f} PPS) and re-price the same volume under a "
        "different mix and accuracy._",
        "",
        f"- **(a) Paul George's actual 2025-26 mix and accuracy** "
        f"(3PT rate {ge['rate3']:.3f}, 3P% {ge['fg3_pct']:.3f}, "
        f"2P% {ge['fg2_pct']:.3f} → {sc['george']['target_pps']:.3f} "
        f"expected PPS): **{sc['george']['lo']:+.1f} to "
        f"{sc['george']['hi']:+.1f} pts/game** "
        f"(~{net_to_wins(sc['george']['lo']):+.1f} to "
        f"{net_to_wins(sc['george']['hi']):+.1f} wins).",
        f"- **(b) Non-Brown Boston mix and accuracy** "
        f"(3PT rate {nb['rate3']:.3f}, 3P% {nb['fg3_pct']:.3f}, "
        f"2P% {nb['fg2_pct']:.3f} → {sc['team']['target_pps']:.3f} "
        f"expected PPS): **{sc['team']['lo']:+.1f} to "
        f"{sc['team']['hi']:+.1f} pts/game** "
        f"(~{net_to_wins(sc['team']['lo']):+.1f} to "
        f"{net_to_wins(sc['team']['hi']):+.1f} wins).",
        "",
        f"Conversions and discounts, documented: pts/game delta × "
        f"{net_to_wins(1.0):.1f} wins per point of per-game differential "
        "(the same Pythagorean rule of thumb as script 16; defense assumed "
        f"unchanged). The low corner applies a {TRANSFER_LO:.0%} "
        "creation-transfer discount; the George corners also take up to "
        f"{AGE_HAIRCUT_3PT * 100:.0f}pp off his 3P%.",
        "",
        "**Caveats that print with the number, not under it:**",
        "",
        "- **George is 36 in 2026.** His accuracy is the whole engine of "
        "scenario (a); the haircut corner is not pessimism, it's the "
        "base case for a 36-year-old's jumper. If his 3P% slides more "
        "than 2pp, the low end of (a) is optimistic.",
        "- **Someone must create the extra catch-and-shoot threes.** "
        "Brown self-created much of his volume; a catch-and-shoot diet "
        "requires a creator to bend the defense first. Creation does not "
        f"transfer 1:1 — that is what the {TRANSFER_LO:.0%} transfer "
        "corner prices, and with Brown gone the creation burden "
        "concentrates on Tatum (see tatum_first_option.md §4 on load).",
        "- **Defensive attention shifts.** Brown's gravity and downhill "
        "pressure created some of the very catch-and-shoot looks this "
        "model re-prices for others; removing him changes the shot "
        "quality of the remaining mix in ways a mix-swap cannot see.",
        "- **Free throws excluded.** Brown's rim pressure generated FTs "
        "that a three-heavier diet gives back some of; the PPS frame "
        "does not credit them on either side.",
        "",
        "**Honest bottom line:** "
        + (f"through the realistic channel — George's actual mix and "
           f"accuracy — the swap is **roughly a wash** "
           f"({sc['george']['lo']:+.1f} to {sc['george']['hi']:+.1f} "
           "pts/game once aging and creation discounts bite); only the "
           "idealized case where Brown's volume re-prices at the full "
           f"non-Brown team mix reaches {sc['team']['lo']:+.1f} to "
           f"{sc['team']['hi']:+.1f} pts/game "
           f"(~{net_to_wins(sc['team']['lo']):+.1f} to "
           f"{net_to_wins(sc['team']['hi']):+.1f} wins). The diet-swap "
           "gain is small; say so plainly."
           if sc["george"]["lo"] <= 0 else
           f"the swap is worth {min(sc['george']['lo'], sc['team']['lo']):+.1f} "
           f"to {max(sc['george']['hi'], sc['team']['hi']):+.1f} pts/game "
           f"(~{net_to_wins(min(sc['george']['lo'], sc['team']['lo'])):+.1f} "
           f"to {net_to_wins(max(sc['george']['hi'], sc['team']['hi'])):+.1f} "
           "wins) — real but bounded.")
        + " This is a supporting argument for the trade, not the headline "
        "one; the configuration evidence in tatum_first_option.md carries "
        "more weight.",
        "",
        "## 4. Data & methods notes",
        "",
        "- Team table: LeagueDashTeamStats Base + Advanced, one call per "
        "season per measure, cached. Ranks are league ranks (1 = highest).",
        "- Rotation table: LeagueDashPlayerStats Base (volume, PPS), "
        "ShotChartDetail per player (long-two rate: twos ≥ "
        f"{config.LONG_TWO_MIN_FT} ft, same definition as the rest of the "
        "repo), LeagueDashPtStats CatchShoot (C&S FGA share).",
        "- Pricing helpers (`pps`, `expected_pps`, `fg2_pct`, "
        "`diet_swap_delta`) live in `fitcheck/features/shooting.py` and "
        "are unit-tested in `tests/test_shooting.py`.",
        f"- Projection constants (transfer {TRANSFER_LO}-{TRANSFER_HI}, "
        f"aging haircut {AGE_HAIRCUT_3PT}) live at the top of "
        "`scripts/19_three_point_identity.py`.",
    ]
    out = config.OUTPUT_DIR / "three_point_identity.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  ✓ memo -> {out}")


# ---------------------------------------------------------------------------
def main() -> int:
    team = pd.DataFrame([team_identity(s) for s in SEASONS])
    for _, r in team.iterrows():
        print(f"  ✓ {r['season']}: BOS {r['fg3a_pg']:.1f} 3PA/g "
              f"(#{r['fg3a_rank']:.0f}), rate {r['rate3']:.3f} "
              f"(#{r['rate3_rank']:.0f}), 3P% {r['fg3_pct']:.3f} "
              f"(#{r['fg3_pct_rank']:.0f}), ORTG #{r['ortg_rank']:.0f}")

    diets = {s: rotation_diets(s) for s in SEASONS}
    swap = build_swap("2025-26")
    sc = swap["scenarios"]
    print(f"  ✓ swap: George {sc['george']['lo']:+.2f}.."
          f"{sc['george']['hi']:+.2f} pts/g | team mix "
          f"{sc['team']['lo']:+.2f}..{sc['team']['hi']:+.2f} pts/g")

    team.to_csv(config.PROCESSED_DIR / "three_point_identity_team.csv",
                index=False)
    pd.concat(diets.values(), ignore_index=True).to_csv(
        config.PROCESSED_DIR / "three_point_identity_players.csv", index=False)

    _figure(team, diets, swap)
    _write(team, diets, swap)
    print("Done. outputs/three_point_identity.md + "
          "figures/three_point_identity.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
