"""Build the one-page 'Case for Moving On' figure.

Two panels, side by side:
  A) Shot-diet drift 2024-25 -> 2025-26 (the §1 argument)
  B) Brown on-court net rating with vs without Tatum / White, 2025-26 (§2)

Saves outputs/figures/case_for_moving_on.png. Reads from data/processed, so it
runs offline after stages 1-2.
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

RED, BLUE, GREY = "#c0392b", "#2c7fb8", "#95a5a6"


def _term(season: str) -> pd.Series:
    p = config.PROCESSED_DIR / f"termination_quality_{season}.csv"
    return pd.read_csv(p, index_col=0)["Jaylen Brown"]


def _ww(season: str, teammate: str) -> tuple[float, float]:
    p = config.PROCESSED_DIR / f"with_without_{season}.csv"
    df = pd.read_csv(p)
    sub = df[df["teammate"] == teammate].set_index("state")
    w = sub.loc["with", "NET_RATING"] if "with" in sub.index else np.nan
    wo = sub.loc["without", "NET_RATING"] if "without" in sub.index else np.nan
    return float(w), float(wo)


def panel_shot_drift(ax) -> None:
    t24, t25 = _term("2024-25"), _term("2025-26")
    labels = ["3PT rate", "Long-2 rate", "Iso rate\n(3+ dribble)", "Bad-shot\nindex"]
    keys = ["three_rate", "long_two_rate", "iso_dribble_rate", "bad_shot_index"]
    v24 = [float(t24.get(k, np.nan)) for k in keys]
    v25 = [float(t25.get(k, np.nan)) for k in keys]

    x = np.arange(len(keys))
    w = 0.38
    ax.bar(x - w / 2, v24, w, label="2024-25", color=GREY)
    ax.bar(x + w / 2, v25, w, label="2025-26", color=RED)

    # Direction annotations: down = good for 3PT, up = bad for the rest.
    for i, (a, b) in enumerate(zip(v24, v25)):
        arrow = "▲" if b > a else "▼"
        # For 3PT rate, a drop is the *bad* (off-identity) direction.
        bad = (b > a) if keys[i] != "three_rate" else (b < a)
        ax.annotate(f"{arrow} {abs(b - a):.02f}",
                    (x[i] + w / 2, b), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=8.5,
                    color=RED if bad else "#27ae60", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Share of FGA / index")
    ax.set_title("① Shot diet drifted away from the movement-3 system",
                 fontsize=12, fontweight="bold", loc="left")
    ax.legend(loc="upper left", fontsize=9)
    ax.text(0.5, -0.22,
            "Fewer threes, double the long twos, more isolation — "
            "and no shot-making premium (xFG over-expectation ≈ 0.00).",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555",
            style="italic")
    ax.margins(y=0.18)


def panel_contingent(ax) -> None:
    mates = ["Jayson Tatum", "Derrick White"]
    with_v, without_v = [], []
    for m in mates:
        w, wo = _ww("2025-26", m)
        with_v.append(w)
        without_v.append(wo)

    x = np.arange(len(mates))
    w = 0.38
    b1 = ax.bar(x - w / 2, with_v, w, label="Brown WITH", color=BLUE)
    b2 = ax.bar(x + w / 2, without_v, w, label="Brown WITHOUT", color=RED)
    ax.axhline(0, color="black", lw=0.9)

    for bars in (b1, b2):
        for rect in bars:
            h = rect.get_height()
            ax.annotate(f"{h:+.1f}", (rect.get_x() + rect.get_width() / 2, h),
                        textcoords="offset points",
                        xytext=(0, 4 if h >= 0 else -12),
                        ha="center", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([f"± {m}" for m in mates], fontsize=10)
    ax.set_ylabel("On-court Net Rating (2025-26)")
    ax.set_title("② The value was contingent on the creators",
                 fontsize=12, fontweight="bold", loc="left")
    ax.legend(loc="upper right", fontsize=9)
    ax.text(0.5, -0.22,
            "Strip out a primary creator and the on-court net rating collapses — "
            "underwater (−1.0) without White.",
            transform=ax.transAxes, ha="center", fontsize=8.5, color="#555",
            style="italic")


def main() -> int:
    fig, (axl, axr) = plt.subplots(1, 2, figsize=(14, 6.2))
    panel_shot_drift(axl)
    panel_contingent(axr)
    fig.suptitle("The Case for Moving On — Jaylen Brown, Celtics fit",
                 fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    out = config.FIG_DIR / "case_for_moving_on.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
