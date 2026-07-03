"""Central configuration: player/team IDs, seasons, paths, and analysis constants.

Everything downstream imports from here so there are no magic numbers scattered
through the pipeline. IDs are stats.nba.com person/team IDs.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = ROOT / "outputs"
FIG_DIR = OUTPUT_DIR / "figures"

for _d in (RAW_DIR, PROCESSED_DIR, CACHE_DIR, OUTPUT_DIR, FIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Seasons under study
# ---------------------------------------------------------------------------
SEASONS = ["2024-25", "2025-26"]
SEASON_TYPE = "Regular Season"

# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------
CELTICS_TEAM_ID = 1610612738

# ---------------------------------------------------------------------------
# Players (stats.nba.com person IDs)
# ---------------------------------------------------------------------------
SUBJECT = "Jaylen Brown"
SUBJECT_ID = 1627759

# Key Celtics teammates used for comparison / with-without splits.
CELTICS_ROTATION = {
    "Jaylen Brown": 1627759,
    "Jayson Tatum": 1628369,
    "Derrick White": 1628401,
    "Jrue Holiday": 201950,
    "Kristaps Porzingis": 204001,
    "Al Horford": 201143,
    "Payton Pritchard": 1630202,
    "Sam Hauser": 1629130,
}

# Teammates we cut Brown's on-court splits by (with / without).
WITH_WITHOUT_TARGETS = ["Jayson Tatum", "Derrick White", "Jrue Holiday"]

# The contract-value comp set (max/near-max perimeter players) lives in
# fitcheck.data.bref_scraper.BREF_SLUGS — names + Basketball-Reference slugs,
# since the value model is built entirely from BRef data.

# ---------------------------------------------------------------------------
# Analysis thresholds (documented so the "bad shot" definition is auditable)
# ---------------------------------------------------------------------------
# A "bad shot" here = a contested long two, or an early-clock isolation jumper.
LONG_TWO_MIN_FT = 16          # feet: 16ft -> 3pt line = "long two" zone
CONTESTED_MAX_DEF_FT = 4      # closest defender within N feet == contested
LATE_SHOT_CLOCK = 7           # <= N sec on shot clock == late clock
ISO_MIN_DRIBBLES = 3          # >= N dribbles before shot == self-created / iso-ish
ISO_MIN_TOUCH_TIME = 6.0      # >= N sec of touch time == holds the ball

# Salary cap for cap-% math. Update per season (in USD).
SALARY_CAP = {
    "2024-25": 140_588_000,
    "2025-26": 154_647_000,
}

# nba_api request pacing (seconds between calls) to avoid rate limiting.
REQUEST_SLEEP = 0.6
