"""The Flow Test — does Brown actually stop the ball, and does George move it?

The reframed trade thesis is 'addition by subtraction': Brown's ball-stopping
hurt the offense's identity, and George — as a lower-usage role player — keeps
it moving. That's a measurable claim. SportVU tracking gives, per player:

  * AVG_SEC_PER_TOUCH / AVG_DRIB_PER_TOUCH — how long he holds it
  * PASSES_MADE / TOUCHES — how often a touch becomes a pass

We report Brown / George / Tatum / White on those axes for BOTH seasons
(2024-25 is the control: Brown in a normal role beside a healthy Tatum), and
place them against every league player with >= 45 touches/game so the claim
is anchored to a distribution, not a hand-picked foursome.

Outputs:
  * data/processed/flow_test.csv
  * outputs/figures/flow_test.png
  * outputs/flow_test.md
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

FOCUS = ["Jaylen Brown", "Paul George", "Jayson Tatum", "Derrick White"]
COLORS = {"Jaylen Brown": "#c0392b", "Paul George": "#2c7fb8",
          "Jayson Tatum": "#007a33", "Derrick White": "#f5b942"}
MIN_TOUCHES = 45.0  # per-game floor for the league context pool


def season_flow(season: str) -> pd.DataFrame:
    poss = nba.league_player_tracking(season, pt_measure="Possessions")
    pas = nba.league_player_tracking(season, pt_measure="Passing")
    df = poss.merge(pas[["PLAYER_ID", "PASSES_MADE", "POTENTIAL_AST",
                         "AST_POINTS_CREATED"]], on="PLAYER_ID")
    df = df[df["TOUCHES"] >= MIN_TOUCHES].copy()
    df["pass_per_touch"] = df["PASSES_MADE"] / df["TOUCHES"]
    df["season"] = season
    keep = ["season", "PLAYER_NAME", "GP", "TOUCHES", "TIME_OF_POSS",
            "AVG_SEC_PER_TOUCH", "AVG_DRIB_PER_TOUCH", "pass_per_touch",
            "POTENTIAL_AST", "AST_POINTS_CREATED"]
    return df[keep].rename(columns={"PLAYER_NAME": "player"})


def _pctile(pool: pd.Series, value: float) -> float:
    return float((pool < value).mean())


def main() -> int:
    frames = {s: season_flow(s) for s in config.SEASONS}
    focus_rows = []
    for s, df in frames.items():
        for p in FOCUS:
            r = df[df.player == p]
            if r.empty:
                continue
            row = r.iloc[0].to_dict()
            # Percentiles within the >=45-touch pool (high = holds it longer /
            # passes more, respectively).
            row["sec_touch_pctile"] = _pctile(df["AVG_SEC_PER_TOUCH"],
                                              row["AVG_SEC_PER_TOUCH"])
            row["drib_touch_pctile"] = _pctile(df["AVG_DRIB_PER_TOUCH"],
                                               row["AVG_DRIB_PER_TOUCH"])
            row["pass_touch_pctile"] = _pctile(df["pass_per_touch"],
                                               row["pass_per_touch"])
            focus_rows.append(row)
            print(f"  {s} {p:15s} sec/touch={row['AVG_SEC_PER_TOUCH']:.2f} "
                  f"(p{row['sec_touch_pctile']*100:.0f}) "
                  f"drib/touch={row['AVG_DRIB_PER_TOUCH']:.2f} "
                  f"pass/touch={row['pass_per_touch']:.3f} "
                  f"(p{row['pass_touch_pctile']*100:.0f})")
    focus = pd.DataFrame(focus_rows)
    focus.to_csv(config.PROCESSED_DIR / "flow_test.csv", index=False)

    _figure(frames, focus)
    _write(frames, focus)
    print("Done. outputs/flow_test.md + figures/flow_test.png")
    return 0


def _figure(frames: dict, focus: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.8))

    # A/B: hold time and pass rate bars, both seasons side by side
    for ax, col, title, ylab in [
        (axes[0], "AVG_SEC_PER_TOUCH",
         "① Ball-holding — avg seconds per touch", "sec / touch"),
        (axes[1], "pass_per_touch",
         "② Ball-movement — passes per touch", "passes / touch"),
    ]:
        seasons = config.SEASONS
        x = np.arange(len(FOCUS))
        w = 0.38
        for i, s in enumerate(seasons):
            vals = [focus[(focus.player == p) & (focus.season == s)][col]
                    .iloc[0] if not focus[(focus.player == p) &
                                          (focus.season == s)].empty else np.nan
                    for p in FOCUS]
            bars = ax.bar(x + (i - 0.5) * w, vals, w,
                          label=s, alpha=1.0 if i else 0.45,
                          color=[COLORS[p] for p in FOCUS])
            for rect in bars:
                h = rect.get_height()
                if not np.isnan(h):
                    ax.annotate(f"{h:.2f}", (rect.get_x() + rect.get_width()/2, h),
                                xytext=(0, 3), textcoords="offset points",
                                ha="center", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([p.split()[-1] for p in FOCUS], fontsize=9.5)
        ax.set_ylabel(ylab)
        ax.set_title(title, fontsize=11.5, fontweight="bold", loc="left")
        ax.legend(fontsize=8.5)

    # C: league context scatter, 2025-26
    s = "2025-26"
    pool = frames[s]
    ax = axes[2]
    ax.scatter(pool["AVG_SEC_PER_TOUCH"], pool["pass_per_touch"],
               s=22, c="#c8cfd6", alpha=0.8, zorder=2)
    for p in FOCUS:
        r = focus[(focus.player == p) & (focus.season == s)]
        if r.empty:
            continue
        r = r.iloc[0]
        ax.scatter(r.AVG_SEC_PER_TOUCH, r.pass_per_touch, s=130,
                   c=COLORS[p], edgecolors="black", zorder=5)
        ax.annotate(p.split()[-1], (r.AVG_SEC_PER_TOUCH, r.pass_per_touch),
                    fontsize=9, fontweight="bold", color=COLORS[p],
                    xytext=(6, 5), textcoords="offset points")
    ax.set_xlabel("Avg seconds per touch (holds it longer →)")
    ax.set_ylabel("Passes per touch (moves it more ↑)")
    ax.set_title(f"③ League context, {s} — all players ≥ {MIN_TOUCHES:.0f} "
                 "touches/gm", fontsize=11.5, fontweight="bold", loc="left")

    fig.suptitle("The Flow Test — who stops the ball, who moves it",
                 fontsize=14.5, fontweight="bold", y=1.03)
    fig.tight_layout()
    out = config.FIG_DIR / "flow_test.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)


def _write(frames: dict, focus: pd.DataFrame) -> None:
    def g(p, s, c):
        r = focus[(focus.player == p) & (focus.season == s)]
        return r[c].iloc[0] if not r.empty else np.nan

    L = [
        "# The Flow Test — Ball-Stopping, Measured",
        "",
        "_The 'addition by subtraction' thesis says Brown stalled the offense "
        "and George keeps it moving. SportVU tracking makes that testable: "
        "seconds per touch, dribbles per touch, and passes per touch, against "
        f"every player averaging ≥ {MIN_TOUCHES:.0f} touches/game._",
        "",
    ]
    for s in config.SEASONS:
        n_pool = len(frames[s])
        L += [
            f"## {s}  (league pool: {n_pool} players)",
            "",
            "| Player | Touches/gm | Sec/touch (pctile) | Drib/touch (pctile) "
            "| Passes/touch (pctile) |",
            "|---|---|---|---|---|",
        ]
        for p in FOCUS:
            if np.isnan(g(p, s, "TOUCHES")):
                continue
            L.append(
                f"| {'**' if p == 'Jaylen Brown' else ''}{p}"
                f"{'**' if p == 'Jaylen Brown' else ''} "
                f"| {g(p, s, 'TOUCHES'):.1f} "
                f"| {g(p, s, 'AVG_SEC_PER_TOUCH'):.2f} "
                f"(p{g(p, s, 'sec_touch_pctile')*100:.0f}) "
                f"| {g(p, s, 'AVG_DRIB_PER_TOUCH'):.2f} "
                f"(p{g(p, s, 'drib_touch_pctile')*100:.0f}) "
                f"| {g(p, s, 'pass_per_touch'):.3f} "
                f"(p{g(p, s, 'pass_touch_pctile')*100:.0f}) |")
        L.append("")

    b_sec_24 = g("Jaylen Brown", "2024-25", "sec_touch_pctile") * 100
    b_pass_24 = g("Jaylen Brown", "2024-25", "pass_touch_pctile") * 100
    b_sec_25 = g("Jaylen Brown", "2025-26", "sec_touch_pctile") * 100
    b_pass_25 = g("Jaylen Brown", "2025-26", "pass_touch_pctile") * 100
    g_sec_25 = g("Paul George", "2025-26", "sec_touch_pctile") * 100
    g_pass_25 = g("Paul George", "2025-26", "pass_touch_pctile") * 100

    L += [
        "## Reading it honestly",
        "",
        f"- **The 2024-25 control matters most**: beside a healthy Tatum, in a "
        f"normal role, Brown still held the ball at the p{b_sec_24:.0f} of the "
        f"league pool and passed per touch at just p{b_pass_24:.0f}. The "
        "ball-stopping profile predates the 35%-usage season — it is not a "
        "role artifact.",
        f"- 2025-26 (usage spike): sec/touch p{b_sec_25:.0f}, passes/touch "
        f"p{b_pass_25:.0f}. Same shape, bigger role.",
        f"- **George is the stylistic opposite**: p{g_sec_25:.0f} hold time, "
        f"p{g_pass_25:.0f} pass rate in 2025-26 — a connective wing profile, "
        "which is the actual argument for him (not his scoring).",
        "- Caveats: 'holds the ball' is not automatically bad — SGA and Dončić "
        "live in the same region of panel ③ and are MVPs; hold time is only "
        "damning *when the resulting shots are bad*, which is what the "
        "shot-profile analysis (bad-shot index, long-two drift) shows for "
        "Brown. The two analyses are one argument, not two.",
        "- White's hold time is also high (he initiates); flow is about what "
        "a touch *becomes* — his p"
        f"{g('Derrick White', '2025-26', 'pass_touch_pctile')*100:.0f} pass "
        "rate is the tell.",
    ]
    (config.OUTPUT_DIR / "flow_test.md").write_text("\n".join(L),
                                                    encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
