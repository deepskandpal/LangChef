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
import json
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

# Three groups, because they answer three different questions. Guide is "how do
# I use this", Reference is "how does it work and what may I change", Project is
# "what is here". A flat list stopped working at eight entries.
NAV = (
    (
        "Guide",
        (
            ("index.html", "Overview"),
            ("start.html", "Start here"),
            ("numbers.html", "Reading the output"),
        ),
    ),
    (
        "Reference",
        (
            ("concepts.html", "Concepts"),
            ("ref-agreement.html", "Agreement and kappa"),
            ("ref-taxonomy.html", "Disagreement taxonomy"),
            ("ref-sampling.html", "Label planning"),
            ("ref-judging.html", "Judging and pins"),
            ("ref-design.html", "Designing a run"),
            ("ref-compare.html", "Comparing two arms"),
        ),
    ),
    (
        "Project",
        (
            ("cli.html", "Commands"),
            ("integrations.html", "Integrations"),
        ),
    ),
)

PAGES = tuple(entry for _, entries in NAV for entry in entries)

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=JetBrains+Mono:wght@400;500&"
    "family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&"
    'family=Spectral:ital,wght@0,600;1,400&display=swap">'
)


REF_ORDER = (
    ("concepts.html", "Concepts"),
    ("ref-agreement.html", "Agreement and kappa"),
    ("ref-taxonomy.html", "Disagreement taxonomy"),
    ("ref-sampling.html", "Label planning"),
    ("ref-judging.html", "Judging and pins"),
    ("ref-design.html", "Designing a run"),
    ("ref-compare.html", "Comparing two arms"),
)


def onward(page: str) -> str:
    """Previous and next within the reference sequence.

    The pages are deep on their own subject and say nothing about where they sit.
    A reader who lands on one from search has no way to tell what came before it,
    which is how a reference section reads as seven disconnected essays.
    """
    names = [href for href, _ in REF_ORDER]
    if page not in names:
        return ""
    i = names.index(page)
    parts = []
    if i > 0:
        href, label = REF_ORDER[i - 1]
        parts.append(f'<a class="prev" href="{href}"><span>Previous</span>{label}</a>')
    if i < len(REF_ORDER) - 1:
        href, label = REF_ORDER[i + 1]
        parts.append(f'<a class="next" href="{href}"><span>Next</span>{label}</a>')
    if not parts:
        return ""
    return '<nav class="onward" aria-label="Reference sequence">' + "".join(parts) + "</nav>\n"


def sidebar(page: str) -> str:
    """The grouped nav, with the current page marked and a search box on top."""
    groups = []
    for title, entries in NAV:
        items = "\n".join(
            f'    <li><a href="{href}"'
            + (' aria-current="page"' if href == page else "")
            + f">{label}</a></li>"
            for href, label in entries
        )
        groups.append(f"  <h4>{title}</h4>\n  <ul>\n{items}\n  </ul>")
    repo_links = "\n".join(
        f'    <li><a href="{href}">{label}</a></li>'
        for href, label in (
            (f"{BLOB}/docs/AGENT-CONTRACT.md", "Agent contract"),
            (f"{BLOB}/DECISIONS.md", "Decisions"),
            (f"{BLOB}/AGENTS.md", "Working agreement"),
            (f"{BLOB}/dogfood/README.md", "Dogfood"),
            (f"{REPO}/issues", "Issues"),
            (REPO, "Source on GitHub"),
        )
    )
    return (
        '<nav class="sidebar" aria-label="Documentation">\n'
        '  <form class="search" role="search" onsubmit="return false">\n'
        '    <input id="q" type="search" placeholder="Search docs" '
        'aria-label="Search documentation" autocomplete="off" spellcheck="false">\n'
        "    <kbd>/</kbd>\n"
        "  </form>\n"
        '  <div id="results" hidden></div>\n'
        '  <div id="nav">\n'
        + "\n".join(groups)
        + f"\n  <h4>In the repository</h4>\n  <ul>\n{repo_links}\n  </ul>\n"
        + "  </div>\n</nav>\n"
    )


