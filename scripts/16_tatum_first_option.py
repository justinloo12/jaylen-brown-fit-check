"""Tatum as sole first option — the full 2x2 configuration matrix + projection.

The prior memos established that Tatum's shot diet fits the system better
(outputs/tatum_vs_brown.md). This script asks the sharper question: is the
best configuration of this roster *Tatum as the lone first option* rather
than Tatum+Brown load-sharing — and what would a full season of that look
like?

Evidence layers, honestly separated:
  1. OBSERVED, game level — the 2x2 matrix of games (both played / Tatum
     only / Brown only / neither), team record + per-100 net in each cell,
     plus each star's per-game line in his solo cell.
  2. OBSERVED, lineup level — the 2x2 matrix of 5-man lineup minutes
     (both on floor / Tatum-led / Brown-led / neither = supporting-cast
     control), minute-weighted net ratings.
  3. PROJECTION — the lineup gap translated to wins with a documented
     regression discount, and a projected Tatum solo stat line built from
     the observed without-Brown sample blended with a usage-redistribution
     model. All assumptions carry their rationale in the memo.

Outputs:
  * data/processed/tatum_first_option_games.csv, _lineups.csv
  * outputs/figures/tatum_first_option.png
  * outputs/tatum_first_option.md
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
from fitcheck.features.onoff import (availability_cells,
                                     pair_configuration_split)
from fitcheck.features.projection import (intervals_overlap, net_to_wins,
                                          possessions, shrink_gap,
                                          true_shooting, ts_after_usage_shift,
                                          usage_rate, wilson_interval)

TATUM = config.CELTICS_ROTATION["Jayson Tatum"]
BROWN = config.SUBJECT_ID
RED, GREEN, GREY, DARK = "#c0392b", "#007A33", "#b5b8b1", "#4a4f4a"

# --- projection assumptions (every one of these is quoted in the memo) ----
SHRINK_LO, SHRINK_HI = 0.4, 0.6      # lineup-gap regression discount
USG_PROJ_LO, USG_PROJ_HI = 32.0, 33.0  # projected solo usage (from ~30%)
TS_SLOPE_LO, TS_SLOPE_HI = 0.3, 0.6  # TS pts lost per +1 usage pt (rule of thumb)

CELL_LABELS = {"both": "Both played", "tatum_only": "Tatum only",
               "brown_only": "Brown only", "neither": "Neither (control)"}
LINEUP_LABELS = {"both": "Together", "a_only": "Tatum-led (Brown off)",
                 "b_only": "Brown-led (Tatum off)",
                 "neither": "Neither (control)"}


# ---------------------------------------------------------------------------
# Observed layer 1: game-level 2x2
# ---------------------------------------------------------------------------
def player_cell_line(logs: pd.DataFrame, team_logs: pd.DataFrame,
                     game_ids: set[str]) -> dict | None:
    """A player's aggregate per-game line over a set of games: PTS/REB/AST,
    aggregate TS%, and aggregate USG% from the standard boxscore formula
    (player totals over team totals in the same games)."""
    g = logs[logs["GAME_ID"].isin(game_ids)]
    if g.empty:
        return None
    j = g.merge(team_logs, on="GAME_ID", suffixes=("", "_TM"))
    return {
        "n": len(g),
        "min": g["MIN"].mean(),
        "pts": g["PTS"].mean(),
        "reb": g["REB"].mean(),
        "ast": g["AST"].mean(),
        "ts": true_shooting(g["PTS"].sum(), g["FGA"].sum(), g["FTA"].sum()),
        "usg": usage_rate(g["FGA"].sum(), g["FTA"].sum(), g["TOV"].sum(),
                          g["MIN"].sum(), j["FGA_TM"].sum(), j["FTA_TM"].sum(),
                          j["TOV_TM"].sum(), (j["MIN_TM"] * 5).sum()),
    }


def team_cell(team_logs: pd.DataFrame, game_ids: set[str]) -> dict:
    """Team record, average margin, and per-100 net over a set of games.
    Net = 100 * total margin / team-side possession estimate (both teams
    play nearly identical possession counts, so this is the standard
    game-log approximation of net rating)."""
    g = team_logs[team_logs["GAME_ID"].isin(game_ids)]
    if g.empty:
        return {"n": 0, "w": 0, "l": 0, "margin": np.nan, "net": np.nan}
    poss = possessions(g["FGA"].sum(), g["OREB"].sum(),
                       g["TOV"].sum(), g["FTA"].sum())
    return {"n": len(g), "w": int((g["WL"] == "W").sum()),
            "l": int((g["WL"] == "L").sum()),
            "margin": g["PLUS_MINUS"].mean(),
            "net": 100 * g["PLUS_MINUS"].sum() / poss}


def game_matrix(season: str) -> tuple[pd.DataFrame, dict]:
    """The four game-level cells for a season + per-cell star lines."""
    t_logs = nba.player_gamelogs(TATUM, season)
    b_logs = nba.player_gamelogs(BROWN, season)
    tm = nba.team_gamelogs(config.CELTICS_TEAM_ID, season)
    raw = availability_cells(set(t_logs["GAME_ID"]), set(b_logs["GAME_ID"]),
                             set(tm["GAME_ID"]))
    cells = {"both": raw["both"], "tatum_only": raw["a_only"],
             "brown_only": raw["b_only"], "neither": raw["neither"]}

    rows = [{"season": season, "cell": k, **team_cell(tm, gids)}
            for k, gids in cells.items()]
    lines = {
        "tatum_both": player_cell_line(t_logs, tm, cells["both"]),
        "tatum_only": player_cell_line(t_logs, tm, cells["tatum_only"]),
        "brown_both": player_cell_line(b_logs, tm, cells["both"]),
        "brown_only": player_cell_line(b_logs, tm, cells["brown_only"]),
    }
    return pd.DataFrame(rows), lines


# ---------------------------------------------------------------------------
# Observed layer 1b: pooled availability split, 2023-24 -> 2025-26
# ---------------------------------------------------------------------------
POOL_LABEL = "pooled"                # all POOL_SEASONS
POOL_EX_LABEL = "pooled_ex_2025-26"  # sensitivity: drop the Tatum injury year


def _avail_row(label: str, cells: dict[str, set], tm: pd.DataFrame,
               t_logs: pd.DataFrame) -> dict:
    """One flat row of the availability table: cell counts, team results in
    the both-played and Tatum-only cells, and Tatum's line in each."""
    both, only = team_cell(tm, cells["both"]), team_cell(tm, cells["tatum_only"])
    row = {"pool": label,
           "n_both": both["n"], "n_tatum_only": only["n"],
           "n_brown_only": len(cells["brown_only"]),
           "n_neither": len(cells["neither"]),
           "both_w": both["w"], "both_l": both["l"],
           "both_margin": both["margin"],
           "only_w": only["w"], "only_l": only["l"],
           "only_margin": only["margin"]}
    for tag, line in (("tb", player_cell_line(t_logs, tm, cells["both"])),
                      ("to", player_cell_line(t_logs, tm, cells["tatum_only"]))):
        for k in ("pts", "reb", "ast", "ts", "usg"):
            row[f"{tag}_{k}"] = line[k] if line else np.nan
    return row


