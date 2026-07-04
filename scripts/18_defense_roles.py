"""What Boston actually lost defensively — Brown's defense split by role.

Builds ON TOP of scripts/14_defense_check.py (which refuted the 'declining
defense' angle and told the trade case to leave defense out of it). This
script asks the sharper post-trade question: what kind of defender left?
Split into on-ball (matchup lens) and off-ball (activity lens), with Tatum
through the identical code path as the benchmark — same rules as every
other memo in this repo.

  ON-BALL:  LeagueSeasonMatchups (partial possessions defended, PPP allowed,
            matchup FG%, TOV forced), a matchup-difficulty cut (vs USG>25%
            players and vs each opponent's #1-usage option), and defended
            FG% vs shooters' norms (PlayerDashPtShotDefend).
  OFF-BALL: hustle tracking per 36 (deflections, loose balls, charges,
            contested shots 2s/3s, box-outs), contested-DREB share,
            DEF_RATING on/off.
  NICHE:    P&R ball-handler defense (Synergy, skipped gracefully if the
            endpoint won't serve a season) and transition defense
            (opponent fast-break points per 48 with each star on vs off).
  CUT:      cross-matching / defended-up-a-position — stats.nba.com does
            not expose matchup position data cheaply; noted in the memo.

Outputs:
  * data/processed/defense_roles.csv
  * outputs/figures/defense_roles.png
  * outputs/defense_roles.md
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
from fitcheck.features import onoff

BROWN, TATUM = config.SUBJECT_ID, config.CELTICS_ROTATION["Jayson Tatum"]
PLAYERS = {"Jaylen Brown": BROWN, "Jayson Tatum": TATUM}
RED, GREEN, GREY = "#c0392b", "#007A33", "#95a5a6"
HIGH_USG = 25.0          # 'high-usage opponent' threshold (USG%)
STAR_MPG, STAR_GP = 24.0, 25   # qualifiers for a team's '#1 option'


# ---------------------------------------------------------------------------
# On-ball: matchups
# ---------------------------------------------------------------------------
def _usage_table(season: str) -> pd.DataFrame:
    adv = nba.league_player_stats(season, measure="Advanced")
    out = adv[["PLAYER_ID", "TEAM_ID", "GP", "MIN", "USG_PCT"]].copy()
    # The endpoint returns USG_PCT as a fraction (0.28); normalize to 0-100.
    if out["USG_PCT"].max() <= 1.5:
        out["USG_PCT"] = out["USG_PCT"] * 100
    return out


def _primary_options(usage: pd.DataFrame) -> set[int]:
    """Each team's highest-usage qualifying player (the '#1 option')."""
    q = usage[(usage["MIN"] >= STAR_MPG) & (usage["GP"] >= STAR_GP)]
    idx = q.groupby("TEAM_ID")["USG_PCT"].idxmax()
    return set(q.loc[idx, "PLAYER_ID"].astype(int))


def _matchup_agg(mu: pd.DataFrame) -> dict:
    poss = mu["PARTIAL_POSS"].sum()
    if not poss:
        return {"poss": 0.0}
    return {
        "poss": float(poss),
        "ppp": mu["PLAYER_PTS"].sum() / poss,
        "fg_pct": mu["MATCHUP_FGM"].sum() / max(mu["MATCHUP_FGA"].sum(), 1),
        "tov_per100": 100 * mu["MATCHUP_TOV"].sum() / poss,
    }


def onball_row(pid: int, season: str) -> dict:
    mu = nba.season_matchups(pid, season)
    usage = _usage_table(season)
    mu = mu.merge(usage.rename(columns={"PLAYER_ID": "OFF_PLAYER_ID"})
                  [["OFF_PLAYER_ID", "USG_PCT"]],
                  on="OFF_PLAYER_ID", how="left")
    primaries = _primary_options(usage)

    total = _matchup_agg(mu)
    high = _matchup_agg(mu[mu["USG_PCT"] >= HIGH_USG])
    prim = _matchup_agg(mu[mu["OFF_PLAYER_ID"].isin(primaries)])
    return {
        **{f"all_{k}": v for k, v in total.items()},
        **{f"high_{k}": v for k, v in high.items()},
        **{f"prim_{k}": v for k, v in prim.items()},
        "high_share": high["poss"] / total["poss"] if total["poss"] else np.nan,
        "prim_share": prim["poss"] / total["poss"] if total["poss"] else np.nan,
    }


