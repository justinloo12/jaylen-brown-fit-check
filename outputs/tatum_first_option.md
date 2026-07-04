# Tatum as Sole First Option — The Configuration Matrix and a Season Projection

_Follow-up to [tatum_vs_brown.md](tatum_vs_brown.md). Question: is this roster's best configuration Tatum as the lone first option rather than Tatum+Brown load-sharing? §1-§2 are **observed**; §3 is a **projection** and says so at every step. 2024-25 is the primary season throughout — Tatum's 2025-26 lasted 16 games (injury), so every 2025-26 cell involving him is a shard, not evidence._

## 1. Observed — the game-level 2x2 (who suited up)

### 2024-25 (primary)

| | Brown played | Brown sat |
|---|---|---|
| **Tatum played** | 40-16 (56 g), net +8.2 | 13-3 (16 g), net +11.8 |
| **Tatum sat** | 6-1 (7 g), net +15.8 | 2-1 (3 g), net -1.8 |

Per-game lines in each star's cells (PTS / REB / AST):

| Player, cell | n | Line |
|---|---|---|
| Tatum, both played | 56 | 26.3 / 8.9 / 6.2, TS 0.582, USG 30.4% |
| Tatum, Brown sat | 16 | 28.8 / 7.8 / 5.1, TS 0.584, USG 34.5% |
| Brown, both played | 56 | 22.1 / 5.8 / 4.3, TS 0.557, USG 28.5% |
| Brown, Tatum sat | 7 | 22.9 / 6.4 / 6.3, TS 0.538, USG 30.7% |

**What the cells actually say (2024-25):**

- **Tatum without Brown (16 games): 13-3, net +11.8** vs 40-16, net +8.2 when both played. Tatum's scoring rose 26.3 → 28.8 PPG on usage 30.4% → 34.5% with TS essentially flat (0.582 → 0.584) — in this sample he absorbed roughly four extra usage points at no efficiency cost.
- **Brown without Tatum (7 games): 6-1, net +15.8 — the best game-level cell in the matrix.** Print that plainly: Brown's solo-carry games were not a problem; Boston blew teams out. His own line in them was modest (22.9 / 6.4 / 6.3, TS 0.538, USG 30.7%), so much of that margin came from the supporting cast — but a 7-game cell can't settle who drove it either way.
- **Neither played (3 games, the control): net -1.8.** Too small to lean on, but directionally the only cell near zero — the lift in the other three cells is not just the supporting cast.

### 2025-26 (secondary — Tatum injury caveat applies to every cell)

| | Brown played | Brown sat |
|---|---|---|
| **Tatum played** | 11-2 (13 g), net +11.0 | 2-1 (3 g), net +5.8 |
| **Tatum sat** | 36-22 (58 g), net +5.7 | 7-1 (8 g), net +19.2 |

Brown carried the season alone: 58 games without Tatum at 28.9 / 7.2 / 5.1, TS 0.568, USG 36.7% — a 36-22 record and +5.7 net. That is real, MVP-ballot-grade solo production and this memo doesn't pretend otherwise. The Tatum-sat-and-Brown-sat cell (8 games, +19.2) is small and blowout-flavored; don't quote it as a supporting-cast measurement.

## 2. Observed — the lineup-level 2x2 (who was on the floor)

Minute-weighted 5-man lineup nets. The **neither** row is the control group: what the supporting cast does with no star on the floor.

| Configuration | 2024-25 | 2025-26 |
|---|---|---|
| Together | +7.6 (1411 min) | +16.2 (318 min) |
| Tatum-led (Brown off) | +11.9 (1212 min) | +3.0 (204 min) |
| Brown-led (Tatum off) | +9.8 (753 min) | +4.8 (2120 min) |
| Neither (control) | +3.5 (593 min) | +12.7 (1304 min) |

**2024-25 reading:** every configuration beat the no-stars control (+3.5), and the ordering is Tatum-led (+11.9) > Brown-led (+9.8) > together (+7.6). Both stars ran better engines apart than the two of them did together — the load-sharing configuration was the *worst* of the three star configurations. That is the core of the sole-first-option case, and note it is symmetric: it argues for consolidation around either star, and the shot-diet evidence (tatum_vs_brown.md §1) is what breaks the tie toward Tatum.

**2025-26 reading:** the matrix inverts (together +16.2, neither +12.7, both 'led' cells lower) — but Tatum's cells sit on 204-318 minutes and the deep 2025-26 bench feasted in low-leverage minutes. Injury-season noise; we do not build the projection on it.

## 3. Projection — a full season of Tatum as sole first option

_Everything below is a **projection**, not an observation. Each assumption is stated with its rationale; ranges, not point estimates._

### 3a. Team level: lineup gap → wins

- Observed 2024-25 lineup gap: Tatum-led +11.9 vs together +7.6 = **+4.3 per 100** (5-man lineup level).
- **Regression discount (40%-60% shrinkage):** lineup nets are not season nets — 'led' samples are contaminated by bench-heavy and garbage-time units, opponent mix is uncontrolled, and extreme lineup splits regress hard. We keep only 40%-60% of the gap: **+1.7 to +2.6 team net points**. The shrinkage band is a judgment call, chosen before computing the win total; the undiscounted figure is shown so you can apply your own.
- **Net → wins at ~2.7 wins per point** (standard Pythagorean rule of thumb, 82 games): **+4.7 to +7.0 wins** vs the load-sharing baseline. Undiscounted, the same math would say +11.7 wins — we do not believe that number, which is the point of the discount.

