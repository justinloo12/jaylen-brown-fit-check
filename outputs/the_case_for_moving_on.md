# The Case for Moving On
### A front-office brief: why Boston can live with Jaylen Brown off the roster

_**The trade is now real** — on July 1, 2026 Boston sent Brown to Philadelphia
for Paul George and picks; this brief was written as a hypothetical days
before, and the media consensus grades the deal for Philadelphia. It is an
**advocacy document**: it argues one side on purpose.
Every number is pulled from the Fit Check pipeline (`nba_api` + Basketball-Reference,
2024-25 and 2025-26). It does not fabricate; it prosecutes. A "Where this argument
is weakest" section is included at the end, because a brief that can't survive its
own counter-evidence isn't worth presenting._

---

## The thesis in one line

Boston's edge was a **movement-3 offense with five connected players**. Brown's
game — a ball-dominant, mid-range-heavy, self-creation diet that only produced
winning basketball when Tatum and White carried the offensive infrastructure
around him — pulled against that identity, and the shot profile was drifting the
*wrong* way. Off the books, the Celtics keep the system and shed a $53M shot-taker
whose value was contingent on his co-stars.

---

## 1. The shot-taking is the problem, and it was getting worse

The Celtics won by hunting the two best shots in basketball — at the rim and from
three — and avoiding the long two. Brown's diet moved **away** from that in
2025-26, not toward it:

| Metric | 2024-25 | 2025-26 | Direction |
|---|---|---|---|
| **3-point rate** | 0.32 | **0.26** | ⬇ fewer threes — away from identity |
| **Long-two rate** | 0.07 | **0.14** | ⬆ *doubled* — the shot the system exists to kill |
| **Iso / self-created (3+ dribble) rate** | 0.53 | **0.64** | ⬆ more pound-the-air isolation |
| **Contested-shot rate** | 0.53 | 0.52 | flat, and high |
| **Late-clock rate** | 0.18 | 0.22 | ⬆ more bailout possessions |
| **`bad_shot_index`** (composite) | 0.328 | **0.379** | ⬆ +16% worse |

Read that middle column as a trend line: in a season where Boston needed *more*
ball movement, Brown took **fewer** threes, **doubled** his long-two rate, and
**raised** his isolation rate to nearly two-thirds of his shots. On a team whose
whole thesis is "don't take the long two," he was manufacturing more of them.

**And he's not bailing it out by making tough shots.** The xFG model (a logistic
shot-quality model on 2,661 shots) says he scores almost exactly at expectation —
`shot_making_over_expected` ≈ 0.000 both years. So this isn't a case of a
shot-maker earning the degree of difficulty. He's taking harder, lower-value
shots and converting them at a league-ordinary rate. The difficulty is
self-inflicted, and it's a tax the offense pays on every possession he holds.

> **Bottom line for Angle 1:** the possession-termination profile is trending
> away from what Boston wins with, and there's no shot-making premium to justify
> it. That's the cleanest, least-confounded number in the whole file.

---

## 2. His value was contingent — he needed Tatum and White to prop it up

The 2025-26 lineup data shows how much Brown leaned on the infrastructure around
him. His on-court net rating **collapses** the moment you take a primary creator
off the floor with him:

| Split | Brown ON, teammate ON | Brown ON, teammate OFF | Swing |
|---|---|---|---|
| **± Jayson Tatum** | **+16.2** | +4.8 | **−11.3** |
| **± Derrick White** | **+9.4** | **−1.0** | **−10.4** |

Without White specifically, Brown-led minutes were **underwater (−1.0 net)** — a
losing basketball team. With Tatum next to him he looks like a +16 juggernaut;
strip Tatum out and eleven points of net rating evaporate. That is the statistical
signature of a **complementary star, not a franchise engine** — a player whose
gaudy on-court numbers are borrowed from the creators beside him.

For a team paying him like a co-franchise cornerstone (see §3), "great as long as
he's flanked by Tatum and White" is exactly the profile you can afford to move —
because the system, and the creators who actually power it, stay.

---

## 3. The money made the fit problem unaffordable

You tolerate a contingent, shot-selection-flawed star if he's cheap. Brown wasn't:

- **2025-26 salary: $53,142,264 — 34.4% of the cap.** Over a third of your
  roster, on one player.
- **Cost per win share: ~$7.7M** (2024-25: ~$9.5M). Among a comp set of 20 max
  and near-max perimeter players, that ranks in roughly the **35th–45th
  percentile of value** — below
  the median of his own pay tier.
- His Win Shares (5.2 → 6.9) are solid but not cornerstone-scarce: **Derrick White
  posted 8.5 and 7.0 WS on roughly half the salary.** Boston had a cheaper,
  better-fitting version of "connective two-way wing" already on the roster.

When a third of your cap goes to a below-median-value wing whose production needs
two other stars to show up, the cap sheet *is* the fit argument. Moving on
restores flexibility to reinforce the system instead of subsidizing a player who
strained it.

---

## The 60-second version

1. **Bad shots, getting worse:** fewer threes, double the long twos, more iso —
   `bad_shot_index` up 16% — with zero shot-making premium to pay for it.
2. **Borrowed value:** +16 with Tatam, +4.8 without; **−1.0 without White.** A
   complementary star, not an engine.
3. **Unaffordable to carry the flaw:** 34% of the cap, below-median value among
   max wings, with a cheaper better-fitting wing (White) already in-house.

The Celtics kept the system and the creators who run it. That's the good outcome.

---

## Where this argument is weakest (read before you present it)

Leaving these out would make the brief easy to dismantle. Address them, don't hide
them:

- **2024-25 undercuts the "needs Tatum" claim.** That season, Brown-led lineups
  with Tatum *off* were actually a touch **better** (+9.8 vs +7.6). The
  "contingent value" case rests almost entirely on 2025-26. → *Rebuttal:* the
  most recent season is the relevant one, and it's the one where the roster was
  built around him most — and he still cratered without White.
- **The 2025-26 "without Tatum" split is confounded.** Tatum missed extended time,
  so "without Tatum" overlaps with "whole team depleted." Some of that −11.3 is
  team health, not Brown. → *Rebuttal:* the **White** split (−10.4, and negative
  in absolute terms) is far less confounded and tells the same story.
- **Cost-per-WS punishes every max player.** By construction, stars look
  "expensive." Brown is below the median *of his tier*, not a historic albatross.
  → *Rebuttal:* we're not claiming albatross; we're claiming *replaceable at the
  margin by a better fit already on the roster.*
- **Win Shares undersells shot-creation gravity and defense.** Brown draws the
  toughest wing assignment and bends defenses; WS is a blunt instrument here. →
  This is the real hole. If someone leads with it, the honest answer is "the
  shot-profile drift (§1) is the load-bearing argument; the rest is supporting."

If the shot-profile trend (§1) holds up to scrutiny, the case stands even if a
critic wins every other point. Lead with it.
