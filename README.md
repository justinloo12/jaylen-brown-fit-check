# Fit Check 🏀

**Was trading Jaylen Brown defensible? A data-driven stress test — built as a
hypothetical, overtaken by reality.**

> **The trade happened.** This project was built on July 2, 2026 as a what-if
> exercise — and on July 1, 2026 Boston actually traded Brown to Philadelphia
> for **Paul George, a 2028 first (possibly converting to a favorable swap), a
> 2031 unprotected first, and two seconds** — nearly the exact package modeled
> here. Fit Check does what a front office would: pull the real data, quantify
> "fit" and "value," price the return, then — deliberately — build the
> strongest one-sided case for the trade and stress-test it against its own
> counter-evidence. Read it knowing the media consensus graded the deal for
> Philadelphia and Brown finished 6th in 2025-26 MVP voting: this is the
> minority report.

Built on real data: [`nba_api`](https://github.com/swar/nba_api)
(stats.nba.com shot charts, tracking, lineups, clutch) and
[Basketball-Reference](https://www.basketball-reference.com) (contracts, Win
Shares, draft classes), seasons **2024-25** and **2025-26**, all pulls cached
and reproducible. Full methodology and every known weakness:
**[METHODS.md](METHODS.md)**.

---

## What the neutral analysis found

The pipeline was built to *test* the "Brown doesn't fit" thesis, not assume
it. The honest scorecard is mixed:

| Claim | Verdict | Evidence |
|---|---|---|
| His shot diet drifted away from Boston's movement-3 identity | **Supported (strongest finding)** | 3PT rate 0.32 → 0.26, long-two rate 0.07 → 0.14 (doubled), iso-dribble rate 0.53 → 0.64, `bad_shot_index` +16% — with no shot-making premium (xFG over-expectation ≈ 0.00) |
| "He can't win without Tatum" | **Not supported as stated** | 2024-25 Brown-led lineups were *better* without Tatum (+9.8 vs +7.6). The 2025-26 collapse (−11.3 swing) is confounded by Tatum's injury absence |
| "He puts up empty stats" | **Refuted; a narrower claim survives** | Brown-led lineups won. What holds: in 2025-26, vs .500+ teams his 29 PPG converted to a break-even on-court margin (+0.3), and across two playoff runs Tatum posts better TS%, +/-, and assists |
| He's a clutch liability | **Refuted — cuts the other way** | .632 clutch TS in 2024-25, better than Tatum |
| The contract is an albatross | **Overstated** | Below-median value among max wings (~35th–45th pctile cost/WS vs 20 comps) — mediocre value, not disastrous |

**The defensible thesis** is narrower than the hot take: *the shot-selection
trend is real and moving the wrong way, the impact fades against quality
opponents in the most recent season, and the contract is the longest and
least efficient dollar-for-dollar among the in-house options — so a package
of a cleaner-fitting veteran, a year of extra cap flexibility, and two cheap
draft assets is worth taking seriously, while conceding you'd be trading away
the best player in the deal.*

## The advocacy exercise

With the neutral findings in hand, the second half of the project builds the
strongest **one-sided** case for the hypothetical trade — the way a front
office analyst would argue it in the room — with every number traceable to
the pipeline and a mandatory "where this is weakest" section in each
document:

- **[outputs/trade_case.html](outputs/trade_case.html)** — the full case as a
  self-contained styled deck (figures embedded; open in any browser)
- [outputs/the_case_for_moving_on.md](outputs/the_case_for_moving_on.md) —
  shot profile + creator dependency + contract
- [outputs/paul_george_comparison.md](outputs/paul_george_comparison.md) —
  the return: fit vs production vs cap timeline
- [outputs/high_leverage_and_2028.md](outputs/high_leverage_and_2028.md) —
  clutch/playoff/vs-.500+ splits and the 2028 cap reload
- [outputs/tatum_vs_brown.md](outputs/tatum_vs_brown.md) — post-trade
  baseline: the offense Boston kept, same metrics, no special treatment
- [outputs/efficiency_comps.md](outputs/efficiency_comps.md) — Brown vs the
  20-player max-contract market: TS% vs usage vs pay
- [outputs/flow_test.md](outputs/flow_test.md) — the ball-stopping claim,
  measured: Brown is p1–p2 in passes-per-touch league-wide
- [outputs/report.md](outputs/report.md) — the neutral auto-generated summary

Two quantitative pieces support the return side:

- **Pick value:** 2015–19 draft classes ⇒ picks 15–30 average ~1.7 WS/yr,
  ~$2.1M per win share on a rookie deal vs the ~$7.7M/WS Boston pays Brown —
  a ~4× cost-of-a-win gap (expectations, not guarantees; bust rates included).
- **Lottery model:** exact post-2019 flattened-lottery odds (computed from
  ball combinations, validated against published anchors) show how much more
  a conveyed lottery pick is worth under the new system — e.g. seed 8's
  top-4 odds roughly 2.4× the old regime.

## The three analytical angles

| # | Angle | Key metrics |
|---|-------|-------------|
| 1 | **Shot Profile Fit** | zone rates, iso/dribble rate, contested rate, late-clock rate, `bad_shot_index`, cross-validated xFG |
| 2 | **Winning Basketball** | on/off net rating, **with/without Tatum · White · Holiday** lineup splits, clutch, playoff, vs-.500+ splits |
| 3 | **Contract & Assets** | salary/cap %, cost per WS vs 20 max-tier comps, future cap ledger, draft-pick surplus value, lottery odds |

## Repo layout

```
fitcheck/                     # importable package
├── config.py                 # IDs, seasons, thresholds, cap figures
├── data/
│   ├── cache.py              # parquet/HTML disk cache — never hit an endpoint twice
│   ├── nba_client.py         # cached nba_api wrappers
│   └── bref_scraper.py       # BRef contracts, advanced stats, comp-set slugs
├── features/
│   ├── shot_profile.py       # possession-termination-quality metrics
│   ├── onoff.py              # with/without-teammate lineup splits
│   └── contract.py           # cost-per-win value model
├── models/
│   ├── shot_quality.py       # sklearn xFG (make-prob given shot context)
│   └── lottery.py            # exact draft-lottery pick distributions
└── viz/charts.py             # shot charts, split bars, scatters, radar

scripts/                      # the pipeline, in order
├── 01_pull_data.py           # pull + cache everything
├── 02_build_features.py      # raw → analysis tables
├── 03_contract_value.py      # BRef scrape → cost-per-WS comps
├── 04_make_viz_and_report.py # core figures + neutral report.md
├── 05_case_figure.py         # composite advocacy figure
├── 06_george_compare.py      # hypothetical return: George vs Brown
├── 07_high_leverage_and_2028.py  # clutch/playoff/vs-.500+ + 2028 cap
├── 08_pick_value.py          # draft-slot surplus value (2015-19 classes)
├── 09_trade_case_deck.py     # assembles outputs/trade_case.html
├── 10_lottery_value.py       # flattened-lottery expected value
├── 11_tatum_baseline.py      # post-trade: Tatum through the same lens
├── 12_efficiency_comps.py    # Brown vs the max-contract market (TS%/USG/pay)
└── 13_flow_test.py           # ball-stopping measured: sec/touch, passes/touch

tests/                        # unit tests (stdlib unittest)
notebooks/                    # exploration
METHODS.md                    # methodology + every known limitation
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Stage 1: pull data (cached under data/cache/). Use a US residential IP —
# stats.nba.com geoblocks many datacenter/VPN ranges.
python scripts/01_pull_data.py

# Everything else runs offline off the cache, in order:
for s in scripts/0{2,3,4,5,6,7,8}_*.py scripts/10_*.py scripts/09_*.py; do python "$s"; done

open outputs/trade_case.html   # the deck
open outputs/report.md         # the neutral summary
python -m unittest discover tests   # run the tests
```

## Honesty box

- The advocacy documents argue a side **on purpose** and say so on their face;
  each carries its counter-evidence. The neutral findings live in
  `outputs/report.md` and the table above.
- The biggest known confound (Tatum's 2025-26 absence contaminating the
  with/without split), the bluntness of Win Shares, the equal-weight
  `bad_shot_index`, and the optimism in the pick-value estimates are all
  documented in [METHODS.md](METHODS.md). Read it before quoting numbers.
- Scraping etiquette: both sources are rate-limited by the client (0.6 s /
  3.5 s pacing), everything is cached after one pull, and the cache is
  gitignored rather than redistributed.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with the NBA, the Boston
Celtics, or Basketball-Reference. Data belongs to its sources; this repo
redistributes none of it.