### 3b. Player level: Tatum's projected solo line

Two inputs, blended:

1. **Observed without-Brown sample (16 games, §1):** 28.8 / 7.8 / 5.1, TS 0.584, USG 34.5%. Small sample; opponent mix uncontrolled.
2. **Usage-redistribution model:** baseline = his 56-game with-Brown line (26.3 / 8.9 / 6.2, TS 0.582, USG 30.4%). Assume Brown's vacated possessions push Tatum's usage from ~30% to 32-33%, and charge an efficiency tax of 0.3-0.6 TS points per +1 usage point (a rule-of-thumb range from the public skill-curve literature — an assumption, not a measurement). That yields 27.2-28.2 PPG at TS 0.566-0.577. Note the observed 16-game sample beat this model's efficiency tax (TS held flat at +4 usage points) — the model is the conservative leg.

**Projected Tatum solo-season line (range, not a forecast point):**

| | Low | High |
|---|---|---|
| PTS / game | 27.2 | 28.8 |
| REB / game | 7.8 | 8.9 |
| AST / game | 5.1 | 6.2 |
| TS% | 0.566 | 0.584 |
| USG% | 32.0 | 34.5 |

Ranges are the union of the observed sample and the model corners — deliberately wide. Anyone quoting a single number from this table is misusing it.

## 4. What could go wrong (stated fairly)

- **Load over 82 games.** The observed sample is 16 games sprinkled through a season with Brown absorbing the other 56; a permanent 32-34% usage burden is a different physical proposition. Fatigue-driven efficiency decay would land exactly where the model's tax says.
- **Defenses key on one star.** With Brown gone, Tatum sees the opponent's best defender plus the blitz every night. The 16-game sample includes teams game-planning for a one-off absence, not a season-long scheme.
- **Playoff shot-quality compression.** Load-sharing is worth most in the playoffs, when the first option's diet degrades. The +7.6 'together' net bought a second self-creator for April-June; this memo prices the regular season and says so.
- **Paul George is not 'nobody.'** The realized trade returns a second option; the pure sole-first-option frame is cleaner than the actual 2026-27 roster will be. Treat §3 as an upper-bound articulation of the consolidation thesis, not a Celtics forecast.
- **Brown's side of the ledger is real.** 2024-25 Brown-led lineups (+9.8) beat 'together' too, his 7 solo games in 2024-25 were the best cell in the game matrix, and he carried 58 games in 2025-26 at 28.9 PPG to a playable net. The configuration argument is about the *best* arrangement, not about Brown being unable to lead one.

## 5. Brown in one place (recap of the existing outputs)

_One-stop summary so this memo stands alone; every figure is computed in the linked source, not re-derived here._

| Brown metric | 2024-25 | 2025-26 | Source |
|---|---|---|---|
| 3PT rate | 0.320 | 0.262 | outputs/tatum_vs_brown.md, the_case_for_moving_on.md |
| Long-2 rate | 0.072 | 0.142 | outputs/tatum_vs_brown.md |
| Iso / 3+ dribble rate | 0.534 | 0.639 | outputs/tatum_vs_brown.md |
| Bad-shot index | 0.328 | 0.379 | outputs/tatum_vs_brown.md |
| TS% (season) | 0.555 | 0.573 | outputs/efficiency_comps.md |
| USG% (season) | 28.2 | 35.1 | outputs/efficiency_comps.md |
| Cost per Win Share | $9.5M | $7.7M | outputs/efficiency_comps.md |
| Lineup net WITH Tatum | +7.6 | +16.2 | outputs/report.md, this memo §2 |
| Lineup net WITHOUT Tatum | +9.8 | +4.8 | outputs/report.md, this memo §2 |

- **Live-ball turnovers** ([live_ball_turnovers.md](live_ball_turnovers.md)): 2024-25 Brown 1.75 live/36 (128 pts surrendered) vs Tatum 1.84 (139 pts) — Brown's rate was LOWER when both were healthy. His ball-dominant 2025-26: 131 live TOs, 182 pts surrendered.
- **Defense by role** ([defense_roles.md](defense_roles.md)): Brown was the primary on-ball defender — 19% of his defended possessions on opponents' #1 options vs Tatum's 8% (2024-25), at slightly better points-allowed on those matchups. Boston has to replace that assignment coverage.

Clutch: Brown's 2024-25 clutch TS was .632, better than Tatum (outputs/high_leverage_and_2028.md). Defense: improved in 2025-26 (outputs/defense_check.md). The trade case was never that Brown is bad; it's that the configuration in §2 was available.

## 6. Data & methods notes

- Game logs and team game logs: stats.nba.com via the cached client (`fitcheck/data/nba_client.py`); lineups: LeagueDashLineups 5-man units, minute-weighted (same caveat as always: possession weighting would differ slightly).
- Game-level net = 100 x margin / team-side possession estimate (FGA − OREB + TOV + 0.44·FTA), the standard game-log approximation.
- Per-game USG% computed from the standard boxscore formula (player totals over team totals in the same games), not from the advanced-boxscore endpoint — avoids ~150 extra API calls; the two agree to a few tenths.
- TS% aggregated over cells (total PTS over total true-shot attempts), not averaged per game.
- All projection constants (shrinkage band, usage range, TS slope, wins-per-point) live at the top of `scripts/16_tatum_first_option.py`; the pure formulas are unit-tested in `tests/test_projection.py`.