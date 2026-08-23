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
    ("integrations.html", "Integrations"),
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
    <li><a href="integrations.html">Integrations</a></li>
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


def integration_rows() -> str:
    pills = {
        "shipped": '<span class="pill yes">shipped</span>',
        "partial": '<span class="pill no">partial</span>',
        "next": '<span class="pill no">next up</span>',
        "planned": '<span class="pill no">planned</span>',
        "considering": '<span class="pill no">considering</span>',
    }
    return "\n".join(
        "<tr>"
        f"<td><strong>{html.escape(name)}</strong></td>"
        f"<td>{html.escape(kind)}</td>"
        f"<td>{pills[status]}</td>"
        f"<td>{detail}</td>"
        "</tr>"
        for name, kind, status, detail in INTEGRATIONS
    )


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
  <h1>Did that change make it better or worse?</h1>
  <p class="lede">Model swaps, retriever changes, fine-tunes. LangChef gives you a straight answer —
  or tells you your test set was never big enough to have one.</p>
  <div class="cta">
    <a class="btn solid" href="start.html">Your first evaluation</a>
    <a class="btn ghost" href="@@repo@@">View source</a>
  </div>
</div>

<h2>The situation</h2>

<p>You maintain a retrieval app, a classifier, or an agent that calls a few tools. It works. Then:</p>

<ul>
  <li>your provider <strong>retires the model you shipped on</strong> — you did not choose this, and
  you have weeks;</li>
  <li>you <strong>swap the embedding model</strong>, add a reranker, or change chunking, and
  retrieval shifts underneath the generator;</li>
  <li>you <strong>distil to a fine-tuned small model</strong> to cut the bill, where the question is
  not "is it better" but "did quality hold";</li>
  <li>you give an <strong>agent another tool</strong>, or someone edits a prompt.</li>
</ul>

<p>Same question every time, and it usually gets answered by eyeballing twenty outputs, or by a pass
rate in a spreadsheet that moved three points, or not at all — which is the most common answer, and
why only about a third of teams running AI in production evaluate it on live traffic.</p>

<p>This is not a tooling problem. Half a dozen capable eval platforms exist and several are free.
What is missing is the <em>person</em> who knows whether your grader can be trusted and how many
examples a number needs before it means anything. LangChef stands in for them.</p>

<h2>Four ways this goes wrong</h2>

<h3>The grader nobody graded</h3>
<p>Your judge marks 95% of answers good, which sounds healthy. If only 5% of your answers are
genuinely bad, a judge that marks <em>everything</em> good also scores 95% — and from that number
alone you cannot tell the two apart.</p>
<p class="answer"><strong>LangChef:</strong> you label forty examples once. It then reports whether
the judge agrees with you more than luck explains, how often it misses real problems, how often it
cries wolf, and which kinds of answer it gets wrong.</p>

<h3>The difference that isn't there</h3>
<p>83% to 80% on ninety examples. That swing is comfortably inside what randomness produces when
nothing changed — but the number moved, and somebody has to make a call.</p>
<p class="answer"><strong>LangChef:</strong> returns regression, improvement, or <em>can't tell</em>,
with the range the true difference sits in. When it can't tell, it says how small a change this test
set could ever have caught.</p>

<h3>The ruler that moved</h3>
<p>You tightened the grading prompt on Tuesday. Monday's 83% and Wednesday's 88% were never
measuring the same thing, but they still line up on a chart.</p>
<p class="answer"><strong>LangChef:</strong> records which rubric and model produced every number,
and refuses to compare two runs measured differently. It stops rather than drawing the chart.</p>

<h3>Not knowing which half broke</h3>
<p>Quality drops four points after an embedding swap. Is the generator worse, or is it being handed
worse context? Those have nothing in common as fixes, and one pass rate over both cannot separate
them.</p>
<p class="answer"><strong>LangChef:</strong> one rubric criterion per failure mode — grounding for
retrieval, correctness for generation — and the judge must name the one it failed on, so failures
stay attributable instead of pooled.</p>

<h2>You are the diner, not the chef</h2>

<p>The name is about who does the cooking. You say what you want in plain language. The harness —
Claude Code, or whatever agent your team already runs — takes the order and comes back with one or
two ways to test it. You pick one and agree what it may spend. The kitchen runs the sampling, the
judging and the statistics out of sight. What arrives is a dish and one question: <strong>is this
good enough to ship?</strong></p>

