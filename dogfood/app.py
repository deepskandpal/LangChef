"""The retrieval-augmented app under test, and the knobs that break it.

Deterministic on purpose: no model, no network, no randomness that is not
seeded. A dogfood whose own output moves between runs cannot tell you whether
the eval harness detected a regression or just noise.

The knobs are the planted regressions. Each one is a real failure mode of a real
RAG system, and each degrades the answer in a different way, so a harness that
only notices one of them is not a harness.

They also differ in the *shape* of the answer they demand, which is the harder
test. One is too small to resolve and must come back inconclusive. One hides
entirely in a slice. One does not move the mean at all — not on average, but in
every trial — and shows up only as a spread. A tool that can subtract two pass
rates gets three of the six right.

Every knob here was run before it was written down, because a knob that looks
like a knob and changes nothing makes the rig lie about its own sensitivity. The
first retrieval knob set ``top_k=1`` and the app answered from ``retrieved[0]``
whatever ``k`` was, so every answer in the arm was the answer the baseline gave
and the self-test reported a detector that could not miss.
"""

import hashlib
import math
from dataclasses import dataclass, replace

from dogfood.corpus import Document, Question, documents
from dogfood.corpus import words as _words

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

# A clause the app adds that is in no document and in no expected answer. Every
# content word here is absent from the corpus, which is what a groundedness
# check is looking for: text the model produced rather than retrieved. The claim
# is plausible, specific and completely invented, which is what makes
# hallucination hard to catch by reading and easy to catch by overlap.
FABRICATION = " This was updated following the Q3 policy review board ruling."

# The retriever the baseline ships with. Any other name is a different vector
# space, and `_noise` reads it as one.
BASE_EMBEDDER = "e5-base"
RETRIEVER_NOISE = 0.35
TRIALS = 24  # repeated calls, for the knobs whose signature is a spread


@dataclass(frozen=True)
class Config:
    """One configuration of the app. The defaults are the baseline."""

    name: str = "baseline"
    top_k: int = 4
    chunk_chars: int = 240
    hedge_below: float = 0.20
    paraphrase_every: int = 4  # 0 = never; n = paraphrase every nth answer
    drop_every: int = 0  # 0 = index is current; n = every nth document is missing
    docs_per_chunk: int = 1  # 1 = a chunk is one document; n = n packed together
    embedder: str = BASE_EMBEDDER  # which vector space the retriever ranks in
    tail_noise: float = RETRIEVER_NOISE  # that space's error on rare vocabulary
    temperature: float = 0.2  # how often a call departs from the modal wording
    embellish_every: int = 0  # 0 = never; n = every nth answer gains an invented clause

    def describe(self) -> str:
        return (
            f"top_k={self.top_k} chunk_chars={self.chunk_chars} "
            f"hedge_below={self.hedge_below} paraphrase_every={self.paraphrase_every} "
            f"drop_every={self.drop_every} docs_per_chunk={self.docs_per_chunk} "
            f"embedder={self.embedder} tail_noise={self.tail_noise} "
            f"temperature={self.temperature} embellish_every={self.embellish_every}"
        )


BASELINE = Config()

# Each variant moves exactly one knob, so a detected regression has one cause.
# The knobs break an answer in different ways — the fact is not in the index,
# the fact is cut off, the app gives up, the chunk is too coarse to rank, the
# retriever lost the rare words, the wording will not sit still — and each one
# is chosen for the *shape* of the finding it demands, not for its size.
#
# Effect sizes are deliberately spread. A dogfood where every planted regression
# is obvious proves only that the harness can see obvious things:
#
#   * `truncated-context` is smaller than 90 goldens can resolve, and the honest
#     outcome for it is "inconclusive, and here is the smallest effect we could
#     have seen" rather than a false all-clear.
#   * `chunk-size-doubled` breaks retrieval and mostly does not reach the pass
#     rate: recall falls 14.4 points and the pass rate 7.8, which is again under
#     what 90 goldens resolve. The finding is a layer upstream of the verdict.
#   * `embedding-swap` leaves head queries untouched and takes a third of the
#     tail. A harness that reports "quality fell" and stops has missed it.
#   * `temperature-0.9` does not move the mean at all — by construction, the
#     true pass rate is identical in every trial. What it moves is the spread
#     between repeated runs. A harness that only compares means will report
#     nothing here, correctly and uselessly.
VARIANTS: dict[str, Config] = {
    "stale-index": replace(BASELINE, name="stale-index", drop_every=5),  # ~-20pp
    "eager-hedging": replace(BASELINE, name="eager-hedging", hedge_below=0.35),  # ~-10pp
    "truncated-context": replace(BASELINE, name="truncated-context", chunk_chars=90),  # ~-3pp
    # Twice the chunk, and the context budget has not changed — so half as many
    # chunks fit in it.
    "chunk-size-doubled": replace(
        BASELINE, name="chunk-size-doubled", docs_per_chunk=2, chunk_chars=480, top_k=2
    ),
    "embedding-swap": replace(
        BASELINE, name="embedding-swap", embedder="minilm-small", tail_noise=1.10
    ),
    "temperature-0.9": replace(BASELINE, name="temperature-0.9", temperature=0.9),
    # The only arm that moves Groundedness. Every other knob answers out of a
    # document, so whatever else is wrong with the answer it is still grounded
    # in what was retrieved. This one invents.
    "hallucinated-detail": replace(BASELINE, name="hallucinated-detail", embellish_every=6),
}

