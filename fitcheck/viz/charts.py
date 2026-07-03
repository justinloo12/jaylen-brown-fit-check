"""Matplotlib visualizations. Each function saves to outputs/figures and
returns the path. No seaborn dependency required, but used if present.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fitcheck.config import FIG_DIR


def _draw_court(ax, color="black", lw=1.5):
    """Minimal half-court for shot charts (hoop at origin, feet*10 units)."""
    from matplotlib.patches import Circle, Rectangle, Arc
    ax.add_patch(Circle((0, 0), radius=7.5, lw=lw, ec=color, fc="none"))
    ax.add_patch(Rectangle((-30, -7.5), 60, -1, lw=lw, ec=color, fc=color))
    ax.add_patch(Rectangle((-80, -47.5), 160, 190, lw=lw, ec=color, fc="none"))
    ax.add_patch(Arc((0, 142.5), 120, 120, theta1=0, theta2=180, lw=lw, ec=color))
    ax.add_patch(Arc((0, 0), 475, 475, theta1=22, theta2=158, lw=lw, ec=color))
    ax.plot([-220, -220], [-47.5, 92.5], color=color, lw=lw)
    ax.plot([220, 220], [-47.5, 92.5], color=color, lw=lw)
    ax.set_xlim(-250, 250)
    ax.set_ylim(-50, 425)
    ax.set_aspect("equal")
    ax.axis("off")


def shot_chart_hex(shots: pd.DataFrame, title: str,
                   fname: str = "shot_chart.png") -> Path:
    """Hexbin-style shot chart from LOC_X / LOC_Y."""
    fig, ax = plt.subplots(figsize=(7, 6.5))
    _draw_court(ax)
    made = shots["SHOT_MADE_FLAG"] == 1
    ax.scatter(shots.loc[~made, "LOC_X"], shots.loc[~made, "LOC_Y"],
               c="#c0392b", marker="x", s=18, alpha=0.5, label="Miss")
    ax.scatter(shots.loc[made, "LOC_X"], shots.loc[made, "LOC_Y"],
               c="#27ae60", marker="o", s=18, alpha=0.6,
               edgecolors="white", linewidths=0.3, label="Make")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8)
    path = FIG_DIR / fname
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def with_without_bar(splits: dict[str, pd.DataFrame],
                     fname: str = "with_without_net.png") -> Path:
    """Grouped bar: subject NET_RATING with vs without each teammate.

    ``splits`` maps teammate name -> the 2-row frame from
    onoff.with_without_split (states 'with'/'without').
    """
    mates = list(splits.keys())
    with_vals, without_vals = [], []
    for m in mates:
        df = splits[m].set_index("state")
        with_vals.append(df.loc["with", "NET_RATING"] if "with" in df.index else np.nan)
        without_vals.append(df.loc["without", "NET_RATING"] if "without" in df.index else np.nan)

    x = np.arange(len(mates))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w / 2, with_vals, w, label="Brown WITH teammate", color="#2c7fb8")
    ax.bar(x + w / 2, without_vals, w, label="Brown WITHOUT teammate", color="#d95f0e")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"± {m}" for m in mates])
    ax.set_ylabel("Net Rating (minute-weighted)")
    ax.set_title("Jaylen Brown on-court Net Rating: with vs without key creators",
                 fontsize=12, fontweight="bold")
    ax.legend()
    path = FIG_DIR / fname
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def cost_per_win_scatter(value_df: pd.DataFrame, highlight: str = "Jaylen Brown",
                         fname: str = "cost_per_win.png") -> Path:
    """Scatter: production (WS) vs pay (cap %), Brown highlighted."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(value_df["cap_pct"] * 100, value_df["WS"],
               c="#888", s=60, alpha=0.7)
    for _, r in value_df.iterrows():
        is_hi = r["player"] == highlight
        ax.annotate(r["player"], (r["cap_pct"] * 100, r["WS"]),
                    fontsize=8, fontweight="bold" if is_hi else "normal",
                    color="#c0392b" if is_hi else "#333",
                    xytext=(4, 3), textcoords="offset points")
        if is_hi:
            ax.scatter([r["cap_pct"] * 100], [r["WS"]], c="#c0392b", s=140,
                       zorder=5, edgecolors="black")
    ax.set_xlabel("Salary as % of cap")
    ax.set_ylabel("Win Shares")
    ax.set_title("Pay vs Production — is Brown's cap hit earning its keep?",
                 fontsize=12, fontweight="bold")
    path = FIG_DIR / fname
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def profile_radar(profile: pd.Series, baseline: pd.Series, title: str,
                  fname: str = "profile_radar.png") -> Path:
    """Radar comparing Brown's termination profile to a baseline (team/league)."""
    keys = [k for k in ["long_two_rate", "iso_dribble_rate", "contested_rate",
                        "late_clock_rate", "three_rate"] if k in profile]
    vals = [profile.get(k, 0) for k in keys]
    base = [baseline.get(k, 0) for k in keys]
    ang = np.linspace(0, 2 * np.pi, len(keys), endpoint=False).tolist()
    vals += vals[:1]; base += base[:1]; ang += ang[:1]

    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"polar": True})
    ax.plot(ang, vals, color="#c0392b", label="Brown")
    ax.fill(ang, vals, color="#c0392b", alpha=0.2)
    ax.plot(ang, base, color="#2c7fb8", label="Baseline")
    ax.fill(ang, base, color="#2c7fb8", alpha=0.15)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels([k.replace("_rate", "").replace("_", " ") for k in keys],
                       fontsize=8)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    path = FIG_DIR / fname
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