def shell(page: str, title: str, body: str, description: str) -> str:
    """One page, wrapped in the site frame."""
    # One entry per group. Eight top-level links is a list, not a navigation.
    heads = [(entries[0][0], title) for title, entries in NAV]
    here = next((title for title, entries in NAV if page in [h for h, _ in entries]), None)
    nav = "\n".join(
        f'      <a href="{href}"{' class="here"' if title == here else ""}>{title}</a>'
        for href, title in heads
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
{sidebar(page)}
<main>
{anchored(body)}
{onward(page)}
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
<script src="search.js" defer></script>
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

<h2>Which of these are you</h2>

<p>The answer changes what this tool does for you, so it is worth settling before anything else.
The difference is not what your app is built from. It is <strong>whether you already know the right
answer</strong>.</p>

<div class="grid2">
  <div class="panel">
    <h3>You do not have the answer</h3>
    <p><strong>Q&amp;A, summarisation, generation, agent output.</strong> There is no single correct
    string, so something has to <em>read</em> the answer and judge it. That something is usually a
    model, and a model nobody has checked is not a measuring instrument.</p>
    <p><strong>Calibration comes first here</strong>, and it is the part almost nobody sells. If
    your judge disagrees with your own people three times in ten, every number computed downstream
    inherits that error and none of them will tell you.</p>
  </div>
  <div class="panel">
    <h3>You already have the answer</h3>
    <p><strong>Retrieval, classification, reranking.</strong> You know which document should have
    come back, which label is correct, which ordering is right. Comparing to it is arithmetic, not
    judgement.</p>
    <p><strong>There is nothing to calibrate</strong>, and we will not pretend otherwise. Skip
    straight to the experiment. recall@k, MRR, nDCG, accuracy and F1 are computed from your targets,
    and no rubric, no judge and no forty labels are involved.</p>
  </div>
</div>

<p>Neither is the lesser path. If you have hard targets you have <em>solved</em> the hardest
problem in evaluation already, and you get an answer sooner. What you still need is the part that
has nothing to do with judging:</p>

<ul>
  <li><strong>Paired statistics.</strong> Both arms answer the same questions, so only the examples
  that changed carry information. Treating them as two independent samples is how a real regression
  comes back as noise.</li>
  <li><strong>The detection limit.</strong> "recall@5 went from 0.71 to 0.69" means nothing without
  knowing the smallest move your set could have seen.</li>
  <li><strong>The discipline.</strong> The margin decided before the run, the design approved before
  traffic, the refusal to read out whichever run happens to look best.</li>
</ul>

<div class="callout warn">
  <span class="k">Being straight about what is built</span>
  <p>Today the tool runs the free-text path end to end. The hard-target path is designed and not
  yet shipped: bringing your own rows of input and target is
  <a href="@@repo@@/issues/14">#14</a>, and it is blocked on one decision that has to be made before
  any statistics are written. The paired comparison, the detection limit and the pre-registration
  all exist now and are task-agnostic. What is missing is the loader and the per-task metrics.</p>
</div>

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

<div class="callout warn">
  <span class="k">Check this walkthrough is for you</span>
  <p>This page follows a <strong>free-text</strong> task: the assistant writes prose, there is no
  single correct answer, and so a judge has to read it. Steps 2, 3, 5 and 6 exist entirely to check
  that judge before you trust it.</p>
  <p>If your task has a <strong>hard target</strong>, meaning you already know which document should
  have been retrieved, which label is correct, or which ordering is right, then
  <strong>none of those four steps apply to you</strong>. There is nothing to calibrate, because
  comparing against a known answer is arithmetic rather than judgement. Your version of this
  walkthrough is steps 1, 7, 8 and 9: collect examples, have the experiment designed, run it, read
  it out. That path is designed and not yet shipped
  (<a href="@@repo@@/issues/14">#14</a>); the comparison, the detection limit and the
  pre-registration it depends on all exist today.</p>
  <p><a href="index.html#which-of-these-are-you">Which one am I?</a></p>
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

<p>"Try again" has a command. Once you have changed the rubric,
<code>langchef calibrate diff</code> re-scores the new one against the labels you already have and
tells you whether agreement actually moved — no re-labelling, and only the new rubric costs
anything:</p>

<pre><code>$ langchef calibrate diff
  kappa  +0.57 -&gt; +0.84   +0.27 [+0.11, +0.45]   <span class="g">IMPROVED</span>
  moved  0 miss(es) fixed, 0 introduced; 8 false alarm(s) fixed, 0 introduced</code></pre>

<p>That interval is a paired one, because both rubrics judged the same examples against the same
labels. <a href="ref-agreement.html">Agreement and kappa</a> explains why that matters more than it
sounds like it should.</p>

<h2>Step 7 — Have the experiment designed · 1 minute</h2>

<p>You do not have to work out how many examples you need, or what size of change counts as real.
Describe what you are doing and let the tool cost it:</p>

<pre><code>$ langchef experiment design \
    --intent "move to the replacement model, quality must hold within 3 points" \
    --variant-arm new-model --kind non-inferiority --margin 0.03

2 candidate design(s) for support
 -&gt; as-it-stands   n=90     detects &gt;=13.2%  53 judge call(s)
      note: These goldens cannot resolve 3.0%. The smallest effect this
            design could detect is 13.2%.
    powered        n=1745   detects &gt;=3.0%   1655 judge call(s)
      note: Needs 1655 more golden(s) than the suite has (90).
  This is a proposal. Nothing runs until: langchef experiment approve ...</code></pre>

<p>That note is the answer most tools will not give you. <strong>Ninety examples cannot resolve a
three-point change</strong> — and you now know it before spending anything, rather than after a
run comes back inconclusive. Collect more goldens, or accept the detection limit deliberately.</p>

<p>If you are trading quality for cost or latency, <code>--margin</code> is not optional: it is how
much you are willing to lose, and it has to be set now. Deciding it after seeing the result is how a
null result quietly becomes a green light.</p>

<pre><code>langchef experiment approve support-new-model   <span class="c"># a person, on the record</span></code></pre>

<p>The design lands in <code>evals/experiments/</code> as reviewable TOML with a content hash. Edit
any part of it afterwards and the approval lapses by itself, which is what stops an experiment being
reshaped around the result it produced.</p>

<h2>Step 8 — Run it and read out · 1 minute</h2>

<pre><code>langchef baseline set                       <span class="c"># pin the model you're on today</span>

<span class="c"># re-answer the same questions on the replacement model, into</span>
<span class="c"># evals/goldens/support.new-model.jsonl, then:</span>

langchef judge run --arm new-model --experiment support-new-model
langchef experiment readout support-new-model</code></pre>

<p>Running under the experiment holds it to the budget you approved: at the ceiling the run stops,
exits 4, and writes exactly what it did not score — rather than quietly spending more than you
agreed to. The readout refuses an unapproved design, and refuses a run that stopped short of the one
you registered.</p>

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

<h2>Step 9 — Write it up · 5 seconds</h2>

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

<p><strong>You do not have to do it by hand.</strong> Pass the tolerance and the tool applies it:</p>

<pre><code>langchef compare --variant new-model <span class="o">--tolerance 0.03</span>

  difference -1.2% [-4.1%, +1.7%]  p=0.4127
  INCONCLUSIVE
  against a 3.0% tolerance: QUALITY <span class="o">UNRESOLVED</span>
    unresolved is not held. This run could not resolve 3.0%;
    it needed to see 6.0% or larger.</code></pre>

<h3>The three answers, in plain words</h3>

<div class="scroller"><table>
<thead><tr><th>Verdict</th><th>Means</th><th>Do</th></tr></thead>
<tbody>
<tr><td><strong>held</strong></td><td>the whole range clears your tolerance</td><td>ship it, and quote the range</td></tr>
<tr><td><strong>failed</strong></td><td>the whole range is past your tolerance</td><td>do not ship; the loss is real and bigger than you agreed to</td></tr>
<tr><td><strong>unresolved</strong></td><td>the range straddles it. <strong>This run cannot tell you</strong></td><td>collect more, or accept the risk knowingly. <strong>Not permission to ship</strong></td></tr>
</tbody></table></div>

<div class="callout warn">
  <span class="k">Unresolved is the one that gets misread</span>
  <p>It looks like a pass and it is not. It is the tool saying the evidence is absent, which is a
  different statement from the evidence being reassuring. That is why it prints the detection limit
  beside it: <em>"it needed to see 6.0% or larger"</em> tells you the run was never capable of
  answering, and roughly how many more examples would make it capable.</p>
</div>

<h3>When the margin was decided is the whole mechanism</h3>

<p>A tolerance passed on the command line and one carried in a pre-registration produce the same
three words. They are not the same evidence. A margin set before the run constrains the person who
set it; one typed after seeing the interval constrains nobody, and can be retyped until the answer is
agreeable.</p>

<p>So the output says which it was, every time:</p>

<pre><code>    margin came from the command line, not a pre-registration,
    so it constrains nobody: it could have been chosen after
    seeing the interval above.</code></pre>

<p>And if the run belongs to a pre-registered experiment, a <code>--tolerance</code> that disagrees
with the registered margin is <strong>refused at exit 2</strong> rather than preferred. Otherwise the
one command that sits outside the gate would be the way around it.</p>

<p class="dim"><em>Textbook name: a non-inferiority test. One detail worth knowing: the interval is
two-sided at your confidence level, and this test reads one bound of it, so the effective one-sided
level is higher than the number quoted. That is the conservative direction, and the payload reports
both rather than letting you assume.</em></p>

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

<p><code>compare</code> reports that split for you. Under the overall verdict it prints one line per
criterion, so the answer to "which half broke" arrives with the answer to "did it break".</p>

<pre><code>  difference -11.1% [-17.8%, -5.6%]  p=0.0020
  <span class="r">REGRESSION</span>
  attribution over 2 criterion(s), Holm-corrected — not 2 separate findings:
    Directness     -16.7% [-24.4%, -8.9%]  p=0.0001  <span class="r">MOVED WORSE</span>
    Correctness    +5.6% [+1.1%, +11.1%]  p=0.0625  inconclusive
                   (nothing under 12.0% was in reach for this criterion)</code></pre>

<p>Read that as one finding with a location, not as two results. The generator got more cautious;
retrieval did not move in a way this run could resolve. <strong>The second line is the one that
saves a day of looking in the wrong place.</strong></p>

<div class="callout">
  <span class="k">Why "MOVED WORSE" and not "REGRESSION"</span>
  <p>Different words on purpose. The overall verdict is one comparison you asked for. The
  per-criterion lines are that same comparison, broken up — and with five criteria, one of them
  crossing a threshold by chance is ordinary. The p-values on those lines are corrected for how many
  criteria were examined, and each carries its own detection limit, because the overall limit does
  not apply to a slice of the overall comparison. <a href="ref-compare.html#which-criterion-moved">How
  that correction works</a>.</p>
</div>

<p>Every scored example records its criterion in <code>runs/&lt;id&gt;/scores.parquet</code>, so
the calibration report groups by criterion and by slice as well — the same axis, one run at a time
instead of across a pair.</p>

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

<h2>If your task has a hard target</h2>

<p>Retrieval, classification and reranking come with the right answer already known, so the
calibration half of this page does not apply to you. There is no rubric, no judge and no kappa,
because nothing is being judged. <strong>Skip every number above that describes agreement.</strong></p>

<p>What still applies, and is most of why this tool exists:</p>

<div class="scroller"><table>
<thead><tr><th>Number</th><th>Why it still matters</th></tr></thead>
<tbody>
<tr><td><strong>The paired difference and its interval</strong></td><td>Both arms answer the same
queries, so only the ones whose outcome changed carry information. This is true whether the outcome
came from a judge or from an exact match against your target.</td></tr>
<tr><td><strong>The detection limit</strong></td><td>The one people most need and least often have.
"recall@5 moved from 0.71 to 0.69" is not a finding until you know the smallest move your set could
have resolved.</td></tr>
<tr><td><strong>The verdict</strong></td><td>Regression, improvement or inconclusive, on the same
rule: a direction only counts when the whole interval agrees with it.</td></tr>
<tr><td><strong>The non-inferiority margin</strong></td><td>Swapping a cheaper embedding model is
still a "did quality hold" question, and still wants its tolerance fixed before the run.</td></tr>
</tbody></table></div>

<p>The per-task metrics themselves, recall@k, MRR, nDCG for retrieval and accuracy, precision,
recall and F1 for classification, are computed from your targets rather than judged. They are
designed and not yet shipped: see <a href="@@repo@@/issues/14">#14</a>.</p>

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


CONCEPTS = """
<div class="eyebrow">Reference</div>
<h1>Concepts</h1>
<p class="lede">Every idea LangChef uses, in a few lines each, with a link to the page that explains
it properly. Start here if a word in the output is unfamiliar, or if you are about to change the
code and want to know what you are changing.</p>

<div class="callout">
  <span class="k">You do not need statistics to use this</span>
  <p>The tool computes all of it. This section exists so that the numbers are not a black box, and
  so that anyone who wants to change how they are computed can find the ground they rest on.
  Every page opens with a worked example from the project's own test data before it explains
  anything.</p>
</div>

<h2>The things you supply</h2>

<h3>Example</h3>
<p>One question your app was asked, the answer it gave, and the context it retrieved. Also called a
<em>golden</em>. Fifty to a hundred is a normal starting set, taken from real traffic rather than
invented, because invented questions are always easier than the ones users actually ask.</p>

<h3>Rubric</h3>
<p>What "a good answer" means, written down as Markdown. Each <code>###</code> heading is one
criterion and the judge must name the one it failed on. Roughly what you would tell a new teammate
on their first day. It is hashed, so editing it revokes its approval.
<a href="ref-agreement.html#what-the-rubric-has-to-do">Why the headings matter</a>.</p>

<h3>Label</h3>
<p>Your own verdict on an example, pass or fail, recorded by hand. This is the ground truth
everything else is measured against. It is the only part nobody can automate for you, and roughly
forty of them is the usual ask.</p>

<h2>Judging</h2>

<h3>Judge</h3>
<p>The thing that reads an answer and says pass or fail. Usually a model with your rubric in the
prompt; sometimes, as in the default here, plain token matching. A judge is a measuring instrument,
not a metric, which is the single idea the rest of the product is built on.</p>

<h3>Pin</h3>
<p>The rubric hash, the provider and the models that produced a set of verdicts, recorded on every
run. Two runs are only comparable if their pins match. When they do not, <code>compare</code> exits
5 rather than drawing a chart of two different measurements.</p>

<h3>Two-tier judging</h3>
<p>A cheap model scores everything; a strong model re-scores only the cases the cheap one was
unsure about. Built in from the start rather than added later, because the model is part of the
cache key and retrofitting it would invalidate every cached verdict in every workspace. <a href="ref-judging.html#two-tiers">More</a>.</p>

<h2>Calibration: is the judge any good</h2>

<h3>Calibration</h3>
<p>Comparing the judge's verdicts against your labels on the same examples, to find out how far it
can be trusted. It comes before everything else because an eval suite built on an unchecked judge
produces confident nonsense, and no downstream statistic repairs that.
<a href="ref-agreement.html">Full page</a>.</p>

<h3>Agreement, or Cohen's kappa</h3>
<p>How much you and the judge agree, after subtracting the agreement two coins would produce by
luck. Runs 0 to 1. It exists because raw accuracy flatters any judge on a lopsided suite: where 95%
of answers are fine, a judge that says "fine" to everything is 95% accurate and worthless.
<a href="ref-agreement.html#kappa-subtract-the-luck">How it is computed</a>.</p>

<h3>Catch rate and false alarm rate</h3>
<p>Of the problems you found, how many the judge also flagged (catch rate, or TPR). Of the answers
that were fine, how many it flagged anyway (false alarm rate, or FPR). These two say <em>how</em> a
judge fails, which is what actually changes a rubric.
<a href="ref-agreement.html#the-two-numbers-you-act-on">More</a>.</p>

<h3>Confidence interval</h3>
<p>The range the true value probably sits in. Printed beside every rate, because "80%" measured on
fifteen examples and "80%" measured on fifteen hundred are different claims. A wide interval means
label more examples, not that the judge is erratic.
<a href="ref-agreement.html#the-interval-and-why-wilson">Why Wilson and not the textbook one</a>.</p>

<h3>Disagreement taxonomy</h3>
<p>Six disagreements is a count, not a finding. The taxonomy groups them by which rubric criterion
the judge cited and which slice of traffic they fell in, and refuses to report a slice whose
interval does not clear the base rate.
<a href="ref-taxonomy.html">Full page</a>.</p>

<h3>Label planning</h3>
<p>Choosing which examples are worth a person's ten minutes. Sampling at random on a suite where the
judge flags 15% wastes most of the budget confirming passes, so the plan takes every flagged example
plus a sample of the rest, and prefers cases the judge was unsure about.
<a href="ref-sampling.html">Full page</a>.</p>

<h2>Experiments: did the change help</h2>

<h3>Arm, run, baseline</h3>
<p>An <strong>arm</strong> is one version of your app. A <strong>run</strong> is one scoring pass
over one arm. The <strong>baseline</strong> is the run you pinned as the reference. Both arms answer
the same questions with the same example ids; that pairing is what lets a small set say anything.</p>

<h3>Paired comparison</h3>
<p>Because both arms answer identical questions, only the examples that <em>changed verdict</em>
carry information. If 200 pass under both and 3 flip, the evidence is in the 3. Treating the arms as
independent samples throws that away and real regressions come back as noise.
<a href="ref-compare.html#why-paired-and-not-two-samples">Full page</a>.</p>

<h3>Minimum detectable effect</h3>
<p>The smallest change your run could have caught. Quoted on every inconclusive result, because "no
significant difference" on ninety examples usually means "this set could never have seen it". It
turns a shrug into a plan: collect more, or accept the limit knowingly.
<a href="ref-compare.html#the-smallest-change-you-could-have-seen">More</a>, and how a run is <a href="ref-design.html">designed around it</a>.</p>

<h3>Non-inferiority and the margin</h3>
<p>Swapping in a cheaper model is not a hunt for an improvement, it is a check that the drop stays
inside a tolerance you set <em>before</em> the run. You read the bottom of the interval against that
margin, not the middle. Deciding the margin afterwards is how a null result becomes a green light.
<a href="ref-compare.html#did-quality-hold">More</a>.</p>

<h2>Discipline</h2>

<h3>Pre-registration</h3>
<p>The experiment design, written to <code>evals/experiments/</code> and approved by a person before
any traffic. It carries a content hash, so editing it afterwards revokes the approval on its own.
Reading out without one exits 2; reading out a run that departed from one marks the result
exploratory and recommends no decision. <a href="ref-design.html#editing-it-afterwards-revokes-it-with-nobody-watching">Full page</a>.</p>

<h3>Gates as exit codes</h3>
<p>A rule in a prompt is a suggestion. These are exit codes: <code>2</code> refused because an
approval is missing, <code>5</code> refused because the two runs were measured differently,
<code>4</code> stopped because the agreed budget ran out. An agent cannot argue with a non-zero
exit. <a href="numbers.html#when-the-tool-refuses">The full table</a>.</p>

<h3>The quality ledger</h3>
<p>An append-only record of every run, calibration and decision. Entries are never edited; a
correction is a new entry, so what was believed at the time survives. It answers the question a
leaderboard cannot: has quality moved this quarter, and what did we do about it.</p>
"""


REF_AGREEMENT = """
<div class="eyebrow">Reference</div>
<h1>Agreement and kappa</h1>
<p class="lede">How LangChef decides whether your judge can be trusted, worked from real numbers,
with the code and the papers behind each step. No statistics background assumed.</p>

<div class="worked">
  <span class="k">The worked example used throughout this page</span>
  <p>From the project's own dogfood run. You labelled 40 examples by hand; the judge had already
  scored the same 40. Every number on this page comes from these four counts.</p>
<pre><code>                judge fail   judge pass
  you fail         12 (tp)       3 (fn)    = 15
  you pass          3 (fp)      22 (tn)    = 25
                  = 15         = 25         40</code></pre>
  <p>Twelve times you both said bad. Twenty-two times you both said fine. Six times you disagreed:
  three the judge missed, three it cried wolf on.</p>
</div>

<h2>Why accuracy is not the answer</h2>

<p>You agreed on 34 of 40, so the judge is <strong>85% accurate</strong>. That sounds usable.</p>

<p>Now take a judge that does nothing but say "pass" to everything. On this same set it scores
<strong>62.5%</strong>. On a realistic production suite where only 5% of answers are bad, that same
do-nothing judge scores <strong>95%</strong>.</p>

<p>Accuracy rewards guessing the common answer. It cannot separate a judge that works from one that
has noticed most things are fine. That is the whole reason this page exists.</p>

<h2>Kappa: subtract the luck</h2>

<p>You flagged 37.5% of examples. The judge flagged 37.5%. If both of you were flipping weighted
coins at those rates and never reading the answers, <strong>you would still agree 53.1% of the
time</strong>.</p>

<p>So the question is not how often you agreed, but how much of the room above luck you closed.</p>

<pre><code>  room above chance:   100%  -  53.1%   =  46.9%
  you actually closed:  85%  -  53.1%   =  31.9%

  kappa = 31.9 / 46.9 = 0.68</code></pre>

<p>In one line: <strong>kappa = (agreement observed − agreement by luck) / (1 − agreement by
luck)</strong>. One is perfect, zero is no better than coin-flipping. The do-nothing judge above
scores exactly <strong>0.00</strong>, which is the point.</p>

<div class="incode">
  <div>Computed in <b>src/langchef/core/agreement.py</b></div>
  <div><b>confusion()</b> counts the four cells from paired verdicts</div>
  <div><b>cohen_kappa()</b> the formula above</div>
  <div><b>kappa_interval()</b> its uncertainty, see below</div>
</div>

<h3>How we read it, and where the thresholds came from</h3>

<div class="scroller"><table>
<thead><tr><th>Kappa</th><th>We say</th><th>What to do</th><th>Landis &amp; Koch call it</th></tr></thead>
<tbody>
<tr><td class="num">0.8 and up</td><td>strong</td><td>trust the numbers downstream</td><td>almost perfect</td></tr>
<tr><td class="num">0.6 to 0.8</td><td>usable</td><td>act on it, quote the interval too</td><td>substantial</td></tr>
<tr><td class="num">0.4 to 0.6</td><td>weak</td><td>fix the rubric before experimenting</td><td>moderate</td></tr>
<tr><td class="num">below 0.4</td><td>not usable</td><td>stop; do not report pass rates</td><td>fair or worse</td></tr>
</tbody></table></div>

<p><strong>These bands are a convention, not a law.</strong> They descend from Landis and Koch
(1977), who proposed them for observer agreement in medical data and said plainly that the divisions
were arbitrary. We kept the shape because it is the one most readers already know, and collapsed the
lower three into "not usable" because for our purpose the difference between fair and slight does
not change what you do. If your domain has its own convention, use that instead.</p>

<h2>The two numbers you act on</h2>

<p>Kappa says whether the judge is worth anything overall. These say <em>how it fails</em>, which is
what changes a rubric.</p>

<div class="scroller"><table>
<thead><tr><th></th><th>Here</th><th>Means</th></tr></thead>
<tbody>
<tr><td><strong>Catch rate</strong> (TPR, recall, sensitivity)</td><td class="num">12/15 = 80%</td><td>Of the problems you found, the judge caught 12. Three shipped past it.</td></tr>
<tr><td><strong>False alarm rate</strong> (FPR)</td><td class="num">3/25 = 12%</td><td>Of the answers that were fine, it flagged three anyway.</td></tr>
</tbody></table></div>

<p>They trade off. Push a judge to catch more and it cries wolf more. A judge with a respectable
kappa can still be unusable in the direction you happen to care about, which is why the report gives
you all three rather than a single score.</p>

<p>The report also carries <strong>PPV</strong> (when it flags something, how often it is right) and
<strong>NPV</strong> (when it passes something, how often it is right). Those are the ones to read if
you are deciding how much to trust an individual verdict rather than the judge as a whole.</p>

<h2>The interval, and why Wilson</h2>

<p><code>12/15</code> is not "80%". It is <em>80%, measured on fifteen examples</em>, and those are
different claims. So every rate is printed with the range the true value probably sits in.</p>

<p>The textbook interval, the one most people are taught, would say:</p>

<pre><code>  0.8 ± 1.96 × √(0.8 × 0.2 / 15)   =   [59.8%, <span class="r">100.2%</span>]</code></pre>

<p><strong>100.2%.</strong> It runs off the end of the scale, because that formula assumes a bell
curve and a proportion near a boundary is not one. At 15/15 it collapses to <code>[100%, 100%]</code>,
claiming certainty from fifteen examples. At 1/15 it goes negative.</p>

<p>The Wilson interval does not do that. It stays inside 0 to 1, goes asymmetric near the edges, and
holds its coverage down to single-digit counts. Your actual catch-rate interval is
<strong>[54.8%, 93.0%]</strong>.</p>

<p>That width is the honest content of the measurement. The judge's true catch rate could be 55%,
and forty labels cannot rule it out.</p>

<div class="worked">
  <span class="k">Read the kappa interval too</span>
  <p>Kappa here is <strong>0.68, interval [0.44, 0.92]</strong>. By the table above, 0.44 is "weak,
  fix the rubric" and 0.92 is "strong, trust it". Forty labels cannot tell those apart. The point
  estimate reads usable; the interval says you do not actually know yet. That is not a flaw in the
  measurement, it is the measurement.</p>
</div>

<div class="incode">
  <div><b>wilson()</b> the score interval for every rate</div>
  <div><b>kappa_interval()</b> Fleiss, Cohen and Everitt's asymptotic variance</div>
  <div>Checked against scipy's own Wilson implementation and, for kappa, against a bootstrap that
  knows nothing about the formula. See <b>tests/test_agreement.py</b>.</div>
</div>

<h2>Matthews correlation, in one line</h2>

<p><strong>0.68 here.</strong> A single correlation between the two raters' verdicts, from −1 to +1,
which unlike accuracy degrades honestly when one class dominates. It is there for when someone wants
one number, and it is a better one number than accuracy.</p>

<h2>Where you disagreed</h2>

<p>Six disagreements is a count. It does not tell you what to fix, so the taxonomy groups them by
which rubric criterion the judge cited and which slice of your traffic they fell in, then refuses to
report a slice whose interval does not clear the base rate.</p>

<p>In this run <code>topic=returns</code> disagreed <strong>33% of the time against a 15% base rate,
a 2.2x lift</strong>, on nine examples, with an interval of [12.1%, 64.6%]. The bottom of that
interval sits below the base rate, so it is not reported. That guard is the most important thing in
the codebase and it has its own page: <a href="ref-taxonomy.html">disagreement taxonomy</a>.</p>

<h2>Did the rubric change help?</h2>

<p>The taxonomy tells you <em>where</em> the judge disagrees. You act on it by rewriting the rubric —
and then you have two calibrations and one question: did that help, or did it just move the noise
around? <code>langchef calibrate diff</code> answers it. It re-scores the revised rubric against the
same labels and reports the change in kappa <em>and</em> in both rates, each with an interval.</p>

<p>The worked example below uses a larger labelled set — sixty rather than the forty above — for a
reason worth knowing before you run this. On forty labels, a revision that repairs two false alarms
lands at <strong>+0.10, interval [0.00, 0.25]</strong>: inconclusive. Forty labels are enough to
measure a judge and not enough to resolve a small change to one.</p>

<pre><code>$ langchef calibrate diff --rubric answer-quality-v2
rubric delta on 60 labelled example(s) from run base
  answer-quality@290335165c70  -&gt;  answer-quality-v2@8ad25d2ca381
  kappa  +0.57 -&gt; +0.84   +0.27 [+0.11, +0.45]   <span class="g">IMPROVED</span>
  TPR    80.0% -&gt; 80.0%   +0.0% [+0.0%, +0.0%]   p=1.0000  inconclusive
         (nothing under 25.1% was in reach on these labels)
  TNR    80.0% -&gt; 100.0%   +20.0% [+7.5%, +32.5%]   p=0.0156  improved
  moved  0 miss(es) fixed, 0 introduced; 8 false alarm(s) fixed, 0 introduced</code></pre>

<p>In plain words: dropping the criterion the judge was reading as word-containment stopped all eight
false alarms and cost nothing in catch rate. The <code>moved</code> line is the actionable one — a
revision that fixes four false alarms by introducing four misses is not the same change as this, and
kappa alone cannot tell them apart.</p>

<div class="worked">
  <span class="k">Why this is not two reports side by side</span>
  <p>Both rubrics scored <em>the same sixty examples</em> against <em>the same sixty labels</em>. A
  rubric revision changes the instrument, not the ground truth. So the two kappas are two
  measurements on one sample, not two samples — and they move together, because the eight repaired
  examples are the only thing separating them.</p>
  <p>The two calibrations on their own read <strong>0.57 [0.36, 0.78]</strong> and
  <strong>0.84 [0.69, 0.99]</strong>. Those intervals overlap, and "they overlap, so nothing
  changed" is the mistake. Do the same thing arithmetically — add the two variances as though the
  calibrations were independent — and you get <strong>[+0.01, +0.53]</strong>: more than twice as
  wide, and on data one repaired example lighter it straddles zero and the revision gets thrown
  away.</p>
  <p>The paired interval is <strong>[+0.11, +0.45]</strong>. It is not a tighter answer to the same
  question; it is the answer to the right one.</p>
</div>

<p>This is the same defect as the minimum detectable effect computed with an unpaired formula on
paired data, which reported 15.6% where the truth was 6.0%. It does not crash and it does not look
wrong. It quietly turns real improvements into shrugs, which is how a rubric-iteration loop stops
being worth running.</p>

<h3>The two rates get an exact test, not a bootstrap</h3>

<p>Kappa is not an average of anything, so its interval is a bootstrap that resamples examples and
carries the human label and both verdicts on every draw. The catch rate and the false-alarm rate are
simpler than that. Because the human labels do not move, <strong>the human-fail examples are
literally the same examples under both rubrics</strong>: the denominator is fixed and only the
numerator can move. That is exactly McNemar's setting, so only the examples where the two rubrics
disagree <em>with each other</em> carry information — the same arithmetic, and the same code, that
<a href="ref-compare.html">compare</a> uses on two arms.</p>

<p>Two more things the output commits to. <strong>Kappa is the headline and the two rates are its
halves</strong>, so their p-values are Holm-corrected across that family of two and a direction is
named only when the corrected p clears alpha <em>and</em> the whole interval agrees with it — never
one without the other. And <strong>a delta needs the same judge model at both ends</strong>: move the
model between the two and the command exits 5 rather than reporting a rubric change that is partly a
model change.</p>

<p>The revised rubric does not need approving first, and deliberately so. Gate one stops a rubric
nobody has read from scoring a suite for real; this command produces the evidence that reading is
supposed to rest on. The output records that the candidate is unapproved, so nothing downstream can
mistake it for a signed-off instrument.</p>

<div class="incode">
  <div>Computed in <b>src/langchef/core/delta.py</b></div>
  <div><b>kappa_delta()</b> the paired percentile bootstrap over examples</div>
  <div><b>delta()</b> both rates, exact McNemar, Holm-corrected across the pair</div>
  <div>The unpaired interval is written out once, in <b>tests/test_delta.py</b>, purely so the paired
  one can be measured against it. It appears nowhere under <b>src/</b>.</div>
</div>

<h2>What the rubric has to do</h2>

<p>Each <code>###</code> heading in your rubric is one criterion, and the judge must name the one it
failed on. That is what makes the taxonomy possible at all: without an attributed failure there is
nothing to group by, and a regression in a retrieval app cannot be told apart from a regression in
the generator.</p>

<p>It is also why editing a rubric revokes its approval. The criteria are the axis the taxonomy is
reported along, so renaming one silently changes what every past number meant.</p>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No weighted kappa.</strong> Verdicts here are pass or fail, so there is no notion of a
  near-miss to weight. If task classes with ordered labels arrive, this is where it changes.</li>
  <li><strong>No multi-class kappa yet.</strong> The variance formula is written for a 2×2 table.
  Classification datasets with more than two labels need an N×N version, tracked as part of the
  bring-your-own-dataset work.</li>
  <li><strong>A delta compares two rubrics, never two label sets.</strong> <code>calibrate diff</code>
  is paired on the labelled examples the two calibrations share, and refuses when they share none:
  two calibrations on different examples differ by rubric <em>and</em> by example set, and no
  interval can separate those two causes.</li>
  <li><strong>No inter-annotator agreement.</strong> We compare one judge against one set of human
  labels. Multiple human labellers disagreeing with each other is a real and harder problem, and
  Krippendorff's alpha is the usual tool. Out of scope for now.</li>
  <li><strong>The stratified label weights are recorded and are not valid weights.</strong> This
  is the sharpest limitation on this page, and it is stronger than "not yet applied". The label plan
  sorts each stratum by the judge's confidence and takes the lowest, so a row's inclusion
  probability is 0 or 1 rather than <code>n/N</code>. Post-stratification cannot repair that,
  because selection inside a stratum tracks the very thing being estimated. A seeded coverage
  simulation put a nominal 95% interval at <strong>43% actual coverage for the catch rate</strong>.
  So read every rate on this page as describing <em>the labelled set</em>, not as an estimate of
  your whole suite. The underlying question, whether one label budget buys estimation or diagnosis,
  is open.</li>
  <li><strong>scikit-learn is a test dependency, never a runtime one.</strong> Every statistic is
  hand-rolled and checked against an independent implementation. If the product and its check came
  from the same library, the check would only prove the library agrees with itself.</li>
</ul>

<h2>Further reading</h2>

<p>Ordered by how useful they are if you are actually changing this code.</p>

<ul class="reading">
  <li><strong>Brown, Cai and DasGupta (2001), "Interval Estimation for a Binomial Proportion",
  <em>Statistical Science</em> 16(2), 101–133.</strong> The paper that settles why not to use the
  textbook interval: it shows the Wald interval's coverage is chaotic and that the usual
  reassurances about when it is safe are "misleading and defective". It recommends Wilson for small
  n, which is what we use. Start at §1.1 and Figure 1; the picture makes the argument on its own.
  <span class="where">Open PDF: www-stat.wharton.upenn.edu/~lbrown/Papers/2001a Interval estimation for a binomial proportion.pdf</span></li>

  <li><strong>Cohen (1960), "A Coefficient of Agreement for Nominal Scales",
  <em>Educational and Psychological Measurement</em> 20(1), 37–46.</strong> The original kappa. Short,
  and the motivating argument in the opening pages is the same one this page makes about accuracy.</li>

  <li><strong>Fleiss, Cohen and Everitt (1969), "Large sample standard errors of kappa and weighted
  kappa", <em>Psychological Bulletin</em> 72, 323–327.</strong> The asymptotic variance
  <code>kappa_interval()</code> implements. Read this one if you touch that function; the index
  gymnastics in the published form is where implementations go wrong, which is why our test checks
  it against a bootstrap.
  <span class="where">doi:10.1037/h0028106</span></li>

  <li><strong>Landis and Koch (1977), "The Measurement of Observer Agreement for Categorical Data",
  <em>Biometrics</em> 33(1), 159–174.</strong> Where the slight / fair / moderate / substantial /
  almost perfect bands come from. Worth reading precisely because they present the divisions as
  arbitrary, which is not how they are usually cited.</li>

  <li><strong>Chicco and Jurman (2020), "The advantages of the Matthews correlation coefficient (MCC)
  over F1 score and accuracy in binary classification evaluation", <em>BMC Genomics</em> 21:6.</strong>
  Open access and the most readable thing on this list. Worked examples of accuracy and F1 flattering
  a bad classifier, which is the same failure this page opens with.</li>

  <li><strong>Zheng et al. (2023), "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena",
  arXiv:2306.05685.</strong> Not about kappa, but about the instrument. §3.1 catalogues position bias,
  verbosity bias and self-enhancement bias in model judges. Read it before you trust a judge you have
  not calibrated, and before you let a model grade its own family's output.</li>
</ul>

<p class="dim">Citations verified against the publishers' records rather than quoted from memory.
Where only a section could be confirmed, a section is what is cited.</p>
"""


REF_COMPARE = """
<div class="eyebrow">Reference</div>
<h1>Comparing two arms</h1>
<p class="lede">How LangChef decides whether a change helped, hurt, or cannot be told apart, and why
"cannot be told apart" is a result rather than a shrug.</p>

<div class="worked">
  <span class="k">The worked example</span>
  <p>From the dogfood: the baseline against an arm with documents deliberately dropped from the
  retrieval index. Both arms answered the same 90 questions.</p>
<pre><code>  baseline 83.3%   variant 63.3%
  difference -20.0% [-27.8%, -12.2%]  p=0.0000
  <span class="r">REGRESSION</span>

  of 90 goldens, 18 changed verdict: 18 broke, 0 fixed</code></pre>
  <p>The planted effect was −20 points. The measurement recovered it to the decimal.</p>
</div>

<h2>Why paired, and not two samples</h2>

<p>Both arms answer <em>the same questions</em>, with the same example ids. That is not a
convenience, it is the whole reason a set of 90 can say anything.</p>

<p>Think about what actually carries information. If 72 goldens pass under both arms, they tell you
nothing about the difference between them: they are the same question, answered acceptably twice.
The evidence lives entirely in the <strong>18 that changed verdict</strong>.</p>

<pre><code>                variant pass   variant fail
  baseline pass       72             18      <- broke
  baseline fail        0              0      <- fixed</code></pre>

<p>The test asks one question about those 18: <em>given that a verdict flipped, was it equally
likely to flip either way?</em> Eighteen broke and none were fixed. If the two arms were really
equivalent, that is a coin landing heads eighteen times.</p>

<p>Treating the arms as two independent samples instead throws the pairing away, inflates the
variance, and real regressions come back as "not significant". That failure is quiet and it is
common.</p>

<div class="incode">
  <div>Computed in <b>src/langchef/core/compare.py</b></div>
  <div><b>discordance()</b> the paired 2×2; only the off-diagonal moves the estimate</div>
  <div><b>mcnemar_p()</b> exact binomial on the discordant pairs</div>
  <div><b>compare()</b> the verdict, the interval, and the detection limit</div>
  <div><b>by_criterion()</b> the same test inside each criterion, corrected across them</div>
  <div><b>holm()</b> step-down adjusted p-values for the family of criteria</div>
</div>

<h3>Exact, not the chi-square approximation</h3>

<p>The classical McNemar statistic uses a chi-square approximation. We use the exact binomial test
instead, because the discordant counts that decide real cases are small, and the approximation is
least reliable exactly when the decision is closest. With 18 flips the two agree; with 4 they do
not, and 4 is a number you will see.</p>

<h2>The verdict comes from the interval, not the p-value</h2>

<p>Three outcomes, and the middle one is the one people misread.</p>

<div class="scroller"><table>
<thead><tr><th>Verdict</th><th>Condition</th><th>Means</th></tr></thead>
<tbody>
<tr><td><strong>REGRESSION</strong></td><td>whole interval below zero</td><td>worse, and the evidence supports acting</td></tr>
<tr><td><strong>IMPROVEMENT</strong></td><td>whole interval above zero</td><td>better, same standard</td></tr>
<tr><td><strong>INCONCLUSIVE</strong></td><td>interval spans zero</td><td>this set cannot tell them apart. <strong>Not "no difference"</strong></td></tr>
</tbody></table></div>

<p>A direction only counts when the entire range agrees with it. The p-value is reported because
people ask for it, but it does not decide anything here: a p-value answers "how surprising is this
if nothing changed", which is not the question you came with.</p>

<p>The interval itself is a percentile bootstrap over the pairs, resampled together so the pairing
survives. It is seeded, because the contract calls <code>compare</code> deterministic and a
comparison that moves between identical runs is not one.</p>

<h2>The smallest change you could have seen</h2>

<p>This is the most useful number in the tool, and the one no dashboard gives you.</p>

<pre><code>  difference +0.0% [+0.0%, +0.0%]  p=1.0000
  <span class="o">INCONCLUSIVE</span>
  (smallest effect this run could have seen: 6.0%)</code></pre>

<p>That run came from an arm with a <strong>real, deliberately planted −3.3 point regression</strong>.
The judge saw nothing. The honest report is not "no regression found", it is "nothing we could have
seen", and the second half of that sentence is the actionable part: ninety goldens could never have
resolved three points.</p>

<p>It is computed from the <strong>discordant rate</strong>, not the pass rate, because under a
paired test that is what carries the information. Two hundred goldens where four flip carry far less
than two hundred where forty do, and a formula built on the pass rate cannot see that difference.</p>

<p>When nothing flipped at all, the rate is not taken as zero. Zero discordant pairs is not evidence
that any effect was detectable; it is an unknown rate that this many goldens bound from above, so
the upper end of its interval is used. That is why a completely quiet run still reports a finite
limit rather than claiming infinite sensitivity.</p>

<p>Rule of thumb: <strong>halving the effect you want to detect needs roughly four times the
goldens.</strong></p>

<h2>Which criterion moved</h2>

<p>"Quality fell 11 points" is a fact. "The generator got more cautious and retrieval held" is an
answer. The judge already names the criterion it cited on every failure, so the comparison can be
attributed rather than left as one number over two systems.</p>

<pre><code>  attribution over 2 criterion(s), Holm-corrected — not 2 separate findings:
    Directness     -16.7% [-24.4%, -8.9%]  p=0.0001  <span class="r">MOVED WORSE</span>
    Correctness    +5.6% [+1.1%, +11.1%]  p=0.0625  inconclusive
                   (nothing under 12.0% was in reach for this criterion)</code></pre>

<p>That is the dogfood's <code>eager-hedging</code> arm: the app was made to decline more often, and
nothing else was touched. The overall drop is 11 points; the breakdown puts 17 of them on Directness
and finds no movement in Correctness it can stand behind.</p>

<h3>The pairing is inside a criterion, never across two</h3>

<p>Each criterion gets the same treatment as the whole suite: the same example under both arms, the
same exact McNemar over the pairs that flipped <em>on that criterion</em>, the same seeded bootstrap.
Nothing switches to a two-sample test on a smaller slice.</p>

<p>This matters most for the case the headline cannot see at all. An answer that failed Correctness
under the baseline and Groundedness under the variant is a fail in both arms — <strong>zero
discordant pairs, nothing to report</strong> — while the criteria show a Correctness fix and a
Groundedness break. Something moved, and only the breakdown says what.</p>

<p>Because the judge cites exactly one criterion per failure, the per-criterion differences add up
to the overall difference. When a judge fails something without naming a criterion, the leftover is
reported as <code>unattributed</code> rather than quietly dropped.</p>

<h3>Five criteria means five chances to be wrong</h3>

<p>With five criteria and a 5% threshold, one of them crossing by chance is ordinary — about a
one-in-four run. Printing five uncorrected verdicts would manufacture a finding roughly every fourth
time you ran the tool, and every one of them sends somebody to rewrite a component that was fine.</p>

<p>So the p-values are <strong>Holm-corrected across the criteria examined</strong>. Sort them, hold
the smallest to α/k, the next to α/(k−1), and so on; the family-wise error rate stays at 5% no matter
how the criteria are correlated, and they are correlated here — one cited criterion per failure makes
them push against each other.</p>

<p>Holm rather than Bonferroni because it is uniformly more powerful at the same guarantee. Holm
rather than a false-discovery-rate procedure because these criteria are the two or three halves of
one system: the question is <em>which one broke</em>, so a false positive costs a person a day in the
wrong file, and that is the error rate worth controlling.</p>

<div class="callout">
  <span class="k">Different words, on purpose</span>
  <p>A criterion is never called a <code>regression</code> or an <code>improvement</code>. It is
  <code>moved_worse</code>, <code>moved_better</code> or <code>inconclusive</code>. Those are
  attributions of one comparison, and the vocabulary says so in the payload rather than in a footnote
  a reader drops on the way to the number.</p>
</div>

<p>A direction is only named when <em>both</em> the corrected p-value clears the threshold and the
interval sits entirely on one side of zero. Either one alone can mislead: five flips the same way is
p = 0.0625 and cannot be rejected, but its bootstrap interval still clears zero. That is the
<code>Correctness</code> line above — the interval alone would have called it an improvement.</p>

<h3>Each criterion carries its own detection limit</h3>

<p>This is the part that is easy to get wrong. The overall detection limit was computed for the
overall comparison at the overall threshold; quoting it beside a per-criterion line it cannot support
is the failure mode here.</p>

<p>So every criterion reports its own, computed at α/k — the strictest rung of the ladder, and the
one a lone signal actually faces. It is <strong>not</strong> automatically wider than the overall
limit: a criterion that few examples flipped on is estimated <em>more</em> precisely, not less, and
the multiplicity price pushes the other way. Both effects are real, so the number is computed rather
than assumed, per criterion, every time.</p>

<div class="callout warn">
  <span class="k">The attribution is only as good as the judge doing the citing</span>
  <p>A judge names one criterion per failing example, so an example that failed Correctness tells you
  nothing about whether it would also have failed Groundedness. A criterion is credited with a
  failure only when it was cited. That is a real limit, and it is the second reason this is reported
  as attribution rather than as a set of independent per-criterion measurements.</p>
</div>

<h2>Did quality hold</h2>

<p>Swapping in a cheaper or smaller model is a different question and reading it the same way will
mislead you. You are not hunting an improvement; you are checking the drop stays inside a tolerance.</p>

<p><strong>Set the margin before the run.</strong> Then read the bottom of the interval against it,
not the middle:</p>

<pre><code>  difference -1.2% [-4.1%, +1.7%]
  <span class="o">INCONCLUSIVE</span></code></pre>

<p>The middle looks fine, barely down. But the range reaches −4.1%, past a three-point tolerance.
<strong>This run has not shown quality held.</strong> It has shown that a drop big enough to matter
is still consistent with what was measured.</p>

<p>Three outcomes: <code>held</code> when the whole interval clears the margin, <code>failed</code>
when it is entirely past it, <code>unresolved</code> when it straddles. Unresolved is not permission
to ship.</p>

<div class="callout warn">
  <span class="k">Why the margin must be pre-registered</span>
  <p>A margin chosen after seeing the interval is not a tolerance, it is a rationalisation. This is
  why the design is written to <code>evals/experiments/</code>, hashed, and approved by a person
  before any traffic, and why editing it afterwards revokes the approval. The discipline is the
  feature; the arithmetic is easy.</p>
</div>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No interim looks, no sequential testing.</strong> The stopping rule in every design is
  "score them all, then read out once". Peeking at a running experiment and stopping when it looks
  good inflates the false-positive rate badly. Always-valid sequential bounds are a real answer to
  this and are not built yet.</li>
  <li><strong>No correction across <em>arms</em>.</strong> The per-criterion breakdown is corrected
  across criteria, because those k tests are run together and we know k. Sweeping ten variants and
  reporting the best is the other multiplicity problem, and this tool does not see it: it compares
  two arms at a time and cannot know how many comparisons you already ran. That correction is yours
  to make, and it is a known way to find an effect that is not there.</li>
  <li><strong>No simultaneous intervals.</strong> Each criterion's interval is at the nominal level,
  so the k of them do not jointly cover at 95%. The correction is applied to the tests, which is what
  gates the attribution; the intervals are printed for magnitude. Reading them as k separate verdicts
  is the mistake the wording is chosen to prevent.</li>
  <li><strong>No continuous or graded outcomes.</strong> Everything here is pass or fail. Retrieval
  metrics like recall@k are continuous and classification is multi-class; both need different tests,
  and that choice is deliberately being made before any code depends on it.</li>
  <li><strong>No bandits over judge scores.</strong> Allocating traffic by a judge's own score
  rewards whatever the judge is biased toward, including verbosity and position. If it is ever done
  here, quality non-inferiority is established first and the bandit runs on cost and latency only.</li>
</ul>

<h2>Further reading</h2>

<ul class="reading">
  <li><strong>Dietterich (1998), "Approximate Statistical Tests for Comparing Supervised
  Classification Learning Algorithms", <em>Neural Computation</em> 10(7), 1895–1923.</strong> The
  closest thing to a direct precedent for what <code>compare</code> does: five candidate tests for
  deciding whether one system beats another on the same data, evaluated for how often they claim a
  difference that is not there. Read it before changing the test.
  <span class="where">doi:10.1162/089976698300017197</span></li>

  <li><strong>McNemar (1947), "Note on the sampling error of the difference between correlated
  proportions or percentages", <em>Psychometrika</em> 12(2), 153–157.</strong> The original, and
  short. The phrase that matters is "correlated proportions": that correlation is the pairing, and
  it is the thing an unpaired test discards.</li>

  <li><strong>Holm (1979), "A simple sequentially rejective multiple test procedure",
  <em>Scandinavian Journal of Statistics</em> 6(2), 65–70.</strong> Six pages, and the procedure the
  per-criterion breakdown uses. The argument worth having is in the opening: the correction costs
  power, and the alternative is not "no correction", it is a correction performed silently by the
  reader. Read it before changing how the criteria are gated.</li>

  <li><strong>Kohavi, Tang and Xu (2020), <em>Trustworthy Online Controlled Experiments</em>,
  Cambridge University Press.</strong> The practitioner's book on running experiments honestly.
  Chapter 17 covers power and sample size; the early chapters on trustworthiness are the reason the
  gates in this tool exist at all. Not open access, but several of the authors' underlying papers are
  free at exp-platform.com.</li>

  <li><strong>Cohen (1988), <em>Statistical Power Analysis for the Behavioral Sciences</em>,
  2nd ed.</strong> Chapter 1 for what power actually means, chapter 6 for proportions. This is the
  ground under the minimum detectable effect, and it is worth reading chapter 1 once even if you
  never touch the formula.</li>

  <li><strong>Piaggio et al. (2012), "Reporting of noninferiority and equivalence randomized trials:
  extension of the CONSORT 2010 statement", <em>JAMA</em> 308(24), 2594–2604.</strong> Open. Written
  for clinical trials, but it is the clearest published treatment of the one thing people get wrong
  about non-inferiority: the margin has to be justified in advance, and a null result is not
  equivalence.</li>
</ul>

<p class="dim">Volumes, issues and page ranges verified against publisher records. Where a claim
could only be confirmed at paper level rather than section level, it is cited at paper level.</p>
"""


REF_TAXONOMY = """
<div class="eyebrow">Reference</div>
<h1>Disagreement taxonomy</h1>
<p class="lede">Six disagreements is a count. This is the part that turns it into something you can
act on, and the part that refuses to when the evidence will not carry it.</p>

<div class="worked">
  <span class="k">The worked example</span>
  <p>The same 40 labelled examples as the <a href="ref-agreement.html">agreement page</a>: your
  judge and you disagreed six times, three misses and three false alarms, a base rate of
  <strong>15%</strong>. Knowing that number tells you nothing about what to change.</p>
</div>

<h2>Two shapes, and they do not cost the same</h2>

<p>Every disagreement is one of two things, named from the judge's point of view.</p>

<div class="scroller"><table>
<thead><tr><th>Shape</th><th>What happened</th><th>What it costs</th></tr></thead>
<tbody>
<tr><td><strong>false alarm</strong></td><td>judge said fail, you said pass</td><td><strong>Trust.</strong> Every one is a person going to look at something that turned out to be fine. Enough of them and nobody reads the reports.</td></tr>
<tr><td><strong>miss</strong></td><td>judge said pass, you said fail</td><td><strong>The whole suite.</strong> These are the regressions that ship. One miss can cost more than fifty false alarms.</td></tr>
</tbody></table></div>

<p>They are reported separately because the fix differs. False alarms usually mean a criterion is
worded too strictly. Misses usually mean the rubric never mentioned the thing that went wrong.</p>

<h2>Which criterion is at fault</h2>

<p>Each <code>###</code> heading in your rubric is one criterion, and the judge names the one it
failed on. Group the disagreements by that name and the six become a diagnosis:</p>

<pre><code>  Directness     2/3 =  66.7%   [20.8%, 93.9%]   2 false alarms
  Groundedness   1/8 =  12.5%   [ 2.2%, 47.1%]   1 false alarm
  Correctness    0/4 =   0.0%   [ 0.0%, 49.0%]</code></pre>

<p>Read the denominators: they are the examples where the judge <em>cited that criterion</em>, not
your suite. So the middle column says <strong>when this judge invokes Directness, it is wrong two
times in three.</strong> That is a rubric edit, and a specific one. Correctness is behaving.</p>

<p>Now read the interval. Two of three rests on <strong>three examples</strong>, and the true rate
is somewhere between 21% and 94%. The direction is worth acting on because the fix is cheap; the
number is not worth quoting to anybody.</p>

<div class="callout warn">
  <span class="k">This axis cannot see misses</span>
  <p>A miss is the judge saying pass. A judge that passed an example named no failing criterion, so
  there is nothing to group by. <strong>Every disagreement in the table above is a false alarm, and
  that is structural rather than a property of this data.</strong></p>
  <p>Which is awkward, because misses are the expensive kind. Attributing them would need the judge
  to report which criteria it considered and cleared, not only the one it failed. The provider shim
  already computes coverage of that shape for a different purpose, so the path exists and is not
  wired up. Until it is, read the criterion table as an account of <em>why your judge cries wolf</em>,
  and nothing more.</p>
</div>

<h2>Which part of your traffic</h2>

<p>The other axis is whatever slice metadata came with your examples. Same six disagreements, cut by
topic:</p>

<pre><code>  returns    3/9  = 33.3%   [12.1%, 64.6%]
  accounts   2/16 = 12.5%   [ 3.5%, 36.0%]
  shipping   1/15 =  6.7%   [ 1.2%, 29.8%]

  base rate across all 40: 15.0%</code></pre>

<p>There it is. <strong>Returns disagrees 33% of the time against a 15% base rate. A 2.2x lift.</strong>
That is the line that sends somebody off to investigate for a day.</p>

<h2>Why the tool will not report that</h2>

<p>Look at the interval on the returns row: <strong>[12.1%, 64.6%]</strong>. The bottom of it,
12.1%, sits <em>below</em> the 15% base rate. The evidence is consistent with returns being no worse
than anything else.</p>

<p>So <code>concentrations()</code> marks it <code>separated: false</code> and the memo leaves it
out. The rule is one line:</p>

<pre><code>  separated = worst.interval.lo &gt; base_rate</code></pre>

<div class="callout warn">
  <span class="k">The most important guard in this codebase</span>
  <p>Every slice report has a worst row. That is arithmetic, not a finding. Sort three topics by
  disagreement rate and one of them is 2.2x the average <em>whatever the data says</em>, because
  something has to be first.</p>
  <p>A tool that names the worst-looking slice every time is a random number generator with good
  manners. It will be right occasionally, which is worse than being wrong reliably, because the
  occasional hit is what convinces people to keep trusting it.</p>
</div>

<p>There is a second guard beside it. A slice with fewer than <code>min_bucket</code> examples,
five by default, is not ranked at all. One disagreement out of two is a 50% rate and a 3.3x lift,
and it is nothing.</p>

<p>When a concentration <em>does</em> separate, it is reported with its interval attached, so you
can see whether "twice as bad on long answers" rests on four examples or four hundred.</p>

<h2>What to do with each finding</h2>

<div class="scroller"><table>
<thead><tr><th>What you see</th><th>What it means</th><th>What to do</th></tr></thead>
<tbody>
<tr><td>One criterion holds most of the false alarms</td><td>That criterion is worded too strictly</td><td>Edit its wording, re-approve, re-run. The rubric hash changes, so this is tracked</td></tr>
<tr><td>Misses dominate and no criterion explains them</td><td>The rubric never mentioned the failure mode</td><td>Read the missed examples and add a criterion</td></tr>
<tr><td>A separated concentration</td><td>One part of your traffic really is harder</td><td>Label more <em>there</em>, or split the suite and calibrate separately</td></tr>
<tr><td>A concentration that did not separate</td><td>You have not learned anything yet</td><td>Nothing. This is the finding you were about to waste a day on</td></tr>
</tbody></table></div>

<div class="incode">
  <div>Computed in <b>src/langchef/core/taxonomy.py</b></div>
  <div><b>Judgement.kind</b> classifies each row as miss, false_alarm, or agreement</div>
  <div><b>by_criterion()</b> groups by the rubric heading the judge cited</div>
  <div><b>by_slice()</b> groups by one metadata dimension, worst rate first</div>
  <div><b>concentrations()</b> ranks dimensions and applies the separation test</div>
  <div><b>summarise()</b> the whole thing as plain data for the memo</div>
</div>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No correction for the number of slices examined.</strong> The separation test is a
  per-slice filter, not a family-wise one. Cut your data forty ways and it is still doing forty
  independent checks. The honest mitigation today is that slice dimensions come from metadata you
  already had, rather than being searched for. If automatic slice discovery is ever added, a
  correction has to arrive with it.</li>
  <li><strong>No interaction terms.</strong> Returns-and-long-answer might be far worse than either
  alone. Finding that reliably needs more labels than anyone is going to give us.</li>
  <li><strong>No causal claim.</strong> A separated concentration says disagreement clusters there.
  It does not say the topic caused it. Returns questions may simply be longer, and length may be
  the real driver.</li>
  <li><strong>No automatic rubric editing.</strong> The taxonomy points at a criterion. A person
  writes the new wording and approves it. A tool that rewrites the definition of "good" in response
  to its own error pattern is optimising for its own agreement.</li>
  <li><strong>Misses are not attributed</strong>, as above. This is the largest gap on the page.</li>
</ul>

<h2>Further reading</h2>

<ul class="reading">
  <li><strong>ISIS-2 Collaborative Group (1988), <em>The Lancet</em> 332(8607), 349–360.</strong>
  The single best argument for the separation test, and it is funny. Reporting subgroup results for
  aspirin after heart attack, the authors listed <strong>astrological birth sign first</strong> in
  the table, showing the drug to be useless for the roughly 3,000 patients born under Gemini or
  Libra. That placement was deliberate and negotiated with the journal: the authors agreed to print
  subgroup analyses only if the star signs came first, so readers could see for themselves what such
  analyses are worth. Every slice table you will ever read has a worst row.
  <span class="where">Context: annalsofoncology.org, "From astrology to prostate cancer: what is the role of subgroup analyses?"</span></li>

  <li><strong>Gelman and Loken (2014), "The Statistical Crisis in Science", <em>American
  Scientist</em> 102(6), 460.</strong> The garden of forking paths: you do not need to run forty
  tests to get a false positive, you only need to have <em>chosen which one to run</em> after seeing
  the data. Directly why <code>concentrations()</code> applies a fixed rule to every dimension
  rather than letting anyone pick the interesting one.
  <span class="where">Open PDF: sites.stat.columbia.edu/gelman/research/published/ForkingPaths.pdf</span></li>

  <li><strong>"On Looking at Subgroups", <em>Circulation</em> (2008).</strong> A short practitioner
  treatment of when a subgroup finding is worth believing: pre-specified, biologically plausible,
  one of few, and large. Our slices meet the first and third by construction and rarely the fourth.
  <span class="where">doi:10.1161/CIRCULATIONAHA.108.836601</span></li>

  <li><strong>Wilson (1927) and Brown, Cai and DasGupta (2001).</strong> The interval behind the
  separation test, covered on the <a href="ref-agreement.html#the-interval-and-why-wilson">agreement
  page</a>. Worth reading if you intend to change the test, because the guard is only as good as the
  lower bound it compares.</li>
</ul>

<p class="dim">Citations verified against publisher records. Where only a section could be
confirmed, a section is what is cited.</p>
"""


REF_SAMPLING = """
<div class="eyebrow">Reference</div>
<h1>Label planning</h1>
<p class="lede">Which forty examples a person should spend their ten minutes on, why it is not a
random forty, and the open question about what those labels can then be used to claim.</p>

<div class="worked">
  <span class="k">The worked example</span>
  <p>Ninety scored examples. The judge failed fifteen of them. You have time for forty labels.</p>
<pre><code>  langchef label plan --budget 40

  selected 40 of 90
    fail stratum   15   (every one the judge flagged)
    pass stratum   25
  19 of the 40 chosen because the judge was unsure</code></pre>
</div>

<h2>Why not just take forty at random</h2>

<p>Because of where the information is. Pick forty of these ninety at random and you would expect
about <strong>6.7</strong> of them to be examples the judge flagged. Your entire catch rate would
rest on six or seven labels, and its interval would be so wide the number could not support a
decision.</p>

<p>Stratifying by the judge's own verdict takes <strong>all fifteen</strong> instead. Same ten
minutes, same forty labels, and the number you most need is measured on more than twice the
evidence.</p>

<p>That gap widens sharply as suites get more realistic. On a production suite where the judge flags
<strong>2%</strong>, a random forty contains fewer than one flagged example on average. The catch
rate is not merely imprecise, it does not exist.</p>

<h2>Why the judge's uncertain cases come first</h2>

<p>Within each stratum the plan sorts by the judge's own confidence and takes the least confident
first. Nineteen of the forty above were chosen that way.</p>

<p>The reasoning is that a label is worth what it changes. A case the judge scored 0.98 will almost
certainly agree with you, and confirms what you already believed. A case it scored 0.51 is where two
candidate rubrics give different answers, so labelling it settles something.</p>

<p>This is uncertainty sampling, the oldest idea in active learning, and it is very good at the job
it is built for: <strong>improving the instrument</strong>. Keep that phrase, because the rest of
this page turns on it.</p>

<h2>The same plan every time</h2>

<p>Ties break on <code>sha256(seed + example_id)</code> rather than on list order or a random draw.
So the same run and the same budget produce the same forty on any machine, in any order the scores
arrived, and a plan can be regenerated without re-labelling anything. A labelling plan that
shuffles when you re-run it is a plan nobody can pick up halfway.</p>

<div class="callout warn">
  <span class="k">The open question, and it is a real one</span>
  <p>Each selected row carries a <code>weight</code>, the stratum size over the number taken. It
  looks like an inclusion weight, the kind that lets you scale a sample back up to the population.
  <strong>It is not one, and the rates on the calibration report are not population estimates.</strong></p>
  <p>The reason is on this page. Selection inside a stratum is not random: it takes the lowest
  confidence rows deterministically. So a row's chance of being picked is 0 or 1 given its
  confidence rank, not <code>n/N</code>. Post-stratification cannot repair that, because the
  selection tracks the very thing being estimated, and confidence tracks disagreement almost by
  definition.</p>
  <p>A seeded coverage simulation contributed on
  <a href="@@repo@@/issues/30">#30</a> put a nominal 95% interval at <strong>43% actual coverage for
  the catch rate</strong>, and at 100% for the true negative rate, which is the opposite failure and
  just as useless.</p>
  <p><strong>Read the calibration numbers as describing the forty examples you labelled</strong>,
  not as an estimate of your whole suite. The underlying question is whether one label budget can
  buy estimation and diagnosis at once, and it is open at
  <a href="@@repo@@/issues/60">#60</a>. It probably cannot, in which case the plan splits into a
  random part for measuring and an uncertainty-selected part for diagnosing.</p>
</div>

<h2>What the reasons mean</h2>

<p>Every selected row says why it was picked, because a person labelling forty things deserves to
know which ones are load-bearing.</p>

<div class="scroller"><table>
<thead><tr><th>Reason</th><th>Means</th></tr></thead>
<tbody>
<tr><td><code>judge was unsure</code></td><td>Low confidence, and in the first half of its stratum. These are the ones most likely to change a rubric</td></tr>
<tr><td><code>stratum coverage (fail)</code></td><td>Here to keep the flagged stratum full, which is what holds the catch rate up</td></tr>
<tr><td><code>stratum coverage (pass)</code></td><td>Here to keep the false alarm rate measurable</td></tr>
</tbody></table></div>

<div class="incode">
  <div>Computed in <b>src/langchef/core/sampling.py</b></div>
  <div><b>plan()</b> the split, the ordering, and the weight on each row</div>
  <div><b>_tiebreak()</b> hashed ordering, so the plan is stable across machines</div>
  <div><b>summarise()</b> what the plan did, for the person about to label</div>
</div>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No adaptive re-planning mid-budget.</strong> The plan is computed once from the scores.
  Choosing the next example based on labels already given would be closer to real active learning
  and would make the sample even harder to reason about statistically than it already is.</li>
  <li><strong>No stratification on anything but the judge's verdict.</strong> Not topic, not length,
  not customer. Those are the slice dimensions the <a href="ref-taxonomy.html">taxonomy</a> reports
  along, and stratifying on the same axis you later test for concentration would bias the test.</li>
  <li><strong>No more than two strata.</strong> Verdicts are pass or fail here. Task classes with
  ordered or multi-class labels need a different design, which is part of the open work.</li>
  <li><strong>No estimate of how many labels you need.</strong> The plan spends the budget you give
  it. Whether forty is enough for the claim you want to make is exactly what
  <a href="@@repo@@/issues/60">#60</a> is about, and the honest answer today is that we do not
  know.</li>
</ul>

<h2>Further reading</h2>

<ul class="reading">
  <li><strong>Cochran (1977), <em>Sampling Techniques</em>, 3rd ed., chapter 5.</strong> Stratified
  random sampling, including the arithmetic for why unequal allocation beats proportional allocation
  when one stratum is both small and important, which is precisely the flagged stratum here. Chapter
  5A covers the estimator that would apply if selection within strata were random. Read it alongside
  <a href="@@repo@@/issues/60">#60</a>, because it is the design we may be moving toward.</li>

  <li><strong>Settles (2009), "Active Learning Literature Survey", University of Wisconsin–Madison
  Computer Sciences Technical Report 1648.</strong> The standard reference for why you would pick
  uncertain cases at all. The uncertainty sampling section is the direct precedent for what
  <code>plan()</code> does. Worth reading with the tension on this page in mind: that literature is
  about training a better model, not about producing an unbiased estimate of how good one is, and
  those goals pull in opposite directions.
  <span class="where">Open PDF: minds.wisconsin.edu/bitstream/handle/1793/60660/TR1648.pdf</span></li>

  <li><strong>Kish (1965), <em>Survey Sampling</em>.</strong> The origin of the design effect and the
  effective sample size that a weighted sample carries. Relevant here mostly as a caution: the
  Kish-effective interval was the first thing tried for this problem and it failed its coverage
  check badly, which is documented on <a href="@@repo@@/issues/30">#30</a>.</li>

  <li><strong>Brown, Cai and DasGupta (2001).</strong> The interval used on whatever sample you end
  up with, covered on the
  <a href="ref-agreement.html#the-interval-and-why-wilson">agreement page</a>.</li>
</ul>

<p class="dim">Citations verified against publisher records. Where only a section could be
confirmed, a section is what is cited.</p>
"""


REF_JUDGING = """
<div class="eyebrow">Reference</div>
<h1>Judging and pins</h1>
<p class="lede">The judge is a measuring instrument, not a metric. This page is how one is defined,
how it is pinned so two runs can be compared, and how it is stopped from spending money you did not
agree to.</p>

<div class="worked">
  <span class="k">The worked example</span>
  <p>One example, scored against a two-criterion rubric by the judge that ships in the box.</p>
<pre><code>  question   Do you ship to Canada?
  answer     Yes, standard shipping to Canada takes 5-7 business days.
  context    We ship to Canada. Standard delivery is 5-7 business days.

  verdict     fail
  confidence  0.6
  criterion   Groundedness
  rationale   40% of the answer's content words appear in the retrieved context</code></pre>
  <p>Three things to notice. It named <strong>which criterion</strong> failed, which is what makes
  the <a href="ref-taxonomy.html">taxonomy</a> possible. It gave a <strong>confidence</strong>,
  which is what drives escalation and label planning. And it gave a <strong>rationale you can
  argue with</strong>, which is what makes a wrong verdict findable.</p>
</div>

<h2>The rubric is the definition of good</h2>

<p>A rubric is Markdown. Each <code>###</code> heading is one criterion, and the judge must name the
one it failed on.</p>

<pre><code>### Groundedness
Every claim traceable to the context.

### Correctness
Answers the question asked.</code></pre>

<pre><code>  criteria parsed:  ('Groundedness', 'Correctness')
  rubric ref:       support@4f2f2ee68288</code></pre>

<p>That <code>ref</code> is a name plus a content hash, and it is the pin for the rubric. Change
three words in one criterion and it moves:</p>

<pre><code>  support@4f2f2ee68288   ->   support@d7f133b168ab</code></pre>

<p>Which is the point. Editing a rubric changes what "good" means, so it revokes its own approval
and invalidates every cached verdict produced under the old wording. You cannot quietly loosen the
definition and compare against last week.</p>

<div class="callout warn">
  <span class="k">A judge can only cite criteria you wrote</span>
  <p>In the worked example the rubric has Groundedness and Correctness and no criterion about
  hedging. Feed it <em>"I'm not able to say for certain whether we ship to Canada"</em> and it
  returns <code>fail</code> against <strong>Correctness</strong>, because that is the closest thing
  in your rubric to what went wrong.</p>
  <p>The verdict is right and the attribution is misleading, and no amount of calibration will
  surface it, because you and the judge agree on the verdict. If your taxonomy keeps blaming one
  criterion for unrelated failures, the rubric is missing a criterion.</p>
</div>

<h2>Pins: what produced these numbers</h2>

<p>Every run records the instrument that produced it.</p>

<div class="scroller"><table>
<thead><tr><th>Field</th><th>Why it is in the pin</th></tr></thead>
<tbody>
<tr><td><code>rubric</code></td><td>The name and content hash. A different definition of good is a different measurement</td></tr>
<tr><td><code>provider</code></td><td>Which backend produced the verdicts</td></tr>
<tr><td><code>cheap_model</code></td><td>The model that scored everything</td></tr>
<tr><td><code>strong_model</code></td><td>The model that re-scored the unsure ones, if any</td></tr>
</tbody></table></div>

<p>Compare two runs whose pins differ and the tool <strong>exits 5 and refuses</strong>, naming what
moved:</p>

<pre><code>  pin moved — cheap_model: 'gpt-4o-mini' -> 'claude-haiku-4-5'</code></pre>

<p>This is the difference between measuring a change in your app and measuring a change in your
ruler. Both look like a moving number. Only one of them is a finding.</p>

<h2>The cache, and what is in the key</h2>

<p>Verdicts are content-addressed. The key covers everything that changes what a correct verdict
<em>is</em>:</p>

<pre><code>  example_id, question, answer, context, expected, rubric ref, model, tier</code></pre>

<p><strong>Slices are deliberately not in the key.</strong> They are metadata for grouping, so
adding a <code>topic</code> tag to your examples would otherwise invalidate every cached verdict
and re-buy the whole run for nothing.</p>

<p>Tier is in the key, so the same example judged cheaply and judged strongly are two entries rather
than one overwriting the other:</p>

<pre><code>  cheap tier   fd3da9b9f7259e30...
  strong tier  47eb382ec2f5e922...</code></pre>

<p>The practical effect is that re-running an arm after a change is nearly free, and only genuinely
new work costs anything. It is also why the integrity gates exist: with a warm cache, re-running an
arm until it reads out better costs nothing, which is exactly why <code>readout</code> refuses when
more than one run matches.</p>

<h2>Two tiers</h2>

<p>A cheap model scores every example. Anything it scored <strong>below 0.6</strong> is re-scored by
a strong model, and only those.</p>

<p>The confidence in the worked example is exactly 0.6, so it would not escalate. The threshold is
a floor, not a ceiling.</p>

<p>This was built in from the start rather than added later, for a specific reason: <strong>the
model is part of the cache key.</strong> Retrofitting a second tier would have invalidated every
cached verdict in every workspace on the day it shipped.</p>

<h2>Budgets, and stopping before the bill</h2>

<p>A run can carry a ceiling on <em>provider calls</em>, not on examples. A cached example is free
and does not count against it.</p>

<p>When the ceiling is hit the run stops where it is, writes what was left unscored to
<code>runs/&lt;id&gt;/undone.json</code>, and <strong>exits 4</strong>. It does not silently produce
a partial result that looks whole.</p>

<p>The reasoning is that a partial result whose shape you know is worth more than a bill you did not
agree to. An agent handed exit 4 knows to stop and ask rather than to retry.</p>

<h2>The judge in the box</h2>

<p>The default provider is not a model. It is deterministic token containment: what fraction of the
answer's content words appear in the retrieved context, and does the expected string appear. It
needs <strong>no API key, no network, and no money</strong>.</p>

<p>It is genuinely weak, and that is deliberate. It exists so the whole pipeline can be run,
tested and dogfooded end to end before anyone spends anything, and so the test suite never depends
on a provider being up. Its version string is part of the cache key, so changing its checks without
bumping that version would leave every warm cache serving verdicts from the old logic.</p>

<div class="incode">
  <div><b>src/langchef/judge/rubric.py</b> — parse, criteria, digest, ref</div>
  <div><b>src/langchef/judge/providers.py</b> — the single seam a backend plugs into</div>
  <div><b>src/langchef/judge/cache.py</b> — <b>judgement_key()</b>, what is and is not in it</div>
  <div><b>src/langchef/judge/runner.py</b> — <b>Pin</b>, escalation, the budget ceiling</div>
</div>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No position or verbosity mitigation.</strong> Model judges favour the first answer
  shown and longer answers regardless of content. We do not swap positions or normalise length. The
  defence here is different: calibration measures how far your judge disagrees with you, so a judge
  with a verbosity bias shows up as a bad kappa rather than as a silent skew. That is a weaker
  defence than fixing the bias, and it is honest about being one.</li>
  <li><strong>No model grading its own family's output.</strong> Self-enhancement bias is real. If
  the judge and the system under test share a model family, calibrate before believing anything.</li>
  <li><strong>No scores, only verdicts.</strong> Pass or fail, with a confidence. A judge returning
  7.4 out of 10 invites arithmetic that its own precision cannot support.</li>
  <li><strong>No prompt tuning loop.</strong> Nothing here rewrites your rubric to improve
  agreement. A tool that edits the definition of good in response to its own error rate is
  optimising for its own agreement, and the number stops meaning anything.</li>
  <li><strong>No retries on a disagreeing verdict.</strong> Asking again until it agrees is not
  measurement.</li>
</ul>

<h2>Further reading</h2>

<ul class="reading">
  <li><strong>Zheng et al. (2023), "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena",
  arXiv:2306.05685.</strong> Read <strong>§3.1, Limitations</strong>, before trusting any judge you
  have not calibrated. It catalogues position bias, verbosity bias and self-enhancement bias, and
  demonstrates the verbosity one with a repetitive-list attack that fools several judges. This is
  the paper that makes the case for this whole product: the instrument has known, measurable,
  reproducible faults.
  <span class="where">Open PDF: arxiv.org/pdf/2306.05685</span></li>

  <li><strong>Gu et al. (2024), "A Survey on LLM-as-a-Judge", arXiv:2411.16594.</strong> Broader and
  more recent, for when you want the landscape rather than one careful study.</li>

  <li><strong>The calibration statistics</strong> on the
  <a href="ref-agreement.html">agreement page</a>. Every claim on this page about a judge being
  trustworthy is settled there, not here.</li>
</ul>

<p class="dim">Citations verified against publisher records. Where only a section could be
confirmed, a section is what is cited.</p>
"""


REF_DESIGN = """
<div class="eyebrow">Reference</div>
<h1>Designing a run</h1>
<p class="lede">The experiment lifecycle in full: design, approve, check, read out. Every output on
this page is real, captured from a workspace built from scratch, including the refusals.</p>

<p><a href="start.html">Start here</a> walks the whole product in nine steps and spends about a
minute on this part. This page is the other half: what each of these four commands actually writes,
what it refuses and why, and what the file on disk looks like at every stage.</p>

<h2>Where this sits in a whole run</h2>

<p>Designing is step nine of thirteen, and the eight before it are what make it mean anything.</p>

<div class="scroller"><table>
<thead><tr><th></th><th>Command</th><th>What it is for</th></tr></thead>
<tbody>
<tr><td class="num">1</td><td><code>langchef init</code></td><td>Scaffold the workspace</td></tr>
<tr><td class="num">2</td><td>collect examples</td><td>50–100 from real traffic</td></tr>
<tr><td class="num">3</td><td>write the rubric</td><td><a href="ref-judging.html#the-rubric-is-the-definition-of-good">Judging and pins</a></td></tr>
<tr><td class="num">4</td><td><code>langchef approve rubric</code></td><td><strong>Gate one.</strong> Judging refuses at exit 2 without it</td></tr>
<tr><td class="num">5</td><td><code>langchef judge run</code></td><td><a href="ref-judging.html">Judging and pins</a></td></tr>
<tr><td class="num">6</td><td><code>langchef label plan</code></td><td><a href="ref-sampling.html">Label planning</a></td></tr>
<tr><td class="num">7</td><td>label them yourself</td><td>The only part nobody can automate</td></tr>
<tr><td class="num">8</td><td><code>langchef calibrate report</code></td><td><a href="ref-agreement.html">Agreement</a>, <a href="ref-taxonomy.html">taxonomy</a></td></tr>
<tr><td class="num"><strong>9</strong></td><td><strong><code>experiment design</code></strong></td><td><strong>From here down is this page</strong></td></tr>
<tr><td class="num"><strong>10</strong></td><td><strong><code>experiment approve</code></strong></td><td>Gate two</td></tr>
<tr><td class="num"><strong>11</strong></td><td><code>judge run --arm variant</code></td><td>The other arm, same pin</td></tr>
<tr><td class="num"><strong>12</strong></td><td><strong><code>experiment readout</code></strong></td><td><a href="ref-compare.html">Comparing two arms</a></td></tr>
<tr><td class="num">13</td><td><code>langchef memo write</code></td><td>One page a person can disagree with</td></tr>
</tbody></table></div>

<p><strong>If your task has a hard target</strong>, steps 3 to 8 do not apply and the run is 1, 2,
then 9 to 13. <a href="index.html#which-of-these-are-you">Which one am I?</a></p>

<h2>Step 9 — design</h2>

<p>You have 90 goldens, a scored baseline, and you want to move to the replacement model. You care
about a five point change.</p>

<pre><code>langchef experiment design --suite support --variant-arm variant \
  --intent "move to the replacement model" --target-effect 0.05 --id model-swap</code></pre>

<p>Prose to stderr, for you:</p>

<pre><code>2 candidate design(s) for support: move to the replacement model
 -&gt; as-it-stands   n=90     detects &gt;=13.2%    0 judge call(s)
      note: These goldens cannot resolve 5.0%. The smallest effect this
            design could detect is 13.2%; a real change below that will
            come back inconclusive.
    powered        n=628    detects &gt;=5.0%   538 judge call(s)
      note: Needs 538 more golden(s) than the suite has (90). Collect them
            before running, or accept the detection limit of the design above.</code></pre>

<p>The arrow marks the one recorded. <code>--accept powered</code> records the other. Neither is a
refusal: choosing the 13.2% design knowingly is a fine decision, and choosing it <em>without
knowing</em> is the thing this prevents.</p>

<h3>What it writes</h3>

<p>A TOML file in <code>evals/experiments/</code>, reviewed like code:</p>

<pre><code># LangChef pre-registration.
#
# Written before the run and reviewed like code. Editing anything below
# changes the digest and revokes the approval, which is the point: an
# experiment whose design moved after the traffic is not an experiment.

[experiment]
baseline_arm = "baseline"
variant_arm = "variant"
hypothesis = "move to the replacement model"
kind = "superiority"
n = 90
mde = 0.13206799371997818
target_effect = 0.05
power = 0.8
level = 0.95
discordance_assumed = 0.2
discordance_source = "assumed default (20%) — no prior comparison here"
rubric = "answer-quality@290335165c70"
stopping_rule = "Score all 90 goldens in both arms, then read out once. No
  interim looks: stopping early when a result looks good is the most common
  way an experiment reports an effect that is not there."
guardrails = [
  "The rubric must still be answer-quality@290335165c70 at run time; a changed rubric revokes approval.",
  "Both arms must be scored under the same pin, or compare exits 5.",
  "Calibration must exist for this judge; a memo without it says so in full.",
]

[budget]
judge_calls = 0
source = "the design's own estimate"</code></pre>

<p>There is no <code>[approval]</code> block yet. That is the next step and a separate one.</p>

<div class="callout warn">
  <span class="k">It will not overwrite one</span>
  <p>Run the same command with the same <code>--id</code> again and it refuses:</p>
  <pre><code>model-swap.toml already exists — pass a different --id, or delete it
deliberately. Overwriting a pre-registration silently is how one stops
meaning anything.</code></pre>
</div>

<h2>Step 10 — approve, which is gate two</h2>

<p>Try to read out first and you get refused, at <strong>exit 2</strong>:</p>

<pre><code>langchef experiment readout model-swap        # exit 2

langchef: refused — an approval gate is unmet — experiment model-swap has not
been approved — review the design, then run:
  langchef experiment approve model-swap</code></pre>

<p>Approving appends a block and nothing else:</p>

<pre><code>[approval]
digest = "3f1053d32846"
at = "2026-08-28T17:16:21+00:00"
by = "human"</code></pre>

<p>That digest is a hash of the body <strong>excluding the <code>[approval]</code> block</strong>,
which is what lets approval be recorded in the same file without changing what was approved.</p>

<h3>Editing it afterwards revokes it, with nobody watching</h3>

<p>Change one number in the design and leave the approval block alone:</p>

<pre><code>-target_effect = 0.05
+target_effect = 0.15</code></pre>

<pre><code>langchef experiment readout model-swap        # exit 2

langchef: refused — an approval gate is unmet — the design for model-swap
changed since it was approved (3f1053d32846 -&gt; 510086cece38). Re-read it,
then run: langchef experiment approve model-swap</code></pre>

<p><strong>It names both digests.</strong> You cannot widen a margin, drop a guardrail or move a
target after seeing the numbers and still hold an approval. The whole mechanism is a hash over the
body and about eight lines of code.</p>

<h2>Step 11 — score the other arm</h2>

<pre><code>langchef judge run --suite support --arm variant --run-id var-1 \
  --experiment model-swap

judge: n=90  provider_calls=24  cache_hits=66  cache_misses=24
       fail=42  pass=48  fail_rate=0.467  budget_exhausted=False  unscored=0</code></pre>

<p><strong>24 calls, 66 cache hits.</strong> Only the answers that actually changed needed judging,
because verdicts are content-addressed on the example and the rubric.
<a href="ref-judging.html#the-cache-and-what-is-in-the-key">How the key works</a>.</p>

<p><code>--experiment</code> links the run to the pre-registration and applies its budget. Hit the
ceiling and the run stops, writes what is left to <code>runs/&lt;id&gt;/undone.json</code>, and
exits <strong>4</strong> rather than returning a partial result that looks whole.</p>

<h2>Step 12 — read out</h2>

<pre><code>langchef experiment readout model-swap        # exit 0

readout for model-swap@3f1053d32846 on 90 shared golden(s)
  difference -26.7% [-35.6%, -17.8%]
  REGRESSION
  -&gt; evals/runs/var-1/readout.json</code></pre>

<p>The JSON an agent reads carries the working, not only the verdict:</p>

<pre><code>{
  "experiment_id": "model-swap",
  "design_digest": "3f1053d32846",
  "baseline_run": "base-1",
  "baseline_rate": 0.8,
  "difference": -0.2666666666666667,
  "interval": {"lo": -0.3555, "hi": -0.1777, "level": 0.95},
  "discordance": {"broke": 24, "fixed": 0, "both_pass": 48, "both_fail": 18},
  "discordant": 24,
  "exploratory": false,
  "improvement": false,
  "inconclusive": false
}</code></pre>

<p><code>design_digest</code> ties the result to the exact design that was approved. The
<code>discordance</code> block is the evidence: 66 goldens agreed under both arms and carry no
information, <strong>24 broke and none were fixed</strong>, and that is what the verdict rests on.
<a href="ref-compare.html#why-paired-and-not-two-samples">Why only those 24 matter</a>.</p>

<p><code>exploratory: true</code> appears when a run departed from its design. The result is still
printed, and it recommends no decision.</p>

<h2><code>experiment check</code> and <code>list</code></h2>

<p><code>check</code> answers "does what I have match what was registered", and reports rather than
decides:</p>

<pre><code>langchef experiment check model-swap          # exit 0

model-swap@3f1053d32846: approved
  the run matches the pre-registration</code></pre>

<pre><code>langchef experiment list

1 pre-registration(s)
  model-swap                   approved   n=90</code></pre>

<div class="callout warn">
  <span class="k">A known gap in <code>check</code></span>
  <p>Run <code>check</code> against an experiment whose variant arm was <em>never scored at all</em>
  and it still reports <code>the run matches the pre-registration</code> at exit 0, with
  <code>variant_run: null</code> in the payload. It is verifying the approval, not the existence of
  a run. Read <code>variant_run</code> rather than the sentence until this is fixed.</p>
</div>

<h2>Why two candidates and not one answer</h2>

<p>The first uses the goldens you have and says what they can resolve. The second appears only when
you named a target the first cannot reach, and it is usually the more useful, because <strong>"you
need 628 examples and you have 90" is an answer, where a shrug is not.</strong></p>

<p>The failure without it is running the underpowered version, getting "no significant difference",
and reading that as "no difference". Those are not the same sentence.</p>

<h2>The number that governs everything</h2>

<pre><code>  detect 20.0%   ->  n =    40
  detect 10.0%   ->  n =   157
  detect  5.0%   ->  n =   628
  detect  2.5%   ->  n =  2512</code></pre>

<p><strong>Halving the effect you want to detect costs roughly four times the examples.</strong> That
is the shape of the arithmetic rather than a property of this tool, and it is why "collect more
goldens" stops being advice quite quickly.</p>

<p>It is computed from the <em>discordant</em> rate, not the pass rate, because the comparison is
paired. With no prior comparison, 20% is assumed and <code>discordance_source</code> says so. Run
the arms once and the next design uses your real rate: the example above came back with 24
discordant of 90, so the next design for this suite starts from 26.7% rather than the guess.</p>

<h2>What a design fixes, and why each one</h2>

<div class="scroller"><table>
<thead><tr><th>Field</th><th>Why it is decided in advance</th></tr></thead>
<tbody>
<tr><td><code>n</code>, <code>mde</code></td><td>So "inconclusive" reads as "this could never have seen it" rather than "no effect"</td></tr>
<tr><td><code>margin</code></td><td>A tolerance chosen after seeing the interval is not a tolerance, it is a rationalisation</td></tr>
<tr><td><code>stopping_rule</code></td><td>Score everything, read out once. Stopping early when it looks good is the most common way an experiment reports an effect that is not there</td></tr>
<tr><td><code>guardrails</code></td><td>What must not get worse while you chase the thing you are chasing</td></tr>
<tr><td><code>rubric</code></td><td>Pinned by hash, so a changed definition of good revokes the approval</td></tr>
<tr><td><code>cost</code></td><td>Calls always, money only if a price was configured. Inventing a price is worse than admitting the gap</td></tr>
</tbody></table></div>

<h2>Non-inferiority refuses without a margin</h2>

<pre><code>a non-inferiority design needs --margin: how much quality you are
willing to lose. Deciding it after the run is not a design.</code></pre>

<p>With a three point margin on these 90 goldens you get the same two-candidate shape and a second
caveat worth reading twice:</p>

<pre><code>[as-it-stands]  n=90     detects 13.2%
  ! Quality holds only if the whole interval clears −3.0%.
    The point estimate is not the test.

[powered]       n=1745   detects  3.0%</code></pre>

<h2>The gates, as exit codes</h2>

<p>A rule in a prompt is a suggestion, and an agent can talk itself past one. These are exit codes.</p>

<div class="scroller"><table>
<thead><tr><th>Code</th><th>When</th><th>Meaning</th></tr></thead>
<tbody>
<tr><td class="num"><strong>2</strong></td><td>no approved design, the design moved since approval, or more than one run matches an arm</td><td>Refused. Reading out whichever run ran last is how an experiment gets repeated until it says something better</td></tr>
<tr><td class="num"><strong>5</strong></td><td>the two runs were produced under different pins</td><td>Refused. You would be comparing two rulers, not two systems</td></tr>
<tr><td class="num"><strong>4</strong></td><td>the agreed call budget ran out</td><td>Stopped. What is unscored goes to <code>undone.json</code></td></tr>
</tbody></table></div>

<div class="incode">
  <div><b>src/langchef/core/design.py</b> — <b>propose()</b>, <b>required_n()</b>, <b>estimate_cost()</b></div>
  <div><b>src/langchef/workspace/experiments.py</b> — the TOML, and <b>digest()</b> over the body without the approval</div>
  <div><b>src/langchef/cli/design_cmd.py</b> — design, approve, check, readout, list</div>
  <div><b>src/langchef/core/gates.py</b> — gate one on the rubric, gate two on the experiment</div>
</div>

<h2>What we deliberately do not do</h2>

<ul>
  <li><strong>No sequential or always-valid designs.</strong> Score everything, read out once.
  Peeking and stopping when it looks good inflates the false positive rate badly. Always-valid
  confidence sequences are the real answer and are not built.</li>
  <li><strong>No multi-arm designs.</strong> Two arms at a time. Sweeping five variants and
  reporting the winner without correction finds effects that are not there.</li>
  <li><strong>No automatic approval.</strong> An agent can design and check. It cannot approve.
  That step is where a person accepts a cost and a claim, and automating it would remove the only
  human in the loop.</li>
  <li><strong>No cost model beyond calls times a price you supply.</strong> No token estimation, no
  provider price list to go stale. <code>usd</code> stays <code>null</code> until you configure a
  price.</li>
  <li><strong>No boolean for "is this design sensible".</strong> <code>runnable_now</code> says
  whether it can be executed with the goldens that exist and <code>shortfall</code> says how many
  more are needed. Whether 538 more goldens are worth collecting is a judgement, and the tool
  declines to encode one.</li>
</ul>

<h2>Further reading</h2>

<ul class="reading">
  <li><strong>Nosek, Ebersole, DeHaven and Mellor (2018), "The preregistration revolution",
  <em>PNAS</em> 115(11), 2600–2606.</strong> Why the approval step exists at all: the distinction
  between generating a hypothesis from observations and testing one with new observations is not
  respected in practice, and the cost is credibility. Open access, and short.
  <span class="where">doi:10.1073/pnas.1708274114</span></li>

  <li><strong>Kohavi, Tang and Xu (2020), <em>Trustworthy Online Controlled Experiments</em>,
  chapter 17.</strong> Power and sample size as practitioners meet them. The earlier chapters on
  trustworthiness are why the gates here are exit codes rather than advice.</li>

  <li><strong>Cohen (1988), <em>Statistical Power Analysis for the Behavioral Sciences</em>,
  chapters 1 and 6.</strong> The ground under <code>required_n()</code>.</li>

  <li><strong>The arithmetic</strong> lives on the
  <a href="ref-compare.html#the-smallest-change-you-could-have-seen">comparison page</a>. This page
  is the process around it.</li>
</ul>

<p class="dim">Every command output on this page was captured from a real workspace built from
scratch, refusals included. Citations verified against publisher records.</p>
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
<tr><td class="mono">langchef calibrate diff</td><td>After changing the rubric. Tells you whether the change helped.</td></tr>
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
    # concepts.html is NOT redirected any more. It briefly pointed at
    # numbers.html after the August rewrite, and now names a real page again:
    # the concept scaffolding. An old bookmark for "concepts" landing on
    # Concepts is the right outcome, so the URL is reclaimed rather than
    # forwarded. Anything added here must not collide with a page in NAV.
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


SEARCH_JS = """// Sidebar search. No dependency and no build step: the index is generated by
// scripts/build_docs.py from the rendered pages, so it cannot drift from them.
(function () {
  var box = document.getElementById("q");
  var out = document.getElementById("results");
  var nav = document.getElementById("nav");
  if (!box || !out || !nav) return;
  var index = null;

  fetch("search-index.json")
    .then(function (r) { return r.json(); })
    .then(function (d) { index = d; })
    .catch(function () { box.placeholder = "Search unavailable"; box.disabled = true; });

  function render(hits, query) {
    if (!query) { out.hidden = true; nav.hidden = false; return; }
    nav.hidden = true;
    out.hidden = false;
    if (!hits.length) { out.innerHTML = '<p class="none">No match for \u201c' + query + '\u201d.</p>'; return; }
    var html = "", page = null;
    hits.slice(0, 24).forEach(function (h) {
      if (h.page !== page) { page = h.page; html += "<h5>" + h.page + "</h5>"; }
      html += '<a href="' + h.href + '">' + h.title + "</a>";
    });
    out.innerHTML = html;
  }

  function search(query) {
    if (!index) return [];
    var terms = query.toLowerCase().split(/\\s+/).filter(Boolean);
    var scored = [];
    for (var i = 0; i < index.length; i++) {
      var e = index[i];
      var hay = (e.title + " " + e.page + " " + e.text).toLowerCase();
      var score = 0, ok = true;
      for (var t = 0; t < terms.length; t++) {
        if (hay.indexOf(terms[t]) === -1) { ok = false; break; }
        score += e.title.toLowerCase().indexOf(terms[t]) !== -1 ? 4 : 1;
      }
      if (ok) scored.push({ e: e, score: score });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.map(function (r) { return r.e; });
  }

  var timer;
  box.addEventListener("input", function () {
    clearTimeout(timer);
    var q = box.value.trim();
    timer = setTimeout(function () { render(search(q), q); }, 80);
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "/" && document.activeElement !== box) { ev.preventDefault(); box.focus(); }
    if (ev.key === "Escape" && document.activeElement === box) {
      box.value = ""; render([], ""); box.blur();
    }
  });
})();
"""


def anchored(markup: str) -> str:
    """Give every h2 and h3 an id, so a search result can land on the heading."""

    def add(match):
        level, attrs, inner = match.group(1), match.group(2), match.group(3)
        if "id=" in attrs:
            return match.group(0)
        text = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
        return f'<h{level}{attrs} id="{slug}">{inner}</h{level}>'

    return re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", add, markup, flags=re.S)


def search_index(pages: dict[str, str]) -> str:
    """Every heading on every page, as one flat searchable list.

    Generated from the rendered HTML rather than maintained by hand, for the same
    reason the command table is: an index that can disagree with the pages it
    indexes is worse than no index.
    """
    entries = []
    for name, markup in sorted(pages.items()):
        if not name.endswith(".html"):
            continue
        found = re.search(r"<title>(.*?)</title>", markup)
        page_title = html.unescape(found.group(1)) if found else name
        page_title = page_title.replace(" — LangChef", "").strip() or "LangChef"
        body = markup.split("<main>", 1)[-1].split("</main>", 1)[0]

        lede = re.search(r'<p class="lede">(.*?)</p>', body, re.S)
        entries.append(
            {
                "page": page_title,
                "title": page_title,
                "href": name,
                "text": re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", lede.group(1))))
                if lede
                else "",
            }
        )
        for match in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>(.*?)(?=<h[23]|\Z)", body, re.S):
            title = html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
            if not title:
                continue
            text = html.unescape(re.sub(r"<[^>]+>", " ", match.group(3)))
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
            entries.append(
                {
                    "page": page_title,
                    "title": title,
                    "href": f"{name}#{slug}",
                    "text": re.sub(r"\s+", " ", text).strip()[:400],
                }
            )
    return json.dumps(entries, indent=0, ensure_ascii=False)


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
        "concepts.html": shell(
            "concepts.html",
            "Concepts — LangChef",
            fill(CONCEPTS, common),
            "Every idea LangChef uses, in a few lines each, with a link to the page that explains "
            "it properly. No statistics background assumed.",
        ),
        "ref-agreement.html": shell(
            "ref-agreement.html",
            "Agreement and kappa — LangChef",
            fill(REF_AGREEMENT, common),
            "How LangChef decides whether your judge can be trusted: kappa, catch rate, false "
            "alarms and Wilson intervals, worked from real numbers with the papers behind them.",
        ),
        "ref-taxonomy.html": shell(
            "ref-taxonomy.html",
            "Disagreement taxonomy — LangChef",
            fill(REF_TAXONOMY, common),
            "Where a judge disagrees rather than how often: misses against false alarms, which "
            "criterion is at fault, and why the tool refuses to name the worst-looking slice.",
        ),
        "ref-sampling.html": shell(
            "ref-sampling.html",
            "Label planning — LangChef",
            fill(REF_SAMPLING, common),
            "Which forty examples are worth a person's ten minutes, why it is not a random forty, "
            "and the open question about what those labels can be used to claim.",
        ),
        "ref-judging.html": shell(
            "ref-judging.html",
            "Judging and pins — LangChef",
            fill(REF_JUDGING, common),
            "How a judge is defined, how it is pinned so two runs can be compared, and how it is "
            "stopped from spending money you did not agree to.",
        ),
        "ref-design.html": shell(
            "ref-design.html",
            "Designing a run — LangChef",
            fill(REF_DESIGN, common),
            "How the experiment is worked out before you run it: how many goldens, what it can "
            "and cannot see, what it costs, and why editing an approved design revokes it.",
        ),
        "ref-compare.html": shell(
            "ref-compare.html",
            "Comparing two arms — LangChef",
            fill(REF_COMPARE, common),
            "Paired comparison, exact McNemar, the minimum detectable effect, and why "
            "inconclusive is a result rather than a shrug.",
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
    clash = set(REDIRECTS) & set(pages)
    if clash:
        raise SystemExit(
            f"redirect(s) {sorted(clash)} would overwrite a real page. "
            "A URL cannot both forward and hold content."
        )
    pages["search-index.json"] = search_index(pages)
    pages["search.js"] = SEARCH_JS
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
