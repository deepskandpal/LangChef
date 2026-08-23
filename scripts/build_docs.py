#!/usr/bin/env python3
"""Render the documentation site into docs/, for GitHub Pages.

The command reference is generated from ``langchef.core.contract`` rather than
written by hand, for the same reason ``docs/AGENT-CONTRACT.md`` is: a docs page
that claims a command exists when it does not is worse than no page. ``--check``
fails if the committed site is stale, which is how CI keeps it honest.

No build tooling and no third-party dependency — the site is four static pages
and one stylesheet, which is the right amount of machinery for a project whose
whole claim is that text is the record.
"""

import argparse
import html
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))

from langchef import __version__  # noqa: E402
from langchef.core.contract import COMMANDS, RULES  # noqa: E402
from langchef.core.exits import REASON, Exit  # noqa: E402

REPO = "https://github.com/deepskandpal/LangChef"
BLOB = f"{REPO}/blob/main"

PAGES = (
    ("index.html", "Overview"),
    ("quickstart.html", "Quickstart"),
    ("concepts.html", "Concepts"),
    ("cli.html", "Commands"),
)

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=JetBrains+Mono:wght@400;500&"
    "family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&"
    'family=Spectral:ital,wght@0,600;1,400&display=swap">'
)

SIDEBAR = f"""
<nav class="sidebar" aria-label="Documentation">
  <h4>Documentation</h4>
  <ul>
    <li><a href="index.html">Overview</a></li>
    <li><a href="quickstart.html">Quickstart</a></li>
    <li><a href="concepts.html">Concepts</a></li>
    <li><a href="cli.html">Command reference</a></li>
  </ul>
  <h4>In the repository</h4>
  <ul>
    <li><a href="AGENT-CONTRACT.md">Agent contract</a></li>
    <li><a href="{BLOB}/DECISIONS.md">Decisions</a></li>
    <li><a href="{BLOB}/dogfood/README.md">Dogfood</a></li>
    <li><a href="{BLOB}/TRACKER.md">Work tracker</a></li>
    <li><a href="{REPO}">Source on GitHub</a></li>
  </ul>
</nav>
"""


def shell(page: str, title: str, body: str, description: str) -> str:
    """One page, wrapped in the site frame."""
    nav = "\n".join(
        f'      <a href="{href}"{' class="here"' if href == page else ""}>{label}</a>'
        for href, label in PAGES
    )
    year = datetime.now(UTC).strftime("%Y")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="website">
{FONTS}
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="topbar">
  <div class="shell">
    <a class="wordmark" href="index.html"><span class="dot"></span>LangChef</a>
    <nav class="topnav">
{nav}
      <a href="{REPO}">GitHub</a>
    </nav>
  </div>
</header>

<div class="shell layout">
{SIDEBAR}
<main>
{body}
</main>
</div>

<footer class="site">
  <div class="shell">
    <span>LangChef {__version__} — Apache-2.0</span>
    <span>An installed eval engineer.</span>
    <span><a href="{REPO}">Source</a></span>
    <span>&copy; {year} Deepak Kandpal</span>
  </div>
</footer>
</body>
</html>
"""


def command_rows() -> str:
    rows = []
    for c in COMMANDS:
        pill = (
            '<span class="pill yes">live</span>'
            if c.implemented
            else f'<span class="pill no">{html.escape(c.milestone)}</span>'
        )
        writes = "—" if c.writes == "-" else f"<code>{html.escape(c.writes)}</code>"
        rows.append(
            "<tr>"
            f'<td class="mono">langchef {html.escape(c.name)}</td>'
            f"<td>{html.escape(c.summary)}</td>"
            f'<td class="mono">{html.escape(c.determinism)}</td>'
            f"<td>{writes}</td>"
            f"<td>{pill}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def exit_rows() -> str:
    live = {0, 1, 2, 5}
    rows = []
    for code in Exit:
        note = (
            "in use"
            if int(code) in live
            else '<span class="pill no">reserved — not yet emitted</span>'
        )
        rows.append(
            f'<tr><td class="num">{int(code)}</td>'
            f"<td>{html.escape(REASON[code])}</td><td>{note}</td></tr>"
        )
    return "\n".join(rows)


INDEX = """
<div class="hero">
  <div class="eyebrow">An installed eval engineer</div>
  <h1>Your evals, maintained by an agent that already lives in your repository.</h1>
  <p class="lede">LangChef calibrates the judge, runs the experiment, and writes the memo — on your
  compute and your keys. Every number comes from a deterministic CLI; the model spends its effort on
  judgement, never on arithmetic.</p>
  <div class="cta">
    <a class="btn solid" href="quickstart.html">Get started</a>
    <a class="btn ghost" href="@@repo@@">View source</a>
  </div>