def shot_defend_row(pid: int, season: str) -> dict:
    df = nba.player_shot_defend(pid, season)
    out = {}
    for cat, key in [("Overall", "dfg_overall"), ("Less Than 6 Ft", "dfg_rim")]:
        r = df[df["DEFENSE_CATEGORY"] == cat]
        if not r.empty:
            out[key] = float(r.iloc[0]["PCT_PLUSMINUS"]) * 100
            out[key + "_fga"] = float(r.iloc[0]["D_FGA"])
    return out


# ---------------------------------------------------------------------------
# Off-ball: hustle, rebounding, on/off
# ---------------------------------------------------------------------------
def offball_row(pid: int, season: str) -> dict:
    hu = nba.league_hustle(season)
    h = hu[hu["PLAYER_ID"] == pid].iloc[0]
    per36 = lambda c: float(h[c]) / float(h["MIN"]) * 36
    rb = nba.league_player_tracking(season, pt_measure="Rebounding")
    r = rb[rb["PLAYER_ID"] == pid].iloc[0]
    adv = nba.league_player_stats(season, measure="Advanced")
    a = adv[adv["PLAYER_ID"] == pid].iloc[0]
    return {
        "deflections36": per36("DEFLECTIONS"),
        "loose36": per36("LOOSE_BALLS_RECOVERED"),
        "charges": float(h["CHARGES_DRAWN"]),
        "contested36": per36("CONTESTED_SHOTS"),
        "contested2_36": per36("CONTESTED_SHOTS_2PT"),
        "contested3_36": per36("CONTESTED_SHOTS_3PT"),
        "boxouts36": per36("DEF_BOXOUTS"),
        "dreb_pct": float(a["DREB_PCT"]) * 100,
        "dreb_contest_pct": float(r["DREB_CONTEST_PCT"]) * 100,
    }


def onoff_def_row(pid: int, season: str) -> dict:
    adv = onoff.on_off_table(nba.team_on_off(config.CELTICS_TEAM_ID, season))
    key = adv.columns[0]
    name = "Brown" if pid == BROWN else "Tatum"
    r = adv[adv[key].str.contains(name, na=False)].iloc[0]
    misc = nba.team_on_off(config.CELTICS_TEAM_ID, season, measure="Misc")
    m = misc[misc["VS_PLAYER_ID"] == pid].set_index("COURT_STATUS")
    fb48 = {s: float(m.loc[s, "OPP_PTS_FB"]) / float(m.loc[s, "MIN"]) * 48
            for s in ("ON", "OFF")}
    return {"def_on": float(r["DEF_RATING_ON"]),
            "def_off": float(r["DEF_RATING_OFF"]),
            "opp_fb48_on": fb48["ON"], "opp_fb48_off": fb48["OFF"]}


def synergy_row(pid: int, season: str) -> dict:
    try:
        sy = nba.synergy_playtype(season, play_type="PRBallHandler")
        r = sy[sy["PLAYER_ID"] == pid]
        if r.empty:
            return {}
        r = r.iloc[0]
        return {"pnr_ppp": float(r["PPP"]), "pnr_poss": float(r["POSS"]),
                "pnr_pctile": float(r["PERCENTILE"])}
    except Exception as exc:  # noqa: BLE001 - endpoint is flaky by design
        print(f"    ! synergy unavailable for {season}: {exc}")
        return {}


# ---------------------------------------------------------------------------
def build() -> pd.DataFrame:
    rows = []
    for name, pid in PLAYERS.items():
        for season in config.SEASONS:
            print(f"  {name} {season}")
            row = {"player": name, "season": season}
            row.update(onball_row(pid, season))
            row.update(shot_defend_row(pid, season))
            row.update(offball_row(pid, season))
            row.update(onoff_def_row(pid, season))
            row.update(synergy_row(pid, season))
            rows.append(row)
    return pd.DataFrame(rows)


