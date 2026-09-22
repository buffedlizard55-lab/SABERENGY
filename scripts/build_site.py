"""Write docs/index.html from docs/run_summary.json.

The page is static so GitHub Pages does not need a build step. Re-run this
after `python -m saberengy.pipeline`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "docs" / "run_summary.json"
OUT = ROOT / "docs" / "index.html"


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def num(value, digits=3):
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return esc(value)


def baseline_blurb(tests: dict) -> str:
    parts = []
    for label, block in tests.items():
        metrics = block.get("metrics") or {}
        name = label.replace("_", " ")
        beats = metrics.get("model_beats_trailing_mean")
        if beats is True:
            corr_model = metrics.get("correlation_model")
            corr_base = metrics.get("correlation_trailing_mean")
            if corr_model is not None and corr_base is not None and corr_model <= corr_base:
                parts.append(f"{name}: lower MAE, correlation not better")
            else:
                parts.append(f"{name}: lower MAE")
        elif beats is False:
            parts.append(f"{name}: does not beat the trailing mean")
    if not parts:
        return "No holdout in this run."
    return ". ".join(parts) + ". Not an overall win."


def yn(value) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "—"


def player_rows(tests: dict) -> str:
    rows = []
    for label, block in tests.items():
        metrics = block.get("metrics") or {}
        model = block.get("model") or {}
        rows.append(
            "<tr>"
            f"<td>{esc(label.replace('_', ' '))}</td>"
            f"<td>{esc(metrics.get('n', '—'))}</td>"
            f"<td>{num(metrics.get('mae_model'))}</td>"
            f"<td>{num(metrics.get('mae_trailing_mean'))}</td>"
            f"<td>{yn(metrics.get('model_beats_trailing_mean'))}</td>"
            f"<td>{num(metrics.get('correlation_model'))}</td>"
            f"<td>{num(metrics.get('correlation_trailing_mean'))}</td>"
            f"<td>{esc(model.get('n_sims', '—'))}</td>"
            f"<td>{num(model.get('pass_slope'))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='9'>No player tests in this summary.</td></tr>"


def game_rows(checks: dict) -> str:
    rows = []
    for label, block in checks.items():
        rows.append(
            "<tr>"
            f"<td>{esc(label.replace('_', ' '))}</td>"
            f"<td>{esc(block.get('n', '—'))}</td>"
            f"<td>{num(block.get('mae_margin_model'))}</td>"
            f"<td>{num(block.get('mae_margin_market'))}</td>"
            f"<td>{num(block.get('mae_total_model'))}</td>"
            f"<td>{num(block.get('mae_total_market'))}</td>"
            f"<td>{esc(block.get('training_games', '—'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def upcoming_rows(upcoming: dict) -> str:
    rows = []
    for game in upcoming.get("games") or []:
        rows.append(
            "<tr>"
            f"<td>{esc(game.get('gameday'))}</td>"
            f"<td>{esc(game.get('matchup'))}</td>"
            f"<td>{esc(game.get('spread_line'))}</td>"
            f"<td>{esc(game.get('total_line'))}</td>"
            f"<td>{esc(game.get('away_qb'))}</td>"
            f"<td>{esc(game.get('home_qb'))}</td>"
            f"<td>{'played' if game.get('played') else 'not played'}</td>"
            "</tr>"
        )
    return "\n".join(rows) or "<tr><td colspan='7'>No week-3 rows in the schedule file.</td></tr>"


def lineup_samples(lineups: dict) -> str:
    samples = lineups.get("sample") or []
    if not samples:
        return "<p>No sample lineups in this run.</p>"
    blocks = []
    for index, lineup in enumerate(samples, start=1):
        items = "".join(f"<li>{esc(name)}</li>" for name in lineup)
        blocks.append(f"<div class='card'><h3>Sample {index}</h3><ol>{items}</ol></div>")
    return "\n".join(blocks)


def irregularity_rows(rows: list) -> str:
    if not rows:
        return "<p>None recorded in this run.</p>"
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{esc(row.get('gameday'))}</td>"
            f"<td>{esc(row.get('matchup'))}</td>"
            f"<td>{esc(row.get('spread_line'))}</td>"
            f"<td>{esc(row.get('total_line'))}</td>"
            f"<td>{esc(row.get('actual_total'))}</td>"
            f"<td>{esc(row.get('flag'))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Date</th><th>Game</th><th>Spread</th>"
        "<th>Total line</th><th>Actual total</th><th>Flag</th></tr></thead><tbody>"
        + "\n".join(body)
        + "</tbody></table>"
    )


def blocked_rows(rows: list) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{esc(row.get('item'))}</td>"
            f"<td><a href='{esc(row.get('url'))}'>{esc(row.get('url'))}</a></td>"
            f"<td>{esc(row.get('status'))}</td>"
            "</tr>"
        )
    return "\n".join(body)


def provenance_text(data: dict) -> str:
    weeks = (data.get("player_weeks") or {}).get("seasons") or {}
    bits = []
    for season, info in weeks.items():
        bits.append(f"{esc(season)}: {esc(info.get('status'))}")
    used = esc((data.get("player_weeks") or {}).get("source_used"))
    return used + (". " + "; ".join(bits) if bits else "")


def render(summary: dict) -> str:
    generated = esc(summary.get("generated_on"))
    elapsed = esc(summary.get("elapsed_seconds"))
    games = summary.get("data", {}).get("games") or {}
    lineups = summary.get("lineups") or {}
    upcoming = summary.get("upcoming_nfl_week") or {}
    contest = lineups.get("contest_summary") or {}
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SABERENGY — public-data DFS research</title>
  <style>
    :root {{
      --ink: #1c1917;
      --muted: #57534e;
      --line: #e7e5e4;
      --paper: #fafaf9;
      --card: #ffffff;
      --accent: #1f4d3a;
      --warn: #9a3412;
      --warn-bg: #fff7ed;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--paper);
      font: 16px/1.5 "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
    }}
    a {{ color: var(--accent); }}
    header, main {{ width: min(980px, calc(100% - 2rem)); margin: 0 auto; }}
    main {{ overflow-x: auto; }}
    header {{ padding: 2.5rem 0 1rem; }}
    h1 {{ font-size: 2rem; line-height: 1.15; margin: 0 0 0.4rem; letter-spacing: -0.02em; }}
    h2 {{ font-size: 1.25rem; margin: 2rem 0 0.6rem; }}
    h3 {{ font-size: 1rem; margin: 0 0 0.4rem; }}
    p, li {{ color: var(--ink); }}
    .lede {{ font-size: 1.125rem; max-width: 42rem; }}
    .meta {{ color: var(--muted); font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.875rem; }}
    .warn {{
      background: var(--warn-bg);
      border: 1px solid #fed7aa;
      color: var(--warn);
      padding: 0.8rem 1rem;
      border-radius: 8px;
      margin: 1rem 0;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 0.9rem 1rem;
    }}
    .card strong {{ display: block; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted); }}
    .scroll {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; background: white; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.875rem; }}
    pre {{ overflow-x: auto; background: white; border: 1px solid var(--line); padding: 0.8rem 1rem; border-radius: 8px; }}
    th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 0.45rem 0.5rem; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.9em; }}
    footer {{ width: min(980px, calc(100% - 2rem)); margin: 2rem auto 3rem; color: var(--muted); font-size: 0.875rem; }}
    ol.lineup {{ margin: 0; padding-left: 1.2rem; }}
  </style>
</head>
<body>
<header>
  <p class="meta">Independent research · not affiliated with SaberSim or DraftKings · generated {generated}</p>
  <h1>SABERENGY</h1>
  <p class="lede">{esc(summary.get("what_this_is"))}</p>
</header>
<main>
  <div class="warn">
    <strong>Do not enter these lineups.</strong>
    Official DraftKings salaries were not used. The 2025 week 3 lineups below are a historical position check, not the current slate. The contest-sim block is a smoke test, not a result.
  </div>

  <div class="grid">
    <div class="card"><strong>Salaries</strong>Not used. Cap not applied.</div>
    <div class="card"><strong>Model vs trailing mean</strong>{esc(baseline_blurb(summary.get("player_forward_tests") or {}))}</div>
    <div class="card"><strong>Current NFL week</strong>2026 week 3 is on the schedule. Player projections were not produced.</div>
    <div class="card"><strong>Run time</strong>{elapsed} seconds. Machine-readable copy: <a href="run_summary.json">run_summary.json</a>.</div>
  </div>

  <h2>Player forward tests</h2>
  <p>Each test uses only rows dated before that week. Scoring is partial DraftKings offense: yards, touchdowns, receptions, interceptions, and the 100/300-yard bonuses. Fumbles, two-point conversions, and return touchdowns are not in the weekly file, so they are not scored. Rules: <a href="https://www.draftkings.com/help/rules/1/1">DraftKings NFL Classic</a>, re-read 2026-09-22.</p>
  <table>
    <thead>
      <tr><th>Holdout</th><th>n</th><th>MAE model</th><th>MAE trailing mean</th><th>Beats baseline</th><th>Corr model</th><th>Corr baseline</th><th>Sims</th><th>Pass slope</th></tr>
    </thead>
    <tbody>
      {player_rows(summary.get("player_forward_tests") or {})}
    </tbody>
  </table>
  <p>A negative pass slope means more pass attempts when the team is trailing. That is a fit on past team totals, not a claim that the player model is better than a trailing mean. The 2025 week 3 MAE edge is one early-season week on mirror data. It is not an established edge.</p>

  <h2>Game environment</h2>
  <p>The game check adds a historical residual to the posted spread and total. It should land near the market. A small difference is not an edge.</p>
  <table>
    <thead>
      <tr><th>Week</th><th>n</th><th>Margin model</th><th>Margin market</th><th>Total model</th><th>Total market</th><th>Training games</th></tr>
    </thead>
    <tbody>
      {game_rows(summary.get("game_environment_forward_tests") or {})}
    </tbody>
  </table>
  <p>Spread convention, measured in the same file: positive <code>spread_line</code> means the expected home margin. Example kept in the model: 2024 week 1 BAL at KC, spread +3, KC 27–20. Source: <a href="https://github.com/nflverse/nfldata/blob/master/data/games.csv">nflverse/nfldata games.csv</a>. License field from the GitHub API was null on 2026-09-22. This is not an official NFL feed. File in this run: {esc(games.get("rows"))} rows, max gameday {esc(games.get("max_gameday"))}.</p>

  <h2>2026 week 3 schedule</h2>
  <p>Player projections: {esc(upcoming.get("player_projections"))}. Quarterback names are copied from the schedule file. They were not checked against an official depth chart. A surprising name is a file value, not a confirmation.</p>
  <table>
    <thead>
      <tr><th>Date</th><th>Game</th><th>Expected home margin</th><th>Total</th><th>Away QB</th><th>Home QB</th><th>Status</th></tr>
    </thead>
    <tbody>
      {upcoming_rows(upcoming)}
    </tbody>
  </table>

  <h2>Historical lineup check</h2>
  <p>{esc(lineups.get("label"))}. Slate: {esc(lineups.get("slate"))}. Position-legal: {esc(lineups.get("all_position_legal"))}. Count: {esc(lineups.get("n_lineups"))}. {esc(lineups.get("name_note"))}</p>
  <p>{esc(lineups.get("contest_sim_note"))} Interpretable: {esc(contest.get("interpretable"))}. {esc(contest.get("why_not_interpretable"))}</p>
  <div class="grid">
    {lineup_samples(lineups).replace("<ol>", "<ol class='lineup'>")}
  </div>

  <h2>What the code actually does</h2>
  <ul>
    <li>NFL projections: team pass volume shifts with the simulated score difference, then attempts, targets, and carries are split by each player's recent share. Points are the partial DraftKings table.</li>
    <li>Lineups with roster rules: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX, 1 DST, at least two games, $50,000 cap only when every player has a salary. The fetched NFL rules page does not state an 8-player team cap, so that cap is not enforced.</li>
    <li>Contest sim: ranks lineups against a payout list the caller supplies. Dupes are an identical-lineup count, not SaberSim's unpublished formula. Metric names follow <a href="https://support.sabersim.com/en/articles/12079199-how-contest-sims-work">How Contest Sims Work</a>.</li>
    <li>MLB: an odds-ratio plate-appearance function is unit-tested. No live MLB slate was scored. A re-fetch of the MLB rules page returned “Busy” on this pass, so the MLB scoring table was not re-confirmed here. Prior transcription: <a href="https://www.draftkings.com/help/rules/2/2">MLB Classic rules</a>.</li>
    <li>The old ownership sampler is not roster-legal. It draws ids by weight and ignores slots.</li>
  </ul>

  <h2>Player-file provenance</h2>
  <p>{provenance_text(summary.get("data") or {})}. Canonical weekly files are CC-BY-4.0 at <a href="https://github.com/nflverse/nflverse-data">nflverse-data</a>. The mirror is not that license. Mirror files: <a href="https://github.com/cwalenciak/the-odds-line/tree/master/player_stats">the-odds-line player_stats</a>.</p>

  <h2>Public SaberSim pages, for comparison</h2>
  <p>These describe SaberSim. They are not a claim that this repository copied the product or the paywall.</p>
  <ul>
    <li><a href="https://www.sabersim.com/">Homepage</a> — “18 sports. 4 sites. 1 platform.” This repo does not cover 18 sports.</li>
    <li><a href="https://support.sabersim.com/en/articles/12078831-how-projections-work">How projections work</a> — play-by-play sims; projection is the average of trials; floor, median, and ceiling percentiles.</li>
    <li><a href="https://support.sabersim.com/en/articles/12079141-building-lineups">Building lineups</a> — Sim mode, Optimizer mode, Correlation and Sim Diversity sliders. The equations are not published. Ours are labeled as ours.</li>
    <li><a href="https://www.sabersim.com/pricing">Pricing</a> — 13 contest-type names. Our per-type weights are unvalidated guesses.</li>
    <li><a href="https://support.sabersim.com/en/articles/12079563-using-late-swap">Late swap</a> and <a href="https://support.sabersim.com/en/articles/12079605-using-contest-flashback">Contest flashback</a> — documented on their site. Our modules do not call a live injury feed or download contest CSVs.</li>
  </ul>

  <h2>Blocked on this run</h2>
  <table>
    <thead><tr><th>Item</th><th>Link</th><th>Status</th></tr></thead>
    <tbody>
      {blocked_rows(summary.get("blocked") or [])}
    </tbody>
  </table>

  <h2>Irregularities kept, not deleted</h2>
  {irregularity_rows(summary.get("irregularities") or [])}

  <h2>Reproduce</h2>
  <pre><code>python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m unittest saberengy.tests.test_core saberengy.tests.test_nfl_forward
PYTHONPATH=src python -m saberengy.pipeline
PYTHONPATH=src python scripts/build_site.py</code></pre>
  <p>The demo command uses invented players and salaries. It is not the forward test.</p>

  <h2>Next session</h2>
  <ol>
    <li>Download <a href="https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv">stats_player_week_2026.csv</a> from a network that can reach the release CDN, then project 2026 week 3. Do not invent the file.</li>
    <li>Fetch a keyless MLB slate from <a href="https://statsapi.mlb.com/api/v1/schedule?sportId=1&amp;date=2026-09-22">the Stats API schedule</a> once TLS from the runner works. Re-read the MLB rules page before scoring.</li>
    <li>Add a salary file only from a source the operator can download without a paid trial. Until then, keep the cap off and the lineups labeled.</li>
    <li>Do not treat the 2025 week 3 MAE gap as a model win until it repeats on the canonical file and on later weeks.</li>
  </ol>
</main>
<footer>
  Quote ledger: VERIFICATION.md. Gaps: LIMITATIONS.md. Not a wagering product.
</footer>
</body>
</html>
"""


def main() -> None:
    summary = json.loads(SUMMARY.read_text())
    OUT.write_text(render(summary))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