</div>

<p class="thesis">Every product in this market is capable and most are cheap. They also all assume a
human eval engineer exists to design the rubrics, interpret the numbers and maintain the suites.
Below a certain size that person does not exist — which is why only about a third of teams running AI
in production evaluate it online at all.</p>

<h2>The one screen that explains it</h2>

<p>Two comparisons from the project's own test harness. Both arms had a regression planted in them
deliberately, so the right answer is known in advance.</p>

<pre><code>$ langchef compare --variant stale-index
base -&gt; stale-index on 90 shared golden(s)
  baseline 83.3%   variant 63.3%
  difference -20.0% [-27.8%, -12.2%]  p=0.0000
  <span class="r">REGRESSION</span>

$ langchef compare --variant truncated-context
  difference +0.0% [+0.0%, +0.0%]  p=1.0000
  <span class="o">INCONCLUSIVE</span>
  (smallest effect this run could have seen: 6.0%)</code></pre>

<p>The second one is the point. There <em>is</em> a regression in that arm — we planted a 3.3-point
one — and ninety goldens cannot resolve it. The honest answer is not <em>“no regression found”</em>;
it is <em>“nothing we could have seen”</em>, and LangChef says so by quoting the smallest effect the
run could have detected. A tool that reported a clean bill of health there would be worse than no
tool at all.</p>

<h2>What makes it different</h2>

<div class="grid2">
  <div class="panel">
    <h3>Calibration comes first</h3>
    <p>A judge is a measuring instrument, not a metric. LangChef measures judge–human agreement
    before it will let a pass rate mean anything, and reports Cohen's κ with an interval rather than
    an accuracy figure that flatters every judge on a skewed suite.</p>
  </div>
  <div class="panel">
    <h3>Refusals are exit codes</h3>
    <p>An approval gate written into a prompt is a suggestion. Here an unapproved or edited rubric
    exits <code>2</code>, and a comparison across two different measurement pins exits <code>5</code>.
    An agent cannot argue with a non-zero exit.</p>
  </div>
  <div class="panel">
    <h3>Nothing leaves your machine</h3>
    <p>No data plane, no hosted dashboard, no vendor holding your traces. The CLI runs where your
    code already runs, and the whole workspace is text a reviewer reads in a pull request.</p>
  </div>
  <div class="panel">
    <h3>It runs with no API key</h3>
    <p>The default judge is deterministic — token overlap against expected facts and retrieved
    context. Real models are one config line away, but you can see the entire product work before
    spending anything.</p>
  </div>
</div>

<h2>Where it is today</h2>

<p>M0 through M4 are done: the full loop runs, with @@live@@ of @@total@@ commands live. Production
connectors, scheduling and unattended operation are next. The
<a href="@@blob@@/TRACKER.md">work tracker</a> is the current state, and
<a href="@@blob@@/DECISIONS.md">DECISIONS.md</a> records the calls that got made and why.</p>

<div class="callout warn">
  <span class="k">Pre-alpha</span>
  <p>Version @@version@@. The workspace format and the CLI surface are still moving. The exit codes
  are the part that is meant to be stable — they are a public contract and are never renumbered.</p>
</div>
"""

QUICKSTART = """
<div class="eyebrow">Quickstart</div>
<h1>The whole loop, in about a minute</h1>
<p class="lede">No API key, no network, no model. The default judge is deterministic, so every number
below reproduces exactly on your machine.</p>

