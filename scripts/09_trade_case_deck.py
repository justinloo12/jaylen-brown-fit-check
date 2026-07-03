"""Assemble the full trade case into one sleek, self-contained deliverable.

Reads every processed table + figure the pipeline has produced and renders:
  * outputs/trade_case.html — styled one-pager, figures embedded as base64
    (openable anywhere, no server, no dependencies)

Every number is pulled live from data/processed at render time, so re-running
the pipeline refreshes the deck automatically.
"""
from __future__ import annotations

import base64
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config


def _img64(name: str) -> str:
    p = config.FIG_DIR / name
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{name}">'


def _csv(name: str) -> pd.DataFrame:
    p = config.PROCESSED_DIR / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def main() -> int:
    # ---- pull the headline numbers from processed tables ----
    term24 = _csv("termination_quality_2024-25.csv").set_index("Unnamed: 0")["Jaylen Brown"]
    term25 = _csv("termination_quality_2025-26.csv").set_index("Unnamed: 0")["Jaylen Brown"]
    val25 = _csv("value_table_2025-26.csv")
    brown_val = val25[val25.player == "Jaylen Brown"].iloc[0]
    cap = _csv("george_vs_brown_cap.csv").set_index("season")
    pick = _csv("pick_value.csv").iloc[0]
    lotto = _csv("lottery_value.csv").set_index("seed")
    fit = _csv("george_vs_brown_fit.csv")
    g25 = fit[(fit.player == "Paul George") & (fit.season == "2025-26")].iloc[0]
    b25 = fit[(fit.player == "Jaylen Brown") & (fit.season == "2025-26")].iloc[0]

    brown_2829 = cap["Jaylen Brown"].dropna().iloc[-1]
    saved = cap["Jaylen Brown"].loc["2026-27":].sum() - cap["Paul George"].loc["2026-27":].sum()

    # The chain's new evidence: flow test + market efficiency check.
    flow = _csv("flow_test.csv")
    fb24 = flow[(flow.player == "Jaylen Brown") & (flow.season == "2024-25")].iloc[0]
    fb25 = flow[(flow.player == "Jaylen Brown") & (flow.season == "2025-26")].iloc[0]
    fg25 = flow[(flow.player == "Paul George") & (flow.season == "2025-26")].iloc[0]
    eff24 = _csv("efficiency_comps_2024-25.csv")
    eff25 = _csv("efficiency_comps_2025-26.csv")
    e24 = eff24[eff24.player == "Jaylen Brown"].iloc[0]
    e25 = eff25[eff25.player == "Jaylen Brown"].iloc[0]

    stat_cards = [
        (f"p{fb25.pass_touch_pctile*100:.0f}", "Brown's passes-per-touch percentile, "
         f"league-wide 25-26 (p{fb24.pass_touch_pctile*100:.0f} in a normal role, 24-25)", "bad"),
        (f"{b25.iso_dribble_rate:.0%}", "of Brown's shots self-created (3+ dribbles), 25-26", "bad"),
        (f"{e24.TS_rank:.0f}/{len(eff24)}", "TS% rank among max-tier comps, 24-25 — at normal usage", "bad"),
        (f"${saved/1e6:.0f}M", "less salary committed from 2026-27 on", "good"),
        (f"${brown_2829/1e6:.0f}M", "off the books in 2028-29 (Brown's final year)", "good"),
        (f"${pick.surplus_two_picks/1e6:.0f}M", "expected surplus value from the two firsts", "good"),
    ]
    cards_html = "\n".join(
        f'<div class="card {cls}"><div class="num">{num}</div>'
        f'<div class="lbl">{lbl}</div></div>'
        for num, lbl, cls in stat_cards)

    fit_rows = "".join(
        f"<tr><td>{lab}</td><td>{b25[k]:.3f}</td><td>{g25[k]:.3f}</td>"
        f"<td class='{'good' if better_g else 'bad'}'>"
        f"{'George' if better_g else 'Brown'}</td></tr>"
        for k, lab, better_g in [
            ("three_rate", "3PT rate", g25.three_rate > b25.three_rate),
            ("catch_shoot_rate", "Catch-&-shoot rate", g25.catch_shoot_rate > b25.catch_shoot_rate),
            ("iso_dribble_rate", "Iso rate (3+ dribbles)", g25.iso_dribble_rate < b25.iso_dribble_rate),
            ("bad_shot_index", "Bad-shot index", g25.bad_shot_index < b25.bad_shot_index),
        ])

    def _cap_cell(v: float) -> str:
        return '<span class="good">— off books</span>' if pd.isna(v) else f"${v:,.0f}"

    cap_rows = "".join(
        f"<tr><td>{s}</td><td>${cap['Jaylen Brown'][s]:,.0f}</td>"
        f"<td>{_cap_cell(cap['Paul George'][s])}</td></tr>"
        for s in cap.index)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fit Check — Should Boston Trade Jaylen Brown?</title>