# What the knobs are known to do to the true pass rate, for the self-test.
PLANTED_EFFECT: dict[str, float] = {
    "stale-index": -0.200,
    "eager-hedging": -0.100,
    "truncated-context": -0.033,
    "chunk-size-doubled": -0.078,
    "embedding-swap": -0.122,
    "temperature-0.9": 0.000,
    "hallucinated-detail": -0.144,
}

# `hallucinated-detail` is the one whose finding is a *criterion*. It is the only
# arm that moves Groundedness, because every other knob answers out of a
# retrieved document and is therefore grounded whatever else is wrong with it.
# The planted truth is that Groundedness carries all of the loss and Correctness
# carries exactly none: the requested fact is still in the answer, sitting next
# to a sentence the app invented.
PLANTED_CRITERION_EFFECT: dict[str, dict[str, float]] = {
    "hallucinated-detail": {"Groundedness": -0.1333, "Correctness": 0.000},
}

# `chunk-size-doubled` is the one whose damage is mostly upstream of the pass
# rate: the gold document reaches the prompt far less often, and only some of
# that survives as a wrong answer. Both halves are planted, and the retrieval
# half is the larger — which is the finding.
PLANTED_RECALL_EFFECT: dict[str, float] = {"chunk-size-doubled": -0.144}

# `embedding-swap` is the one whose finding is a slice, not a total. The planted
# truth is that head queries are untouched and the tail carries all of it.
PLANTED_SLICE_EFFECT: dict[str, dict[str, float]] = {
    "embedding-swap": {"head": 0.000, "tail": -0.333},
}

# `temperature-0.9` is the one whose finding is a spread, not a mean. The planted
# truth is how much wider the *measured* pass rate scatters between repeated
# calls, and it follows from the sampling temperature and nothing else: the
# chance of departing from the modal wording is 37x higher at 0.9 than at 0.2,
# and the between-trial variance of the pass rate goes with it.
PLANTED_VARIANCE_RATIO: dict[str, float] = {"temperature-0.9": 16.0}


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


@dataclass(frozen=True)
class Chunk:
    """What the retriever indexes: one or more documents, packed together.

    At the baseline a chunk is a document, so ``chunk_id`` is a ``doc_id`` and
    every score below is the score it was before chunks existed.
    """

    chunk_id: str
    docs: tuple[Document, ...]
    text: str


def chunks(config: Config, corpus: list[Document] | None = None) -> list[Chunk]:
    """Pack the index into retrieval units of ``docs_per_chunk`` documents."""
    corpus = index(config, corpus)
    size = max(1, config.docs_per_chunk)
    packed = []
    for start in range(0, len(corpus), size):
        group = tuple(corpus[start : start + size])
        packed.append(
            Chunk(
                chunk_id="+".join(d.doc_id for d in group),
                docs=group,
                text=" ".join(d.text for d in group),
            )
        )
    return packed


def _score(question: set[str], document: Document) -> float:
    """Token overlap, length-normalised. What the reader uses to pick an answer."""
    text = _words(document.text)
    if not text or not question:
        return 0.0
    return len(question & text) / len(question)