<h2>1. Install</h2>
<p><a href="https://docs.astral.sh/uv/">uv</a> is the only prerequisite — it fetches the interpreter
itself, so no system Python is involved and nothing is installed globally.</p>
<pre><code>curl -LsSf https://astral.sh/uv/install.sh | sh   <span class="c"># if you don't have it</span>

git clone @@repo@@.git langchef
cd langchef
uv sync
uv run langchef doctor</code></pre>

<p>A green <code>doctor</code> means the interpreter is the pinned one, an expertise pack resolves,
and no provider credential is sitting in your environment. That last check passes on
<em>absence</em>: the test suite replays deterministic judgements, so a key in the environment means
a test could quietly start spending money.</p>

<h2>2. See it work on a known-broken app</h2>
<p>The repository ships a small retrieval app whose failures were planted deliberately, so you can
check the harness against answers that are known in advance.</p>
<pre><code>uv run python -m dogfood.build          <span class="c"># corpus, goldens, ground-truth labels</span>
uv run pytest tests/test_dogfood.py -v  <span class="c"># the self-test</span></code></pre>

<h2>3. Run it on your own application</h2>
<pre><code>cd your-project
langchef init</code></pre>
<p>That scaffolds <code>evals/</code> — configuration, a starter rubric, and directories for goldens,
labels, runs, baselines, memos and the ledger. Add your examples as JSONL under
<code>evals/goldens/</code>, one object per line:</p>
<pre><code>{"example_id": "q-001",
 "question": "What are the payment terms?",
 "answer": "Payment terms are net thirty days.",
 "context": ["Payment terms on every invoice are net thirty days."],
 "expected": "net thirty days",
 "slices": {"topic": "billing"}}</code></pre>

<h2>4. Open gate one</h2>
<p>Nothing runs until a person has read the rubric and signed it off. This is not a formality — it is
the mechanism, and it is enforced by the CLI rather than by a prompt.</p>
<pre><code>$ langchef judge run
langchef: <span class="r">refused</span> — an approval gate is unmet — no rubric approved yet —
review it, then run: langchef approve rubric answer-quality

$ langchef approve rubric
approved answer-quality@290335165c70
  - Correctness
  - Groundedness
  - Directness</code></pre>
<p>Editing the rubric afterwards changes its hash and revokes the approval automatically. There is no
separate revocation step because none is needed.</p>

<h2>5. Score, label, calibrate</h2>
<pre><code>langchef judge run --arm baseline
langchef label plan --budget 40
<span class="c"># a person fills in the verdicts in evals/labels/&lt;rubric&gt;.todo.jsonl</span>
langchef label import evals/labels/answer-quality.todo.jsonl
langchef calibrate report</code></pre>
<pre><code>calibration for base on 40 labelled example(s)
  kappa      0.68  0.44..0.92
  TPR        80.0%  (12/15)
  FPR        12.0%
  disagreed  6 ({'false_alarm': 3, 'miss': 3})</code></pre>
<p>The plan is stratified by the judge's own verdict, not sampled at random. On a suite where the
judge flags 17% of examples, random sampling spends most of a labelling budget confirming passes and
leaves the true-positive rate resting on a handful of cases.</p>

<h2>6. Compare and write it up</h2>
<pre><code>langchef baseline set
langchef judge run --arm variant
langchef compare
langchef memo render</code></pre>
<p>The memo leads with whether the judge can be trusted, then the result, then what the run could not
rule out. Every figure in it traces to a file under <code>runs/</code>.</p>

<h2>7. Hand it to the agent</h2>
<p>The Claude Code adapter ships the calibration playbook as a skill and two commands that drive the
CLI. The gates stay in the CLI, so they hold whether or not the agent reads the skill.</p>
<pre><code>claude plugin install ./adapters/claude-code</code></pre>
"""

CONCEPTS = """
<div class="eyebrow">Concepts</div>
<h1>Five ideas the rest of it rests on</h1>
<p class="lede">Read this once and the command reference explains itself.</p>

