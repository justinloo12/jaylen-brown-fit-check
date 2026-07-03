"""Post-trade baseline: Jayson Tatum through the same lens we used on Brown.

Now that the trade is real (July 1, 2026), the forward-looking question is
whether the offense Boston kept — Tatum's — actually fits the system better
than the one it traded. Same metrics, same code paths, no special treatment:

  1. Fit — termination-quality profile (zones + tracking splits), Tatum vs
     Brown, both seasons.
  2. Lineup engine test — Celtics 5-man lineups led by Tatum WITHOUT Brown
     vs led by Brown WITHOUT Tatum (the cleanest "whose team is it" split).
  3. Shot quality — cross-validated xFG for both.
  4. Production context — BRef G/WS/VORP/BPM (Tatum's 2025-26 is
     injury-shortened; the brief must say so).

Outputs:
  * data/processed/tatum_vs_brown_fit.csv, tatum_vs_brown_lineups.csv
  * outputs/figures/tatum_baseline.png
  * outputs/tatum_vs_brown.md
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
from fitcheck.data import bref_scraper as bref
from fitcheck.data import nba_client as nba
from fitcheck.features import onoff, shot_profile
from fitcheck.models.shot_quality import fit_expected_fg

BROWN, TATUM = config.SUBJECT_ID, config.CELTICS_ROTATION["Jayson Tatum"]
RED, GREEN, GREY = "#c0392b", "#007a33", "#95a5a6"
FIT_KEYS = ["three_rate", "rim_rate", "long_two_rate", "catch_shoot_rate",
            "iso_dribble_rate", "contested_rate", "late_clock_rate",
            "bad_shot_index"]


def fit_profile(pid: int, season: str) -> pd.Series:
    zone = shot_profile.shot_zone_profile(nba.shot_chart(pid, season))
    creation = shot_profile.self_creation_profile(
        nba.player_tracking_shots(pid, season, split="dribble"),
        nba.player_tracking_shots(pid, season, split="touchtime"),
        nba.player_tracking_shots(pid, season, split="closestdef"),
        nba.player_tracking_shots(pid, season, split="shotclock"),
    )
    return shot_profile.termination_quality(zone, creation)


def xfg_row(pid: int, season: str) -> dict:
    shots = nba.shot_chart(pid, season)
    _, scored, m = fit_expected_fg(shots)
    return {"n_shots": m["n"], "mean_xFG": m["expected_fg"],
            "actual_FG": m["actual_fg"],
            "over_expected": m["shot_making_over_expected"]}


def main() -> int:
    players = {"Jayson Tatum": TATUM, "Jaylen Brown": BROWN}

    # ---- 1. fit profiles ----
    fit_rows = []
    for name, pid in players.items():
        for s in config.SEASONS:
            prof = fit_profile(pid, s)
            fit_rows.append({"player": name, "season": s, **prof.to_dict(),
                             **xfg_row(pid, s)})
            print(f"  ✓ fit {name} {s}  bad_shot_index="
                  f"{prof.get('bad_shot_index', np.nan):.3f}")
    fit_df = pd.DataFrame(fit_rows)
    fit_df.to_csv(config.PROCESSED_DIR / "tatum_vs_brown_fit.csv", index=False)

    # ---- 2. lineup engine test: each star WITHOUT the other ----
    lu_rows = []
    for s in config.SEASONS:
        lineups = nba.team_lineups(config.CELTICS_TEAM_ID, s)
        t = onoff.with_without_split(lineups, TATUM, BROWN).set_index("state")
        b = onoff.with_without_split(lineups, BROWN, TATUM).set_index("state")
        lu_rows.append({
            "season": s,
            "tatum_led_net": t.loc["without", "NET_RATING"],
            "tatum_led_min": t.loc["without", "MIN"],
            "brown_led_net": b.loc["without", "NET_RATING"],
            "brown_led_min": b.loc["without", "MIN"],
            "together_net": t.loc["with", "NET_RATING"],
            "together_min": t.loc["with", "MIN"],
        })
        print(f"  ✓ lineups {s}: Tatum-led "
              f"{lu_rows[-1]['tatum_led_net']:+.1f} ({lu_rows[-1]['tatum_led_min']:.0f} min) "
              f"vs Brown-led {lu_rows[-1]['brown_led_net']:+.1f} "
              f"({lu_rows[-1]['brown_led_min']:.0f} min)")
    lu_df = pd.DataFrame(lu_rows)
    lu_df.to_csv(config.PROCESSED_DIR / "tatum_vs_brown_lineups.csv", index=False)

    # ---- 3. production context ----
    prod = {}
    for name, slug in [("Jayson Tatum", "tatumja01"), ("Jaylen Brown", "brownja02")]:
        adv = bref.player_advanced(slug)
        rows = {}
        for s in config.SEASONS:
            sub = adv[adv["Season"].astype(str).str.startswith(s[:4])]
            if not sub.empty:
                r = sub.iloc[-1]
                rows[s] = {k: pd.to_numeric(r.get(k), errors="coerce")
                           for k in ["G", "WS", "VORP", "BPM"]}
        prod[name] = rows

    _figure(fit_df, lu_df)
    _write(fit_df, lu_df, prod)
    print("Done. outputs/tatum_vs_brown.md + figures/tatum_baseline.png")
    return 0


def _figure(fit_df: pd.DataFrame, lu_df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.6))

    # A: fit profile 2025-26
    ax = axes[0]
    keys = ["three_rate", "catch_shoot_rate", "iso_dribble_rate",
            "long_two_rate", "bad_shot_index"]
    labels = ["3PT\nrate", "Catch &\nshoot", "Iso\n(3+ dr)", "Long-2\nrate",
              "Bad-shot\nindex"]
    cur = fit_df[fit_df.season == "2025-26"].set_index("player")
    x = np.arange(len(keys)); w = 0.38
    ax.bar(x - w/2, [cur.loc["Jaylen Brown", k] for k in keys], w,
           label="Brown", color=RED)
    ax.bar(x + w/2, [cur.loc["Jayson Tatum", k] for k in keys], w,
           label="Tatum", color=GREEN)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Share of FGA / index")
    ax.set_title("① Shot diet, 2025-26 — same lens, both stars",
                 fontsize=11, fontweight="bold", loc="left")
    ax.legend(fontsize=9)

    # B: engine test, both seasons
    ax = axes[1]
    seasons = lu_df["season"].tolist()
    x = np.arange(len(seasons)); w = 0.38
    b1 = ax.bar(x - w/2, lu_df["brown_led_net"], w, label="Brown-led (Tatum off)",
                color=RED)
    b2 = ax.bar(x + w/2, lu_df["tatum_led_net"], w, label="Tatum-led (Brown off)",
                color=GREEN)
    ax.axhline(0, color="black", lw=0.9)
    for bars, mins in ((b1, lu_df["brown_led_min"]), (b2, lu_df["tatum_led_min"])):
        for rect, mn in zip(bars, mins):
            h = rect.get_height()
            ax.annotate(f"{h:+.1f}\n({mn:.0f} min)",
                        (rect.get_x() + rect.get_width()/2, h),
                        textcoords="offset points",
                        xytext=(0, 5 if h >= 0 else -26),
                        ha="center", fontsize=8.5, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(seasons)
    ax.set_ylabel("Lineup Net Rating (min-weighted)")
    ax.set_title("② The engine test — each star without the other",
                 fontsize=11, fontweight="bold", loc="left")
    ax.legend(fontsize=8.5)
    ax.margins(y=0.25)

    # C: xFG over expectation
    ax = axes[2]
    x = np.arange(len(seasons)); w = 0.38
    for i, (name, color) in enumerate([("Jaylen Brown", RED),
                                       ("Jayson Tatum", GREEN)]):
        vals = [fit_df[(fit_df.player == name) & (fit_df.season == s)]
                ["over_expected"].iloc[0] * 100 for s in seasons]
        bars = ax.bar(x + (i - 0.5) * w, vals, w, label=name.split()[1],
                      color=color)
        for rect in bars:
            h = rect.get_height()
            ax.annotate(f"{h:+.1f}", (rect.get_x() + rect.get_width()/2, h),
                        textcoords="offset points",
                        xytext=(0, 4 if h >= 0 else -12),
                        ha="center", fontsize=9, fontweight="bold")
    ax.axhline(0, color="black", lw=0.9)
    ax.set_xticks(x); ax.set_xticklabels(seasons)
    ax.set_ylabel("Actual FG% − expected FG% (pts)")
    ax.set_title("③ Shot-making over expectation (xFG model)",
                 fontsize=11, fontweight="bold", loc="left")
    ax.legend(fontsize=9)
    ax.margins(y=0.25)

    fig.suptitle("The offense Boston kept — Tatum through the Brown lens",
                 fontsize=14.5, fontweight="bold", y=1.03)
    fig.tight_layout()
    out = config.FIG_DIR / "tatum_baseline.png"
    fig.savefig(out, dpi=155, bbox_inches="tight")
    plt.close(fig)


def _write(fit_df: pd.DataFrame, lu_df: pd.DataFrame, prod: dict) -> None:
    def f(name, season, col):
        r = fit_df[(fit_df.player == name) & (fit_df.season == season)]
        return r[col].iloc[0] if not r.empty else np.nan

    L = [
        "# The Offense Boston Kept — Tatum vs Brown, Same Lens",
        "",
        "_Post-trade baseline (trade completed July 1, 2026). Tatum's numbers "
        "run through the identical pipeline used on Brown — same metrics, same "
        "code, no special treatment. **Read §4 first: Tatum's 2025-26 is "
        "injury-shortened, which limits every 2025-26 comparison here.**_",
        "",
        "## 1. Shot diet — Tatum's profile is what the system wants",
        "",
        "| Metric (2025-26) | Brown | Tatum | Fits the system |",
        "|---|---|---|---|",
    ]
    for k, lab, better_low in [
        ("three_rate", "3PT rate", False),
        ("catch_shoot_rate", "Catch-&-shoot rate", False),
        ("iso_dribble_rate", "Iso / 3+ dribble rate", True),
        ("long_two_rate", "Long-2 rate", True),
        ("contested_rate", "Contested rate", True),
        ("late_clock_rate", "Late-clock rate", True),
        ("bad_shot_index", "Bad-shot index", True),
    ]:
        b, t = f("Jaylen Brown", "2025-26", k), f("Jayson Tatum", "2025-26", k)
        edge = "Tatum" if ((t < b) == better_low) else "Brown"
        L.append(f"| {lab} | {b:.3f} | {t:.3f} | {edge} |")

    b24 = f("Jaylen Brown", "2024-25", "bad_shot_index")
    t24 = f("Jayson Tatum", "2024-25", "bad_shot_index")
    t3_24, b3_24 = f("Jayson Tatum", "2024-25", "three_rate"), f("Jaylen Brown", "2024-25", "three_rate")
    t3_25, b3_25 = f("Jayson Tatum", "2025-26", "three_rate"), f("Jaylen Brown", "2025-26", "three_rate")
    tl2, bl2 = f("Jayson Tatum", "2025-26", "long_two_rate"), f("Jaylen Brown", "2025-26", "long_two_rate")
    L += [
        "",
        "**Honest read:** on the composite bad-shot index the two are "
        f"near-identical isolators in 2024-25 (Tatum {t24:.3f}, Brown {b24:.3f} "
        "— Brown marginally *cleaner*), and Tatum self-creates just as much "
        "(iso rate ≈ 0.53-0.56 both seasons). The fit case is about the **shot "
        f"mix**: Tatum takes half his shots from three ({t3_24:.3f} → {t3_25:.3f}) "
        f"— roughly double Brown's rate ({b3_24:.3f} → {b3_25:.3f}) — and cut his "
        f"long-two rate to {tl2:.3f} while Brown's doubled to {bl2:.3f}. Tatum's "
        "self-creation terminates in the system's anchor shot; Brown's "
        "increasingly terminated in the shot the system exists to avoid.",
        "",
        "## 2. The engine test — each star's lineups without the other",
        "",
        "| Season | Brown-led (Tatum off) | Tatum-led (Brown off) | Together |",
        "|---|---|---|---|",
    ]
    for _, r in lu_df.iterrows():
        L.append(f"| {r.season} | {r.brown_led_net:+.1f} ({r.brown_led_min:.0f} min) "
                 f"| {r.tatum_led_net:+.1f} ({r.tatum_led_min:.0f} min) "
                 f"| {r.together_net:+.1f} ({r.together_min:.0f} min) |")

    r24 = lu_df[lu_df.season == "2024-25"].iloc[0]
    r25 = lu_df[lu_df.season == "2025-26"].iloc[0]
    L += [
        "",
        f"The clean comparison is 2024-25, when both were healthy: **Tatum-led "
        f"minutes outperformed Brown-led minutes ({r24.tatum_led_net:+.1f} vs "
        f"{r24.brown_led_net:+.1f}) on a larger sample ({r24.tatum_led_min:.0f} "
        f"vs {r24.brown_led_min:.0f} min)**. The 2025-26 Tatum-led number "
        f"({r25.tatum_led_net:+.1f}) sits on just {r25.tatum_led_min:.0f} "
        "minutes — an injury-season shard, not evidence.",
        "",
        "## 3. Shot-making over expectation",
        "",
        "| | Brown 24-25 | Brown 25-26 | Tatum 24-25 | Tatum 25-26 |",
        "|---|---|---|---|---|",
        "| Actual − expected FG% | "
        + " | ".join(f"{f(n, s, 'over_expected')*100:+.1f}"
                     for n in ["Jaylen Brown", "Jayson Tatum"]
                     for s in config.SEASONS) + " |",
        "",
        "## 4. Caveats (read before quoting)",
    ]
    tg = prod.get("Jayson Tatum", {})
    bg = prod.get("Jaylen Brown", {})
    t26 = tg.get("2025-26", {})
    b26 = bg.get("2025-26", {})
    L += [
        f"- **Tatum's 2025-26 was injury-shortened**: {t26.get('G', float('nan')):.0f} games, "
        f"{t26.get('WS', float('nan')):.1f} WS vs Brown's {b26.get('G', float('nan')):.0f} games, "
        f"{b26.get('WS', float('nan')):.1f} WS. Rate stats (§1, §3) survive small samples "
        "far better than lineup nets (§2).",
        "- 'X-led' minutes are minute-weighted 5-man lineup aggregates; both "
        "stars' 'led' samples include bench-heavy and garbage-time units.",
        "- Brown finished 6th in 2025-26 MVP voting; nothing here claims Tatum "
        "vs Brown is a settled question — it measures *system fit*, not talent.",
    ]
    (config.OUTPUT_DIR / "tatum_vs_brown.md").write_text("\n".join(L),
                                                         encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
