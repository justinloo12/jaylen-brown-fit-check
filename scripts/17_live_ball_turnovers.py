"""The hidden tax: Brown's live-ball turnovers and what they cost.

The bad-shot index prices the shot Brown takes; this script prices the
possessions he gives away. A live-ball turnover (steal credited) hands the
opponent a running start; a dead-ball turnover at least lets the defense
set. From full play-by-play we classify every Brown turnover and walk the
opponent's ensuing possession to count the points surrendered — then run
the IDENTICAL computation for Tatum and for the Celtics as a whole (the
benchmark; a number with no baseline is a vibe).

Heaviest pull in the project: one PlayByPlayV3 call per Celtics game
(2 seasons x 82 games), every one cached in data/cache/.

Outputs:
  * data/processed/live_ball_turnovers.csv
  * outputs/figures/live_ball_turnovers.png
  * outputs/live_ball_turnovers.md
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
from fitcheck.features.turnovers import (FAST_WINDOW_SECONDS,
                                         summarize_ledger, turnover_ledger)

BOS = config.CELTICS_TEAM_ID
BROWN, TATUM = config.SUBJECT_ID, config.CELTICS_ROTATION["Jayson Tatum"]
RED, GREEN, GREY = "#c0392b", "#007A33", "#95a5a6"
TEAM_HINT = "CELTIC"  # how Boston team rebounds read in PBP descriptions


def season_ledgers(season: str) -> tuple[dict[str, pd.DataFrame], int]:
    """Concatenated turnover ledgers for Brown / Tatum / all Celtics over
    every game of a season. Returns (ledgers, games_failed)."""
    tm = nba.team_gamelogs(BOS, season).sort_values("GAME_ID")
    parts = {"Jaylen Brown": [], "Jayson Tatum": [], "Celtics (team)": []}
    failed = 0
    for _, g in tm.iterrows():
        try:
            pbp = nba.play_by_play(g["GAME_ID"])
        except Exception as exc:  # noqa: BLE001 - log and keep going
            print(f"    ! PBP failed for {g['GAME_ID']}: {exc}")
            failed += 1
            continue
        home = "vs." in g["MATCHUP"]
        kw = dict(team_is_home=home, team_hint=TEAM_HINT)
        parts["Jaylen Brown"].append(
            turnover_ledger(pbp, BOS, player_id=BROWN, **kw))
        parts["Jayson Tatum"].append(
            turnover_ledger(pbp, BOS, player_id=TATUM, **kw))
        parts["Celtics (team)"].append(turnover_ledger(pbp, BOS, **kw))
    ledgers = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame()
               for k, v in parts.items()}
    return ledgers, failed


def player_minutes(pid: int, season: str) -> tuple[float, int]:
    logs = nba.player_gamelogs(pid, season)
    return float(logs["MIN"].sum()), len(logs)


def build_rows() -> pd.DataFrame:
    rows = []
    for season in config.SEASONS:
        print(f"  season {season} (up to 82 PBP pulls; cached after first run)")
        ledgers, failed = season_ledgers(season)
        for who, ledger in ledgers.items():
            s = summarize_ledger(ledger)
            if who == "Jaylen Brown":
                mins, gp = player_minutes(BROWN, season)
            elif who == "Jayson Tatum":
                mins, gp = player_minutes(TATUM, season)
            else:
                tm = nba.team_gamelogs(BOS, season)
                mins, gp = float(tm["MIN"].sum() * 5), len(tm)
            rows.append({"season": season, "who": who, "gp": gp,
                         "minutes": mins, "games_failed": failed, **s,
                         "live_per36": s["live"] / mins * 36 if mins else np.nan,
                         "pts_against_per_g": s["pts_against"] / gp if gp else np.nan})
            print(f"    {who}: {s['tov']} TOV, {s['live']} live "
                  f"({s['live_share']:.0%}), {s['pts_against']:.0f} pts against")
    return pd.DataFrame(rows)


def _figure(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 5.8))
    players = ["Jaylen Brown", "Jayson Tatum"]
    colors = {"Jaylen Brown": RED, "Jayson Tatum": GREEN}
    seasons = config.SEASONS
    d = df.set_index(["who", "season"])

    ax = axes[0]
    x = np.arange(len(seasons)); w = 0.36
    for i, p in enumerate(players):
        vals = [d.loc[(p, s), "live_per36"] for s in seasons]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=p.split()[1],
                      color=colors[p])
        for rect, s in zip(bars, seasons):
            n = d.loc[(p, s), "live"]
            ax.annotate(f"{rect.get_height():.2f}\n({n:.0f} live)",
                        (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        textcoords="offset points", xytext=(0, 4),
                        ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(seasons, fontsize=12.5)
    ax.set_ylabel("Live-ball turnovers per 36 min", fontsize=12.5)
    ax.set_title("Live-ball turnover rate (steal credited)",
                 fontsize=14, fontweight="bold", loc="left")
    ax.legend(fontsize=11.5); ax.margins(y=0.28)

    ax = axes[1]
    for i, p in enumerate(players):
        vals = [d.loc[(p, s), "pts_per_live"] for s in seasons]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=p.split()[1],
                      color=colors[p])
        for rect, s in zip(bars, seasons):
            tot = d.loc[(p, s), "pts_against"]
            ax.annotate(f"{rect.get_height():.2f}\n({tot:.0f} pts)",
                        (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        textcoords="offset points", xytext=(0, 4),
                        ha="center", fontsize=11, fontweight="bold")
    team = [d.loc[("Celtics (team)", s), "pts_per_live"] for s in seasons]
    for xi, tv in zip(x, team):
        ax.hlines(tv, xi - 0.42, xi + 0.42, color="#333333", ls="--", lw=1.6)
        ax.annotate(f"team {tv:.2f}", (xi + 0.44, tv), fontsize=10,
                    va="center", color="#333333")
    ax.set_xticks(x); ax.set_xticklabels(seasons, fontsize=12.5)
    ax.set_ylabel("Opponent points per live-ball TO", fontsize=12.5)
    ax.set_title("What each live-ball TO cost (total season pts in label)",
                 fontsize=14, fontweight="bold", loc="left")
    ax.legend(fontsize=11.5); ax.margins(y=0.28)

    fig.suptitle("The hidden tax — points surrendered off live-ball turnovers",
                 fontsize=16.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = config.FIG_DIR / "live_ball_turnovers.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


def _write(df: pd.DataFrame) -> None:
    d = df.set_index(["who", "season"])

    def r(who, season):
        return d.loc[(who, season)]

    def row_md(who, season):
        x = r(who, season)
        return (f"| {who} | {season} | {x['tov']:.0f} | {x['live']:.0f} "
                f"({x['live_share']:.0%}) | {x['live_per36']:.2f} "
                f"| {x['pts_against']:.0f} | {x['pts_per_live']:.2f} "
                f"| {x['fast_share']:.0%} |")

    b25, b24 = r("Jaylen Brown", "2025-26"), r("Jaylen Brown", "2024-25")
    t24 = r("Jayson Tatum", "2024-25")
    tm25 = r("Celtics (team)", "2025-26")
    failed = int(df["games_failed"].max())

    L = [
        "# The Hidden Tax — Live-Ball Turnovers, Priced from Play-by-Play",
        "",
        "_Companion to [tatum_first_option.md](tatum_first_option.md). The "
        "bad-shot index prices the shots; this prices the giveaways. Every "
        "Celtics game's play-by-play, both seasons; identical code path for "
        "Brown, Tatum, and the team baseline. Definitions in §3._",
        "",
        "## 1. The ledger",
        "",
        "| Who | Season | TOV (PBP) | Live-ball (share) | Live per 36 "
        "| Opp pts off them | Pts per live TO | Fast-conv. share |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for who in ["Jaylen Brown", "Jayson Tatum", "Celtics (team)"]:
        for season in config.SEASONS:
            L.append(row_md(who, season))
    L += [
        "",
        "## 2. Honest read",
        "",
        f"- **The clean comparison is 2024-25** (both healthy): Brown gave "
        f"the ball away live {b24['live_per36']:.2f} times per 36 vs "
        f"Tatum's {t24['live_per36']:.2f}, and each of Brown's live TOs "
        f"cost {b24['pts_per_live']:.2f} opponent points vs "
        f"{t24['pts_per_live']:.2f} for Tatum. Say it plainly: **Brown's "
        "live-ball rate was LOWER than Tatum's when both were healthy** — "
        "on rate, this angle does not indict Brown relative to the star "
        "Boston kept; only his per-giveaway cost ran higher.",
        f"- **2025-26 is Brown's ball-dominant season** (usage ~35%): "
        f"{b25['live']:.0f} live-ball turnovers that surrendered "
        f"{b25['pts_against']:.0f} points — {b25['pts_against_per_g']:.1f} "
        f"per game he played — of which {b25['fast_share']:.0%} were "
        f"converted fast (first opponent attempt within "
        f"{FAST_WINDOW_SECONDS:.0f}s). Tatum's 2025-26 column sits on 16 "
        "games and is context, not evidence.",
        f"- **Benchmark:** the Celtics as a whole gave up "
        f"{tm25['pts_per_live']:.2f} points per live-ball TO in 2025-26 "
        "(dashed line in the figure). A star's live TOs are not obviously "
        "worse than anyone else's — the tax is in *how many* he commits at "
        "his usage, not a special per-TO penalty.",
        "- The narrative link to the shot-diet finding is stated only as "
        "far as the data goes: Brown's iso/3+-dribble rate rose 0.53 → "
        "0.64 in 2025-26 (tatum_vs_brown.md §1) while he carried his "
        "highest usage; the live-ball counts above are the giveaway side "
        "of that ball-dominant diet. We measured the cost; we did not "
        "measure causation between dribble counts and steals, and don't "
        "claim it.",
        "",
        "## 3. Definitions & methods",
        "",
        "- **Live-ball TO** = a steal was credited on the event (PBP V3 "
        "shows the steal as a companion row at the identical clock). "
        "Offensive fouls, travels, out-of-bounds, violations = dead-ball.",
        "- **Points off a live TO** = opponent points from the steal until "
        "Boston next gains possession (next Boston shot attempt, FT, "
        "turnover, rebound incl. team rebounds, or period end). Opponent "
        "offensive rebounds and and-1s stay in the window by design.",
        f"- **Fast conversion** = first opponent attempt within "
        f"{FAST_WINDOW_SECONDS:.0f} seconds of the steal *and* points "
        "scored in the window.",
        "- PBP turnover counts can differ from official box scores by ~1 "
        "per game on bookkeeping edge cases (e.g. 5-second inbound calls); "
        "player-level counts matched the box score in spot checks.",
        f"- Games with failed PBP pulls this run: {failed} (of 82 per "
        "season; a rerun backfills from cache).",
        "- Code: `fitcheck/features/turnovers.py` (unit-tested in "
        "`tests/test_turnovers.py`); driver `scripts/17_live_ball_turnovers.py`.",
    ]
    out = config.OUTPUT_DIR / "live_ball_turnovers.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  ✓ memo -> {out}")


def main() -> int:
    df = build_rows()
    df.to_csv(config.PROCESSED_DIR / "live_ball_turnovers.csv", index=False)
    _figure(df)
    _write(df)
    print("Done. outputs/live_ball_turnovers.md + figures/live_ball_turnovers.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
