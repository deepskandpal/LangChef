#!/usr/bin/env python3
"""Render the documentation site into docs/, for GitHub Pages.

The command reference is generated from ``langchef.core.contract`` rather than
written by hand, for the same reason ``docs/AGENT-CONTRACT.md`` is: a docs page
that claims a command exists when it does not is worse than no page. ``--check``
fails if the committed site is stale, which is how CI keeps it honest.

No build tooling and no third-party dependency — the site is four static pages
and one stylesheet, which is the right amount of machinery for a project whose
whole claim is that text is the record.

The prose is written for a senior engineer who maintains an LLM feature and has
no evaluation background: worked example before the general rule, plain words
before the textbook name. If a page cannot be followed without already knowing
what calibration is, it has failed.
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
from langchef.core.contract import COMMANDS  # noqa: E402
from langchef.core.exits import REASON, Exit  # noqa: E402

REPO = "https://github.com/deepskandpal/LangChef"
BLOB = f"{REPO}/blob/main"

PAGES = (
    ("index.html", "Overview"),
    ("start.html", "Start here"),
    ("numbers.html", "Reading the output"),
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
    <li><a href="start.html">Your first evaluation</a></li>
    <li><a href="numbers.html">Reading the output</a></li>
    <li><a href="cli.html">Command reference</a></li>
  </ul>
  <h4>In the repository</h4>
  <ul>
    <li><a href="{BLOB}/docs/AGENT-CONTRACT.md">Agent contract</a></li>
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
  <div class="eyebrow">Evaluation for teams without an evaluation team</div>
  <h1>You changed the prompt. Is the app better or worse?</h1>
  <p class="lede">Most teams shipping an LLM feature cannot answer that with a straight face.
  LangChef is a command-line tool that answers it properly — and, just as often, tells you honestly
  that your test set cannot.</p>
  <div class="cta">
    <a class="btn solid" href="start.html">Your first evaluation</a>
    <a class="btn ghost" href="@@repo@@">View source</a>
  </div>
</div>

<h2>The situation</h2>

<p>You maintain something built on a model. Retrieval-augmented search over your own documents, a
support-ticket classifier, a summariser inside a bigger product. It works. Then somebody bumps the
chunk size, or a model version moves under you, or a prompt gets tightened to fix one complaint —
and the question is always the same one.</p>

<p>Today that question usually gets answered in one of three ways:</p>

<ul>
  <li><strong>Someone eyeballs twenty outputs.</strong> Fast, and it does catch obvious breakage. It
  cannot see a five-point regression, and nobody claims otherwise.</li>
  <li><strong>A pass rate in a spreadsheet</strong>, produced by asking a model to grade the outputs.
  Better — and the source of the two most common mistakes in this whole field, below.</li>
  <li><strong>Nobody checks.</strong> This is the most common answer. Roughly a third of teams
  running AI in production evaluate it on live traffic at all.</li>
</ul>

<p>None of this is a tooling problem. There are half a dozen capable evaluation platforms and
several are free. What is missing is the <em>person</em> — someone who knows whether your grader can
be trusted, how many examples you need before a number means anything, and whether a three-point
drop is a regression or noise. Below a certain size that person does not exist and cannot be
justified as a hire. LangChef is meant to stand in for them.</p>

<h2>Three ways this goes wrong</h2>

<h3>1. The grader nobody graded</h3>

<p>Say you ask a model to mark each answer good or bad, and it marks 95% of them good. That sounds
like a healthy system.</p>

<p>Now suppose only 5% of your answers are genuinely bad. A grader that blindly marks
<em>everything</em> good also scores 95%. From that number alone you cannot tell the two apart — and
one of them is worthless.</p>

<div class="callout">
  <span class="k">The general version</span>
  <p>An LLM judge is a measuring instrument, and almost nobody checks it against a human before
  trusting what it measures. Every number downstream inherits whatever it gets wrong.</p>
</div>

<p><strong>What LangChef does:</strong> asks you to label about forty examples yourself, once. Then
it tells you in plain words whether the grader agrees with you more than luck would explain, how
often it misses real problems, how often it cries wolf — and which kinds of answers it gets wrong.
If the grader is not good enough to build on, you find out before you build on it.</p>

<h3>2. The difference that isn't there</h3>

<p>Your pass rate was 83%. After the change it is 80%. Regression?</p>

<p>On ninety test cases: you cannot tell. A swing that size is comfortably inside what randomness
produces when nothing has changed at all. But nothing in a spreadsheet says so. The number moved,
somebody has to make a call, and the call gets made on a feeling.</p>

<div class="callout">
  <span class="k">The general version</span>
  <p>A small test set cannot resolve a small difference. The honest response to "did it get worse"
  is sometimes "this test set could never have told you".</p>
</div>

<p><strong>What LangChef does:</strong> returns one of three answers — <strong>regression</strong>,
<strong>improvement</strong>, or <strong>can't tell</strong> — with the range the true difference
probably sits in. When the answer is "can't tell", it also tells you the smallest change this test
set <em>could</em> have caught, so you know whether to add examples or move on.</p>

<h3>3. The ruler that moved</h3>

<p>You tightened the grading prompt on Tuesday. Monday's run scored 83%, Wednesday's scored 88%.
Plotted together, that looks like progress.</p>

<p>It isn't a comparison at all. You changed the instrument between the two readings, so the two
numbers were never measuring the same thing — but nothing stops them lining up on a chart.</p>

<div class="callout">
  <span class="k">The general version</span>
  <p>Two measurements are only comparable if the thing doing the measuring held still.</p>
</div>

<p><strong>What LangChef does:</strong> records exactly which rubric and which model produced every
number, and <em>refuses</em> to compare two runs that were measured differently. It stops with an
error instead of drawing the chart.</p>

<h2>The vocabulary, once</h2>

<p>Five words that the rest of these docs use. If you already know them, skip ahead.</p>

<div class="scroller"><table>
<thead><tr><th>Word</th><th>What it means here</th></tr></thead>
<tbody>
<tr><td><strong>Example</strong></td><td>One question your app was asked, the answer it gave, and what it retrieved to answer it. Also called a <em>golden</em>. You need 50–100.</td></tr>
<tr><td><strong>Rubric</strong></td><td>What "a good answer" means, written down. Roughly what you'd tell a new teammate on their first day. It's a Markdown file you review like code.</td></tr>
<tr><td><strong>Judge</strong></td><td>The thing that reads an answer and says pass or fail. Usually a model with your rubric in the prompt. Sometimes just string matching.</td></tr>
<tr><td><strong>Label</strong></td><td>Your own verdict on an example — pass or fail — recorded by hand. The ground truth the judge is checked against.</td></tr>
<tr><td><strong>Calibration</strong></td><td>Comparing the judge's verdicts to your labels to find out how much the judge can be trusted.</td></tr>
</tbody></table></div>

<p>Two more that show up in output: a <strong>run</strong> is one scoring pass over your examples,
and an <strong>arm</strong> is which version produced them — usually <code>baseline</code> against
whatever you changed.</p>

<h2>What you get back</h2>

<div class="grid2">
  <div class="panel">
    <h3>A verdict you can act on</h3>
    <p>Regression, improvement, or can't-tell — with a range, and with the size of the smallest
    change this run could have detected. Never a bare number with no error bars.</p>
  </div>
  <div class="panel">
    <h3>A memo, not a dashboard</h3>
    <p>One page that opens with whether the judge can be trusted, then the result, then what the run
    could <em>not</em> rule out. Every figure traces to a file on disk.</p>
  </div>
  <div class="panel">
    <h3>A record that accumulates</h3>
    <p>An append-only log of every run, calibration and decision. Six months later you can see what
    was believed at the time and why a call was made.</p>
  </div>
  <div class="panel">
    <h3>Nothing leaves your machine</h3>
    <p>No hosted service, no vendor holding your traces, no account. It runs where your code runs,
    on your keys, and the whole workspace is text you review in a pull request.</p>
  </div>
</div>

<h2>What this is not</h2>

<ul>
  <li><strong>Not a benchmark suite.</strong> It does not ship test cases. Your examples come from
  your traffic, because a benchmark of somebody else's questions tells you nothing about yours.</li>
  <li><strong>Not a dashboard.</strong> There is no UI and no hosted anything.</li>
  <li><strong>Not a replacement for reading your outputs.</strong> It tells you whether a change
  moved the needle; it will not tell you what to build next.</li>
  <li><strong>Not magic about labels.</strong> Somebody has to say what good means and mark forty
  examples once. There is no way around that, and anyone claiming otherwise is selling you a judge
  nobody checked.</li>
</ul>

<h2>Is this for you?</h2>

<p><strong>Probably yes</strong> if you maintain an LLM feature in production, you have no
evaluation engineer, and you can spare an afternoon once plus about ten minutes per change.</p>

<p><strong>Probably not</strong> if you already have an eval team and a calibrated judge — you have
solved this — or if your feature is still changing shape weekly, in which case come back when it
settles.</p>

<div class="callout warn">
  <span class="k">Pre-alpha — version @@version@@</span>
  <p>@@live@@ of @@total@@ commands are live. The workspace format and the command surface are still
  moving; the exit codes are the part meant to be stable. See the
  <a href="@@blob@@/TRACKER.md">work tracker</a> for what is done and what is open.</p>
</div>
"""