def pooled_availability() -> pd.DataFrame:
    """Per-season availability rows over config.POOL_SEASONS plus two pooled
    rows: the full window and the window minus 2025-26 (Tatum injury year).

    One player-gamelog call per star per season and one team-gamelog call per
    season, all cache-backed. GAME_IDs are unique across seasons, so pooling
    is a straight union of the per-season cell sets over concatenated logs.
    """
    rows, t_frames, tm_frames = [], [], []
    season_cells: dict[str, dict[str, set]] = {}
    for s in config.POOL_SEASONS:
        t_logs = nba.player_gamelogs(TATUM, s)
        b_logs = nba.player_gamelogs(BROWN, s)
        tm = nba.team_gamelogs(config.CELTICS_TEAM_ID, s)
        raw = availability_cells(set(t_logs["GAME_ID"]),
                                 set(b_logs["GAME_ID"]), set(tm["GAME_ID"]))
        cells = {"both": raw["both"], "tatum_only": raw["a_only"],
                 "brown_only": raw["b_only"], "neither": raw["neither"]}
        season_cells[s] = cells
        t_frames.append(t_logs)
        tm_frames.append(tm)
        rows.append(_avail_row(s, cells, tm, t_logs))

    t_all = pd.concat(t_frames, ignore_index=True)
    tm_all = pd.concat(tm_frames, ignore_index=True)
    pools = {POOL_LABEL: list(config.POOL_SEASONS),
             POOL_EX_LABEL: [s for s in config.POOL_SEASONS if s != "2025-26"]}
    for label, subset in pools.items():
        merged = {k: set().union(*(season_cells[s][k] for s in subset))
                  for k in ("both", "tatum_only", "brown_only", "neither")}
        rows.append(_avail_row(label, merged, tm_all, t_all))
    return pd.DataFrame(rows)


