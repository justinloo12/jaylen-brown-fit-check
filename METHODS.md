# Methods & Limitations

Everything in this repo is computed from two sources — **stats.nba.com** (via
[`nba_api`](https://github.com/swar/nba_api)) and
**[Basketball-Reference](https://www.basketball-reference.com)** — pulled once,
cached under `data/cache/`, and reproducible by re-running `scripts/01–10`.
This page documents how each number is built and, more importantly, where each
one is soft. If you quote a figure from this project, quote its caveat with it.

---

## 0. The premise — hypothetical when built, real as of July 1, 2026

This project was built (morning of July 2, 2026) as a *what-if* exercise. On
**July 1, 2026** the trade became real: Boston sent Brown to Philadelphia for
**Paul George, a 2028 first-round pick (reported as possibly converting to a
swap more favorable to Boston), a 2031 unprotected Philadelphia first, and two
second-round picks** (per NBA.com, The Boston Globe, The Washington Post,
July 1–2, 2026). Notes:

- The Basketball-Reference contract tables cached here still show pre-trade
  teams — BRef lags transactions by days. The pipeline's numbers are
  unaffected (they describe past seasons), but team labels are stale.
- The modeled package (George + two unprotected firsts) is **close to but not
  identical to** the actual terms: the 2028 first may be only a swap, which
  weakens §5–6's pick-value math; the two seconds are upside not modeled.
- **The media consensus grades the trade for Philadelphia** ("A+" for the
  Sixers, "40 cents on the dollar" in the Boston press), and Brown finished
  6th in 2025-26 MVP voting. The advocacy documents here are a minority
  report arguing Boston's side.

Additionally, the advocacy documents (`the_case_for_moving_on.md`,
`paul_george_comparison.md`, `high_leverage_and_2028.md`, `trade_case.html`)
**argue one side on purpose**. They do not fabricate, and each carries a
"weakest points" section — but they are prosecution briefs, not verdicts. The
neutral summary is `outputs/report.md`.

## 1. Shot profile ("possession termination quality")

- **Zone rates** (rim / short-mid / long-two / three) come from
  `ShotChartDetail` (every FGA with location). "Long two" = 2PT attempt from
  ≥ 16 ft (`config.LONG_TWO_MIN_FT`).
- **Creation rates** (iso-dribble, catch-and-shoot, contested, late-clock)
  come from the `PlayerDashPtShots` tracking splits, weighted by FGA share.
  "Iso" is proxied by **3+ dribbles before the shot** — a shot-creation proxy,
  not Synergy play-type data. It will count some transition pull-ups as "iso."
- **`bad_shot_index`** = the *equal-weighted* mean of long-two rate,
  iso-dribble rate, contested rate, and late-clock rate. The equal weights are
  an editorial choice, not an estimated model. The index is useful for
  season-over-season *direction* (its components all move the same way for
  Brown 24-25 → 25-26); the level itself has no independent meaning.
- **xFG model** (`fitcheck/models/shot_quality.py`): logistic regression,
  make-probability from shot distance + zone, 5-fold cross-validated
  (AUC ≈ 0.62–0.65). It contains **no defender or clock features** at the
  shot level (stats.nba.com stopped exposing per-shot defender distance), so
  "shot-making over expectation ≈ 0" means *relative to location*, not
  relative to full context.

## 2. Lineup / on-off splits

- With/without-teammate net ratings are aggregated from **5-man lineup data**
  (`LeagueDashLineups`), weighted by **minutes, not possessions**. Minute
  weighting is directionally sound but not exact; pace differences across
  lineups shift the true possession-weighted figure slightly.
- **The single biggest confound in the repo:** in 2025-26 Tatum missed
  extended time, so "Brown without Tatum" minutes disproportionately came
  from depleted-roster stretches. The −11.3 with/without-Tatum swing is
  *partly* team health. The without-White split (−10.4, negative in absolute
  terms) is less confounded and is the number the briefs are told to lead
  with. The 2024-25 season shows **no** such collapse (+9.8 without Tatum) —
  any "Brown needs Tatum" claim must carry that year as counter-evidence.
- Small-minute lineups (garbage time) are included; read the `MIN` column
  before trusting a split.

## 3. Clutch / playoff / vs-.500+ splits

- "Clutch" = NBA.com definition (last 5 min, margin ≤ 5) — small samples by
  construction; single-season clutch TS% is noisy and **favors Brown** in
  2024-25 (.632 TS). The briefs concede this rather than bury it.
- Playoff comparisons cover two runs only. The vs-.500+ collapse
  (+0.3 avg +/- at 29 PPG) is a **2025-26 signal only**; 2024-25 shows Brown
  holding +6.0 vs winning teams.

## 4. Contract value

- Salaries and future guaranteed years scraped from BRef player pages
  (historical `all_salaries` + forward `contracts_<team>` tables).
- **Cost-per-Win-Share** mechanically punishes every max contract; the comp
  set is therefore restricted to max/near-max perimeter players so the
  comparison is within-tier. Win Shares itself undersells defense and
  off-ball gravity — it is the bluntest instrument used here.
- Cap percentages use announced/projected caps in `config.SALARY_CAP`.
  Boston-specific apron mechanics are **simplified**: the 2028-29 "freed slot"
  is best read as luxury-tax/second-apron relief and a large expiring for
  trade matching, not clean max cap room.

## 5. Draft-pick value

- Slot values = average WS/season by draft position, 2015–19 classes
  (careers mature enough to measure), scraped from BRef draft pages.
  **Known bias:** WS/season over a *career* includes prime years beyond the
  rookie deal, so rookie-deal production for late firsts is likely
  overstated somewhat; treat surplus values as optimistic point estimates.
- Rookie-scale cost uses a ~$3.5M/yr midpoint over 4 years — an
  approximation of the CBA scale for picks 15–30, not exact figures.
- Surplus value prices a win at **Brown's realized $/WS** — i.e., "wins at
  the price Boston was actually paying." A different price of a win scales
  every surplus figure linearly.
- Per-slot n = 5; the lottery model smooths slot values with a log-decay fit
  before mixing over seeds.

## 6. Lottery model

- Pick distributions are computed **exactly** from the official ball-combination
  counts (140/140/140/125/… of 1000), enumerating ordered draws — no
  simulation, no copied odds table. Validated against published anchors:
  seed 1 top-1 = 14.0%, seed 1 top-4 = 52.1%, seed 14 = 0.5%/2.4%.
- The old-lottery comparison uses the 1994–2018 weights with 3 picks drawn.
- The "lottery kicker" section **assumes the hypothetical picks convey
  unprotected from a lottery-seeded team**. Protections or a good sender team
  collapse it back to the late-first baseline.

## 7. Data engineering notes

- Every stats.nba.com endpoint call is paced (0.6 s) and cached to parquet;
  BRef requests are paced (3.5 s, well under their 20 req/min limit) and
  cached as HTML. Re-runs are fully offline. `data/cache/` is gitignored.
- `nba_api`'s `PlayerDashPtShots` and `TeamDashPtShots` return their result
  tables in **different orders** (player: 7 frames, team: 6). The client
  maps them explicitly; this was caught by inspecting bucket labels, and is
  exactly the kind of silent mislabeling a cached pipeline can hide — verify
  `*_RANGE` columns if you extend the splits.
- Season coverage: 2024-25 and 2025-26 regular seasons (playoffs where
  noted). Data snapshot: **July 2, 2026**.