START = """
<div class="eyebrow">Start here</div>
<h1>Your first evaluation</h1>
<p class="lede">A worked example, start to finish. About forty-five minutes the first time, most of
it spent labelling. Ten minutes per change after that.</p>

<div class="callout">
  <span class="k">The scenario</span>
  <p>Your support assistant answers customer questions from your help centre. You want to retrieve
  five document chunks instead of three, because someone thinks answers are getting cut short. Does
  that actually help?</p>
</div>

<h2>Install — 2 minutes</h2>

<p><a href="https://docs.astral.sh/uv/">uv</a> is the only prerequisite. It fetches its own Python,
so nothing is installed globally and no system package is touched.</p>

<pre><code>curl -LsSf https://astral.sh/uv/install.sh | sh   <span class="c"># if you don't have it</span>

git clone @@repo@@.git langchef
cd langchef
uv sync
uv run langchef doctor</code></pre>

<p>Want to see the whole thing work before pointing it at your own app? The repository ships a small
search app with faults deliberately planted in it, so you can watch the tool find them:</p>

<pre><code>uv run python -m dogfood.build
uv run pytest tests/test_dogfood.py -v</code></pre>

<h2>Step 1 — Collect examples · 10 minutes</h2>

<p>An example is one question, the answer your app gave, and the context it retrieved. Pull 50–100
from your logs. Real questions, not invented ones — invented questions are always easier than the
ones users actually ask.</p>

<pre><code>cd your-project
langchef init</code></pre>

<p>That creates an <code>evals/</code> directory. Put your examples in
<code>evals/goldens/support.baseline.jsonl</code>, one JSON object per line:</p>

<pre><code>{"example_id": "q-001",
 "question": "How long do refunds take?",
 "answer": "Refunds are issued within ten working days of the parcel arriving back.",
 "context": ["Refunds are issued within ten working days of the parcel arriving back."],
 "expected": "ten working days",
 "slices": {"topic": "returns"}}</code></pre>

<p><code>expected</code> is the fact a correct answer has to contain — you know this because you
picked the question. <code>slices</code> are optional tags; they are how the tool later tells you
"this only breaks on billing questions".</p>

<h2>Step 2 — Say what "good" means · 10 minutes</h2>

<p><code>langchef init</code> wrote a starter rubric at
<code>evals/rubrics/answer-quality.md</code>. Open it and make it yours. It is Markdown, each
<code>###</code> heading is one criterion, and the judge has to name the criterion it failed on:</p>

<pre><code>### Correctness

The answer states the fact the question asked for. An answer that is
merely adjacent to the right topic fails this criterion.

### Groundedness

Every claim is supported by the retrieved context. An answer that is
correct but not present in the context still fails: on a retrieval
system that is a lucky guess, and it will not stay lucky.

### Directness

The answer answers. Hedging into uselessness when the context contains
the answer fails here.</code></pre>

<p>This is the highest-leverage twenty minutes in the whole process. A vague rubric produces a vague
judge, and no amount of statistics downstream repairs that.</p>

<h2>Step 3 — Sign it off · 10 seconds</h2>

<p>Nothing will run until a person has read the rubric and approved it:</p>

<pre><code>$ langchef judge run --arm baseline
langchef: <span class="r">refused</span> — an approval gate is unmet — no rubric approved yet

$ langchef approve rubric
approved answer-quality@290335165c70
  - Correctness
  - Groundedness
  - Directness</code></pre>

<p>That hash is the point. If you edit the rubric later, the hash changes, the approval lapses
automatically, and the next run stops until you re-read it. This is what prevents trap three — the
ruler moving without anyone noticing.</p>

<h2>Step 4 — Score them · 30 seconds</h2>

<pre><code>$ langchef judge run --arm baseline
judge: n=90  provider_calls=90  pass=75  fail=15</code></pre>

<p>Out of the box this uses a judge that needs no API key and no network — it checks whether the
expected fact is present, whether the answer is grounded in the retrieved context, and whether it
hedged. It is a real technique and a reasonable starting point, and it has a real weakness you are
about to discover in step 6.</p>

<p>To use a real model instead, set two lines in <code>evals/config.toml</code>:</p>

<pre><code>[judge]
provider = "litellm"
cheap_model = "anthropic/claude-haiku-4-5"
strong_model = "anthropic/claude-sonnet-5"   <span class="c"># re-scores only the unsure cases</span></code></pre>

<h2>Step 5 — Label forty yourself · 20 minutes</h2>

<p>This is the only manual work, and it is not optional. It is the <em>only</em> way to find out
whether the judge is worth anything.</p>

<pre><code>$ langchef label plan --budget 40
40 of 90 examples planned for labelling
  by stratum: {'fail': 15, 'pass': 25}
  -&gt; evals/labels/answer-quality.todo.jsonl</code></pre>

<p>It does not pick forty at random. It takes every example the judge flagged plus a sample of the
ones it passed, because a random sample of a suite with a 17% failure rate spends most of your
attention confirming things that were already fine.</p>

<p>Open that file, read each answer, and set <code>"verdict"</code> to <code>"pass"</code> or
<code>"fail"</code> — your honest opinion, not what you think the judge said. Then:</p>

<pre><code>langchef label import evals/labels/answer-quality.todo.jsonl</code></pre>

<h2>Step 6 — Find out if your judge is any good · 5 seconds</h2>

<pre><code>$ langchef calibrate report
calibration for base on 40 labelled example(s)
  kappa      0.68  0.44..0.92
  TPR        80.0%  (12/15)
  FPR        12.0%
  disagreed  6 ({'false_alarm': 3, 'miss': 3})</code></pre>

<p>In plain words: <strong>this judge is usable but not great.</strong> It caught 12 of the 15
problems you found, cried wolf on 12% of the good answers, and agrees with you meaningfully more
than chance would explain. <a href="numbers.html">Reading the output</a> decodes each of those lines
properly, including what to do when the number is bad.</p>

<p>If agreement had come back below 0.4, the correct move is to stop, fix the rubric, and try again
— not to carry on and report pass rates from a judge that disagrees with you.</p>

<h2>Step 7 — Make the change and compare · 1 minute</h2>

<pre><code>langchef baseline set                       <span class="c"># pin what you have as the reference</span>

<span class="c"># now switch retrieval to top-5, regenerate answers into</span>
<span class="c"># evals/goldens/support.top-5.jsonl, then:</span>

langchef judge run --arm top-5
langchef compare --variant support-top-5</code></pre>

<p>One of three things comes back.</p>

<pre><code>  baseline 83.3%   variant 63.3%
  difference -20.0% [-27.8%, -12.2%]  p=0.0000
  <span class="r">REGRESSION</span></code></pre>
<p>It broke something. The range says the true damage is somewhere between 12 and 28 points.</p>

<pre><code>  difference +0.0% [+0.0%, +0.0%]  p=1.0000
  <span class="o">INCONCLUSIVE</span>
  (smallest effect this run could have seen: 6.0%)</code></pre>
<p>This is the one people misread. It does <em>not</em> mean the change was safe. It means ninety
examples could never have detected anything smaller than a six-point swing, so if your change moved
things by three points, this run was always going to shrug. Add examples, or accept that you are not
going to resolve a change this small.</p>

<h2>Step 8 — Write it up · 5 seconds</h2>

<pre><code>langchef memo render</code></pre>

<p>A one-page Markdown memo in <code>evals/memos/</code>. It opens with whether the judge can be
trusted, because a confident result from an unchecked judge is worse than no result. Then the
finding, then what the run could not rule out. Commit it next to the change it justifies.</p>

<h2>After the first time</h2>

<p>Steps 1–6 are setup. From then on, each change costs you two commands and about a minute:</p>

<pre><code>langchef judge run --arm my-change
langchef compare --variant support-my-change</code></pre>

<p>Re-label every month or so, or whenever you touch the rubric — the judge's trustworthiness drifts
as your traffic changes, and the tool will keep quoting the last calibration until you refresh it.</p>

<h2>Handing it to an agent</h2>

<p>If you use Claude Code, the adapter ships the whole playbook above as a skill, so the agent runs
the loop and reads the results the way this page describes:</p>

<pre><code>claude plugin install ./adapters/claude-code</code></pre>

<p>The approval gate stays in the CLI rather than in the prompt, so it holds whether or not the
agent cooperates.</p>
"""

