"""Stage 3 — contract value model (BRef scrape → cost-per-win table).

Scrapes Win Shares / VORP and salaries for Brown + comp wings, then builds the
cost-per-WS / cost-per-VORP table saved to data/processed/value_table_<season>.csv.

BRef rate-limits hard; this is slow on a cold cache by design. Re-runs are fast.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config
from fitcheck.data import bref_scraper as bref
from fitcheck.features import contract


def build(season: str) -> pd.DataFrame:
    print(f"\n=== Contract value {season} ===")
    rows = []
    for name, slug in bref.BREF_SLUGS.items():
        try:
            adv = bref.player_advanced(slug)
            con = bref.player_contract(slug)
            metrics = contract.latest_season_value(adv, season)
            salary = contract.contract_aav(con, season)
            rows.append(contract.value_row(name, season, salary, metrics))
            print(f"  ✓ {name:26s} WS={metrics.get('WS')}  $={salary}")
        except Exception as e:
            print(f"  ✗ {name:26s} {type(e).__name__}: {e}")
    table = contract.build_value_table(rows)
    if not table.empty:
        out = config.PROCESSED_DIR / f"value_table_{season}.csv"
        table.to_csv(out, index=False)
        print(f"  -> wrote {out}")
        brown = table[table["player"] == "Jaylen Brown"]
        if not brown.empty:
            r = brown.iloc[0]
            print(f"  Brown cost/WS=${r['cost_per_WS']:,.0f}  "
                  f"value pctile={r['value_pctile']:.2f} (1.0=best)")
    return table


def main() -> int:
    for s in config.SEASONS:
        build(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
