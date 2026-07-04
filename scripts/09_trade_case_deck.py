"""Render outputs/trade_case.html — the self-contained editorial long-read.

Content mirrors scripts/15_build_pptx_deck.py ("Breaking Down the Jaylen
Brown Trade", 11 slides) exactly: same numbers, same slide order, same
honesty flags. Figures from outputs/figures/ are downscaled to <=1600px
wide and embedded as base64 so GitHub Pages serves a single file with no
external assets (system font stacks only).

Design register: editorial magazine — serif display headlines, restrained
sans body, near-black ink on white, dark-green hero, Celtics green used
sparingly for key numbers and section labels, one red accent for negatives.
"""
from __future__ import annotations

import base64
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from fitcheck import config

MAX_W = 1600  # px — downscale embedded figures to keep the file lean


def _img64(name: str, alt: str) -> str:
    p = config.FIG_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"missing figure: {p}")
    raw = p.read_bytes()
    try:
        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)),
                           Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            raw = buf.getvalue()
    except ImportError:
        pass  # embed at native size if PIL is unavailable
    b64 = base64.b64encode(raw).decode()
    return (f'<figure><img src="data:image/png;base64,{b64}" alt="{alt}">'
            f"</figure>")


def main() -> int:
    figs = {
        "diet": _img64("case_for_moving_on.png",
                       "Brown shot-diet drift, 2024-25 to 2025-26"),
        "identity": _img64("three_point_identity.png",
                           "Boston three-point identity vs Brown's shot mix"),
        "redis": _img64("wing_redistribution.png",
                        "Redistributing Brown's shots across the wings"),
        "onoff": _img64("with_without_net_2025-26.png",
                        "Brown lineup net ratings with and without co-stars"),
        "solo": _img64("tatum_first_option.png",
                       "Tatum as a first option: record and production"),
        "avail": _img64("career_availability.png",
                        "Career availability, Tatum vs Brown"),
        "eff": _img64("efficiency_comps.png",
                      "Cost per win share among max-tier contracts"),
    }

    comp_rows = "".join(
        f"<tr><td>{lab}</td><td>{jb}</td><td class='pg'>{pg}</td></tr>"
        for lab, jb, pg in [
            ("3PT rate", "0.262", "0.497"),
            ("Catch-&amp;-shoot rate", "0.163", "0.409"),
            ("Iso / 3+ dribble rate", "0.639", "0.404"),
            ("Contested-shot rate", "0.517", "0.370"),
            ("Bad-shot index", "0.379", "0.273"),
        ])

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Breaking Down the Jaylen Brown Trade</title>
<style>
  :root {{
    --ink:#16181d; --muted:#5c6470; --faint:#8a919c;
    --green:#007A33; --dark:#0A2A1A; --red:#B3403A; --gold:#BA9653;
    --rule:#e3e5e8; --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
    --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,Helvetica,Arial,sans-serif;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html {{ -webkit-text-size-adjust:100%; }}
  body {{ background:#fff; color:var(--ink); font:17px/1.65 var(--sans); }}
  a {{ color:var(--green); text-decoration:none; border-bottom:1px solid #b9d6c5; }}
  a:hover {{ border-bottom-color:var(--green); }}

  /* ---- hero ---- */
  .hero {{ background:var(--dark); color:#f4f6f4; padding:88px 24px 72px; }}
  .hero-inner {{ max-width:820px; margin:0 auto; }}
  .kicker {{ font:600 12px/1 var(--sans); letter-spacing:.22em;
    text-transform:uppercase; color:#9ab2a4; }}
  .hero h1 {{ font-family:var(--serif); font-weight:400; letter-spacing:-.01em;
    font-size:clamp(38px,6.4vw,60px); line-height:1.08; margin:26px 0 22px;
    color:#fff; }}
  .dek {{ font-size:19px; line-height:1.55; color:#c6d5cb; max-width:640px; }}
  .herostats {{ display:flex; gap:56px; flex-wrap:wrap; margin-top:52px;
    border-top:1px solid rgba(255,255,255,.14); padding-top:30px; }}
  .herostats .num {{ font-family:var(--serif); font-size:44px; line-height:1;
    color:#fff; }}
  .herostats .lab {{ font-size:11.5px; letter-spacing:.14em;
    text-transform:uppercase; color:#8fa89b; margin-top:9px; }}

  /* ---- article ---- */
  .article {{ max-width:760px; margin:0 auto; padding:24px; }}
  section {{ margin:72px 0; }}
  .slug {{ font:600 12px/1 var(--sans); letter-spacing:.2em;
    text-transform:uppercase; color:var(--green); margin-bottom:14px; }}
  h2 {{ font-family:var(--serif); font-weight:400; font-size:31px;
    line-height:1.2; letter-spacing:-.01em; margin-bottom:18px; }}
  p {{ margin:0 0 18px; color:#2a2e35; }}
  p b, p strong {{ font-weight:650; color:var(--ink); }}
  .neg {{ color:var(--red); font-weight:650; }}
  .pos {{ color:var(--green); font-weight:650; }}
  figure {{ margin:30px -60px; }}
  figure img {{ width:100%; display:block; border:1px solid var(--rule);
    border-radius:2px; }}
  @media (max-width:920px) {{ figure {{ margin:26px 0; }} }}
  .bignum {{ margin:34px 0; padding-left:22px; border-left:2px solid var(--rule); }}
  .bignum .n {{ font-family:var(--serif); font-size:46px; line-height:1.05;
    color:var(--green); }}
  .bignum .n.down {{ color:var(--red); }}
  .bignum .c {{ font-size:14.5px; color:var(--muted); margin-top:6px;
    max-width:52ch; }}
  .aside {{ font-style:italic; color:var(--faint); font-size:15px;
    line-height:1.6; margin:22px 0; }}
  table {{ width:100%; border-collapse:collapse; margin:26px 0;
    font-size:15.5px; font-variant-numeric:tabular-nums; }}
  th {{ font:600 11.5px/1.3 var(--sans); letter-spacing:.12em;
    text-transform:uppercase; color:var(--faint); text-align:left;
    padding:0 14px 10px 0; border-bottom:1px solid var(--ink); }}
  td {{ padding:11px 14px 11px 0; border-bottom:1px solid var(--rule); }}
  td.pg {{ color:var(--green); font-weight:650; }}
  .rule {{ border:0; border-top:1px solid var(--rule); margin:0; }}

  /* ---- closer ---- */
  .closer {{ background:var(--dark); color:#e8efe9; padding:72px 24px;
    margin-top:88px; }}
  .closer-inner {{ max-width:760px; margin:0 auto; }}
  .closer .slug {{ color:var(--gold); }}
  .closer h3 {{ font-family:var(--serif); font-weight:400; font-size:24px;
    line-height:1.3; color:#fff; margin:30px 0 8px; }}
  .closer p {{ color:#b9cabf; font-size:16.5px; }}
  .closer .aside {{ color:#8fa89b; border-top:1px solid rgba(255,255,255,.14);
    padding-top:24px; margin-top:44px; }}
  footer {{ max-width:760px; margin:0 auto; padding:34px 24px 60px;
    font-size:13.5px; color:var(--faint); line-height:1.7; }}
</style></head><body>

<div class="hero"><div class="hero-inner">
  <div class="kicker">A Data Audit &middot; July 2026</div>
  <h1>Breaking Down the Jaylen&nbsp;Brown Trade</h1>
  <p class="dek">On July 1, 2026, Boston traded Brown to Philadelphia for
  Paul George and picks. This is the audit, built the day after: a neutral
  scorecard, the strongest evidence-based case for the trade, and every
  counter-argument we could find.</p>
  <div class="herostats">
    <div><div class="num">25&ndash;4</div><div class="lab">When Brown sat, 2023&ndash;present</div></div>
    <div><div class="num">34.4%</div><div class="lab">Of the salary cap</div></div>
    <div><div class="num">+11.9</div><div class="lab">Tatum-led lineup net</div></div>
  </div>
</div></div>

<div class="article">

<section>
  <div class="slug">01 &mdash; The Setup</div>
  <h2>A $53M wing, a movement-3 system, and a real trade to audit</h2>
  <p>Brown's $53.1M salary in 2025-26 was <b>34.4% of the cap</b> &mdash; over
  a third of the sheet on one wing. Over the same stretch his shot diet got
  <span class="neg">16% worse</span> year over year (bad-shot index 0.328
  &rarr; 0.379), drifting away from the system. In return Boston received
  <b>four assets</b>: Paul George, a 2028 first, a 2031 unprotected first,
  and two seconds.</p>
  <p>Boston's edge was a movement-3 offense with five connected players. The
  question this audit answers with data: did Brown's game pull with that
  identity or against it &mdash; and was the return worth it? Every chart
  comes from a reproducible, unit-tested pipeline.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">02 &mdash; The Shot Diet</div>
  <h2>The shot profile was drifting away from what Boston wins with</h2>
  <p><b>Fewer threes, doubled long twos.</b> Brown's 3PT rate fell 0.32
  &rarr; 0.26 while his long-two rate doubled, 0.07 &rarr; 0.14 &mdash; the
  one shot the system exists to kill. <b>Two-thirds of his shots were
  self-created</b>: iso / 3+ dribble rate rose 0.53 &rarr; 0.64, with more
  late-clock bailouts (0.18 &rarr; 0.22).</p>
  {figs['diet']}
  <p><b>And there was no tough-shot premium.</b> The xFG model (2,661 shots)
  scores his shot-making at expectation &mdash; &asymp; +0.000 both years.
  The difficulty was self-inflicted. This is the cleanest, least-confounded
  number in the file: the possession-termination profile trended away from
  the identity, with no shot-making bailout.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">03 &mdash; The Game Plan</div>
  <h2>Boston's identity is math &mdash; and Brown was its one outlier</h2>
  <p>Boston finished <b>#1, #1, and #4 in three-point volume</b> with a
  top-2 offense all three years &mdash; threes returned 1.10 points per shot
  vs 0.97 for twos. Brown was <span class="neg">last of 7 perimeter players
  in 3PT rate (.263 vs the team's .467)</span> and first in long twos.</p>
  {figs['identity']}
  <p>It was a shot-mix problem, not a finishing one &mdash; his 1.046 points
  per shot vs the team's 1.101. And priced honestly, swapping his diet for
  George's is roughly a wash after creation and aging discounts. The offense
  case supports; it doesn't headline.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">04 &mdash; Where the Shots Go</div>
  <h2>Redistribute Brown's 21.7 shots to the wings &mdash; priced honestly</h2>
  <p>The ceiling: <span class="pos">+1.3 pts/g (~3.5 wins)</span> if every
  wing's efficiency survived the extra volume &mdash; it won't.
  Usage-adjusted, the mechanical redistribution is roughly a wash
  (&minus;0.7 to +0.9 wins). And the George-only 1-for-1 is
  <span class="neg">negative</span> &mdash; spreading beats concentrating.</p>
  {figs['redis']}
  <p>The real upside isn't in this mechanical model &mdash; it's Tatum's
  creation (5.7&ndash;6.1 assists, .498 3PT-rate gravity) upgrading the shots
  these wings get, and that effect is already measured in the +11.9 Tatum-led
  lineups. Combined honest range: <b>+4 to +8 wins</b> &mdash; the
  projections overlap and do not stack.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">05 &mdash; Contingent Value</div>
  <h2>The production needed Tatum and White to prop it up</h2>
  <p><b>With Tatum: +16.2. Without: +4.8.</b> An 11.3-point swing in
  2025-26 &mdash; Brown's lineups won when the infrastructure was on the
  floor. <b>With White: +9.4. Without: <span class="neg">&minus;1.0</span>.</b>
  Same story with the other connector; Brown-led lineups without White were
  underwater.</p>
  {figs['onoff']}
  <p>A $53M player whose value is contingent on his co-stars is a fit
  problem, not a star.</p>
  <p class="aside">The honest caveat: Tatum's injury contaminates the
  2025-26 split. The confound is documented, not hidden &mdash; it softens,
  but doesn't reverse, the pattern.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">06 &mdash; The Hierarchy Test</div>
  <h2>First-option Tatum beat load-sharing &mdash; on the floor and in the
  standings</h2>
  <div class="bignum"><div class="n">25&ndash;4</div>
  <div class="c">Boston's record when Brown sat, 2023&ndash;present: 86.2%,
  +13.3 per game across 29 games &mdash; including 10&ndash;0 in the title
  year. Both healthy: 73.7%.</div></div>
  <p>The lineup ladder points the same way: <b>Tatum-led +11.9 &gt; together
  +7.6 &gt; neither +3.5</b> (the control). And when the load shifted, the
  production held: pooled first-option Tatum ran
  <b>28.0 / 7.9 / 5.7 at 34.6% usage</b> (+4.7 points of usage) with TS
  .593 &rarr; .572 &mdash; a modest efficiency dip, printed, not hidden.</p>
  {figs['solo']}
  <p>The projection, not observation: the +4.3 lineup gap, shrunk 40&ndash;60%
  for bench and garbage-time contamination, comes to +1.7&ndash;2.6 team net
  &mdash; worth <b>~5&ndash;7 wins a season</b>. Tatum's projected solo line:
  27.2&ndash;28.8 pts, 7.8&ndash;8.9 reb, 5.1&ndash;6.2 ast, .566&ndash;.584
  TS &mdash; stated as a range from the observed 16-game sample and a
  documented usage-tradeoff model, because false precision is how decks lie.</p>
  {figs['avail']}
  <p class="aside">Honesty flags: Wilson intervals on the win rates overlap
  &mdash; the claim is &ldquo;no evidence of drop-off,&rdquo; not proof. And
  Brown's own 7-game solo cell was the matrix's best (6&ndash;1, +15.8). See
  section 09.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">07 &mdash; The Contract</div>
  <h2>Max-contract price, below-median-efficiency production</h2>
  <div class="bignum"><div class="n down">$7.7M</div>
  <div class="c">Per win share: 6.9 WS on $53.1M at 34% of the cap, with a
  .573 TS% &mdash; below the max-wing median.</div></div>
  {figs['eff']}
  <p>Picks 15&ndash;30 buy the same wins at <span class="pos">~$2.1M per win
  share</span> on rookie deals.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">08 &mdash; The Return</div>
  <h2>George is the cleaner stylistic fit &mdash; and the picks are the
  point</h2>
  <table>
    <tr><th>2025-26 shot profile</th><th>Brown</th><th>George</th></tr>
    {comp_rows}
  </table>
  <p>George takes the shots the system is built to generate &mdash; he plugs
  in instead of stopping it.</p>
  <p><b>Plus the picks: a 2028 first and a 2031 unprotected first.</b> Under
  the post-2019 flattened lottery &mdash; exact odds enumerated across all
  <b>24,024 seed permutations</b> &mdash; late-lottery firsts convey
  materially more top-4 equity than the old system gave them. Cheap,
  controllable, tradeable: the assets a capped-out roster can't otherwise
  get.</p>
</section>

<hr class="rule">

<section>
  <div class="slug">09 &mdash; The Counter-Evidence</div>
  <h2>Where the case is weakest, on the record</h2>
  <p><b>Brown could carry.</b> His 7-game solo cell was the best in the
  2024-25 matrix (6&ndash;1, +15.8), and he carried 58 games alone in
  2025-26 at 28.9 ppg (36&ndash;22, +5.7). The man can be a first option
  &mdash; just not here.</p>
  <p><b>The defense is a real loss.</b> Brown took 19% of his defended
  possessions against opponents' #1 options (Tatum: 8%) at better
  points-allowed, with <b>&minus;4.2 / &minus;5.7</b> defended-FG% margins.
  Boston traded its toughest assignment.</p>
  <p><b>The turnover tax wasn't his.</b> Play-by-play says Brown's live-ball
  turnover rate (<b>1.75 per 36</b>) was lower than Tatum's (1.84) in
  2024-25. That angle exonerates him &mdash; and the media consensus graded
  the trade for Philadelphia.</p>
  <p>An argument that can't survive its own counter-evidence isn't worth
  presenting. Every brief in this project ships with its weakest points
  attached.</p>
</section>

</div>

<div class="closer"><div class="closer-inner">
  <div class="slug">10 &mdash; Bottom Line</div>
  <h3>The fit was real and it was drifting.</h3>
  <p>Fewer threes, doubled long twos, two-thirds self-created &mdash; with
  no shot-making premium to pay for it.</p>
  <h3>The value was contingent.</h3>
  <p>Brown-led lineups needed Tatum and White on the floor; at 34% of the
  cap, contingent is expensive.</p>
  <h3>The return buys identity and optionality.</h3>
  <p>George takes the system's shots; two firsts add the cheap, controllable
  assets a capped roster can't otherwise acquire.</p>
  <p class="aside">Honesty note: this deck argues Boston's side on purpose;
  the neutral scorecard, the Tatum-injury confound, and the media's
  pro-Philadelphia consensus are all documented in the repo.</p>
</div></div>

<footer>Fit Check &middot; Jaylen Brown trade audit &middot; built from a
reproducible, unit-tested pipeline (nba_api / stats.nba.com and
Basketball-Reference, seasons 2024-25 &amp; 2025-26).
Receipts, memos, and code:
<a href="https://github.com/justinloo12/jaylen-brown-fit-check">
github.com/justinloo12/jaylen-brown-fit-check</a> &middot; regenerated by
scripts/09_trade_case_deck.py.</footer>
</body></html>"""

    out = config.OUTPUT_DIR / "trade_case.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