NUMBERS = """
<div class="eyebrow">Reading the output</div>
<h1>What every number means</h1>
<p class="lede">Plain English first, the textbook name second. You do not need any of this to use the
tool — it is here for when a number looks wrong and you want to know what it is telling you.</p>

<h2>Can this judge be trusted?</h2>

<pre><code>calibration for base on 40 labelled example(s)
  kappa      0.68  0.44..0.92
  TPR        80.0%  (12/15)
  FPR        12.0%
  disagreed  6 ({'false_alarm': 3, 'miss': 3})</code></pre>

<h3>Agreement — the <code>kappa</code> line</h3>

<p><strong>How much the judge agrees with you, after subtracting the agreement you would get by
luck.</strong> Runs from 0 (no better than guessing) to 1 (perfect).</p>

<p>Why not just "it agreed with me 90% of the time"? Because on a suite where 95% of answers are
fine, a judge that says "fine" to everything agrees with you 95% of the time and is worthless. This
number sees through that; a raw percentage does not.</p>

<div class="scroller"><table>
<thead><tr><th>Agreement</th><th>Reading</th><th>What to do</th></tr></thead>
<tbody>
<tr><td class="num">0.8 and up</td><td>strong</td><td>Trust the results downstream.</td></tr>
<tr><td class="num">0.6 – 0.8</td><td>usable</td><td>Fine to act on. Quote the range alongside any finding.</td></tr>
<tr><td class="num">0.4 – 0.6</td><td>weak</td><td>Fix the rubric before running experiments on it.</td></tr>
<tr><td class="num">below 0.4</td><td>not usable</td><td>Stop. Do not report pass rates from this judge.</td></tr>
</tbody></table></div>

<p class="dim"><em>Textbook name: Cohen's κ.</em></p>

<h3>Catch rate — the <code>TPR</code> line</h3>

<p><strong>Of the problems you found by hand, how many did the judge also flag?</strong> Here, 12 of
the 15. The other three shipped past it.</p>

<p>The counts matter as much as the percentage: "80%" reads like a solid measurement until you see
it rests on fifteen examples. That is why the tool always prints <code>(12/15)</code> next to it.</p>

<p class="dim"><em>Textbook name: true positive rate, or recall.</em></p>

<h3>False alarm rate — the <code>FPR</code> line</h3>

<p><strong>Of the answers that were actually fine, how many did the judge flag anyway?</strong> Every
one of these is somebody investigating a non-problem. A judge with a high false alarm rate gets
ignored within about two weeks, which is worse than having no judge.</p>

<p class="dim"><em>Textbook name: false positive rate.</em></p>

<h3>The range after each number</h3>

<p><code>0.44..0.92</code> is not decoration. It is the honest width of what forty labels can tell
you: the true agreement is probably somewhere in there. <strong>A wide range means "label more
examples", not "the judge is inconsistent".</strong></p>

<p class="dim"><em>Textbook name: a 95% confidence interval — Wilson for rates, asymptotic for
agreement.</em></p>

<h3>Where it disagreed</h3>

<p>The report also groups the disagreements: which rubric criterion the judge cited when it was
wrong, and whether any slice of your traffic is worse than the rest. A line like
<code>topic=returns disagrees 33% of the time against a 15% base rate</code> is the actionable form
of "the judge is unreliable".</p>

<div class="callout">
  <span class="k">Watch for "separated": false</span>
  <p>A slice can look twice as bad as average and still be marked <code>separated: false</code>. That
  means the finding rests on too few examples to distinguish from ordinary variation, and the memo
  deliberately leaves it out rather than sending you to chase noise.</p>
</div>

<h2>Did the change help?</h2>

<pre><code>base -&gt; variant on 90 shared golden(s)
  baseline 83.3%   variant 63.3%
  difference -20.0% [-27.8%, -12.2%]  p=0.0000
  REGRESSION</code></pre>

<h3>The verdict</h3>

<div class="scroller"><table>
<thead><tr><th>Verdict</th><th>Means</th></tr></thead>
<tbody>
<tr><td><strong>REGRESSION</strong></td><td>The change made things worse, and the evidence is strong enough to act on.</td></tr>
<tr><td><strong>IMPROVEMENT</strong></td><td>The change made things better, same standard of evidence.</td></tr>
<tr><td><strong>INCONCLUSIVE</strong></td><td>This test set cannot tell the two versions apart. <strong>Not the same as "no difference".</strong></td></tr>
</tbody></table></div>

<h3>The difference, and its range</h3>

<p><code>-20.0% [-27.8%, -12.2%]</code> — the pass rate dropped twenty points, and the true drop is
probably between twelve and twenty-eight. The verdict is decided by the range, not the p-value: a
direction only counts when the whole range agrees with it.</p>

<h3>How many examples actually changed</h3>

<p>Both versions answered the same questions, so what matters is how many <em>flipped</em>. If 200
examples pass under both versions and 3 flip, the entire evidence is in those 3. The tool reports
that count, and everything is computed from it.</p>

<p class="dim"><em>Textbook name: discordant pairs, tested with an exact McNemar test. The pairing is
why this is not a two-sample proportion test — treating the arms as independent throws away the fact
that they answered identical questions, and real regressions then come back "not significant".</em></p>

<h3>The smallest change this run could have caught</h3>

<pre><code>  INCONCLUSIVE
  (smallest effect this run could have seen: 6.0%)</code></pre>

<p><strong>The single most useful number in the tool.</strong> It converts a shrug into a plan. Your
run could not have detected anything under six points — so if you were hoping to catch a two-point
regression, you need more examples, and no amount of re-reading this output will change that.</p>

<p>Roughly: to halve the smallest detectable change, you need about four times the examples.</p>

<p class="dim"><em>Textbook name: minimum detectable effect, computed from the flip rate rather than
the pass rate, because under a paired test that is what carries the information.</em></p>

<h2>Was this even a fair comparison?</h2>

<p>Every run records the rubric hash, the provider and the models that produced it. Together those
are the <strong>pin</strong> — the exact ruler used.</p>

<pre><code>$ langchef compare --variant later-run
langchef: <span class="r">pin mismatch</span> — rubric 'answer-quality@290335165c70'
-&gt; 'answer-quality@b12aabd7ee8e' — these are two measurements, not a
comparison. Re-run the older arm under the current pin.</code></pre>

<p>You edited the rubric between the runs, so the numbers were produced by different instruments.
The tool stops rather than drawing the chart. Re-score the older version under the current rubric
and compare again — the cache makes that cheap.</p>

<h2>When the tool refuses</h2>

<p>Refusals are exit codes, so a script or an agent cannot talk its way past them.</p>

<div class="scroller"><table>
<thead><tr><th>Code</th><th>What happened</th><th>What to do</th></tr></thead>
<tbody>
<tr><td class="num">0</td><td>Fine.</td><td>—</td></tr>
<tr><td class="num">1</td><td>Something is missing or malformed.</td><td>Read the message; it names the fix.</td></tr>
<tr><td class="num">2</td><td>Nobody has approved the rubric, or it changed since they did.</td><td>Read the rubric, then <code>langchef approve rubric</code>.</td></tr>
<tr><td class="num">5</td><td>The two runs were measured differently.</td><td>Re-run the older arm under the current pin.</td></tr>
</tbody></table></div>

<p>Codes <code>3</code> and <code>4</code> are reserved for abstention and spend caps and are not
emitted yet. The full table, generated from the binary, is on the
<a href="cli.html">commands page</a>.</p>

<div class="callout">
  <span class="k">If an agent is driving</span>
  <p>Exit 2 means stop and ask a person. It never means find another way round — editing the
  approval in <code>config.toml</code> is forging a signature, and the shipped Claude Code skill says
  so in as many words.</p>
</div>

<h2>The memo</h2>

<p><code>langchef memo render</code> assembles all of the above into one page, in a fixed order:
whether the judge can be trusted, then the result, then what the run could not rule out. That order
is deliberate. A confident result from an unchecked judge is worse than no result, so the trust
question is never an appendix.</p>
"""

