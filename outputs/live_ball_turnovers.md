# The Hidden Tax — Live-Ball Turnovers, Priced from Play-by-Play

_Companion to [tatum_first_option.md](tatum_first_option.md). The bad-shot index prices the shots; this prices the giveaways. Every Celtics game's play-by-play, both seasons; identical code path for Brown, Tatum, and the team baseline. Definitions in §3._

## 1. The ledger

| Who | Season | TOV (PBP) | Live-ball (share) | Live per 36 | Opp pts off them | Pts per live TO | Fast-conv. share |
|---|---|---|---|---|---|---|---|
| Jaylen Brown | 2024-25 | 162 | 105 (65%) | 1.75 | 128 | 1.22 | 43% |
| Jaylen Brown | 2025-26 | 259 | 131 (51%) | 1.93 | 182 | 1.39 | 53% |
| Jayson Tatum | 2024-25 | 209 | 134 (64%) | 1.84 | 139 | 1.04 | 39% |
| Jayson Tatum | 2025-26 | 39 | 25 (64%) | 1.72 | 35 | 1.40 | 48% |
| Celtics (team) | 2024-25 | 931 | 567 (61%) | 1.03 | 689 | 1.22 | 43% |
| Celtics (team) | 2025-26 | 943 | 505 (54%) | 0.92 | 682 | 1.35 | 49% |

## 2. Honest read

- **The clean comparison is 2024-25** (both healthy): Brown gave the ball away live 1.75 times per 36 vs Tatum's 1.84, and each of Brown's live TOs cost 1.22 opponent points vs 1.04 for Tatum. Say it plainly: **Brown's live-ball rate was LOWER than Tatum's when both were healthy** — on rate, this angle does not indict Brown relative to the star Boston kept; only his per-giveaway cost ran higher.
- **2025-26 is Brown's ball-dominant season** (usage ~35%): 131 live-ball turnovers that surrendered 182 points — 2.6 per game he played — of which 53% were converted fast (first opponent attempt within 8s). Tatum's 2025-26 column sits on 16 games and is context, not evidence.
- **Benchmark:** the Celtics as a whole gave up 1.35 points per live-ball TO in 2025-26 (dashed line in the figure). A star's live TOs are not obviously worse than anyone else's — the tax is in *how many* he commits at his usage, not a special per-TO penalty.
- The narrative link to the shot-diet finding is stated only as far as the data goes: Brown's iso/3+-dribble rate rose 0.53 → 0.64 in 2025-26 (tatum_vs_brown.md §1) while he carried his highest usage; the live-ball counts above are the giveaway side of that ball-dominant diet. We measured the cost; we did not measure causation between dribble counts and steals, and don't claim it.

## 3. Definitions & methods

- **Live-ball TO** = a steal was credited on the event (PBP V3 shows the steal as a companion row at the identical clock). Offensive fouls, travels, out-of-bounds, violations = dead-ball.
- **Points off a live TO** = opponent points from the steal until Boston next gains possession (next Boston shot attempt, FT, turnover, rebound incl. team rebounds, or period end). Opponent offensive rebounds and and-1s stay in the window by design.
- **Fast conversion** = first opponent attempt within 8 seconds of the steal *and* points scored in the window.
- PBP turnover counts can differ from official box scores by ~1 per game on bookkeeping edge cases (e.g. 5-second inbound calls); player-level counts matched the box score in spot checks.
- Games with failed PBP pulls this run: 0 (of 82 per season; a rerun backfills from cache).
- Code: `fitcheck/features/turnovers.py` (unit-tested in `tests/test_turnovers.py`); driver `scripts/17_live_ball_turnovers.py`.