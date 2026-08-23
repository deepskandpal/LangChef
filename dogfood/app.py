"""The retrieval-augmented app under test, and the knobs that break it.

Deterministic on purpose: no model, no network, no randomness that is not
seeded. A dogfood whose own output moves between runs cannot tell you whether
the eval harness detected a regression or just noise.

The knobs are the planted regressions. Each one is a real failure mode of a real
RAG system, and each degrades the answer in a different way, so a harness that
only notices one of them is not a harness.
"""

import hashlib
import re
from dataclasses import dataclass, replace

from dogfood.corpus import Document, Question, documents

WORD = re.compile(r"[a-z0-9']+")
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "could",
        "for",
        "from",
        "has",
        "have",
        "how",
        "in",
        "is",
        "it",
        "its",
        "me",
        "of",
        "on",
        "or",
        "please",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
    }
)

# Deterministic paraphrase: same meaning, different words. This is what creates
# honest judge/human disagreement — a person reads through it, a token-overlap
# judge does not.
SYNONYMS: tuple[tuple[str, str], ...] = (
    ("thirty", "30"),
    ("twenty eight", "28"),
    ("twenty two", "22"),
    ("ninety", "90"),
    ("seventy two", "72"),
    ("eighteen", "18"),
    ("fifteen", "15"),
    ("fifty", "50"),
    ("ten", "10"),
    ("seven", "7"),
    ("two", "2"),
    ("working days", "business days"),
    ("business day", "working day"),
    ("per month", "monthly"),
    ("of delivery", "after it arrives"),
)

HEDGE = "I don't know — the retrieved documents do not contain that information."


@dataclass(frozen=True)
class Config:
    """One configuration of the app. The defaults are the baseline."""

    name: str = "baseline"
    top_k: int = 4
    chunk_chars: int = 240
    hedge_below: float = 0.20
    paraphrase_every: int = 4  # 0 = never; n = paraphrase every nth answer
    drop_every: int = 0  # 0 = index is current; n = every nth document is missing

    def describe(self) -> str:
        return (
            f"top_k={self.top_k} chunk_chars={self.chunk_chars} "
            f"hedge_below={self.hedge_below} paraphrase_every={self.paraphrase_every} "
            f"drop_every={self.drop_every}"
        )


BASELINE = Config()

# Each variant moves exactly one knob, so a detected regression has one cause.
# The three chosen are the ones that break an answer in three different ways:
# the fact is not in the index, the fact is cut off, and the app gives up.
# Effect sizes are deliberately spread. A dogfood where every planted
# regression is obvious proves only that the harness can see obvious things;
# the third one here is smaller than 90 goldens can resolve, and the honest
# outcome for it is "inconclusive, and here is the smallest effect we could
# have seen" rather than a false all-clear.
VARIANTS: dict[str, Config] = {
    "stale-index": replace(BASELINE, name="stale-index", drop_every=5),  # ~-20pp
    "eager-hedging": replace(BASELINE, name="eager-hedging", hedge_below=0.35),  # ~-10pp
    "truncated-context": replace(BASELINE, name="truncated-context", chunk_chars=90),  # ~-3pp
}

# What the knobs are known to do to the true pass rate, for the self-test.
PLANTED_EFFECT: dict[str, float] = {
    "stale-index": -0.200,
    "eager-hedging": -0.100,
    "truncated-context": -0.033,
}


def index(config: Config, corpus: list[Document] | None = None) -> list[Document]:
    """What the retriever can actually see.

    ``drop_every`` simulates the most boring production regression there is: the
    index fell behind and some documents are simply not in it any more. Nothing
    about the app is broken, and every answer that needed a missing document is
    now wrong.
    """
    corpus = corpus if corpus is not None else documents()
    if not config.drop_every:
        return corpus
    return [doc for position, doc in enumerate(corpus) if position % config.drop_every]