def _career_figure(cdf: pd.DataFrame) -> None:
    """Small companion figure: both-played vs Tatum-only average margin per
    season, plus the pooled window. ~2.4 aspect, kept deliberately plain."""
    p = cdf.set_index("pool")
    labels = list(config.POOL_SEASONS) + [POOL_LABEL]
    disp = [f"{s}\nboth {p.loc[s, 'n_both']:.0f} g / "
            f"solo {p.loc[s, 'n_tatum_only']:.0f} g" for s in labels[:-1]]
    disp.append(f"Pooled 3 seasons\nboth {p.loc[POOL_LABEL, 'n_both']:.0f} g / "
                f"solo {p.loc[POOL_LABEL, 'n_tatum_only']:.0f} g")

    fig, ax = plt.subplots(figsize=(13.2, 5.5))
    x, w = np.arange(len(labels)), 0.36
    b1 = ax.bar(x - w / 2, [p.loc[s, "both_margin"] for s in labels], w,
                color=GREY, label="Both played")
    b2 = ax.bar(x + w / 2, [p.loc[s, "only_margin"] for s in labels], w,
                color=GREEN, label="Tatum played, Brown sat")
    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            if not np.isnan(h):
                ax.annotate(f"{h:+.1f}",
                            (rect.get_x() + rect.get_width() / 2, h),
                            textcoords="offset points", xytext=(0, 5),
                            ha="center", fontsize=13, fontweight="bold")
    ax.axvline(len(labels) - 1.5, color=DARK, lw=0.8, ls="--", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(disp, fontsize=11.5)
    ax.set_ylabel("Average game margin (points)", fontsize=12.5)
    ax.set_title("Boston with vs without Brown when Tatum played — "
                 "2023-24 → 2025-26 (current-system window)",
                 fontsize=14, fontweight="bold", loc="left")
    ax.axhline(0, color="black", lw=0.9)
    ax.legend(fontsize=11.5, loc="upper left")
    ax.margins(y=0.25)
    ax.tick_params(axis="y", labelsize=11)
    fig.text(0.005, -0.03,
             "Solo cells are small and Brown's absences are not random "
             "(injury/rest scheduling); see memo §1b before quoting.",
             fontsize=10, style="italic", color=DARK)
    fig.tight_layout()
    out = config.FIG_DIR / "career_availability.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


def _fmt_avail(r: pd.Series, side: str) -> str:
    n = r[f"n_{'both' if side == 'both' else 'tatum_only'}"]
    if n == 0:
        return "— (0 g)"
    pre = "both" if side == "both" else "only"
    return (f"{r[f'{pre}_w']:.0f}-{r[f'{pre}_l']:.0f} ({n:.0f} g), "
            f"margin {r[f'{pre}_margin']:+.1f}")


def _fmt_tatum(r: pd.Series, tag: str) -> str:
    if np.isnan(r[f"{tag}_pts"]):
        return "—"
    return (f"{r[f'{tag}_pts']:.1f} / {r[f'{tag}_reb']:.1f} / "
            f"{r[f'{tag}_ast']:.1f}, TS {r[f'{tag}_ts']:.3f}, "
            f"USG {r[f'{tag}_usg']:.1f}%")


def _career_section(cdf: pd.DataFrame) -> list[str]:
    """Memo lines for §1b: per-season table, pooled results, Wilson check."""
    p = cdf.set_index("pool")
    full, ex = p.loc[POOL_LABEL], p.loc[POOL_EX_LABEL]
    wl_b = wilson_interval(full["both_w"], full["n_both"])
    wl_o = wilson_interval(full["only_w"], full["n_tatum_only"])
    overlap = intervals_overlap(wl_b, wl_o)
    pct = lambda w, n: w / n if n else float("nan")

    L = [
        "",
        "### 1b. The pooled sample — the same split across the "
        "current-system window (2023-24 → 2025-26)",
        "",
        "_The 16-game cell above is the right sample for \"current Tatum,\" "
        "but it is still 16 games. Pooling the identical split across the "
        "three Mazzulla-era seasons roughly doubles it. The window is "
        "deliberately 2023-24 → 2025-26: this is the current system "
        "(the movement-3 identity) with Tatum as the established first "
        "option. Earlier Tatum-Brown seasons (2017-2022) are excluded on "
        "purpose — Kyrie/Kemba/Hayward-era rosters gave both players "
        "different roles, so pooling them would answer a different question "
        "than the one this memo asks._",
        "",
        "| Season | Both played | Tatum played, Brown sat "
        "| Tatum line, Brown sat |",
        "|---|---|---|---|",
    ]
    for s in config.POOL_SEASONS:
        r = p.loc[s]
        L.append(f"| {s} | {_fmt_avail(r, 'both')} "
                 f"| {_fmt_avail(r, 'only')} | {_fmt_tatum(r, 'to')} |")
    L += [
        f"| **Pooled** | **{_fmt_avail(full, 'both')}** "
        f"| **{_fmt_avail(full, 'only')}** | **{_fmt_tatum(full, 'to')}** |",
        f"| Pooled ex-2025-26 (injury year) | {_fmt_avail(ex, 'both')} "
        f"| {_fmt_avail(ex, 'only')} | {_fmt_tatum(ex, 'to')} |",
        "",
        f"All four cells over the window: both played {full['n_both']:.0f}, "
        f"Tatum only {full['n_tatum_only']:.0f}, Brown only "
        f"{full['n_brown_only']:.0f}, neither {full['n_neither']:.0f}. "
        "(The Brown-only and neither cells are analyzed season-by-season "
        "in §1; they are listed here only so the counts reconcile.)",
        "",
        f"**Tatum, pooled:** with Brown {_fmt_tatum(full, 'tb')} over "
        f"{full['n_both']:.0f} games; with Brown sitting "
        f"{_fmt_tatum(full, 'to')} over {full['n_tatum_only']:.0f} games — "
        f"usage +{full['to_usg'] - full['tb_usg']:.1f} points with TS "
        f"{full['tb_ts']:.3f} → {full['to_ts']:.3f}"
        + (", i.e. at pooled scale the extra load carries a real (if "
           "modest) efficiency cost that the flat 2024-25 cell alone "
           "hid — print that, it cuts against the thesis"
           if full["tb_ts"] - full["to_ts"] > 0.01 else
           " — efficiency essentially held at the higher load")
        + ". ([career_availability.csv]"
        "(../data/processed/career_availability.csv) has every row.)",
        "",
        "**Significance, honestly.** Wilson 95% intervals on win%: "
        f"both played {pct(full['both_w'], full['n_both']):.3f} "
        f"[{wl_b[0]:.3f}, {wl_b[1]:.3f}] on {full['n_both']:.0f} games; "
        f"Tatum-only {pct(full['only_w'], full['n_tatum_only']):.3f} "
        f"[{wl_o[0]:.3f}, {wl_o[1]:.3f}] on {full['n_tatum_only']:.0f} "
        "games. The intervals "
        + ("**overlap substantially** — the pooled sample is consistent "
           "with \"Boston is at least as good in Tatum-only games\" but "
           "cannot statistically separate the two cells. Treat the direction "
           "as suggestive, not proven."
           if overlap else
           "**do not overlap** — a genuinely surprising result for samples "
           "this size; even so, availability splits are observational and "
           "this is not a causal estimate.")
        + f" The margin gap ({full['only_margin']:+.1f} vs "
        f"{full['both_margin']:+.1f}) is likewise within the noise a "
        f"{full['n_tatum_only']:.0f}-game cell carries.",
        "",
    ]
    worse = [s for s in config.POOL_SEASONS
             if p.loc[s, "n_tatum_only"] > 0
             and p.loc[s, "only_margin"] < p.loc[s, "both_margin"]]
    if worse:
        L += ["**Rows that cut the other way, printed with the same "
              "weight:** " +
              "; ".join(
                  f"in {s} Boston's margin was *worse* with Brown out "
                  f"({p.loc[s, 'only_margin']:+.1f} over "
                  f"{p.loc[s, 'n_tatum_only']:.0f} games vs "
                  f"{p.loc[s, 'both_margin']:+.1f} together)" for s in worse)
              + ". The pooled number must not be quoted without these rows.",
              ""]
    else:
        L += ["Every season in the window points the same direction "
              "(Tatum-only margin ≥ both-played margin) — but see the "
              "sample sizes above before treating that as more than "
              "consistency.", ""]
    L += [
        "**Caveats that stay attached to this table:**",
        "",
        "- **Absences are not missing-at-random.** Brown's sit-outs cluster "
        "in injury stretches and scheduled-rest games, whose opponent "
        "quality and context can differ systematically from the both-played "
        "slate. Nothing here controls for opponent strength.",
        f"- **2025-26 is an injury shard.** Tatum played 16 games, so the "
        f"Tatum-only cell that year is {p.loc['2025-26', 'n_tatum_only']:.0f} "
        "games — reported because the brief is to report the n whatever it "
        "is, not because it moves the pool.",
        "- **Windowing is a choice.** Restricting to 2023-24 → 2025-26 "
        "makes the sample role-consistent at the cost of size; the "
        "ex-2025-26 row shows the pool is not carried by the injury season.",
        "",
        f"**What this adds to the conclusion:** the 2024-25 Tatum-only "
        "story survives pooling — "
        f"{full['only_w']:.0f}-{full['only_l']:.0f} "
        f"({pct(full['only_w'], full['n_tatum_only']):.0%}) with a "
        f"{full['only_margin']:+.1f} margin across "
        f"{full['n_tatum_only']:.0f} games vs "
        f"{pct(full['both_w'], full['n_both']):.0%} and "
        f"{full['both_margin']:+.1f} together — but the Wilson check above "
        "caps the claim at *\"no evidence Boston drops off when Tatum plays "
        "without Brown, in the current system\"*. It does not upgrade the "
        "sole-first-option case from suggestive to proven, and this memo "
        "doesn't pretend it does.",
    ]
    return L


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------
def build_projection(lu24: pd.DataFrame, lines24: dict) -> dict:
    """Everything the projection section quotes, computed in one place."""
    lu = lu24.set_index("state")
    gap = lu.loc["a_only", "NET_RATING"] - lu.loc["both", "NET_RATING"]
    net_lo, net_hi = shrink_gap(gap, SHRINK_LO, SHRINK_HI)
    wins_lo, wins_hi = net_to_wins(net_lo), net_to_wins(net_hi)

    base, obs = lines24["tatum_both"], lines24["tatum_only"]
    # usage-redistribution model: scale true-shot volume with usage, tax
    # efficiency with the rule-of-thumb slope; evaluate all 4 corners.
    corners = []
    for usg in (USG_PROJ_LO, USG_PROJ_HI):
        for slope in (TS_SLOPE_LO, TS_SLOPE_HI):
            ts = ts_after_usage_shift(base["ts"], base["usg"], usg, slope)
            pts = base["pts"] * (usg / base["usg"]) * (ts / base["ts"])
            corners.append({"usg": usg, "slope": slope, "ts": ts, "pts": pts})
    model_pts = [c["pts"] for c in corners]
    model_ts = [c["ts"] for c in corners]

    return {
        "gap": gap, "net_lo": net_lo, "net_hi": net_hi,
        "wins_lo": wins_lo, "wins_hi": wins_hi,
        "model_pts_lo": min(model_pts), "model_pts_hi": max(model_pts),
        "model_ts_lo": min(model_ts), "model_ts_hi": max(model_ts),
        # headline ranges = union of the model range and the observed
        # without-Brown sample, so neither source is hidden by the other.
        "pts_lo": min(min(model_pts), obs["pts"]),
        "pts_hi": max(max(model_pts), obs["pts"]),
        "ts_lo": min(min(model_ts), obs["ts"]),
        "ts_hi": max(max(model_ts), obs["ts"]),
        "reb_lo": min(base["reb"], obs["reb"]),
        "reb_hi": max(base["reb"], obs["reb"]),
        "ast_lo": min(base["ast"], obs["ast"]),
        "ast_hi": max(base["ast"], obs["ast"]),
        "usg_lo": USG_PROJ_LO, "usg_hi": max(USG_PROJ_HI, obs["usg"]),
    }


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def _figure(lu24: pd.DataFrame, lines24: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))

    # Left: the four-cell lineup engine test, 2024-25
    ax = axes[0]
    lu = lu24.set_index("state")
    order = ["both", "a_only", "b_only", "neither"]
    colors = [DARK, GREEN, RED, GREY]
    vals = [lu.loc[s, "NET_RATING"] for s in order]
    mins = [lu.loc[s, "MIN"] for s in order]
    labels = [f"Together\n{mins[0]:,.0f} min",
              f"Tatum-led\n(Brown off)\n{mins[1]:,.0f} min",
              f"Brown-led\n(Tatum off)\n{mins[2]:,.0f} min",
              f"Neither\n(control)\n{mins[3]:,.0f} min"]
    bars = ax.bar(np.arange(4), vals, 0.62, color=colors)
    for rect, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", (rect.get_x() + rect.get_width() / 2, v),
                    textcoords="offset points", xytext=(0, 6), ha="center",
                    fontsize=15, fontweight="bold")
    ax.set_xticks(np.arange(4))
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel("5-man lineup net rating (min-weighted)", fontsize=12.5)
    ax.set_title("The engine test, 2024-25 — all four configurations",
                 fontsize=14, fontweight="bold", loc="left")
    ax.axhline(0, color="black", lw=0.9)
    ax.margins(y=0.22)
    ax.tick_params(axis="y", labelsize=11)

    # Right: Tatum observed per-game line, with vs without Brown (2024-25)
    ax = axes[1]
    base, obs = lines24["tatum_both"], lines24["tatum_only"]
    groups = [("PTS / game", base["pts"], obs["pts"], ""),
              ("TS%", base["ts"] * 100, obs["ts"] * 100, "%"),
              ("USG%", base["usg"], obs["usg"], "%")]
    x = np.arange(len(groups))
    w = 0.36
    b1 = ax.bar(x - w / 2, [g[1] for g in groups], w,
                label=f"With Brown ({base['n']} g)", color=GREY)
    b2 = ax.bar(x + w / 2, [g[2] for g in groups], w,
                label=f"Without Brown ({obs['n']} g)", color=GREEN)
    for bars_ in (b1, b2):
        for rect, (_, _, _, suf) in zip(bars_, groups):
            h = rect.get_height()
            ax.annotate(f"{h:.1f}{suf}",
                        (rect.get_x() + rect.get_width() / 2, h),
                        textcoords="offset points", xytext=(0, 5),
                        ha="center", fontsize=13.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([g[0] for g in groups], fontsize=12.5)
    ax.set_ylabel("Observed per-game value", fontsize=12.5)
    ax.set_title("Tatum with vs without Brown, 2024-25 (observed)",
                 fontsize=14, fontweight="bold", loc="left")
    ax.legend(fontsize=11.5, loc="upper left")
    ax.margins(y=0.22)
    ax.tick_params(axis="y", labelsize=11)

    fig.suptitle("Tatum as sole first option — the configuration evidence",
                 fontsize=17, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = config.FIG_DIR / "tatum_first_option.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ figure -> {out}")


# ---------------------------------------------------------------------------
# Brown recap (one-stop table from the existing processed outputs)
# ---------------------------------------------------------------------------
def brown_recap() -> list[str]:
    fit = pd.read_csv(config.PROCESSED_DIR / "tatum_vs_brown_fit.csv")
    b = fit[fit.player == "Jaylen Brown"].set_index("season")
    eff = {s: pd.read_csv(config.PROCESSED_DIR / f"efficiency_comps_{s}.csv")
           .set_index("player").loc["Jaylen Brown"] for s in config.SEASONS}
    ww = {s: pd.read_csv(config.PROCESSED_DIR / f"with_without_{s}.csv")
          for s in config.SEASONS}
    wwt = {s: ww[s][ww[s].teammate == "Jayson Tatum"].set_index("state")
           for s in config.SEASONS}
    rows = [
        ("3PT rate", *(f"{b.loc[s, 'three_rate']:.3f}" for s in config.SEASONS),
         "outputs/tatum_vs_brown.md, the_case_for_moving_on.md"),
        ("Long-2 rate", *(f"{b.loc[s, 'long_two_rate']:.3f}" for s in config.SEASONS),
         "outputs/tatum_vs_brown.md"),
        ("Iso / 3+ dribble rate", *(f"{b.loc[s, 'iso_dribble_rate']:.3f}" for s in config.SEASONS),
         "outputs/tatum_vs_brown.md"),
        ("Bad-shot index", *(f"{b.loc[s, 'bad_shot_index']:.3f}" for s in config.SEASONS),
         "outputs/tatum_vs_brown.md"),
        ("TS% (season)", *(f"{eff[s]['TS_PCT']:.3f}" for s in config.SEASONS),
         "outputs/efficiency_comps.md"),
        ("USG% (season)", *(f"{eff[s]['USG_PCT']:.1f}" for s in config.SEASONS),
         "outputs/efficiency_comps.md"),
        ("Cost per Win Share", *(f"${eff[s]['cost_per_WS']/1e6:.1f}M" for s in config.SEASONS),
         "outputs/efficiency_comps.md"),
        ("Lineup net WITH Tatum", *(f"{wwt[s].loc['with', 'NET_RATING']:+.1f}" for s in config.SEASONS),
         "outputs/report.md, this memo §2"),
        ("Lineup net WITHOUT Tatum", *(f"{wwt[s].loc['without', 'NET_RATING']:+.1f}" for s in config.SEASONS),
         "outputs/report.md, this memo §2"),
    ]
    L = ["| Brown metric | 2024-25 | 2025-26 | Source |", "|---|---|---|---|"]
    L += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in rows]
    return L