<h2>A judge is an instrument, not a metric</h2>
<p>An eval suite built on an uncalibrated judge produces confident garbage, and no downstream
statistic repairs it. So calibration comes first, and it is reported as agreement with a person —
not accuracy.</p>
<p>Accuracy flatters every judge on a skewed suite: if 95% of outputs are fine, a judge that never
flags anything is 95% accurate and worthless. Cohen's κ removes the agreement you would get by
chance, which is why the thresholds are written against it.</p>
<div class="scroller"><table>
<thead><tr><th>κ</th><th>Reading</th><th>What to do</th></tr></thead>
<tbody>
<tr><td class="num">≥ 0.8</td><td>strong</td><td>downstream numbers can be trusted</td></tr>
<tr><td class="num">0.6–0.8</td><td>usable</td><td>report findings, quote the interval alongside</td></tr>
<tr><td class="num">0.4–0.6</td><td>weak</td><td>fix the rubric before running experiments on it</td></tr>
<tr><td class="num">&lt; 0.4</td><td>not usable</td><td>say so; do not report a pass rate as if it meant something</td></tr>
</tbody></table></div>

<h2>The pin is what makes two runs comparable</h2>
<p>Every run records the rubric hash, the provider and both model slots. Comparing two runs whose
pins disagree is not a comparison — it is two different measurements — so
<code>langchef compare</code> exits <code>5</code> and names the field that moved rather than
rendering a chart of them.</p>
<p>The rubric is a hashed Markdown file for exactly this reason. Editing one word changes the hash,
which invalidates every cached judgement it produced and revokes its approval. That is what stops a
suite silently mixing verdicts from two different definitions of “good” — the most common way an
eval suite starts lying.</p>

<h2>Gates are exit codes</h2>
<p>A model asked nicely not to read out an experiment early will, eventually, read one out early. So
the refusals are not requests.</p>
<div class="scroller"><table>
<thead><tr><th>Code</th><th>Meaning</th><th>Status</th></tr></thead>
<tbody>
@@exits@@
</tbody></table></div>
<div class="callout">
  <span class="k">For agents</span>
  <p>Exit <code>2</code> means stop and ask a person. It never means find another way — editing the
  approval in <code>config.toml</code> yourself is forging a signature, and the skill shipped in the
  Claude Code adapter says so in as many words.</p>
</div>

<h2>The comparison is paired</h2>
<p>Both arms score the same goldens, so the pairs are the unit: exact McNemar over the discordant
pairs, not a two-sample proportion test. If 200 goldens pass under both arms and 3 flip, the evidence
is in the 3. Treating the arms as independent throws the pairing away and inflates the variance, so
real regressions come back “not significant”.</p>
<p>Every inconclusive result carries a <strong>minimum detectable effect</strong>, computed from the
discordant rate rather than the pass rate, because that is what carries the information under
McNemar. “No significant difference” is not a finding. “No difference we could see, and this run
could not have resolved anything under six points” is.</p>

<h2>The output is a memo, not a leaderboard</h2>
<p>A leaderboard shows which variant is ahead today. It hides the two things that decide whether the
number means anything: how well the judge agreed with a person when it was last checked, and what was
decided last time.</p>
<p>So the artifact is a decision memo whose first section is whether the judge can be trusted, and the
persistent record is an append-only ledger. Entries are never edited — a correction is a new entry,
so what was believed at the time survives, which is what makes a post-mortem possible.</p>

<h2>Two streams, always</h2>
<p>JSON to stdout for the agent, prose to stderr for you. There is no <code>--format</code> flag;
<code>--help</code> is the single exception, because it is written for people. Neither mode is an
afterthought bolted onto the other.</p>
<pre><code>langchef doctor              <span class="c"># you read this</span>
langchef doctor 2&gt;/dev/null  <span class="c"># the agent parses this</span></code></pre>

<h2>The rules, verbatim</h2>
<p>These ship inside the binary and an agent reads them at runtime with
<code>langchef contract</code>:</p>
<ol>
@@rules@@
</ol>
"""

CLI = """
<div class="eyebrow">Reference</div>
<h1>Commands</h1>
<p class="lede">Generated from the contract inside the binary, so this table cannot claim a command
that does not exist. @@live@@ of @@total@@ are live today.</p>

