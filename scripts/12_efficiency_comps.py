"""How does Brown stack up against high-efficiency max-contract players?

Positions Brown inside the 20-player max/near-max comp set on the axes that
define 'worth the check': scoring efficiency (TS%), offensive load (USG%),
per-minute value (BRef WS/48), and price (salary, cost/WS).

Data: cached league-wide Advanced stats (nba_api), the stage-3 value tables,
and cached BRef advanced pages — fully offline after stage 1/3.

Outputs:
  * data/processed/efficiency_comps_<season>.csv
  * outputs/figures/efficiency_comps.png
  * outputs/efficiency_comps.md
"""
from __future__ import annotations

import pathlib
import sys
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import bref_scraper as bref
from fitcheck.data import nba_client as nba

RED, BLUE, GREY, GREEN = "#c0392b", "#2c7fb8", "#8a97a5", "#007a33"

# NBA stats display names that differ from our comp-set names.
NBA_ALIASES = {"Jimmy Butler": "Jimmy Butler III"}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def comp_table(season: str) -> pd.DataFrame:
    adv = nba.league_player_stats(season, measure="Advanced")
    base = nba.league_player_stats(season, measure="Base")
    val = pd.read_csv(config.PROCESSED_DIR / f"value_table_{season}.csv")

    lookup = {_norm(n): n for n in adv["PLAYER_NAME"]}
    rows = []
    for name, slug in bref.BREF_SLUGS.items():
        nba_name = lookup.get(_norm(NBA_ALIASES.get(name, name)))
        if nba_name is None:
            print(f"  ! no league-stats row for {name} ({season}) — skipped")
            continue
        a = adv[adv["PLAYER_NAME"] == nba_name].iloc[0]
        b = base[base["PLAYER_NAME"] == nba_name].iloc[0]
        v = val[val["player"] == name]
        badv = bref.player_advanced(slug)
        sub = badv[badv["Season"].astype(str).str.startswith(season[:4])]
        ws48 = pd.to_numeric(sub.iloc[-1].get("WS/48"), errors="coerce") if not sub.empty else np.nan
        rows.append({
            "player": name, "season": season,
            "GP": a["GP"], "MIN": a["MIN"],
            "TS_PCT": a["TS_PCT"], "USG_PCT": a["USG_PCT"] * 100,
            "PTS": b["PTS"],
            "WS48": ws48,
            "salary": v["salary"].iloc[0] if not v.empty else np.nan,
            "cap_pct": v["cap_pct"].iloc[0] if not v.empty else np.nan,
            "cost_per_WS": v["cost_per_WS"].iloc[0] if not v.empty else np.nan,
        })
    df = pd.DataFrame(rows)
    df["TS_rank"] = df["TS_PCT"].rank(ascending=False).astype(int)
    df["WS48_rank"] = df["WS48"].rank(ascending=False)
    return df.sort_values("TS_PCT", ascending=False).reset_index(drop=True)


def league_ts_reference(season: str) -> float:
    """Median TS% among rotation-level players (>= 40 GP, >= 20 MIN)."""
    adv = nba.league_player_stats(season, measure="Advanced")
    qual = adv[(adv["GP"] >= 40) & (adv["MIN"] >= 20.0)]
    return float(qual["TS_PCT"].median())