def _figure(df: pd.DataFrame) -> None:
    d = df.set_index(["player", "season"])
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.0))

    # A: on-ball PPP allowed, 2024-25 (both healthy). All three cuts share
    # the same partial-possession basis; Synergy P&R PPP (different basis)
    # stays in the memo table only.
    ax = axes[0]
    cats = [("all_ppp", "All matchups"), ("high_ppp", f"vs USG>{HIGH_USG:.0f}%"),
            ("prim_ppp", "vs #1 options")]
    x = np.arange(len(cats)); w = 0.36
    for i, (p, c) in enumerate([("Jaylen Brown", RED), ("Jayson Tatum", GREEN)]):
        vals = [d.loc[(p, "2024-25")].get(k, np.nan) for k, _ in cats]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=p.split()[1], color=c)
        for rect in bars:
            if not np.isnan(rect.get_height()):
                ax.annotate(f"{rect.get_height():.2f}",
                            (rect.get_x() + rect.get_width() / 2,
                             rect.get_height()),
                            textcoords="offset points", xytext=(0, 4),
                            ha="center", fontsize=12, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in cats], fontsize=12)
    ax.set_ylabel("Points allowed per partial matchup poss.", fontsize=12.5)
    ax.set_title("On-ball, 2024-25 — points allowed as primary defender",
                 fontsize=14, fontweight="bold", loc="left")
    ax.legend(fontsize=11.5, loc="upper left")
    ax.margins(y=0.28)

    # B: off-ball activity per 36, 2024-25
    ax = axes[1]
    cats2 = [("deflections36", "Deflections"), ("loose36", "Loose balls"),
             ("contested2_36", "Contested 2s"), ("contested3_36", "Contested 3s"),
             ("boxouts36", "Box-outs")]
    x = np.arange(len(cats2))
    for i, (p, c) in enumerate([("Jaylen Brown", RED), ("Jayson Tatum", GREEN)]):
        vals = [d.loc[(p, "2024-25")][k] for k, _ in cats2]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=p.split()[1], color=c)
        for rect in bars:
            ax.annotate(f"{rect.get_height():.2f}",
                        (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        textcoords="offset points", xytext=(0, 4),
                        ha="center", fontsize=11.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([lab for _, lab in cats2], fontsize=12)
    ax.set_ylabel("Per 36 minutes", fontsize=12.5)
    ax.set_title("Off-ball, 2024-25 — activity per 36",
                 fontsize=14, fontweight="bold", loc="left")
    ax.legend(fontsize=11.5)
    ax.margins(y=0.25)

    fig.suptitle("What Boston lost defensively — Brown vs Tatum, same lens",
                 fontsize=16.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = config.FIG_DIR / "defense_roles.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


def _write(df: pd.DataFrame) -> None:
    d = df.set_index(["player", "season"])
    b24, b25 = d.loc[("Jaylen Brown", "2024-25")], d.loc[("Jaylen Brown", "2025-26")]
    t24, t25 = d.loc[("Jayson Tatum", "2024-25")], d.loc[("Jayson Tatum", "2025-26")]

    def has(r, k):
        return k in r and pd.notna(r[k])

    L = [
        "# What Boston Lost Defensively — Brown's Defense by Role",
        "",
        "_Extends [defense_check.md](defense_check.md), which already "
        "refuted the 'declining defense' trade-case angle and concluded "
        "defense is closer to a point in Brown's favor. This memo asks the "
        "post-trade question instead: what kind of defender left? On-ball "
        "vs off-ball, Tatum through the identical code path as benchmark. "
        "**Tatum's 2025-26 columns sit on 16 games (injury) — treat them "
        "as context, not evidence.**_",
        "",
        "## 1. On-ball — the matchup lens",
        "",
        "Season matchup totals as the PRIMARY defender (partial "
        "possessions), with two difficulty cuts: matchups against "
        f"high-usage (>{HIGH_USG:.0f}% USG) opponents, and against each "
        "opponent team's #1-usage option.",
        "",
        "| Metric | Brown 24-25 | Tatum 24-25 | Brown 25-26 | Tatum 25-26 |",
        "|---|---|---|---|---|",
    ]

    def line(lab, key, fmt="{:.2f}"):
        vals = []
        for r in (b24, t24, b25, t25):
            vals.append(fmt.format(r[key]) if has(r, key) else "—")
        return f"| {lab} | " + " | ".join(vals) + " |"

    L += [
        line("Partial poss defended", "all_poss", "{:.0f}"),
        line("PPP allowed (all)", "all_ppp"),
        line("Matchup FG% (all)", "all_fg_pct", "{:.3f}"),
        line("TOV forced / 100 poss", "all_tov_per100", "{:.1f}"),
        line(f"Share of poss vs USG>{HIGH_USG:.0f}%", "high_share", "{:.0%}"),
        line(f"PPP allowed vs USG>{HIGH_USG:.0f}%", "high_ppp"),
        line("Share of poss vs #1 options", "prim_share", "{:.0%}"),
        line("PPP allowed vs #1 options", "prim_ppp"),
        line("Defended FG% vs norm (all, pts)", "dfg_overall", "{:+.1f}"),
        line("Defended FG% vs norm (rim, pts)", "dfg_rim", "{:+.1f}"),
        "",
        "**Read (2024-25, both healthy):** Brown spent a clearly larger "
        "share of his defended possessions on high-usage players "
        f"({b24['high_share']:.0%} vs {t24['high_share']:.0%}) and on "
        f"opponents' #1 options ({b24['prim_share']:.0%} vs "
        f"{t24['prim_share']:.0%}) — **Brown took the harder assignment**. "
        f"His overall points-allowed rate ran higher than Tatum's "
        f"({b24['all_ppp']:.2f} vs {t24['all_ppp']:.2f} per partial poss) "
        "— but that comparison is confounded by exactly that assignment "
        "difficulty: against the #1 options themselves Brown allowed "
        f"{b24['prim_ppp']:.2f} to Tatum's {t24['prim_ppp']:.2f}. In "
        "2025-26, at 35% offensive usage, Brown's defended-FG% margin "
        f"went from neutral ({b24['dfg_overall']:+.1f}) to "
        f"{b25['dfg_overall']:+.1f} overall and {b25['dfg_rim']:+.1f} at "
        "the rim — the improvement defense_check.md already flagged.",
        "",
        "## 2. Off-ball — the activity lens",
        "",
        "| Per 36 (except noted) | Brown 24-25 | Tatum 24-25 | Brown 25-26 | Tatum 25-26 |",
        "|---|---|---|---|---|",
        line("Deflections", "deflections36"),
        line("Loose balls recovered", "loose36"),
        line("Charges drawn (season total)", "charges", "{:.0f}"),
        line("Contested shots", "contested36"),
        line("— contested 2s", "contested2_36"),
        line("— contested 3s", "contested3_36"),
        line("Defensive box-outs", "boxouts36"),
        line("DREB% (advanced)", "dreb_pct", "{:.1f}"),
        line("Contested-DREB share", "dreb_contest_pct", "{:.0f}%"),
        line("Team DEF_RTG on floor", "def_on", "{:.1f}"),
        line("Team DEF_RTG off floor", "def_off", "{:.1f}"),
        "",
        "**Read:** the off-ball profile is workmanlike, not elite — "
        "deflection and loose-ball rates in the same band as Tatum's, "
        "similar contest volume with a heavier 3-point-contest tilt, "
        "fewer box-outs and a materially lower defensive-rebound load "
        f"(DREB% {b24['dreb_pct']:.1f} vs {t24['dreb_pct']:.1f} in "
        "2024-25). The DEF_RTG on/off rows keep the caveat from "
        "defense_check.md §3: both stars' 'off' minutes lean on Boston's "
        "defense-first bench units, so both look worse on-floor by this "
        "one measure; it is the noisiest row in the table for either "
        "player.",
        "",
        "## 3. Niche cuts (the two the data supports)",
        "",
    ]
    if has(b24, "pnr_ppp"):
        L += [
            "**Screen navigation (Synergy, defending P&R ball-handlers):**",
            "",
            "| | Poss | PPP allowed | League pctile |",
            "|---|---|---|---|",
        ]
        for lab, r in [("Brown 24-25", b24), ("Tatum 24-25", t24),
                       ("Brown 25-26", b25), ("Tatum 25-26", t25)]:
            if has(r, "pnr_ppp"):
                L.append(f"| {lab} | {r['pnr_poss']:.0f} | {r['pnr_ppp']:.2f} "
                         f"| {r['pnr_pctile']:.0%} |")
        L += [
            "",
            f"Brown defended more P&R ball-handler possessions than Tatum "
            f"in 2024-25 ({b24['pnr_poss']:.0f} vs {t24['pnr_poss']:.0f}) "
            f"at a better PPP ({b24['pnr_ppp']:.2f} vs "
            f"{t24['pnr_ppp']:.2f}) — guards hunting the Boston stars got "
            "less out of hunting Brown.",
            "",
        ]
    else:
        L += ["_Synergy play-type defense unavailable from the endpoint "
              "for these seasons — skipped rather than approximated._", ""]
    L += [
        "**Transition defense (opponent fast-break points per 48, on vs "
        "off):**",
        "",
        "| | On floor | Off floor | Delta |",
        "|---|---|---|---|",
    ]
    for lab, r in [("Brown 24-25", b24), ("Tatum 24-25", t24),
                   ("Brown 25-26", b25), ("Tatum 25-26", t25)]:
        L.append(f"| {lab} | {r['opp_fb48_on']:.1f} | {r['opp_fb48_off']:.1f} "
                 f"| {r['opp_fb48_on'] - r['opp_fb48_off']:+.1f} |")
    L += [
        "",
        "Opponents got more fast-break points with Brown on the floor in "
        f"both seasons ({b24['opp_fb48_on'] - b24['opp_fb48_off']:+.1f} "
        f"and {b25['opp_fb48_on'] - b25['opp_fb48_off']:+.1f} per 48). "
        "Read alongside [live_ball_turnovers.md](live_ball_turnovers.md): "
        "part of that is his own live-ball giveaways starting the break, "
        "not (or not only) a failure to get back — the two files measure "
        "the same coin from two sides. Tatum shows the same-signed but "
        "smaller effect in 2024-25, and per-48 opponent FB points are "
        "pace- and lineup-confounded; deltas this size are suggestive, "
        "not damning.",
        "",
        "**Cut:** cross-matching / how often each defended up a position — "
        "stats.nba.com does not expose matchup position data at "
        "reasonable cost; reported as not measured rather than guessed.",
        "",
        "## 4. Verdict — what did Boston actually lose?",
        "",
        f"- **The primary on-ball defender, and a good one.** A "
        f"{b24['prim_share']:.0%}-to-{t24['prim_share']:.0%} edge over "
        "Tatum in share of possessions spent on opponents' #1 options, "
        "slightly better points-allowed against those toughest matchups, "
        "better P&R ball-handler defense, and 2025-26 defended-FG% "
        f"margins ({b25['dfg_overall']:+.1f} overall, "
        f"{b25['dfg_rim']:+.1f} at the rim) that are legitimately "
        "excellent. This is the strongest pro-Brown fact in the project "
        "and it is printed prominently on purpose.",
        "- **An ordinary off-ball defender.** Activity and rebounding "
        "metrics are fine-not-special; the versatility claim we could "
        "not measure is acknowledged above.",
        "- **The honest weighing:** the trade case (shot diet, price, "
        "flow) pays for itself or it doesn't — it cannot lean on defense, "
        "and post-trade Boston must now cover #1-option assignments that "
        "Brown was absorbing. Tatum's matchup profile shows he was NOT "
        "doing that job while Brown was here; someone else now has to.",
        "",
        "## 5. Methods",
        "",
        "- Matchups: LeagueSeasonMatchups season totals (partial "
        "possessions; PPP = points allowed / partial poss). High-usage "
        f"cut at USG>{HIGH_USG:.0f}% from LeagueDashPlayerStats Advanced; "
        f"'#1 option' = each team's top-USG player with ≥{STAR_MPG:.0f} "
        f"MPG and ≥{STAR_GP} GP.",
        "- Defended FG%: PlayerDashPtShotDefend PCT_PLUSMINUS (shooters' "
        "FG% vs their season norm when this player is the closest "
        "defender).",
        "- Hustle: LeagueHustleStats totals scaled to per-36. Transition: "
        "TeamPlayerOnOffDetails 'Misc' OPP_PTS_FB scaled per 48 minutes "
        "(not possession-adjusted — noted).",
        "- All pulls cached (`data/cache/`); driver "
        "`scripts/18_defense_roles.py`.",
    ]
    out = config.OUTPUT_DIR / "defense_roles.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  ✓ memo -> {out}")


def main() -> int:
    df = build()
    df.to_csv(config.PROCESSED_DIR / "defense_roles.csv", index=False)
    _figure(df)
    _write(df)
    print("Done. outputs/defense_roles.md + figures/defense_roles.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
