"""Stage 1 — pull & cache all raw data for the study.

Pulls, for each season in config.SEASONS:
  * Brown's shot chart + all four tracking-shot splits
  * Celtics team tracking-shot profile (identity baseline)
  * League team + player advanced stats (winning-team baseline)
  * Celtics on/off details + 5-man lineups (for with/without splits)
  * League clutch stats
  * Brown passing (passes-per-touch)

Everything is cached to data/cache, so re-runs are instant and offline.

Usage:
    python scripts/01_pull_data.py                # both seasons
    python scripts/01_pull_data.py --season 2024-25
    python scripts/01_pull_data.py --force        # ignore cache
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import nba_client as nba

TRACK_SPLITS = ["general", "shotclock", "dribble", "touchtime", "closestdef"]


def pull_season(season: str, *, force: bool = False) -> None:
    sid = config.SUBJECT_ID
    tid = config.CELTICS_TEAM_ID
    print(f"\n=== Pulling {season} ===")

    steps = [
        ("Brown shot chart",
         lambda: nba.shot_chart(sid, season, force=force)),
        ("League team advanced",
         lambda: nba.league_team_stats(season, force=force)),
        ("League player advanced",
         lambda: nba.league_player_stats(season, force=force)),
        ("Celtics on/off",
         lambda: nba.team_on_off(tid, season, force=force)),
        ("Celtics 5-man lineups",
         lambda: nba.team_lineups(tid, season, force=force)),
        ("League clutch",
         lambda: nba.player_clutch(season, force=force)),
        ("Brown passing",
         lambda: nba.player_passing(sid, season, force=force)),
    ]
    for split in TRACK_SPLITS:
        steps.append((f"Brown tracking [{split}]",
                      lambda s=split: nba.player_tracking_shots(sid, season, split=s, force=force)))
        steps.append((f"Celtics tracking [{split}]",
                      lambda s=split: nba.team_tracking_shots(tid, season, split=s, force=force)))

    ok, fail = 0, 0
    for label, fn in steps:
        try:
            df = fn()
            print(f"  ✓ {label:32s} rows={len(df)}")
            ok += 1
        except Exception as e:  # keep going; one dead endpoint shouldn't halt the pull
            print(f"  ✗ {label:32s} {type(e).__name__}: {e}")
            fail += 1
    print(f"  -> {ok} ok, {fail} failed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", choices=config.SEASONS, help="single season")
    ap.add_argument("--force", action="store_true", help="ignore cache")
    args = ap.parse_args()

    try:
        import nba_api  # noqa: F401
    except ImportError:
        print("nba_api not installed. Run: pip install -r requirements.txt")
        return 1

    seasons = [args.season] if args.season else config.SEASONS
    for s in seasons:
        try:
            pull_season(s, force=args.force)
        except Exception:
            traceback.print_exc()
    print("\nDone. Cached under", config.CACHE_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