<p>That question is the only judgement the design asks of you, and it is the only one that does not
need an evaluation background. Everything before it — which metric, how many examples, whether the
judge can be trusted, whether the difference is real — is kitchen work.</p>

<div class="scroller"><table>
<thead><tr><th>In the restaurant</th><th>Here</th><th>Who does it</th></tr></thead>
<tbody>
<tr><td>"Paneer, and make it slightly spicy"</td><td>What "good" means for your app — the rubric</td><td>You, once</td></tr>
<tr><td>The kitchen learns your palate</td><td>Judge calibration against ~40 of your own labels</td><td>You taste, it learns</td></tr>
<tr><td>The waiter suggests a dish or two</td><td>One or two experiment designs</td><td>The harness</td></tr>
<tr><td>You order, and see the price</td><td>Approve the design and its budget, before any traffic</td><td>You</td></tr>
<tr><td>The kitchen cooks</td><td>Sampling, judging, statistics, comparison</td><td>The <code>langchef</code> CLI</td></tr>
<tr><td>The dish arrives</td><td>A decision memo</td><td>—</td></tr>
<tr><td>Do you like it?</td><td>Ship it, or don't</td><td>You</td></tr>
</tbody></table></div>

<div class="callout">
  <span class="k">And you are a regular, not a walk-in</span>
  <p>The part that matters is what happens when you are not in the room. Once the kitchen knows your
  palate it keeps watching — when your provider retires a model, when traffic drifts, when the judge
  starts disagreeing with you again, it notices on a schedule and tells you <em>before</em> you order
  something you will not like. A tool that only works when you are driving it is a tool you have to
  remember to drive.</p>
</div>

<h2>What you get back</h2>

<div class="grid2">
  <div class="panel">
    <h3>A verdict, with error bars</h3>
    <p>Regression, improvement, or can't-tell — never a bare number. Plus the smallest change the
    run could have detected, which turns a shrug into a plan.</p>
  </div>
  <div class="panel">
    <h3>An answer for "did quality hold"</h3>
    <p>Cutting cost with a small model isn't a hunt for an improvement. It's a check that the drop
    sits inside a tolerance you set first. <a href="numbers.html">How to read that</a>.</p>
  </div>
  <div class="panel">
    <h3>A memo, not a dashboard</h3>
    <p>One page that opens with whether the judge can be trusted, then the result, then what the run
    could not rule out. Every figure traces to a file on disk.</p>
  </div>
  <div class="panel">
    <h3>Nothing leaves your machine</h3>
    <p>No hosted service, no account, no vendor holding your traces. It runs where your code runs,
    and the workspace is text you review in a pull request.</p>
  </div>
</div>

<h2>What it is not, and who it is not for</h2>

<p>It ships no test cases — your examples come from your traffic, because a benchmark of someone
else's questions tells you nothing about yours. There is no UI. And somebody does have to say what
"good" means and mark forty examples: anyone promising otherwise is selling you a judge nobody
checked.</p>

<p>Skip it if you already have an eval team and a calibrated judge — you have solved this — or if
your feature is still changing shape weekly. Come back when it settles.</p>

<p>It does not replace the tools you already run. If your runs live in MLflow, they stay in MLflow;
LangChef is the thing that decides what to measure and whether the answer means anything. See
<a href="integrations.html">integrations</a>.</p>

<div class="callout warn">
  <span class="k">Pre-alpha — version @@version@@</span>
  <p>@@live@@ of @@total@@ commands are live. The workspace format and command surface still move;
  the exit codes are the part meant to be stable. The
  <a href="@@blob@@/TRACKER.md">tracker</a> has what is done and what is open.</p>
</div>
"""


START = """
<div class="eyebrow">Start here</div>
<h1>Your first evaluation</h1>
<p class="lede">A worked example, start to finish. About forty-five minutes the first time, most of
it spent labelling. Ten minutes per change after that.</p>

<div class="callout">
  <span class="k">The scenario</span>
  <p>Your support assistant answers customer questions from your help centre, retrieval-augmented
  over your docs. Your provider is retiring the model you shipped on, so you have to move to the
  replacement. Does answer quality hold?</p>
  <p>The same loop covers every other change in the stack — a new embedding model, different
  chunking, a reranker, a fine-tuned small model swapped in to cut the bill. Only the arm you
  compare against changes.</p>
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

