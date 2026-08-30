"""The knowledge base and the questions asked against it.

One fictional company, five topics, one fact per document. Facts are separate
from the questions that ask for them so the same fact can be asked three
different ways — which is what makes the phrasing slice a real cut rather than
a label we invented.

Tokenisation lives here rather than in the app because it is a property of the
corpus: the same word list decides what a document is about, what a question
asks for, and — through ``document_frequency`` — which questions count as head
and which as tail.
"""

import re
from collections import Counter
from dataclasses import dataclass

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


def stem(word: str) -> str:
    """A crude plural strip. 'managers' and 'manager' are the same query term."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def words(text: str) -> set[str]:
    return {stem(w) for w in WORD.findall(text.lower()) if w not in STOPWORDS}


@dataclass(frozen=True)
class Document:
    doc_id: str
    topic: str
    text: str


@dataclass(frozen=True)
class Fact:
    doc_id: str
    topic: str
    text: str
    subject: str
    expected: str


FACTS: tuple[Fact, ...] = (
    Fact(
        "bill-01",
        "billing",
        "Northwind invoices are issued on the first business day of each month.",
        "when invoices are issued",
        "the first business day of each month",
    ),
    Fact(
        "bill-02",
        "billing",
        "Payment terms on every Northwind invoice are net thirty days.",
        "the payment terms",
        "net thirty days",
    ),
    Fact(
        "bill-03",
        "billing",
        "A late payment on a Northwind account accrues interest at one and a half percent per month.",
        "the late payment interest rate",
        "one and a half percent per month",
    ),
    Fact(
        "bill-04",
        "billing",
        "Northwind accepts payment by bank transfer, credit card, and direct debit only.",
        "which payment methods are accepted",
        "bank transfer, credit card, and direct debit",
    ),
    Fact(
        "bill-05",
        "billing",
        "Annual billing on a Northwind plan carries a ten percent discount.",
        "the annual billing discount",
        "ten percent",
    ),
    Fact(
        "bill-06",
        "billing",
        "A Northwind purchase order number must appear on an invoice before it can be paid.",
        "what an invoice needs before payment",
        "a purchase order number",
    ),
    Fact(
        "ship-01",
        "shipping",
        "Standard Northwind delivery within the country takes three to five working days.",
        "standard delivery time",
        "three to five working days",
    ),
    Fact(
        "ship-02",
        "shipping",
        "Express Northwind delivery arrives the next working day if ordered before two in the afternoon.",
        "the express delivery cutoff",
        "before two in the afternoon",
    ),
    Fact(
        "ship-03",
        "shipping",
        "Northwind ships to twenty two countries across Europe and North America.",
        "how many countries are served",
        "twenty two countries",
    ),
    Fact(
        "ship-04",
        "shipping",
        "Northwind orders above two hundred pounds ship free of charge.",
        "the free shipping threshold",
        "two hundred pounds",
    ),
    Fact(
        "ship-05",
        "shipping",
        "A Northwind tracking number is emailed when the parcel leaves the warehouse.",
        "when a tracking number arrives",
        "when the parcel leaves the warehouse",
    ),
    Fact(
        "ship-06",
        "shipping",
        "Northwind does not deliver to post office boxes under any circumstances.",
        "whether post office boxes are served",
        "does not deliver to post office boxes",
    ),
    Fact(
        "ret-01",
        "returns",
        "Northwind accepts returns within twenty eight days of delivery.",
        "the returns window",
        "twenty eight days of delivery",
    ),
    Fact(
        "ret-02",
        "returns",
        "A Northwind return requires the original packaging to be intact.",
        "what a return requires",
        "the original packaging intact",
    ),
    Fact(
        "ret-03",
        "returns",
        "Northwind refunds are issued within ten working days of the parcel arriving back.",
        "how long a refund takes",
        "ten working days",
    ),
    Fact(
        "ret-04",
        "returns",
        "Northwind charges a restocking fee of fifteen percent on opened items.",
        "the restocking fee",
        "fifteen percent on opened items",
    ),
    Fact(
        "ret-05",
        "returns",
        "Custom Northwind orders cannot be returned once production has started.",
        "whether custom orders can be returned",
        "cannot be returned once production has started",
    ),
    Fact(
        "ret-06",
        "returns",
        "A Northwind return label is generated from the orders page of the account portal.",
        "where to get a return label",
        "the orders page of the account portal",
    ),
    Fact(
        "acct-01",
        "account",
        "A Northwind account is closed by written request to the account manager.",
        "how to close an account",
        "written request to the account manager",
    ),
    Fact(
        "acct-02",
        "account",
        "Northwind allows up to fifty named users on a single business account.",
        "the named user limit",
        "fifty named users",
    ),
    Fact(
        "acct-03",
        "account",
        "A dormant Northwind account is archived after eighteen months without an order.",
        "when an account is archived",
        "after eighteen months without an order",
    ),
    Fact(
        "acct-04",
        "account",
        "Northwind account managers respond to written requests within two working days.",
        "the account manager response time",
        "two working days",
    ),
    Fact(
        "acct-05",
        "account",
        "Only the primary Northwind account holder can change the billing address.",
        "who can change the billing address",
        "only the primary account holder",
    ),
    Fact(
        "acct-06",
        "account",
        "A Northwind account number is eight digits and begins with the letters NW.",
        "the account number format",
        "eight digits and begins with the letters NW",
    ),
    Fact(
        "sec-01",
        "security",
        "Northwind requires two factor authentication on every administrator account.",
        "the administrator authentication requirement",
        "two factor authentication",
    ),
    Fact(
        "sec-02",
        "security",
        "Northwind passwords expire every ninety days.",
        "how often passwords expire",
        "every ninety days",
    ),
    Fact(
        "sec-03",
        "security",
        "A Northwind session ends automatically after thirty minutes of inactivity.",
        "the session timeout",
        "thirty minutes of inactivity",
    ),
    Fact(
        "sec-04",
        "security",
        "Northwind stores customer data in data centres in Ireland and Germany only.",
        "where customer data is stored",
        "Ireland and Germany",
    ),
    Fact(
        "sec-05",
        "security",
        "A Northwind security incident is reported to affected customers within seventy two hours.",
        "the incident notification window",
        "within seventy two hours",
    ),
    Fact(
        "sec-06",
        "security",
        "Northwind audit logs are retained for seven years.",
        "how long audit logs are kept",
        "seven years",
    ),
)

PHRASINGS: tuple[tuple[str, str], ...] = (
    ("direct", "Tell me {subject}."),
    ("polite", "Could you tell me {subject}, please?"),
    ("terse", "{subject}?"),
)

# Distractor documents: plausible, on-topic, and answer nothing. Without these a
# top-k of one is as good as a top-k of five and the retrieval knob does nothing.
DISTRACTORS: tuple[Document, ...] = (
    Document(
        "bill-x1",
        "billing",
        "Northwind billing enquiries are handled by the finance team in Leeds.",
    ),
    Document(
        "bill-x2", "billing", "The Northwind billing portal was redesigned in the spring release."
    ),
    Document(
        "ship-x1",
        "shipping",
        "Northwind shipping partners are reviewed once a year by the logistics team.",
    ),
    Document("ship-x2", "shipping", "The Northwind warehouse in Bristol operates six days a week."),
    Document(
        "ret-x1",
        "returns",
        "Northwind returns are processed by the same warehouse team that packs orders.",
    ),
    Document(
        "ret-x2", "returns", "Return volumes at Northwind are highest in the weeks after December."
    ),
    Document(
        "acct-x1",
        "account",
        "Northwind account managers are assigned by region rather than by industry.",
    ),
    Document(
        "acct-x2",
        "account",
        "The Northwind account portal supports single sign on for enterprise plans.",
    ),
    Document(
        "sec-x1",
        "security",
        "Northwind publishes a security overview for prospective customers each year.",
    ),
    Document(
        "sec-x2", "security", "The Northwind security team runs a phishing exercise every quarter."
    ),
)


def documents() -> list[Document]:
    """The whole corpus: one document per fact, plus the distractors."""
    return [Document(f.doc_id, f.topic, f.text) for f in FACTS] + list(DISTRACTORS)


def document_frequency() -> Counter[str]:
    """How many documents each corpus term appears in."""
    df: Counter[str] = Counter()
    for doc in documents():
        df.update(words(doc.text))
    return df


# A question is *head* when its vocabulary is well represented in the corpus —
# "account", "payment", "return" turn up in many documents — and *tail* when it
# is carried by words the corpus barely uses: "restocking", "phishing",
# "timeout". That is the ordinary shape of a support workload, and it is the cut
# an embedding swap moves: a smaller model matches a larger one on common
# vocabulary and loses the rare terms first.
HEAD_DF = 3
_DF = document_frequency()


def frequency(text: str) -> str:
    """``head`` or ``tail`` for one question, from corpus term frequency."""
    return "head" if max((_DF[w] for w in words(text)), default=0) >= HEAD_DF else "tail"


@dataclass(frozen=True)
class Question:
    example_id: str
    text: str
    expected: str
    gold_doc: str
    topic: str
    phrasing: str
    frequency: str = "head"


def questions() -> list[Question]:
    """Every fact, asked three ways. Deterministic and stable across machines."""
    asked: list[Question] = []
    for fact in FACTS:
        for style, template in PHRASINGS:
            text = template.format(subject=fact.subject)
            asked.append(
                Question(
                    example_id=f"{fact.doc_id}-{style}",
                    text=text,
                    expected=fact.expected,
                    gold_doc=fact.doc_id,
                    topic=fact.topic,
                    phrasing=style,
                    frequency=frequency(text),
                )
            )
    return asked