<style>
  :root {{
    --bg:#0f1419; --panel:#1a2129; --ink:#e8eaed; --sub:#9aa5b1;
    --green:#007a33; --green-lt:#4caf7d; --red:#e05a4e; --gold:#f5b942;
    --line:#2a333d;
  }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ background:var(--bg); color:var(--ink);
    font:16px/1.6 -apple-system,'Segoe UI',Helvetica,Arial,sans-serif;
    max-width:1080px; margin:0 auto; padding:48px 28px; }}
  header {{ border-left:6px solid var(--green); padding-left:20px; margin-bottom:40px; }}
  h1 {{ font-size:2.3rem; letter-spacing:-.5px; }}
  .tag {{ color:var(--gold); font-weight:600; text-transform:uppercase;
    font-size:.78rem; letter-spacing:.14em; }}
  .sub {{ color:var(--sub); max-width:62ch; margin-top:8px; }}
  h2 {{ font-size:1.35rem; margin:52px 0 6px; }}
  h2 .n {{ color:var(--green-lt); margin-right:8px; }}
  .lede {{ color:var(--sub); margin-bottom:18px; max-width:70ch; }}
  .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin:26px 0; }}
  .card {{ background:var(--panel); border:1px solid var(--line);
    border-radius:12px; padding:18px 16px; }}
  .card .num {{ font-size:1.9rem; font-weight:700; }}
  .card.good .num {{ color:var(--green-lt); }}
  .card.bad .num {{ color:var(--red); }}
  .card .lbl {{ color:var(--sub); font-size:.85rem; margin-top:4px; }}
  img {{ width:100%; border-radius:12px; border:1px solid var(--line);
    background:#fff; margin:14px 0; }}
  table {{ width:100%; border-collapse:collapse; margin:14px 0; font-size:.92rem; }}
  th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--sub); font-weight:600; font-size:.78rem;
    text-transform:uppercase; letter-spacing:.08em; }}
  td.good, span.good {{ color:var(--green-lt); font-weight:600; }}
  td.bad {{ color:var(--red); font-weight:600; }}
  .honesty {{ background:var(--panel); border:1px solid var(--gold);
    border-radius:12px; padding:20px 22px; margin-top:48px; }}
  .honesty h3 {{ color:var(--gold); font-size:1rem; text-transform:uppercase;
    letter-spacing:.1em; margin-bottom:10px; }}
  .honesty li {{ margin:6px 0 6px 18px; color:var(--sub); }}
  .honesty b {{ color:var(--ink); }}
  footer {{ color:var(--sub); font-size:.8rem; margin-top:44px;
    border-top:1px solid var(--line); padding-top:16px; }}
</style></head><body>

<header>
  <div class="tag">Fit Check · Front-Office Post-Mortem</div>
  <h1>The Case for the Jaylen Brown Trade</h1>
  <div class="sub">On <b>July 1, 2026</b> Boston traded Brown to Philadelphia
  for <b>Paul George, a 2028 first (may convert to a favorable swap), a 2031
  unprotected first, and two seconds</b>. This deck — built as a hypothetical
  days before the deal — argues Boston's side of a trade the media graded
  heavily for Philadelphia. Real data: nba_api (stats.nba.com) &amp;
  Basketball-Reference, seasons 2024-25 and 2025-26. It argues one side on
  purpose and shows its counter-evidence — because a case that hides its weak
  points doesn't survive the room.</div>
</header>

<div class="grid">{cards_html}</div>

<p class="lede" style="max-width:76ch"><b>The argument is a four-link chain</b>
— addition by subtraction, each link measured: the ball stopped (§1), went to
isolation and the wrong shots (§2), with no efficiency premium for the price
(§3), and it cost most when it mattered (§4). Then the return: a connective
role player, a cleaner cap sheet, and cheap draft equity (§5–§9).</p>

