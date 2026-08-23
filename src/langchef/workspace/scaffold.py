"""What ``langchef init`` writes.

The scaffold is opinionated on purpose: a workspace that starts empty is a
workspace nobody fills in. It ships one rubric whose criteria the deterministic
containment judge can actually assess, so a new checkout can run the whole
flow — judge, calibrate, compare, memo — before anyone has a provider key.
"""

from langchef.workspace.formats import write_text
from langchef.workspace.paths import Workspace

CONFIG = """# LangChef workspace.
# Reviewed in pull requests like everything else here.

[workspace]
name = "{name}"
application_class = "{application_class}"
pack = "{pack}"

[judge]
# The deterministic judge needs no key and no network. Swap provider to
# "litellm" and set the models to something real when you have one.
provider = "containment"
cheap_model = "containment/v2"
# A strong model re-scores only the cases the cheap one was unsure about.
# strong_model = "anthropic/claude-sonnet-5"
escalate_below = 0.6
rubric = "{rubric}"

[approvals]
# Gate one. Set by `langchef approve rubric {rubric}` after a person has read
# it. Editing the rubric changes its hash and revokes this automatically.
# rubric = "{rubric}@<digest>"

[compare]
# A comparison is a decision, so the threshold is written down before the run.
level = 0.95
"""

RUBRIC = """# Answer quality

The judge scores one answer at a time and cites exactly one criterion when it
fails. Each `###` heading below is a criterion; the headings are the contract,
so renaming one changes the rubric hash and revokes its approval.

### Correctness

The answer states the fact the question asked for. An answer that is merely
adjacent to the right topic fails this criterion.

### Groundedness

Every claim in the answer is supported by the retrieved context. An answer that
is correct but not present in the context still fails: on a retrieval-augmented
system that is a lucky guess, and it will not stay lucky.

### Directness

The answer answers. Declining, hedging into uselessness, or explaining why the
question is hard when the context contains the answer all fail here.
"""

GITIGNORE = """# Judgement cache — keyed on content, rebuildable, and large.
.cache/
"""

README = """# Eval workspace

Everything the eval agent reads and writes. Reviewable in a pull request by
design: text formats, one binary (`runs/*/scores.parquet`, bulk per-example
scores nobody reads by eye).

```
goldens/    the examples          rubrics/    judging criteria, hashed
labels/     what a person said    runs/       one measurement per directory
baselines/  the reference run     memos/      decision memos
ledger/     the persistent record
```

Start here:

```sh
langchef doctor                 # is this workspace usable
langchef judge run              # score the goldens
langchef calibrate report       # how well does the judge agree with a person
langchef compare                # baseline against variant
langchef memo render            # the decision, in writing
```
"""


def create(
    workspace: Workspace,
    name: str,
    application_class: str = "genai-rag",
    pack: str = "genai-rag",
    rubric: str = "answer-quality",
) -> list[str]:
    """Write the workspace. Existing files are never overwritten."""
    written: list[str] = []
    for directory in workspace.directories():
        directory.mkdir(parents=True, exist_ok=True)

    files = {
        workspace.config: CONFIG.format(
            name=name, application_class=application_class, pack=pack, rubric=rubric
        ),
        workspace.rubrics / f"{rubric}.md": RUBRIC,
        workspace.root / ".gitignore": GITIGNORE,
        workspace.root / "README.md": README,
    }
    for path, text in files.items():
        if path.exists():
            continue
        write_text(path, text)
        written.append(str(path.relative_to(workspace.root.parent)))
    return written
