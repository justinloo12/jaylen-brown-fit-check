# Wing Redistribution — Spreading Brown's Volume Across the Other Wings (incl. George)

_Companion to [three_point_identity.md](three_point_identity.md) (which re-priced Brown's volume at a single target mix) and [tatum_first_option.md](tatum_first_option.md) (the hierarchy projection this one partially overlaps — see the double-counting warning in §3). **Everything here is a projection** built on observed 2025-26 shot mixes._

## 1. The scenario and who absorbs what

Brown's 2025-26 volume (21.7 FGA/g, plus 7.5 FTA/g handled only through the usage math — the pricing itself is FT-excluded, same as script 19) is spread across the remaining perimeter rotation plus Paul George. **Weighting: proportional to each wing's current FGA/g** (shot volume flows to players in proportion to how much they already shoot; a minutes-share weighting would push even more volume onto the lowest-usage shooters and flatter the result). **Caps:** no one gains more than 4.5 FGA/g and no one more than triples their volume (gain ≤ 2× current FGA); capped excess re-flows to the open slots. Tatum is not in the pool — his 16-game 2025-26 falls under the rotation floor, and his usage rise is already the subject of the script-16 projection.

| Player | FGA/g now | Gain | New FGA/g | 3PT rate | Exp. PPS | Δ usage (pts) | Naive Δpts/g |
|---|---|---|---|---|---|---|---|
| Derrick White | 14.4 | +4.5 | 18.9 | 0.576 | 0.979 | +6.2 | -0.30 |
| Paul George | 13.9 | +4.5 | 18.4 | 0.496 | 1.072 | +7.0 | +0.12 |
| Payton Pritchard | 13.8 | +4.5 | 18.3 | 0.514 | 1.123 | +6.4 | +0.35 |
| Sam Hauser | 7.7 | +3.3 | 11.0 | 0.844 | 1.156 | +5.9 | +0.36 |
| Baylor Scheierman | 4.3 | +1.8 | 6.1 | 0.744 | 1.233 | +4.5 | +0.34 |
| Jordan Walsh | 3.9 | +1.7 | 5.6 | 0.462 | 1.205 | +4.4 | +0.26 |
| Hugo González | 3.3 | +1.4 | 4.7 | 0.485 | 1.152 | +4.4 | +0.15 |
| **Jaylen Brown** | 21.7 | −21.7 | 0.0 | 0.263 | 1.046 (realized) | — | — |

Every redistributed shot is priced at the receiver's own mix and accuracy: E[PPS] = 3PT rate × 3 × 3P% + 2PT share × 2 × 2P% (`expected_pps`, unit-tested). Brown's shots are removed at his realized 1.046 PPS. George is priced in the Boston environment at his 2025-26 Philadelphia mix, accuracy, and minutes.

## 2. Three numbers, clearly labeled

1. **NAIVE CEILING: +1.3 pts/game (~+3.5 wins).** Ceiling — assumes efficiency survives the volume increase, because it won't fully. **Printed with this number, not under it: Hauser and Scheierman post those PPS figures at 7.7 and 4.3 FGA/g of curated, low-usage looks — their .84/.74 three-point rates are exactly what makes their expected PPS high, and exactly what a defense starts taking away when their volume jumps ~40%.** Also visible in the table: White's 2025-26 pricing (0.979 expected PPS) is *below* Brown's realized 1.046 — the spread is not uniformly upgrade.

2. **USAGE-ADJUSTED ESTIMATE: -0.3 to +0.3 pts/game (~-0.7 to +0.9 wins).** Two documented adjustments: (a) the −0.3 to −0.6 TS-points-per-+1-usage-point tradeoff — the same rule-of-thumb range script 16 applies to Tatum (Goldman/Rao skill-curve literature) — converted to PPS (ΔPPS ≈ 2×ΔTS) and charged to each receiver's *added* shots at their own usage bump (charging their existing volume too would push this lower still); (b) a 50% creation-transfer discount on the 0.639 share of Brown's volume that was self-created (his 3+ dribble rate, tracking data — same figure quoted in tatum_vs_brown.md), i.e. an effective transfer of 0.680. That volume needs a creator; in practice the creator is Tatum, whose usage rise is what script 16 already projects — the discount here prices the interaction instead of double-counting the gain. The low corner also takes 2pp off George's 3P% (36 in 2026).

3. **GEORGE-ONLY 1-FOR-1 SWAP: -2.0 to -0.6 pts/game (~-5.3 to -1.5 wins) usage-adjusted; +0.6 naive.** Why spreading beats the 1-for-1: George alone must jump +10.8 usage points at age 36 to absorb all of Brown's volume at his .497 three rate, while the spread hands each wing a small bump (+4.4 to +7.0 usage points) and routes shots to .576/.844 three-rate players. Same math, same discounts — concentration is what kills the 1-for-1.

**If the honest number looks small, say so: it is.** The usage-adjusted estimate is -0.7 to +0.9 wins — a rounding error on a season, and the low corner is negative. The shot-mix channel by itself does not carry the trade case; it never did (script 19 reached the same verdict from a different angle).

## 3. DOUBLE-COUNTING WARNING — read before citing any number above

**This projection overlaps the hierarchy projection in [tatum_first_option.md](tatum_first_option.md) (+4.7 to +7.0 wins). They are NOT additive.** What overlaps: the hierarchy number is built from observed without-Brown lineup nets — and those lineups were *already running* the three-heavier mix this script prices shot-by-shot. The better mix is one of the mechanisms *inside* the lineup gap, not a separate effect on top of it. The creation-transfer discount here and the usage-tax on Tatum there are two views of the same possession. What is genuinely incremental here: George's arrival (his mix is priced into this pool but not into the historical lineups) and the explicit caps on how much low-usage shooters can absorb.

**Combined honest range: roughly +4 to +8 wins total** — the hierarchy range (+4.7 to +7.0) widened by this script's uncertainty (-0.7 to +0.9), **not** the sum (which would double-count to +5 to +10 and should not be quoted). If a single number must survive, quote the hierarchy range and treat this memo as the shot-level mechanism check on it.

## 4. Assumptions, constants, and method notes

- Redistribution: proportional to current FGA/g, caps min(+4.5 FGA/g, 2× current); waterfall re-flow (`capped_split`, unit-tested: allocations sum to Brown's volume, caps respected).
- Usage math: standard boxscore USG% differenced (`usage_delta_for_volume`), Boston 2025-26 team totals, added FTs at each receiver's own FTA/FGA rate, turnovers held flat.
- Win conversion: pts/game × 2.7 wins per point of per-game differential — the same Pythagorean rule of thumb as scripts 16 and 19; defense assumed unchanged.
- Free throws excluded from pricing on both sides (Brown's rim pressure drew 7.5 FTA/g; a three-heavier diet returns some of that — this memo, like script 19, does not credit either side).
- Constants live at the top of `scripts/20_wing_redistribution.py`; pure helpers in `fitcheck/features/shooting.py`, tested in `tests/test_redistribution.py` and `tests/test_shooting.py`.