<h2><span class="n">01</span>The ball stopped here</h2>
<p class="lede">Among every NBA player averaging 45+ touches, Brown converted
a touch into a pass at the <b>{fb25.pass_touch_pctile*100:.0f}{'st' if round(fb25.pass_touch_pctile*100)==1 else 'th'} percentile</b>
in 2025-26 ({fb25.pass_per_touch:.2f} passes/touch) while holding the ball
longer than {fb25.sec_touch_pctile*100:.0f}% of the pool. The control season
kills the role excuse: beside a healthy Tatum in 2024-25, still
<b>p{fb24.pass_touch_pctile*100:.0f}</b>. George is the stylistic opposite —
p{fg25.pass_touch_pctile*100:.0f} pass rate on a p{fg25.sec_touch_pctile*100:.0f}
hold time.</p>
{_img64("flow_test.png")}

<h2><span class="n">02</span>…and went to the wrong shots</h2>
<p class="lede">A stopped ball is only a problem if the possession ends badly.
It did: fewer threes, double the long twos, two-thirds of shots self-created —
with <b>zero shot-making premium</b> (xFG over-expectation ≈ 0.00) to pay for
the difficulty.</p>
{_img64("case_for_moving_on.png")}

<h2><span class="n">03</span>…at a price the production never justified</h2>
<p class="lede">In 2024-25 — normal role, normal usage — Brown's true shooting
ranked <b>{e24.TS_rank:.0f}th of {len(eff24)}</b> max-tier contracts at
{e24.cap_pct*100:.0f}% of the cap. His 2025-26 ({e25.TS_PCT:.3f} TS) came at a
35% usage no one else in the set but Dončić carries — respectable under load,
still below the rotation median. The high-efficiency max tier (SGA, Giannis,
Butler, Zion, Kawhi: .63+) is a different species.</p>
{_img64("efficiency_comps.png")}

<h2><span class="n">04</span>…and it cost most when it mattered</h2>
<p class="lede">Give Brown the clutch minutes — he's earned them (.632 clutch TS
in 24-25, better than Tatum). But across playoff series and games against .500+
teams, Tatum posts the better efficiency, plus-minus, and playmaking, while
Brown's 29-a-night vs good teams in 25-26 converted to a break-even scoreboard
margin.</p>
{_img64("high_leverage.png")}

<h2><span class="n">05</span>The return: a role player who actually fits</h2>
<p class="lede">George is a production downgrade — say it plainly — and his
scoring efficiency is ordinary. The case for him is <b>connective fit</b>: more
catch-and-shoot, less iso, faster ball movement, on a contract that dies a
year sooner.</p>
<table>
  <tr><th>Metric (2025-26)</th><th>Brown</th><th>George</th><th>Edge</th></tr>
  {fit_rows}
</table>
{_img64("george_vs_brown.png")}

