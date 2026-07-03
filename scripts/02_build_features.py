"""Stage 2 — turn cached raw data into the analysis tables.

Writes tidy CSVs to data/processed:
  * shot_profile_<season>.csv      — Brown vs Celtics vs league shot diet
  * termination_quality_<season>.csv
  * with_without_<season>.csv      — Brown net rating ± Tatum/White/Holiday
  * clutch_<season>.csv

Reads only from cache, so it runs offline after Stage 1.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import nba_client as nba
from fitcheck.features import onoff, shot_profile


def _safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        print(f"  ! {type(e).__name__}: {e}")
        return default if default is not None else pd.DataFrame()


def build_season(season: str) -> None:
    sid, tid = config.SUBJECT_ID, config.CELTICS_TEAM_ID
    print(f"\n=== Features {season} ===")

    # --- Angle 1: shot profile ---
    shots = _safe(lambda: nba.shot_chart(sid, season))
    zone = shot_profile.shot_zone_profile(shots) if not shots.empty else pd.Series(dtype=float)

    creation = shot_profile.self_creation_profile(
        _safe(lambda: nba.player_tracking_shots(sid, season, split="dribble")),
        _safe(lambda: nba.player_tracking_shots(sid, season, split="touchtime")),
        _safe(lambda: nba.player_tracking_shots(sid, season, split="closestdef")),
        _safe(lambda: nba.player_tracking_shots(sid, season, split="shotclock")),
    )
    term = shot_profile.termination_quality(zone, creation)
    term.to_frame("Jaylen Brown").to_csv(
        config.PROCESSED_DIR / f"termination_quality_{season}.csv")
    print(f"  ✓ termination_quality  bad_shot_index={term.get('bad_shot_index'):.3f}"
          if "bad_shot_index" in term else "  ✓ termination_quality (partial)")

    # --- Angle 2: with/without splits ---
    lineups = _safe(lambda: nba.team_lineups(tid, season))
    ww_rows = []
    if not lineups.empty:
        for mate in config.WITH_WITHOUT_TARGETS:
            mate_id = config.CELTICS_ROTATION[mate]
            split = onoff.with_without_split(lineups, sid, mate_id)
            split["teammate"] = mate
            ww_rows.append(split)
            with_net = split.set_index("state").loc["with", "NET_RATING"] \
                if "with" in split["state"].values else float("nan")
            without_net = split.set_index("state").loc["without", "NET_RATING"] \
                if "without" in split["state"].values else float("nan")
            print(f"  ✓ ± {mate:16s} with={with_net:+.1f}  without={without_net:+.1f}")
        pd.concat(ww_rows, ignore_index=True).to_csv(
            config.PROCESSED_DIR / f"with_without_{season}.csv", index=False)

    # --- Angle 2: clutch ---
    clutch = _safe(lambda: nba.player_clutch(season))
    if not clutch.empty:
        row = onoff.clutch_row(clutch, sid)
        row.to_frame("Jaylen Brown").to_csv(
            config.PROCESSED_DIR / f"clutch_{season}.csv")
        print("  ✓ clutch")


def main() -> int:
    for s in config.SEASONS:
        build_season(s)
    print("\nProcessed tables in", config.PROCESSED_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