<h2>Words used on this page</h2>

<div class="scroller"><table>
<thead><tr><th>Word</th><th>What it means here</th></tr></thead>
<tbody>
<tr><td><strong>Example</strong></td><td>One question your app was asked, the answer it gave, and what it retrieved. Also called a <em>golden</em>. You need 50–100.</td></tr>
<tr><td><strong>Rubric</strong></td><td>What "a good answer" means, written down — roughly what you'd tell a new teammate. A Markdown file you review like code.</td></tr>
<tr><td><strong>Judge</strong></td><td>The thing that reads an answer and says pass or fail. Usually a model with your rubric in the prompt.</td></tr>
<tr><td><strong>Label</strong></td><td>Your own verdict on an example. The ground truth the judge is checked against.</td></tr>
<tr><td><strong>Calibration</strong></td><td>Comparing the judge's verdicts to your labels, to find out how far it can be trusted.</td></tr>
<tr><td><strong>Arm</strong></td><td>One version of your app — usually <code>baseline</code> against the thing you changed.</td></tr>
</tbody></table></div>

<h2>Step 1 — Collect examples · 10 minutes</h2>

<p>An example is one question, the answer your app gave, and the context it retrieved. Pull 50–100
from your logs. Real questions, not invented ones — invented questions are always easier than the
ones users actually ask, and a model migration tends to break on exactly the awkward ones.</p>

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

<p>Notice what those three criteria are doing: <strong>one per failure mode, and they map onto the
stages of your pipeline.</strong> Correctness is the generator. Groundedness is retrieval — an
answer that is right but absent from the retrieved context means your index got lucky. Directness
catches the model refusing when the answer was sitting right there, which is the classic way a
smaller or newer model regresses.</p>

<p>Because the judge has to name the criterion it failed on, failures stay attributable instead of
pooling into one number. When the new model scores worse, you can see whether it is answering badly
or being handed bad context.</p>

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

<p>To use a real model as the judge instead, set a few lines in
<code>evals/config.toml</code>:</p>

<pre><code>[judge]
provider = "litellm"
cheap_model = "anthropic/claude-haiku-4-5"
strong_model = "anthropic/claude-sonnet-5"   <span class="c"># re-scores only the unsure cases</span></code></pre>

<p>Any provider litellm speaks works here. One rule worth keeping: <strong>do not judge a model with
itself.</strong> If you are migrating to a model, grading its answers with that same model measures
its self-consistency, not its quality — which is another reason step 6 exists.</p>

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

<pre><code>langchef baseline set                       <span class="c"># pin the model you're on today</span>

<span class="c"># re-answer the same questions on the replacement model, into</span>
<span class="c"># evals/goldens/support.new-model.jsonl, then:</span>

langchef judge run --arm new-model
langchef compare --variant support-new-model</code></pre>

<p>The questions must be identical across both arms — same <code>example_id</code>, different
answers. That pairing is what lets a small number of examples say anything at all.</p>

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

<p>Re-label every month or so, and whenever you touch the rubric or change the judge model — the
judge's trustworthiness drifts as your traffic changes, and the tool will keep quoting the last
calibration until you refresh it. If you are migrating the judge model itself, re-calibrate first:
you are changing the instrument, not the thing being measured.</p>

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

<h2>"We swapped in a cheaper model — did quality hold?"</h2>

<p>This is a different question from "is it better", and reading the output the same way will
mislead you. You are not hoping for an improvement. You are checking that the drop is small enough
to accept in exchange for the cost or latency you bought.</p>

<p><strong>Decide the tolerance before the run.</strong> Say you will accept up to a three-point
drop for a 70% cost reduction. Then read the <em>bottom end of the range</em>, not the middle:</p>

<pre><code>  difference -1.2% [-4.1%, +1.7%]
  <span class="o">INCONCLUSIVE</span>
  (smallest effect this run could have seen: 5.8%)</code></pre>

<p>The middle looks fine — barely down. But the range reaches −4.1%, past the three points you were
willing to lose. <strong>This run has not shown that quality held.</strong> It has shown that a drop
big enough to matter is still consistent with what you measured.</p>