def _companion_bullets() -> list[str]:
    """Headline numbers from the companion analyses (scripts 17-18), read
    from their processed CSVs when present so this memo stays one-stop."""
    L = [""]
    lb = config.PROCESSED_DIR / "live_ball_turnovers.csv"
    if lb.exists():
        d = pd.read_csv(lb).set_index(["who", "season"])
        b24 = d.loc[("Jaylen Brown", "2024-25")]
        t24 = d.loc[("Jayson Tatum", "2024-25")]
        b25 = d.loc[("Jaylen Brown", "2025-26")]
        L.append(
            f"- **Live-ball turnovers** ([live_ball_turnovers.md]"
            f"(live_ball_turnovers.md)): 2024-25 Brown {b24['live_per36']:.2f} "
            f"live/36 ({b24['pts_against']:.0f} pts surrendered) vs Tatum "
            f"{t24['live_per36']:.2f} ({t24['pts_against']:.0f} pts) — "
            "Brown's rate was LOWER when both were healthy. His "
            f"ball-dominant 2025-26: {b25['live']:.0f} live TOs, "
            f"{b25['pts_against']:.0f} pts surrendered.")
    dr = config.PROCESSED_DIR / "defense_roles.csv"
    if dr.exists():
        d = pd.read_csv(dr).set_index(["player", "season"])
        b24, t24 = d.loc[("Jaylen Brown", "2024-25")], d.loc[("Jayson Tatum", "2024-25")]
        L.append(
            f"- **Defense by role** ([defense_roles.md](defense_roles.md)): "
            f"Brown was the primary on-ball defender — {b24['prim_share']:.0%} "
            "of his defended possessions on opponents' #1 options vs "
            f"Tatum's {t24['prim_share']:.0%} (2024-25), at slightly better "
            "points-allowed on those matchups. Boston has to replace that "
            "assignment coverage.")
    return L if len(L) > 1 else []