def _stem(word: str) -> str:
    """A crude plural strip. 'managers' and 'manager' are the same query term."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _words(text: str) -> set[str]:
    return {_stem(w) for w in WORD.findall(text.lower()) if w not in STOPWORDS}


def _score(question: set[str], document: Document) -> float:
    """Token overlap, length-normalised. What the reader uses to pick an answer."""
    text = _words(document.text)
    if not text or not question:
        return 0.0
    return len(question & text) / len(question)


def _jitter(question: str, doc_id: str) -> float:
    """Deterministic pseudo-noise in [0, 1). Stands in for embedding error.

    Without this the retriever is perfect, the gold document is always rank one,
    and top_k protects against nothing — which would make the retrieval knob a
    regression that cannot regress. A real dense retriever gets the right
    document into the top few far more often than it gets it into first place,
    and that gap is exactly what k buys you.
    """
    digest = hashlib.sha256(f"{question}\x00{doc_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


RETRIEVER_NOISE = 0.35


def retrieve(question: str, config: Config, corpus: list[Document] | None = None):
    """Top-k documents by a noisy retriever, each truncated to the chunk size.

    Two stages, as in any real system: a cheap retriever that is roughly right
    picks the candidates, and the reader chooses among them. Ties break on
    doc_id so retrieval is stable — otherwise the same question returns
    different context on different runs and every comparison is noise.
    """
    corpus = index(config, corpus)
    tokens = _words(question)
    ranked = sorted(
        corpus,
        key=lambda d: (
            -(_score(tokens, d) + RETRIEVER_NOISE * _jitter(question, d.doc_id)),
            d.doc_id,
        ),
    )
    top = ranked[: config.top_k]
    return [(doc, _score(tokens, doc), doc.text[: config.chunk_chars]) for doc in top]


def paraphrase(text: str) -> str:
    """Rewrite an answer so it means the same thing in different words."""
    out = text
    for original, replacement in SYNONYMS:
        out = out.replace(original, replacement)
    return out


def answer(question: Question, config: Config, corpus: list[Document] | None = None):
    """Answer one question.

    Returns the answer, the context it was given, and the provenance a grader
    would need. The provenance never reaches the goldens file — it is how the
    dogfood knows the true verdict without asking anyone, and letting a judge
    see it would make the whole exercise circular.
    """
    retrieved = retrieve(question.text, config, corpus)
    context = [chunk for _, _, chunk in retrieved]
    provenance = {"source_doc": None, "hedged": True, "paraphrased": False, "fact_present": False}
    if not retrieved:
        return HEDGE, context, provenance

    # The reader re-ranks what the retriever handed it. It can only choose from
    # the candidates, which is the whole point of the top_k knob.
    tokens = _words(question.text)
    best_doc, best_score, best_chunk = max(
        retrieved, key=lambda item: (_score(tokens, item[0]), item[0].doc_id)
    )
    if best_score < config.hedge_below:
        return HEDGE, context, provenance

    paraphrased = bool(config.paraphrase_every and _index(question) % config.paraphrase_every == 0)
    text = paraphrase(best_chunk) if paraphrased else best_chunk
    provenance = {
        "source_doc": best_doc.doc_id,
        "hedged": False,
        "paraphrased": paraphrased,
        # Checked against the chunk before paraphrasing: a reader follows the
        # rewording, so a paraphrase does not make an answer wrong.
        "fact_present": _words(question.expected) <= _words(best_chunk),
    }
    return text, context, provenance


def truth(question: Question, provenance: dict) -> str:
    """The verdict a careful person would give, derived from ground truth.

    These stand in for human labels in the dogfood. They are not a model's
    opinion and not the judge's: they follow from facts the harness planted and
    therefore knows. An answer passes when it came from the right document, did
    not decline, and still carried the fact after truncation.
    """
    if provenance["hedged"]:
        return "fail"
    if provenance["source_doc"] != question.gold_doc:
        return "fail"
    return "pass" if provenance["fact_present"] else "fail"


def _index(question: Question) -> int:
    """A stable per-question integer, so 'every nth' is reproducible."""
    return sum(ord(c) for c in question.example_id)


def run(config: Config, asked: list[Question], corpus: list[Document] | None = None) -> list[dict]:
    """Score the whole question set under one configuration."""
    rows = []
    for question in asked:
        text, context, provenance = answer(question, config, corpus)
        rows.append(
            {
                "example_id": question.example_id,
                "question": question.text,
                "answer": text,
                "context": context,
                "expected": question.expected,
                "slices": {
                    "topic": question.topic,
                    "phrasing": question.phrasing,
                },
                "_truth": truth(question, provenance),
                "_provenance": provenance,
            }
        )
    return rows