<p>Two honest ways forward: add examples until the range tightens inside your tolerance, or accept
the risk deliberately and write down that you did. What you should not do is read "inconclusive" as
"no difference" and ship it as proven.</p>

<div class="callout">
  <span class="k">The same logic for a fine-tune</span>
  <p>Distilling to a small fine-tuned model is the same shape of question. So is dropping a reranker
  to save latency, or trimming context to save tokens. Anything where you are buying cost with
  quality wants a tolerance set in advance and the interval read against it.</p>
</div>

<p class="dim"><em>Textbook name: a non-inferiority test. The formal version compares the interval
bound against a pre-registered margin, which is exactly what you are doing by hand here.</em></p>

<h2>Which stage broke?</h2>

<p>When a retrieval app regresses, the number you get back is one number over two systems. The
rubric is how you pull them apart: each criterion is a different failure mode, and the judge names
the one it failed on for every example.</p>

<div class="scroller"><table>
<thead><tr><th>Criterion fails</th><th>Usually means</th><th>Look at</th></tr></thead>
<tbody>
<tr><td><strong>Groundedness</strong></td><td>The answer is not supported by what was retrieved.</td><td>Retrieval — embedding model, chunking, top-k, reranker.</td></tr>
<tr><td><strong>Correctness</strong> (but grounded)</td><td>The right context arrived and the model still got it wrong.</td><td>The generator — model swap, prompt, fine-tune.</td></tr>
<tr><td><strong>Directness</strong></td><td>It refused or hedged with the answer in front of it.</td><td>The generator, usually a newer or smaller model being more cautious.</td></tr>
</tbody></table></div>

<p>Every scored example records its criterion in <code>runs/&lt;id&gt;/scores.parquet</code>, and
the calibration report groups by criterion and by slice. Rolling that into a criterion-by-criterion
<em>comparison</em> between two arms is the next thing on the
<a href="@@blob@@/TRACKER.md">tracker</a>; today you read the breakdown per run and the overall
verdict for the pair.</p>

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