def _pooled(question: set[str], chunk: Chunk) -> float:
    """What the *retriever* sees: the mean of the chunk's per-document scores.

    A dense retriever embeds a chunk as one vector, so a chunk holding two facts
    sits about half way between them and is about half as close to a query about
    either. That dilution is the whole cost of a bigger chunk, and it is
    measured against a noise floor that does not shrink with it.
    """
    return sum(_score(question, d) for d in chunk.docs) / len(chunk.docs)


def _read(question: set[str], chunk: Chunk) -> tuple[float, Document]:
    """What the *reader* sees: the best document in the chunk, and its score.

    The reader has the text in front of it, not a pooled vector, so it is not
    fooled by packing — which is deliberate. It keeps the chunking knob a
    retrieval regression and nothing else, instead of quietly moving the hedge
    threshold as well and making two knobs out of one.
    """
    return max(((_score(question, d), d) for d in chunk.docs), key=lambda p: (p[0], p[1].doc_id))


def _jitter(question: str, doc_id: str, salt: str = "") -> float:
    """Deterministic pseudo-noise in [0, 1). Stands in for embedding error.

    Without this the retriever is perfect, the gold document is always rank one,
    and top_k protects against nothing — which would make the retrieval knob a
    regression that cannot regress. A real dense retriever gets the right
    document into the top few far more often than it gets it into first place,
    and that gap is exactly what k buys you.

    ``salt`` picks the space the error is drawn in. The empty default is the
    baseline retriever, and its digest is byte-for-byte what it was before any
    other space existed — so adding one moved no number that was already here.
    """
    digest = hashlib.sha256(f"{salt}{question}\x00{doc_id}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _noise(question: Question, chunk: Chunk, config: Config) -> float:
    """The retriever's error on one (question, chunk) pair.

    Swapping the embedding model swaps the vector space, and the swap planted
    here is the ordinary one: the smaller model matches the larger on the
    vocabulary it saw constantly and loses the rare words first. So head queries
    land in exactly the same place they did, and tail queries are re-drawn in a
    different space with a wider error.
    """
    if config.embedder != BASE_EMBEDDER and question.frequency == "tail":
        return config.tail_noise * _jitter(question.text, chunk.chunk_id, salt=config.embedder)
    return RETRIEVER_NOISE * _jitter(question.text, chunk.chunk_id)


def retrieve(question: Question, config: Config, corpus: list[Document] | None = None):
    """Top-k chunks by a noisy retriever, each truncated to the chunk size.

    Two stages, as in any real system: a cheap retriever that is roughly right
    picks the candidates, and the reader chooses among them. Ties break on
    chunk_id so retrieval is stable — otherwise the same question returns
    different context on different runs and every comparison is noise.
    """
    tokens = _words(question.text)
    ranked = sorted(
        chunks(config, corpus),
        key=lambda c: (-(_pooled(tokens, c) + _noise(question, c, config)), c.chunk_id),
    )
    top = ranked[: config.top_k]
    return [(chunk, _pooled(tokens, chunk), chunk.text[: config.chunk_chars]) for chunk in top]


def recall(config: Config, asked: list[Question], corpus: list[Document] | None = None) -> float:
    """Share of questions whose gold document reached the prompt at all.

    Retrieval relevance, measured directly rather than inferred from the pass
    rate. A knob that moves this and barely moves the pass rate has still broken
    retrieval, and a suite of 90 pass/fail goldens is the wrong instrument to
    find out — which is the point of measuring it here.
    """
    hit = 0
    for question in asked:
        retrieved = retrieve(question, config, corpus)
        hit += any(d.doc_id == question.gold_doc for chunk, _, _ in retrieved for d in chunk.docs)
    return hit / len(asked)


def paraphrase(text: str) -> str:
    """Rewrite an answer so it means the same thing in different words."""
    out = text
    for original, replacement in SYNONYMS:
        out = out.replace(original, replacement)
    return out


# How far the modal wording of an answer sits above the alternative, in logits.
# The decode is a two-way choice at every answer, so the chance of taking the
# other branch is the softmax of that gap at the sampling temperature — which is
# what makes 0.2 and 0.9 so far apart. A linear reading of temperature would put
# them a factor of four and a half apart; the softmax puts them a factor of
# thirty-seven apart, and the second one is what a decoder actually does.
WORDING_MARGIN = 1.0


def departure(temperature: float) -> float:
    """P(a call departs from the modal wording) at this sampling temperature."""
    if temperature <= 0.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(WORDING_MARGIN / temperature))