<div class="callout">
  <span class="k">Determinism</span>
  <p><code>deterministic</code> — same inputs, same output, always.
  <code>seeded</code> — random but reproducible from a recorded seed.
  <code>cached</code> — results are keyed on content, rubric hash and model pin, so a rerun is free
  and reproducible.</p>
</div>

<div class="scroller"><table>
<thead><tr><th>Command</th><th>Summary</th><th>Determinism</th><th>Writes</th><th>Status</th></tr></thead>
<tbody>
@@commands@@
</tbody></table></div>

<h2>Exit codes</h2>
<div class="scroller"><table>
<thead><tr><th>Code</th><th>Meaning</th><th>Status</th></tr></thead>
<tbody>
@@exits@@
</tbody></table></div>

<h2>Global behaviour</h2>
<ul>
  <li>Every command writes one JSON document to stdout and its narration to stderr.</li>
  <li>Workspace commands search upward for <code>evals/config.toml</code>, the way git finds a
  repository — so they work from anywhere in your tree.</li>
  <li><code>--suite</code> may be omitted when the workspace has exactly one.</li>
  <li>Arms live in per-arm golden files: <code>goldens/&lt;suite&gt;.&lt;arm&gt;.jsonl</code>,
  falling back to <code>goldens/&lt;suite&gt;.jsonl</code>.</li>
</ul>

<p>The machine-readable copy of all of this is
<a href="AGENT-CONTRACT.md">docs/AGENT-CONTRACT.md</a>, or
<code>langchef contract</code> at runtime.</p>
"""


def fill(template: str, values: dict) -> str:
    """Substitute @@name@@ tokens.

    Not %-formatting and not str.format: the prose is full of literal percent
    signs and the code samples are full of braces, and both would need escaping
    everywhere a number or a JSON example appears.
    """
    text = template
    for key, value in values.items():
        text = text.replace(f"@@{key}@@", str(value))
    left = re.findall(r"@@(\w+)@@", text)
    if left:
        raise KeyError(f"unfilled token(s): {sorted(set(left))}")
    return text


def build() -> dict[str, str]:
    live = sum(1 for c in COMMANDS if c.implemented)
    total = len(COMMANDS)
    common = {"repo": REPO, "blob": BLOB, "live": live, "total": total, "version": __version__}

    rules = "\n".join(f"  <li>{html.escape(rule)}</li>" for rule in RULES)

    return {
        "index.html": shell(
            "index.html",
            "LangChef",
            fill(INDEX, common),
            "An installed eval engineer: a scheduled agent that calibrates your judge, runs the "
            "experiment and writes the memo, on infrastructure you already own.",
        ),
        "quickstart.html": shell(
            "quickstart.html",
            "Quickstart — LangChef",
            fill(QUICKSTART, common),
            "Install LangChef and run the whole evaluation loop in about a minute, with no API key.",
        ),
        "concepts.html": shell(
            "concepts.html",
            "Concepts — LangChef",
            fill(CONCEPTS, {**common, "exits": exit_rows(), "rules": rules}),
            "Judge calibration, measurement pins, approval gates as exit codes, paired comparison, "
            "and why the output is a memo rather than a leaderboard.",
        ),
        "cli.html": shell(
            "cli.html",
            "Commands — LangChef",
            fill(CLI, {**common, "commands": command_rows(), "exits": exit_rows()}),
            "Every LangChef command, generated from the agent contract in the binary.",
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the committed site is stale.")
    args = parser.parse_args()

    pages = build()
    pages[".nojekyll"] = ""

    stale = [
        name
        for name, text in pages.items()
        if not (SITE / name).is_file() or (SITE / name).read_text(encoding="utf-8") != text
    ]
    if args.check:
        if stale:
            print(f"stale: {', '.join(sorted(stale))} — run scripts/build_docs.py", file=sys.stderr)
            return 1
        print("ok: documentation site is up to date")
        return 0

    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8")
    print(f"wrote {len(pages)} file(s) to docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