def _figure(dfs: dict[str, pd.DataFrame], refs: dict[str, float]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.2))

    # A: TS% vs USG%, 2025-26, bubble = salary
    season = "2025-26"
    df, ref = dfs[season], refs[season]
    ax = axes[0]
    for _, r in df.iterrows():
        hi = r.player == "Jaylen Brown"
        ax.scatter(r.USG_PCT, r.TS_PCT, s=r.salary / 2e5,
                   c=RED if hi else GREY, alpha=0.9 if hi else 0.55,
                   edgecolors="black" if hi else "none", zorder=5 if hi else 3)
        last = r.player.split()[-1] if r.player != "Jaylen Brown" else "BROWN"
        ax.annotate(last, (r.USG_PCT, r.TS_PCT), fontsize=7.5,
                    fontweight="bold" if hi else "normal",
                    color=RED if hi else "#444",
                    xytext=(5, 4), textcoords="offset points")
    ax.axhline(ref, color=GREEN, lw=1.2, ls="--")
    ax.annotate(f"league median TS ({ref:.3f})", (ax.get_xlim()[0], ref),
                fontsize=8, color=GREEN, xytext=(6, 5),
                textcoords="offset points")
    ax.set_xlabel("Usage % (offensive load)")
    ax.set_ylabel("True Shooting %")
    ax.set_title("① Efficiency vs load, 2025-26 — bubble = salary",
                 fontsize=11.5, fontweight="bold", loc="left")

    # B: TS% ranked bars, 2025-26
    ax = axes[1]
    d = df.sort_values("TS_PCT")
    colors = [RED if p == "Jaylen Brown" else GREY for p in d.player]
    bars = ax.barh(d.player, d.TS_PCT, color=colors)
    for rect, (_, r) in zip(bars, d.iterrows()):
        ax.annotate(f"{r.TS_PCT:.3f} · {r.cap_pct*100:.0f}% cap",
                    (rect.get_width(), rect.get_y() + rect.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=7.5)
    ax.axvline(ref, color=GREEN, lw=1.2, ls="--")
    ax.set_xlim(d.TS_PCT.min() - 0.03, d.TS_PCT.max() + 0.045)
    ax.set_xlabel("True Shooting %")
    ax.set_title("② TS% rank in the max-contract comp set, 2025-26",
                 fontsize=11.5, fontweight="bold", loc="left")

    fig.suptitle("Brown vs the max-contract market — efficiency for the price",
                 fontsize=14.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    out = config.FIG_DIR / "efficiency_comps.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)


def _write(dfs: dict[str, pd.DataFrame], refs: dict[str, float]) -> None:
    L = [
        "# Brown vs the Max-Contract Market — Efficiency for the Price",
        "",
        "_Same 20-player max/near-max comp set as the value model. TS% and USG%"
        " from stats.nba.com; WS/48 from Basketball-Reference; salary from the"
        " stage-3 scrape. Injury-shortened seasons flagged._",
        "",
    ]
    for season, df in dfs.items():
        n = len(df)
        b = df[df.player == "Jaylen Brown"].iloc[0]
        L += [
            f"## {season}",
            "",
            f"League median TS% (rotation players): **{refs[season]:.3f}**",
            "",
            "| Player | GP | TS% | USG% | PTS | WS/48 | Cap % | Cost/WS |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for _, r in df.iterrows():
            tag = "**" if r.player == "Jaylen Brown" else ""
            cw = f"${r.cost_per_WS/1e6:.1f}M" if pd.notna(r.cost_per_WS) else "—"
            L.append(
                f"| {tag}{r.player}{tag} | {r.GP:.0f} | {r.TS_PCT:.3f} "
                f"| {r.USG_PCT:.1f} | {r.PTS:.1f} | "
                f"{r.WS48:.3f} | {r.cap_pct*100:.0f}% | {cw} |")
        L += [
            "",
            f"Brown: TS% rank **{b.TS_rank}/{n}**, WS/48 rank "
            f"**{b.WS48_rank:.0f}/{n}**, at {b.cap_pct*100:.0f}% of the cap.",
            "",
        ]
    L += [
        "## Caveats",
        "- Single-season TS% swings a few points on shot luck; ranks, not "
        "third decimals.",
        "- Usage and efficiency trade off — the scatter (figure, panel ①) is "
        "the fair view: same-load comparisons matter more than the raw rank.",
        "- Injury-shortened seasons (low GP) rank on thin samples; check the "
        "GP column before quoting a rank.",
    ]
    (config.OUTPUT_DIR / "efficiency_comps.md").write_text("\n".join(L),
                                                           encoding="utf-8")


def main() -> int:
    dfs, refs = {}, {}
    for season in config.SEASONS:
        df = comp_table(season)
        dfs[season] = df
        refs[season] = league_ts_reference(season)
        df.to_csv(config.PROCESSED_DIR / f"efficiency_comps_{season}.csv",
                  index=False)
        b = df[df.player == "Jaylen Brown"].iloc[0]
        print(f"  ✓ {season}: Brown TS {b.TS_PCT:.3f} "
              f"(rank {b.TS_rank}/{len(df)}), USG {b.USG_PCT:.1f}, "
              f"WS/48 {b.WS48:.3f}, league median TS {refs[season]:.3f}")
    _figure(dfs, refs)
    _write(dfs, refs)
    print("Done. outputs/efficiency_comps.md + figures/efficiency_comps.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