# ---------------------------------------------------------------------------
# Memo
# ---------------------------------------------------------------------------
def _fmt_cell(r) -> str:
    if r["n"] == 0:
        return "— (0 g)"
    return f"{r['w']}-{r['l']} ({r['n']} g), net {r['net']:+.1f}"


def _line(d: dict | None) -> str:
    if d is None:
        return "—"
    return (f"{d['pts']:.1f} / {d['reb']:.1f} / {d['ast']:.1f}, "
            f"TS {d['ts']:.3f}, USG {d['usg']:.1f}%")


def _write(gm: dict[str, pd.DataFrame], lines: dict[str, dict],
           lu: dict[str, pd.DataFrame], proj: dict, cdf: pd.DataFrame) -> None:
    g24 = gm["2024-25"].set_index("cell")
    g25 = gm["2025-26"].set_index("cell")
    l24 = lu["2024-25"].set_index("state")
    l25 = lu["2025-26"].set_index("state")
    ln24, ln25 = lines["2024-25"], lines["2025-26"]
    tb, to = ln24["tatum_both"], ln24["tatum_only"]
    bo = ln24["brown_only"]

    L = [
        "# Tatum as Sole First Option — The Configuration Matrix and a Season Projection",
        "",
        "_Follow-up to [tatum_vs_brown.md](tatum_vs_brown.md). Question: is "
        "this roster's best configuration Tatum as the lone first option "
        "rather than Tatum+Brown load-sharing? §1-§2 are **observed**; §3 is "
        "a **projection** and says so at every step. 2024-25 is the primary "
        "season throughout — Tatum's 2025-26 lasted 16 games (injury), so "
        "every 2025-26 cell involving him is a shard, not evidence. §1b "
        "pools the availability split across the 2023-24 → 2025-26 window "
        "to put the 16-game cell on a larger sample._",
        "",
        "## 1. Observed — the game-level 2x2 (who suited up)",
        "",
        "### 2024-25 (primary)",
        "",
        "| | Brown played | Brown sat |",
        "|---|---|---|",
        f"| **Tatum played** | {_fmt_cell(g24.loc['both'])} | {_fmt_cell(g24.loc['tatum_only'])} |",
        f"| **Tatum sat** | {_fmt_cell(g24.loc['brown_only'])} | {_fmt_cell(g24.loc['neither'])} |",
        "",
        "Per-game lines in each star's cells (PTS / REB / AST):",
        "",
        "| Player, cell | n | Line |",
        "|---|---|---|",
        f"| Tatum, both played | {tb['n']} | {_line(tb)} |",
        f"| Tatum, Brown sat | {to['n']} | {_line(to)} |",
        f"| Brown, both played | {ln24['brown_both']['n']} | {_line(ln24['brown_both'])} |",
        f"| Brown, Tatum sat | {bo['n']} | {_line(bo)} |",
        "",
        "**What the cells actually say (2024-25):**",
        "",
        f"- **Tatum without Brown ({to['n']} games): "
        f"{g24.loc['tatum_only', 'w']:.0f}-{g24.loc['tatum_only', 'l']:.0f}, "
        f"net {g24.loc['tatum_only', 'net']:+.1f}** vs "
        f"{g24.loc['both', 'w']:.0f}-{g24.loc['both', 'l']:.0f}, "
        f"net {g24.loc['both', 'net']:+.1f} when both played. Tatum's scoring "
        f"rose {tb['pts']:.1f} → {to['pts']:.1f} PPG on usage "
        f"{tb['usg']:.1f}% → {to['usg']:.1f}% with TS essentially flat "
        f"({tb['ts']:.3f} → {to['ts']:.3f}) — in this sample he absorbed "
        "roughly four extra usage points at no efficiency cost.",
        f"- **Brown without Tatum ({bo['n']} games): "
        f"{g24.loc['brown_only', 'w']:.0f}-{g24.loc['brown_only', 'l']:.0f}, "
        f"net {g24.loc['brown_only', 'net']:+.1f} — the best game-level cell "
        "in the matrix.** Print that plainly: Brown's solo-carry games were "
        "not a problem; Boston blew teams out. His own line in them was "
        f"modest ({_line(bo)}), so much of that margin came from the "
        "supporting cast — but a 7-game cell can't settle who drove it "
        "either way.",
        f"- **Neither played ({g24.loc['neither', 'n']:.0f} games, the "
        f"control): net {g24.loc['neither', 'net']:+.1f}.** Too small to "
        "lean on, but directionally the only cell near zero — the lift in "
        "the other three cells is not just the supporting cast.",
        "",
        "### 2025-26 (secondary — Tatum injury caveat applies to every cell)",
        "",
        "| | Brown played | Brown sat |",
        "|---|---|---|",
        f"| **Tatum played** | {_fmt_cell(g25.loc['both'])} | {_fmt_cell(g25.loc['tatum_only'])} |",
        f"| **Tatum sat** | {_fmt_cell(g25.loc['brown_only'])} | {_fmt_cell(g25.loc['neither'])} |",
        "",
        f"Brown carried the season alone: {ln25['brown_only']['n']} games "
        f"without Tatum at {_line(ln25['brown_only'])} — a "
        f"{g25.loc['brown_only', 'w']:.0f}-{g25.loc['brown_only', 'l']:.0f} "
        f"record and {g25.loc['brown_only', 'net']:+.1f} net. That is real, "
        "MVP-ballot-grade solo production and this memo doesn't pretend "
        "otherwise. The Tatum-sat-and-Brown-sat cell "
        f"({g25.loc['neither', 'n']:.0f} games, "
        f"{g25.loc['neither', 'net']:+.1f}) is small and blowout-flavored; "
        "don't quote it as a supporting-cast measurement.",
    ]
    L += _career_section(cdf)
    L += [
        "",
        "## 2. Observed — the lineup-level 2x2 (who was on the floor)",
        "",
        "Minute-weighted 5-man lineup nets. The **neither** row is the "
        "control group: what the supporting cast does with no star on the "
        "floor.",
        "",
        "| Configuration | 2024-25 | 2025-26 |",
        "|---|---|---|",
    ]
    for state in ["both", "a_only", "b_only", "neither"]:
        L.append(
            f"| {LINEUP_LABELS[state]} "
            f"| {l24.loc[state, 'NET_RATING']:+.1f} ({l24.loc[state, 'MIN']:.0f} min) "
            f"| {l25.loc[state, 'NET_RATING']:+.1f} ({l25.loc[state, 'MIN']:.0f} min) |")
    L += [
        "",
        "**2024-25 reading:** every configuration beat the "
        f"no-stars control ({l24.loc['neither', 'NET_RATING']:+.1f}), and the "
        "ordering is Tatum-led "
        f"({l24.loc['a_only', 'NET_RATING']:+.1f}) > Brown-led "
        f"({l24.loc['b_only', 'NET_RATING']:+.1f}) > together "
        f"({l24.loc['both', 'NET_RATING']:+.1f}). Both stars ran better "
        "engines apart than the two of them did together — the load-sharing "
        "configuration was the *worst* of the three star configurations. "
        "That is the core of the sole-first-option case, and note it is "
        "symmetric: it argues for consolidation around either star, and the "
        "shot-diet evidence (tatum_vs_brown.md §1) is what breaks the tie "
        "toward Tatum.",
        "",
        "**2025-26 reading:** the matrix inverts (together "
        f"{l25.loc['both', 'NET_RATING']:+.1f}, neither "
        f"{l25.loc['neither', 'NET_RATING']:+.1f}, both 'led' cells lower) — "
        "but Tatum's cells sit on 204-318 minutes and the deep 2025-26 bench "
        "feasted in low-leverage minutes. Injury-season noise; we do not "
        "build the projection on it.",
        "",
        "## 3. Projection — a full season of Tatum as sole first option",
        "",
        "_Everything below is a **projection**, not an observation. Each "
        "assumption is stated with its rationale; ranges, not point "
        "estimates._",
        "",
        "### 3a. Team level: lineup gap → wins",
        "",
        f"- Observed 2024-25 lineup gap: Tatum-led "
        f"{l24.loc['a_only', 'NET_RATING']:+.1f} vs together "
        f"{l24.loc['both', 'NET_RATING']:+.1f} = **{proj['gap']:+.1f} per "
        "100** (5-man lineup level).",
        f"- **Regression discount ({SHRINK_LO:.0%}-{SHRINK_HI:.0%} "
        "shrinkage):** lineup nets are not season nets — 'led' samples are "
        "contaminated by bench-heavy and garbage-time units, opponent mix "
        "is uncontrolled, and extreme lineup splits regress hard. We keep "
        f"only {SHRINK_LO:.0%}-{SHRINK_HI:.0%} of the gap: "
        f"**{proj['net_lo']:+.1f} to {proj['net_hi']:+.1f} team net "
        "points**. The shrinkage band is a judgment call, chosen before "
        "computing the win total; the undiscounted figure is shown so you "
        "can apply your own.",
        f"- **Net → wins at ~2.7 wins per point** (standard Pythagorean "
        f"rule of thumb, 82 games): **{proj['wins_lo']:+.1f} to "
        f"{proj['wins_hi']:+.1f} wins** vs the load-sharing baseline. "
        f"Undiscounted, the same math would say {net_to_wins(proj['gap']):+.1f} "
        "wins — we do not believe that number, which is the point of the "
        "discount.",
        "",
        "### 3b. Player level: Tatum's projected solo line",
        "",
        "Two inputs, blended:",
        "",
        f"1. **Observed without-Brown sample ({to['n']} games, §1):** "
        f"{_line(to)}. Small sample; opponent mix uncontrolled.",
        f"2. **Usage-redistribution model:** baseline = his "
        f"{tb['n']}-game with-Brown line ({_line(tb)}). Assume Brown's "
        "vacated possessions push Tatum's usage from "
        f"~{tb['usg']:.0f}% to {USG_PROJ_LO:.0f}-{USG_PROJ_HI:.0f}%, and "
        f"charge an efficiency tax of {TS_SLOPE_LO}-{TS_SLOPE_HI} TS points "
        "per +1 usage point (a rule-of-thumb range from the public "
        "skill-curve literature — an assumption, not a measurement). That "
        f"yields {proj['model_pts_lo']:.1f}-{proj['model_pts_hi']:.1f} PPG "
        f"at TS {proj['model_ts_lo']:.3f}-{proj['model_ts_hi']:.3f}. Note "
        "the observed 16-game sample beat this model's efficiency tax (TS "
        "held flat at +4 usage points) — the model is the conservative leg.",
        "",
        "**Projected Tatum solo-season line (range, not a forecast point):**",
        "",
        "| | Low | High |",
        "|---|---|---|",
        f"| PTS / game | {proj['pts_lo']:.1f} | {proj['pts_hi']:.1f} |",
        f"| REB / game | {proj['reb_lo']:.1f} | {proj['reb_hi']:.1f} |",
        f"| AST / game | {proj['ast_lo']:.1f} | {proj['ast_hi']:.1f} |",
        f"| TS% | {proj['ts_lo']:.3f} | {proj['ts_hi']:.3f} |",
        f"| USG% | {proj['usg_lo']:.1f} | {proj['usg_hi']:.1f} |",
        "",
        "Ranges are the union of the observed sample and the model corners "
        "— deliberately wide. Anyone quoting a single number from this "
        "table is misusing it.",
        "",
        "## 4. What could go wrong (stated fairly)",
        "",
        f"- **Load over 82 games.** The observed sample is {to['n']} games "
        "sprinkled through a season with Brown absorbing the other "
        f"{tb['n']}; a permanent {USG_PROJ_LO:.0f}-{proj['usg_hi']:.0f}% "
        "usage burden is a different physical proposition. Fatigue-driven "
        "efficiency decay would land exactly where the model's tax says.",
        "- **Defenses key on one star.** With Brown gone, Tatum sees the "
        "opponent's best defender plus the blitz every night. The 16-game "
        "sample includes teams game-planning for a one-off absence, not a "
        "season-long scheme.",
        "- **Playoff shot-quality compression.** Load-sharing is worth most "
        "in the playoffs, when the first option's diet degrades. The +7.6 "
        "'together' net bought a second self-creator for April-June; this "
        "memo prices the regular season and says so.",
        "- **Paul George is not 'nobody.'** The realized trade returns a "
        "second option; the pure sole-first-option frame is cleaner than "
        "the actual 2026-27 roster will be. Treat §3 as an upper-bound "
        "articulation of the consolidation thesis, not a Celtics forecast.",
        "- **Brown's side of the ledger is real.** 2024-25 Brown-led "
        f"lineups (+{l24.loc['b_only', 'NET_RATING']:.1f}) beat 'together' "
        f"too, his {bo['n']} solo games in 2024-25 were the best cell in "
        f"the game matrix, and he carried {ln25['brown_only']['n']} games "
        f"in 2025-26 at {ln25['brown_only']['pts']:.1f} PPG to a playable "
        "net. The configuration argument is about the *best* "
        "arrangement, not about Brown being unable to lead one.",
        "",
        "## 5. Brown in one place (recap of the existing outputs)",
        "",
        "_One-stop summary so this memo stands alone; every figure is "
        "computed in the linked source, not re-derived here._",
        "",
    ]
    L += brown_recap()
    L += _companion_bullets()
    L += [
        "",
        "Clutch: Brown's 2024-25 clutch TS was .632, better than Tatum "
        "(outputs/high_leverage_and_2028.md). Defense: improved in 2025-26 "
        "(outputs/defense_check.md). The trade case was never that Brown is "
        "bad; it's that the configuration in §2 was available.",
        "",
        "## 6. Data & methods notes",
        "",
        "- Game logs and team game logs: stats.nba.com via the cached "
        "client (`fitcheck/data/nba_client.py`); lineups: LeagueDashLineups "
        "5-man units, minute-weighted (same caveat as always: possession "
        "weighting would differ slightly).",
        "- Game-level net = 100 x margin / team-side possession estimate "
        "(FGA − OREB + TOV + 0.44·FTA), the standard game-log "
        "approximation.",
        "- Per-game USG% computed from the standard boxscore formula "
        "(player totals over team totals in the same games), not from the "
        "advanced-boxscore endpoint — avoids ~150 extra API calls; the two "
        "agree to a few tenths.",
        "- TS% aggregated over cells (total PTS over total true-shot "
        "attempts), not averaged per game.",
        "- All projection constants (shrinkage band, usage range, TS "
        "slope, wins-per-point) live at the top of "
        "`scripts/16_tatum_first_option.py`; the pure formulas are "
        "unit-tested in `tests/test_projection.py`.",
        "- §1b pooling: one player-gamelog call per star per season plus "
        "one team-gamelog call per season over `config.POOL_SEASONS`; "
        "cells classified by `availability_cells` "
        "(`fitcheck/features/onoff.py`), win% intervals from "
        "`wilson_interval` (`fitcheck/features/projection.py`) — both "
        "unit-tested. Margin = team PLUS_MINUS from the team game log "
        "(final-score margin), averaged per cell.",
    ]
    out = config.OUTPUT_DIR / "tatum_first_option.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  ✓ memo -> {out}")


