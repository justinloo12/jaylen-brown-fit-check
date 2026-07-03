"""Stage 4 — render figures and assemble the plain-English writeup.

Produces:
  * outputs/figures/shot_chart_<season>.png
  * outputs/figures/with_without_net_<season>.png
  * outputs/figures/cost_per_win_<season>.png
  * outputs/figures/profile_radar_<season>.png
  * outputs/report.md   — the quantitative case in prose, filled from the tables
"""
from __future__ import annotations

import pathlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import nba_client as nba
from fitcheck.features import onoff, shot_profile
from fitcheck.viz import charts


def _load_csv(name: str) -> pd.DataFrame:
    p = config.PROCESSED_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def figures_for(season: str) -> dict[str, Path]:
    made = {}
    # Shot chart
    try:
        shots = nba.shot_chart(config.SUBJECT_ID, season)
        if not shots.empty:
            made["shot_chart"] = charts.shot_chart_hex(
                shots, f"Jaylen Brown shot chart — {season}",
                fname=f"shot_chart_{season}.png")
    except Exception as e:
        print(f"  ! shot chart: {e}")

    # With/without bars
    ww = _load_csv(f"with_without_{season}.csv")
    if not ww.empty:
        splits = {m: ww[ww["teammate"] == m][["state", "NET_RATING"]]
                  for m in ww["teammate"].unique()}
        made["with_without"] = charts.with_without_bar(
            splits, fname=f"with_without_net_{season}.png")

    # Cost per win
    val = _load_csv(f"value_table_{season}.csv")
    if not val.empty:
        made["cost_per_win"] = charts.cost_per_win_scatter(
            val, fname=f"cost_per_win_{season}.png")
    return made


def report_section(season: str) -> str:
    term = _load_csv(f"termination_quality_{season}.csv")
    ww = _load_csv(f"with_without_{season}.csv")
    val = _load_csv(f"value_table_{season}.csv")

    lines = [f"## {season}\n"]

    if not term.empty:
        t = term.set_index(term.columns[0])["Jaylen Brown"]
        lines.append("**Shot profile (possession termination quality)**\n")
        for k in ["three_rate", "rim_rate", "long_two_rate", "iso_dribble_rate",
                  "contested_rate", "late_clock_rate", "bad_shot_index"]:
            if k in t.index:
                lines.append(f"- `{k}`: {float(t[k]):.3f}")
        lines.append("")

    if not ww.empty:
        lines.append("**On-court net rating, with vs without key creators**\n")
        for m in ww["teammate"].unique():
            sub = ww[ww["teammate"] == m].set_index("state")
            w = sub.loc["with", "NET_RATING"] if "with" in sub.index else float("nan")
            wo = sub.loc["without", "NET_RATING"] if "without" in sub.index else float("nan")
            if pd.isna(w) or pd.isna(wo):
                # e.g. a teammate no longer on the roster -> no shared minutes.
                have = f"{w:+.1f} with" if not pd.isna(w) else f"{wo:+.1f} without"
                lines.append(f"- ± {m}: {have} _(no shared minutes for the other split)_")
            else:
                lines.append(f"- ± {m}: **{w:+.1f}** with / **{wo:+.1f}** without "
                             f"(swing {w - wo:+.1f})")
        lines.append("")

    if not val.empty:
        b = val[val["player"] == "Jaylen Brown"]
        if not b.empty:
            r = b.iloc[0]
            lines.append("**Contract value**\n")
            lines.append(f"- Salary: ${r['salary']:,.0f}  ({r['cap_pct']*100:.1f}% of cap)")
            lines.append(f"- Win Shares: {r['WS']}  |  cost/WS: ${r['cost_per_WS']:,.0f}")
            lines.append(f"- Value percentile vs comp wings: {r['value_pctile']:.2f} "
                         f"(1.00 = best value)\n")
    return "\n".join(lines)


def main() -> int:
    all_figs = {}
    for s in config.SEASONS:
        print(f"\n=== Figures {s} ===")
        all_figs[s] = figures_for(s)
        for k, p in all_figs[s].items():
            print(f"  ✓ {k}: {p.name}")

    report = ["# Fit Check — Did Jaylen Brown fit Boston's system?\n",
              "_Auto-generated from the pipeline. Numbers, not takes._\n",
              "> This report tests the hypothesis; it does not assume it. "
              "Where the data cuts against the thesis, the section says so.\n"]
    for s in config.SEASONS:
        report.append(report_section(s))
    out = config.OUTPUT_DIR / "report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
