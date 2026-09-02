"""A topic classifier over the same corpus, and the covariate shift that breaks it.

The other knobs in `app.py` all degrade a retrieval-augmented answer. This one
degrades a **classifier**, because the failure it plants has no analogue in a
pass rate: under covariate shift the input distribution moves while `P(y|x)`
does not, so the labels stay correct, the model stays unchanged, and accuracy
falls only where the shift landed.

Aggregate accuracy is the wrong instrument for that. It averages the shifted
slice against four unshifted ones and reports something small enough to look
like noise. **A tool that reports one number here is not wrong so much as
useless**, which is a different failure from the ones the other knobs plant and
the reason this one is worth the file.

Nothing here is a model. The classifier is nearest-centroid over term overlap,
built from the corpus documents rather than hand-written, so the vocabulary it
depends on is the corpus's own and the shift below genuinely removes what it was
using. Deterministic, seeded, stdlib only, no network.
"""

from collections import Counter
from dataclasses import dataclass, replace

from dogfood.corpus import Question, documents, questions, words

#: The generic words a shifted question falls back on. They carry no topic, which
#: is the point: the shift does not mislabel anything, it removes the evidence.
GENERIC = ("issue", "problem", "help", "question", "thing", "detail", "info")


def centroids() -> dict[str, Counter]:
    """Topic vocabulary, counted from the corpus rather than declared.

    Building this from the documents matters. A hand-written keyword list would
    make the shift below a tautology, because the same hand would choose which
    words to take away.
    """
    by_topic: dict[str, Counter] = {}
    for document in documents():
        by_topic.setdefault(document.topic, Counter()).update(words(document.text))
    return by_topic


#: Terms that appear under exactly one topic. These are what the classifier
#: actually leans on, and what the covariate shift takes away.
def discriminative() -> dict[str, set[str]]:
    by_topic = centroids()
    everywhere: Counter = Counter()
    for counts in by_topic.values():
        everywhere.update(set(counts))
    return {
        topic: {word for word in counts if everywhere[word] == 1}
        for topic, counts in by_topic.items()
    }


@dataclass(frozen=True)
class ClassifierConfig:
    """One configuration of the classifier. The defaults are the baseline."""

    name: str = "baseline"
    #: Which topic's questions arrive rephrased. None = the input distribution
    #: is the one the classifier was built for.
    shift_topic: str | None = None
    #: Narrow the shift to one phrasing style within that topic. This is what
    #: keeps the aggregate effect small: the shift lands on a cell, not a column.
    shift_phrasing: str | None = None
    #: How many discriminative terms the shift strips from a shifted question.
    #: The rest of the sentence is untouched, so the true label is unchanged.
    shift_strength: int = 0

    def describe(self) -> str:
        return (
            f"shift_topic={self.shift_topic} shift_phrasing={self.shift_phrasing} "
            f"shift_strength={self.shift_strength}"
        )


CLASSIFIER_BASELINE = ClassifierConfig()

#: `security` carries the fewest terms shared with the other four topics, so a
#: shift there is the cleanest available cut: it degrades one slice and leaves
#: the rest of the corpus in exactly the distribution the classifier expects.
CLASSIFIER_VARIANTS: dict[str, ClassifierConfig] = {
    "covariate-shift": ClassifierConfig(
        name="covariate-shift",
        shift_topic="security",
        shift_phrasing="terse",
        shift_strength=3,
    ),
}


#: What the shift is known to do, measured before any test was written that
#: depends on it. The baseline classifier is exactly right on this corpus: five
#: topics with disjoint vocabulary are separable, and that is deliberate, because
#: it makes every number below an exact planted truth rather than an estimate.
PLANTED_ACCURACY: dict[str, float] = {"baseline": 1.000, "covariate-shift": 0.9333}

#: The aggregate effect. Small, and **not** small enough to be missed: all six
#: discordant pairs move the same way, so exact McNemar returns a regression at
#: p=0.031 even though the pre-hoc detection limit for 90 goldens is 11.0 points.
PLANTED_CLASSIFIER_EFFECT: float = -0.0667