def rewords(question: Question, config: Config, trial: int = 0) -> bool:
    """Whether this call rewords its answer.

    A quarter of answers come out reworded at any temperature — that rate is
    ``paraphrase_every`` and temperature does not touch it, which is why the
    means do not move. What temperature changes is whether the *same* question
    is worded the same way the second time it is asked: a departing call throws
    the wording away and redraws it at the same rate.

    That is the whole knob, and it is deliberately the whole knob. The content
    is identical, so ground truth is identical in every trial, so a comparison
    of means has nothing to find and is right to say so. The damage is a
    measured pass rate that will not sit still between runs, and the only
    statistic that sees it is a spread.
    """
    if not config.paraphrase_every:
        return False
    modal = _index(question) % config.paraphrase_every == 0
    departs = _jitter(question.example_id, f"trial-{trial}", salt="departure")
    if departs >= departure(config.temperature):
        return modal
    redraw = _jitter(question.example_id, f"trial-{trial}", salt="wording")
    return redraw < 1.0 / config.paraphrase_every


def answer(
    question: Question,
    config: Config,
    corpus: list[Document] | None = None,
    trial: int = 0,
):
    """Answer one question.

    Returns the answer, the context it was given, and the provenance a grader
    would need. The provenance never reaches the goldens file — it is how the
    dogfood knows the true verdict without asking anyone, and letting a judge
    see it would make the whole exercise circular.
    """
    retrieved = retrieve(question, config, corpus)
    context = [text for _, _, text in retrieved]
    provenance = {
        "source_doc": None,
        "source_docs": (),
        "hedged": True,
        "paraphrased": False,
        "fact_present": False,
        "fabricated": False,
    }
    if not retrieved:
        return HEDGE, context, provenance

    # The reader re-ranks what the retriever handed it. It can only choose from
    # the candidates, which is the whole point of the top_k knob.
    tokens = _words(question.text)
    best_chunk, _, best_text = max(
        retrieved, key=lambda item: (_read(tokens, item[0])[0], item[0].chunk_id)
    )
    best_score, best_doc = _read(tokens, best_chunk)
    if best_score < config.hedge_below:
        return HEDGE, context, provenance

    paraphrased = rewords(question, config, trial)
    text = paraphrase(best_text) if paraphrased else best_text
    fabricated = bool(config.embellish_every) and _index(question) % config.embellish_every == 0
    if fabricated:
        text = text + FABRICATION
    provenance = {
        "source_doc": best_doc.doc_id,
        # Every document the answer text came from. At the baseline that is the
        # one document the reader read; when chunks hold more than one it is the
        # whole chunk, because the whole chunk is what the app emitted. Grading
        # a packed chunk on which half the reader ranked highest would fail
        # answers that a person reads straight through, and count a bookkeeping
        # detail as a regression.
        "source_docs": tuple(d.doc_id for d in best_chunk.docs),
        "hedged": False,
        "paraphrased": paraphrased,
        # Checked against the chunk before paraphrasing: a reader follows the
        # rewording, so a paraphrase does not make an answer wrong.
        "fact_present": _words(question.expected) <= _words(best_text),
        "fabricated": fabricated,
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
    if question.gold_doc not in provenance["source_docs"]:
        return "fail"
    # An invented claim fails even when the requested fact is also present. A
    # person does not read past a fabricated sentence because the rest was
    # right, and an answer they cannot trust is not an answer.
    if provenance["fabricated"]:
        return "fail"
    return "pass" if provenance["fact_present"] else "fail"


def _index(question: Question) -> int:
    """A stable per-question integer, so 'every nth' is reproducible."""
    return sum(ord(c) for c in question.example_id)


def run(
    config: Config,
    asked: list[Question],
    corpus: list[Document] | None = None,
    trial: int = 0,
) -> list[dict]:
    """Score the whole question set under one configuration.

    ``trial`` is which call this is. Everything here is a function of it, so a
    trial is reproducible rather than merely repeatable, and asking the same
    question twice at temperature is the only thing it changes.
    """
    rows = []
    for question in asked:
        text, context, provenance = answer(question, config, corpus, trial)
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
                    "frequency": question.frequency,
                },
                "_truth": truth(question, provenance),
                "_provenance": provenance,
            }
        )
    return rows