INTEGRATIONS_PAGE = """
<div class="eyebrow">Integrations</div>
<h1>What LangChef talks to</h1>
<p class="lede">LangChef decides what to measure and whether the answer means anything. It is not
trying to replace the tools you already run — if your runs live in MLflow, they stay in MLflow.</p>

<div class="callout warn">
  <span class="k">Read the status column</span>
  <p><strong>Shipped</strong> means it works today on <code>main</code>. Everything else is a
  statement of intent and nothing more. Track the order of work in the
  <a href="@@blob@@/TRACKER.md">tracker</a>; open an issue if you need one moved up.</p>
</div>

<div class="scroller"><table>
<thead><tr><th>Integration</th><th>Kind</th><th>Status</th><th>What it does</th></tr></thead>
<tbody>
@@rows@@
</tbody></table></div>

<h2>Why MLflow is first</h2>

<p>Two reasons, and neither is popularity.</p>

<p>The first is where teams already are. A team running retrieval, ranking or a classifier
alongside their GenAI feature almost certainly has an MLflow server, because the classical-ML
tooling around it largely died off in 2025 and MLflow is what survived. Asking them to keep results
somewhere else is asking them to maintain two records of the same thing.</p>

<p>The second is that MLflow 3 ships <code>align()</code> — one of only two things in the ecosystem
that automates judge-versus-human agreement at all. That makes it the nearest thing to a competitor
on the one problem LangChef leads with, which is exactly why interoperating beats competing:
a team that has already aligned a judge in MLflow should be able to bring it, not redo it.</p>

<h2>What an integration is allowed to do</h2>

<ul>
  <li><strong>Read-only by default.</strong> Connectors sample and read; they do not write to your
  production systems.</li>
  <li><strong>No data plane.</strong> Traces are read where they live. Nothing transits infrastructure
  belonging to this project, because there isn't any.</li>
  <li><strong>The workspace stays the record.</strong> An integration may mirror results outward —
  metrics into MLflow, a memo into a pull request — but the source of truth is the text in your
  repository. If you drop an integration, you keep everything.</li>
</ul>

<h2>Asking for one</h2>

<p>The list is short on purpose and the order is not fixed. If a tool your team depends on is
missing or sitting in "considering", say so on the
<a href="@@repo@@/issues">issue tracker</a> — what teams actually run beats what looks strategic
from here.</p>
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


# The integration register. Status is deliberately honest: "shipped" means it
# works today on main, everything else is a commitment of intent and nothing
# more. A docs page that implies an integration exists is worse than no page.
INTEGRATIONS = (
    (
        "MLflow",
        "Experiment tracking",
        "next",
        "Read runs and params from an existing MLflow server; write calibration and comparison "
        "results back as metrics and artifacts, so LangChef's numbers land where your team already "
        "looks. MLflow 3's <code>align()</code> is one of only two things in the ecosystem that "
        "automates judge-human agreement — interoperating with it beats competing with it.",
    ),
    (
        "litellm",
        "Model providers",
        "shipped",
        "One shim over every provider litellm speaks — Anthropic, OpenAI, Google, Bedrock, Vertex, "
        "local. Install with <code>uv sync --extra providers</code>. Nothing else in the codebase "
        "imports a provider SDK, so this is the only file to rewrite if it goes bad.",
    ),
    (
        "Claude Code",
        "Harness",
        "shipped",
        "The calibration playbook as a skill, plus commands that drive the CLI. The approval gates "
        "live in the CLI rather than the prompt, so they hold whether or not the agent cooperates.",
    ),
    (
        "Parquet + DuckDB",
        "Storage & query",
        "partial",
        "Per-example scores are written as Parquet today. DuckDB as the read-side query engine over "
        "the workspace — never as the store — arrives with the connectors.",
    ),
    (
        "Langfuse",
        "Tracing",
        "planned",
        "Pull production traces as evaluation examples instead of hand-assembling goldens. The "
        "obvious second integration: it is open source, self-hostable, and the topology matches — "
        "your traces stay where they are.",
    ),
    (
        "OpenTelemetry (GenAI semconv)",
        "Tracing",
        "planned",
        "Reading traces through the OTel GenAI semantic conventions rather than per-vendor SDKs "
        "would cover several tracing tools at once. Worth doing before Langfuse-specific work if "
        "the conventions have settled.",
    ),
    (
        "Arize Phoenix",
        "Tracing",
        "considering",
        "Open source, widely deployed, and its hosted sibling ships the closest competing agent. "
        "Reading from it is straightforward; the question is whether its users want this.",
    ),
    (
        "LangSmith",
        "Tracing & eval",
        "considering",
        "Large install base among teams already on LangChain. Pulling datasets and traces out is "
        "feasible; writing results back into a vendor data plane is against the grain here.",
    ),
    (
        "Braintrust",
        "Eval platform",
        "considering",
        "Overlaps rather than complements — its Loop assistant occupies the rung below this one. "
        "An import path for teams migrating is more plausible than a live integration.",
    ),
    (
        "GitHub Actions",
        "CI",
        "planned",
        "Run the loop on a schedule in CI for teams without an agent harness, opening a pull "
        "request with the memo. The scheduled loop is the product; the harness is one way to run it.",
    ),
)

REDIRECTS = {
    # Pages that were renamed. They stay reachable rather than 404ing: Pages
    # caches HTML for ten minutes, so a reader with the old navigation open will
    # click these for a while yet, and anyone who bookmarked or linked one
    # should land on the replacement rather than a dead end.
    "quickstart.html": ("start.html", "Your first evaluation"),
    "concepts.html": ("numbers.html", "Reading the output"),
}


def redirect(target: str, label: str) -> str:
    """A page that moved. Sends browsers on and tells crawlers where it went."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url={target}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{target}">
<title>Moved — LangChef</title>
{FONTS}
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="shell" style="padding: 72px 24px; max-width: 60ch;">
  <div class="eyebrow">This page moved</div>
  <h1>{label}</h1>
  <p class="lede">These docs were rewritten. If you are not redirected automatically,
  <a href="{target}">continue to {label}</a>.</p>
</div>
</body>
</html>
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
        "integrations.html": shell(
            "integrations.html",
            "Integrations — LangChef",
            fill(INTEGRATIONS_PAGE, {**common, "rows": integration_rows()}),
            "What LangChef reads from and writes to — MLflow first, then tracing tools and CI. "
            "Status is marked honestly: shipped means it works today.",
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
    for old, (target, label) in REDIRECTS.items():
        pages[old] = redirect(target, label)

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
    print(f"wrote {len(pages)} file(s) to docs/ ({len(REDIRECTS)} redirect(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
