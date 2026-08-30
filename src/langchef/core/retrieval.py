"""Ranked-retrieval metrics: recall@k, MRR, nDCG.

Pure arithmetic over ranked document ids. No I/O, no network, and no task class
named anywhere, so the boundary in DECISIONS #5 holds: these are general
information-retrieval statistics in the same way Cohen's kappa is a general
agreement statistic, not knowledge about anybody's application.

**Ties and truncation are the whole reason this file has a docstring this long.**
Every nDCG implementation differs at the edges, and silence about which choice
was made is how two teams' numbers stop being comparable while both look
correct. The choices here, stated once:

- **Order is the ranking.** The list you pass is taken as the ranked order,
  first element first. Scores are not accepted, so there are no score ties to
  break; if your retriever emits ties, it has already decided their order by the
  time it produces a list, and pretending otherwise would invent a tie-break we
  cannot see.
- **A short list is not padded.** Asking for recall@10 from a retriever that
  returned six documents evaluates the six. It does not treat the missing four
  as misses, because that would score the retriever for a truncation the caller
  chose, and it does not error, because a short list is ordinary.
- **Duplicates are counted once.** A document id appearing twice in one ranking
  is a bug in the retriever, and counting it twice would reward it.
- **No relevant documents means the query is undefined, not zero.** A query with
  an empty ground truth has no recall to measure. Returning 0.0 would drag a
  mean down with a number that means "we could not ask", which is the same
  failure as counting an unmeasurable example as a failure.
- **Binary relevance for nDCG.** Graded relevance is a real thing and this does
  not do it; a document is relevant or it is not. Stated rather than implied.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

__all__ = ["ndcg_at_k", "recall_at_k", "reciprocal_rank"]


def _ranked(retrieved: Sequence[str], k: int | None) -> list[str]:
    """The ranking, de-duplicated in place and cut to k when k is given."""
    seen: set[str] = set()
    ordered: list[str] = []
    for doc in retrieved:
        if doc not in seen:
            seen.add(doc)
            ordered.append(doc)
    return ordered if k is None else ordered[:k]


def recall_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int | None = None) -> float:
    """Share of the relevant documents that appear in the top ``k``.

    ``nan`` when nothing is relevant: that query cannot be scored, and averaging
    a zero in its place would report a retrieval failure that never happened.
    """
    truth = set(relevant)
    if not truth:
        return float("nan")
    found = set(_ranked(retrieved, k)) & truth
    return len(found) / len(truth)


def reciprocal_rank(retrieved: Sequence[str], relevant: Iterable[str]) -> float:
    """1 / rank of the first relevant document, or 0.0 if none is retrieved.

    Zero is the right answer here rather than ``nan``: the query *was*
    answerable, and the retriever missed. That is a real score, unlike recall
    over an empty ground truth.
    """
    truth = set(relevant)
    if not truth:
        return float("nan")
    for position, doc in enumerate(_ranked(retrieved, None), start=1):
        if doc in truth:
            return 1.0 / position
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], relevant: Iterable[str], k: int | None = None) -> float:
    """Discounted cumulative gain over binary relevance, normalised.

    The ideal ranking puts every relevant document first, so the denominator is
    the DCG of ``min(len(relevant), k)`` documents at positions 1..n. Log base 2,
    positions counted from 1, which is the convention scikit-learn and the
    original Jarvelin and Kekalainen paper both use.
    """
    truth = set(relevant)
    if not truth:
        return float("nan")
    ordered = _ranked(retrieved, k)
    gain = sum(1.0 / math.log2(i + 1) for i, doc in enumerate(ordered, start=1) if doc in truth)
    ideal_n = min(len(truth), len(ordered)) if k is None else min(len(truth), k)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_n + 1))
    return gain / ideal if ideal else float("nan")