#: The effect where it actually lives. This is the finding, and it is five times
#: the aggregate. Four topics are untouched by construction.
PLANTED_SHIFT_SLICE: dict[str, dict[str, float]] = {
    "topic": {
        "account": 0.000,
        "billing": 0.000,
        "returns": 0.000,
        "security": -0.3333,
        "shipping": 0.000,
    },
    "phrasing": {"direct": 0.000, "polite": 0.000, "terse": -0.200},
}

#: **The point of this knob.** The aggregate does not go quiet here, which was
#: the outcome originally expected of it. It goes *wrong*: it reports a 6.7 point
#: decline spread over everything, when the truth is a 33 point collapse in one
#: topic and nothing anywhere else. A team reading the aggregate goes and looks
#: at the model. A team reading the slice goes and looks at the help-centre form
#: that changed, which is where the cause is. Both numbers are correct
#: arithmetic; only one of them is an answer.
MISATTRIBUTION_RATIO: float = 5.0


def shift(question: Question, config: ClassifierConfig) -> str:
    """The question as it now arrives, after the input distribution moved.

    Deterministic: the words removed are chosen by sorted order and the
    replacements by position, so the same question always shifts the same way.

    This is a **covariate** shift and not a label shift. The topic of the
    question does not change; only the words a user happened to reach for do.
    Somebody rolled out a new help-centre form with a topic dropdown, so people
    stopped naming the thing they were asking about in the free-text box.
    """
    if config.shift_topic is None or question.topic != config.shift_topic:
        return question.text
    if config.shift_phrasing is not None and question.phrasing != config.shift_phrasing:
        return question.text
    strong = discriminative().get(question.topic, set())
    present = sorted(word for word in words(question.text) if word in strong)
    if not present:
        return question.text

    text = question.text
    for position, word in enumerate(present[: config.shift_strength]):
        text = text.replace(word, GENERIC[position % len(GENERIC)])
    return text


def classify(text: str, by_topic: dict[str, Counter] | None = None) -> str:
    """Nearest centroid by term overlap. Ties break by topic name, never by luck."""
    by_topic = by_topic if by_topic is not None else centroids()
    asked = set(words(text))
    scored = [
        (sum(counts[word] for word in asked), -ord(topic[0]), topic)
        for topic, counts in by_topic.items()
    ]
    return max(scored)[2]


def rows(config: ClassifierConfig, asked: list[Question] | None = None) -> list[dict]:
    """One classification row per question, in the shape the pack declares.

    ``example_id``, ``input``, ``predicted`` and ``ideal`` are the classification
    task class's required fields; the slices ride alongside so the comparison can
    be cut by them. ``ideal`` is the question's real topic and never moves, which
    is what makes this covariate shift rather than concept drift.
    """
    asked = asked if asked is not None else questions()
    by_topic = centroids()
    return [
        {
            "example_id": question.example_id,
            "input": shift(question, config),
            "predicted": classify(shift(question, config), by_topic),
            "ideal": question.topic,
            "slices": {
                "topic": question.topic,
                "phrasing": question.phrasing,
                "frequency": question.frequency,
            },
        }
        for question in asked
    ]


def accuracy(scored: list[dict]) -> float:
    return sum(1 for row in scored if row["predicted"] == row["ideal"]) / len(scored)


def accuracy_by(scored: list[dict], slice_name: str) -> dict[str, float]:
    """Accuracy cut by one slice. The instrument the aggregate hides from."""
    buckets: dict[str, list[dict]] = {}
    for row in scored:
        buckets.setdefault(row["slices"][slice_name], []).append(row)
    return {key: accuracy(rows_) for key, rows_ in sorted(buckets.items())}


__all__ = [
    "CLASSIFIER_BASELINE",
    "MISATTRIBUTION_RATIO",
    "PLANTED_ACCURACY",
    "PLANTED_CLASSIFIER_EFFECT",
    "PLANTED_SHIFT_SLICE",
    "CLASSIFIER_VARIANTS",
    "ClassifierConfig",
    "accuracy",
    "accuracy_by",
    "centroids",
    "classify",
    "discriminative",
    "replace",
    "rows",
    "shift",
]