# ---------------------------------------------------------------------------
def main() -> int:
    gm, lines, lu = {}, {}, {}
    game_rows, lu_rows = [], []
    for s in config.SEASONS:
        gm[s], lines[s] = game_matrix(s)
        lu[s] = pair_configuration_split(
            nba.team_lineups(config.CELTICS_TEAM_ID, s), TATUM, BROWN)
        game_rows.append(gm[s])
        lu_rows.append(lu[s].assign(season=s))
        both = gm[s].set_index('cell').loc['both']
        print(f"  ✓ {s}: both {both['w']}-{both['l']} net {both['net']:+.1f} | "
              f"Tatum-only n={gm[s].set_index('cell').loc['tatum_only', 'n']}")

    pd.concat(game_rows, ignore_index=True).to_csv(
        config.PROCESSED_DIR / "tatum_first_option_games.csv", index=False)
    pd.concat(lu_rows, ignore_index=True).to_csv(
        config.PROCESSED_DIR / "tatum_first_option_lineups.csv", index=False)

    cdf = pooled_availability()
    cdf.to_csv(config.PROCESSED_DIR / "career_availability.csv", index=False)
    full = cdf.set_index("pool").loc[POOL_LABEL]
    print(f"  ✓ pooled {config.POOL_SEASONS[0]}..{config.POOL_SEASONS[-1]}: "
          f"Tatum-only {full['only_w']:.0f}-{full['only_l']:.0f} "
          f"({full['n_tatum_only']:.0f} g, margin {full['only_margin']:+.1f}) "
          f"| both {full['both_w']:.0f}-{full['both_l']:.0f} "
          f"({full['n_both']:.0f} g, margin {full['both_margin']:+.1f})")

    proj = build_projection(lu["2024-25"], lines["2024-25"])
    print(f"  ✓ projection: lineup gap {proj['gap']:+.2f} -> team net "
          f"{proj['net_lo']:+.1f}..{proj['net_hi']:+.1f} -> "
          f"{proj['wins_lo']:+.1f}..{proj['wins_hi']:+.1f} wins")

    _figure(lu["2024-25"], lines["2024-25"])
    _career_figure(cdf)
    _write(gm, lines, lu, proj, cdf)
    print("Done. outputs/tatum_first_option.md + figures/tatum_first_option.png"
          " + figures/career_availability.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