CLI = """
<div class="eyebrow">Reference</div>
<h1>Commands</h1>
<p class="lede">Generated from the contract inside the binary, so this table cannot claim a command
that does not exist. @@live@@ of @@total@@ are live today. If you are here to learn the tool, start
with <a href="start.html">your first evaluation</a> instead.</p>

<h2>The ones you will actually use</h2>

<div class="scroller"><table>
<thead><tr><th>Command</th><th>When</th></tr></thead>
<tbody>
<tr><td class="mono">langchef init</td><td>Once, in your project.</td></tr>
<tr><td class="mono">langchef approve rubric</td><td>After you write or edit the rubric.</td></tr>
<tr><td class="mono">langchef judge run --arm X</td><td>Every time you want a version scored.</td></tr>
<tr><td class="mono">langchef label plan --budget 40</td><td>Once at the start, then monthly.</td></tr>
<tr><td class="mono">langchef label import FILE</td><td>After you have filled the plan in.</td></tr>
<tr><td class="mono">langchef calibrate report</td><td>After importing labels. Tells you if the judge is trustworthy.</td></tr>
<tr><td class="mono">langchef baseline set</td><td>Once you have a version worth comparing against.</td></tr>
<tr><td class="mono">langchef compare --variant X</td><td>The question you came here to answer.</td></tr>
<tr><td class="mono">langchef memo render</td><td>To write the decision down.</td></tr>
</tbody></table></div>

<h2>Everything, generated from the contract</h2>

<div class="callout">
  <span class="k">Determinism</span>
  <p><code>deterministic</code> — same inputs, same output, always.
  <code>seeded</code> — random but reproducible from a recorded seed.
  <code>cached</code> — results are keyed on content, rubric hash and model, so re-running an
  unchanged suite is free.</p>
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

<h2>Two streams</h2>

<p>Every command writes JSON to stdout for a program, and plain text to stderr for you. There is no
<code>--format</code> flag; <code>--help</code> is the one exception, because it is written for
people.</p>

<pre><code>langchef calibrate report              <span class="c"># you read this</span>
langchef calibrate report 2&gt;/dev/null  <span class="c"># a script parses this</span></code></pre>

<h2>Other behaviour worth knowing</h2>

<ul>
  <li>Workspace commands search upward for <code>evals/config.toml</code>, the way git finds a
  repository, so they work from anywhere in your tree.</li>
  <li><code>--suite</code> can be omitted when there is only one.</li>
  <li>Each version's answers live in its own file:
  <code>goldens/&lt;suite&gt;.&lt;arm&gt;.jsonl</code>.</li>
  <li>The rules an agent reads at runtime are in
  <a href="@@blob@@/docs/AGENT-CONTRACT.md">docs/AGENT-CONTRACT.md</a>, or
  <code>langchef contract</code>.</li>
</ul>
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

    return {
        "index.html": shell(
            "index.html",
            "LangChef",
            fill(INDEX, common),
            "Find out whether a change to your LLM feature made it better or worse — and when your "
            "test set is too small to tell. For teams with no evaluation engineer.",
        ),
        "start.html": shell(
            "start.html",
            "Your first evaluation — LangChef",
            fill(START, common),
            "A worked example from install to verdict: collect examples, write the rubric, label "
            "forty, find out if your judge is trustworthy, then compare two versions.",
        ),
        "numbers.html": shell(
            "numbers.html",
            "Reading the output — LangChef",
            fill(NUMBERS, common),
            "Every number LangChef prints, in plain English: judge agreement, catch rate, false "
            "alarms, the verdict, and the smallest change your run could have detected.",
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
    obsolete = ["quickstart.html", "concepts.html"]

    stale = [
        name
        for name, text in pages.items()
        if not (SITE / name).is_file() or (SITE / name).read_text(encoding="utf-8") != text
    ]
    stale += [name for name in obsolete if (SITE / name).is_file()]
    if args.check:
        if stale:
            print(f"stale: {', '.join(sorted(stale))} — run scripts/build_docs.py", file=sys.stderr)
            return 1
        print("ok: documentation site is up to date")
        return 0

    SITE.mkdir(parents=True, exist_ok=True)
    for name, text in pages.items():
        (SITE / name).write_text(text, encoding="utf-8")
    # Pages that used to exist must be removed, or Pages keeps serving them.
    for name in obsolete:
        (SITE / name).unlink(missing_ok=True)
    print(f"wrote {len(pages)} file(s) to docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