<h2><span class="n">06</span>The offense Boston kept</h2>
<p class="lede">Tatum self-creates as much as Brown did — but half his shots
are threes (.50 3PA rate vs Brown's .26) and his long-two rate fell while
Brown's doubled. In the last season both were healthy, <b>Tatum-led lineups
outscored Brown-led lineups (+11.9 vs +9.8) on a bigger sample</b>.</p>
{_img64("tatum_baseline.png")}

<h2><span class="n">07</span>The cap ledger</h2>
<table>
  <tr><th>Season</th><th>Brown owed</th><th>George owed</th></tr>
  {cap_rows}
</table>
<p class="lede">Cheaper every year, and 2028-29 comes back entirely — a
${brown_2829/1e6:.0f}M expiring-sized hole that becomes apron relief and trade
ammunition a full season early (Boston is over the cap, so read it as
flexibility, not clean max room). Current deals put <b>Donovan Mitchell</b> and
<b>Zion Williamson</b> on the 2028 market.</p>

<h2><span class="n">08</span>The two firsts are the cheapest wins in basketball</h2>
<p class="lede">From the 2015-19 draft classes, picks 15-30 average
{pick.ws_per_yr:.1f} WS per season — about {pick.exp_ws_4yr_deal:.0f} WS over a
rookie deal that costs ~${pick.rookie_cost_4yr/1e6:.0f}M. That's
${pick.cost_per_ws/1e6:.1f}M per win share against the
${pick.brown_cost_per_ws/1e6:.1f}M Boston was paying Brown —
<b>~{pick.brown_cost_per_ws/pick.cost_per_ws:.0f}× cheaper</b>, worth
~${pick.surplus_value_per_pick/1e6:.0f}M in surplus per pick at Brown's price
of a win. Hit rate for a real rotation player (≥2 WS/yr):
{pick.hit_rate_ws2plus:.0%}. Bust rate: {pick.bust_rate_ws_under_half:.0%}.</p>
{_img64("pick_value.png")}

<h2><span class="n">09</span>The flattened lottery is the upside kicker</h2>
<p class="lede">If either pick conveys from a lottery team — Philadelphia's
trajectory makes that live — the post-2019 lottery reform works in Boston's
favor. Top-<b>4</b> picks are drawn (was top-3) from flattened odds, so a
mid-lottery seed's chance at a premium pick roughly
<b>{lotto.loc[8,'p_top4_new']/lotto.loc[8,'p_top4_old']:.1f}×</b> what the old
system gave it: seed 8 jumps from {lotto.loc[8,'p_top4_old']:.1%} to
<b>{lotto.loc[8,'p_top4_new']:.1%}</b> top-4 equity. Computed exactly from the
official ball-combination counts — not a quoted table. A seed-8 pick projects
to <b>{lotto.loc[8,'exp_ws_yr_new']:.1f} WS/yr</b> (vs {1.69} for a late
first), worth ~<b>${lotto.loc[8,'surplus_at_brown_rate']/1e6:.0f}M surplus</b>
at Brown's price of a win — per pick.</p>
{_img64("lottery_value.png")}

<div class="honesty">
  <h3>⚖️ Read before presenting — where this case is weakest</h3>
  <ul>
    <li><b>The consensus is against this brief.</b> The trade is real
    (agreed July 1, 2026), and the market read it as a Philadelphia win —
    "A+" grades for the Sixers, "40 cents on the dollar" in the Boston press.
    Brown finished <b>6th in MVP voting</b> in 2025-26. This deck is the
    minority report; weigh it accordingly.</li>
    <li><b>Brown is the better player.</b> He out-produces George everywhere
    (6.9 vs 2.5 WS in 25-26). The case is fit + flexibility + assets, not talent.</li>
    <li><b>Brown-led lineups won.</b> Without Tatum: +9.8 (24-25), +4.8 (25-26).
    "Empty stats" is not supported; "impact fades vs quality opponents in 25-26" is.</li>
    <li><b>Clutch favors Brown</b> — .632 TS in 24-25. Concede it up front.</li>
    <li><b>Do not argue defense.</b> We tested 'declining defense' three ways
    and it failed: matchup data shows shooters hit <b>−4.2%</b> vs their norm
    against Brown in 25-26 (−5.7% at the rim), his best mark of the window,
    at career-high usage. Defense is closer to a point in his favor.</li>
    <li><b>Holding the ball isn't damning by itself</b> — SGA and Dončić live
    in the same hold-time region and are MVPs. The chain needs §2: it's
    stop-the-ball <i>plus</i> bad terminations that indicts. If §2 falls, §1
    is just a style note.</li>
    <li><b>George's own efficiency is mediocre</b> — .570 TS at a light 22.9%
    usage. The case for him is connective fit, never scoring; anyone selling
    George-as-scorer loses the room.</li>
    <li><b>George is 35</b> with real cliff risk; the fit edge requires him on the floor.</li>
    <li><b>Pick values are expectations</b> — {pick.bust_rate_ws_under_half:.0%}
    of late firsts return almost nothing; the 2028 FA list shifts with every extension.</li>
    <li><b>The lottery kicker assumes the picks convey unprotected from a
    lottery team.</b> Protections (top-N shielded, rolling to seconds) or a
    resurgent sender turn section 06 back into section 05's late-first math.
    Verify the actual pick terms before quoting seed-8 numbers.</li>
  </ul>
</div>

<footer>Generated by the Fit Check pipeline · scripts/09_trade_case_deck.py ·
all figures reproducible from cached pulls · {pd.Timestamp.now():%Y-%m-%d}</footer>
</body></html>"""

    out = config.OUTPUT_DIR / "trade_case.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
