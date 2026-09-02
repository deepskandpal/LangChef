"""The last thing between a live API key and a public repository.

`scripts/record_cassette.py` is the one script here that requires a credential
to be present. What it writes goes into a public repository as a test fixture,
so the interesting tests are not that scrubbing works on a key it recognises.
They are the ones about a key it does not.

The audit exists because scrubbing is a transformation and can be wrong. It
reads the finished bytes, knows the actual secret values from the recording
environment, and the recorder refuses to write anything it flags. A scrubber
alone would let a key ride out inside a field nobody thought about, which is
exactly the field it would ride out in.
"""

import json

import pytest

from langchef.judge import scrub


def _assemble(*parts: str) -> str:
    """Build a credential-shaped string at runtime, from fragments.

    These have to match the real provider patterns or the tests below prove
    nothing. But a *literal* that matches a real pattern trips GitHub's secret
    scanner and files an alert against this repository, and that alert is worse
    than it looks: it is a false positive, so a repository carrying one
    permanently teaches everyone who sees it to skim past the next one. The next
    one will not be a false positive.

    Splitting the prefix from the body means no contiguous run in this file
    matches a scanner rule, while the assembled value is byte-identical to what
    the scrubber has to catch.
    """
    return "".join(parts)


FAKE_OPENAI = _assemble("sk", "-proj-", "AAAABBBBCCCCDDDDEEEEFFFF0000")
FAKE_ANTHROPIC = _assemble("sk", "-ant-api03-", "ZZZZYYYYXXXXWWWWVVVV1111")
FAKE_GOOGLE = _assemble("AIza", "SyD-0000111122223333444455556666777")
FAKE_AWS = _assemble("AKIA", "IOSFODNN7EXAMPLE")


@pytest.mark.parametrize("secret", [FAKE_OPENAI, FAKE_ANTHROPIC, FAKE_GOOGLE, FAKE_AWS])
def test_a_credential_shape_is_redacted_wherever_it_sits(secret):
    """Nested in a list, in a dict, in a string. The walk has to reach all of it."""
    body = {
        "choices": [{"message": {"content": f"the key is {secret} apparently"}}],
        "meta": {"echo": [secret, {"deep": secret}]},
    }

    cleaned = json.dumps(scrub.payload(body))

    assert secret not in cleaned
    assert scrub.REDACTED in cleaned


def test_headers_are_an_allowlist_not_a_blocklist():
    """The header a provider adds next year is on nobody's blocklist today."""
    kept = scrub.headers(
        {
            "Content-Type": "application/json",
            "Authorization": _assemble("Bearer ", "sk", "-proj-", "secret-value-here-0000"),
            "x-provider-invented-tomorrow": "some-token",
            "Set-Cookie": "session=abc",
        }
    )

    assert set(kept) == {"Content-Type"}


def test_the_audit_catches_a_key_the_scrubber_does_not_recognise():
    """The case that justifies the audit existing at all.

    A provider whose keys look like nothing in `KEY_SHAPES` gets past the
    scrubber untouched. The audit knows the literal value, so it does not care
    what shape it is.
    """
    secret = "wholly-unlike-any-known-key-format-42"
    blob = json.dumps(scrub.payload({"header": {"x-auth": secret}}))

    assert secret in blob, "the scrubber is not expected to catch this one"
    assert scrub.audit(blob, [secret]) == ["a live credential value appears in the recording"]


def test_clean_bytes_audit_clean():
    blob = json.dumps({"choices": [{"message": {"content": '{"verdict": "pass"}'}}]})

    assert scrub.audit(blob, [FAKE_OPENAI]) == []


def test_the_audit_reports_a_shape_that_survived():
    """Belt and braces: a credential shape in the output is a failure even when
    it is not one of the environment's own secrets. It is somebody's."""
    problems = scrub.audit(json.dumps({"note": FAKE_OPENAI}), [])

    assert problems and "survived scrubbing" in problems[0]


def test_an_empty_secret_is_not_treated_as_a_substring_of_everything():
    """An unset variable reads as an empty string, and `"" in blob` is always
    true. That would make the recorder refuse every recording forever, which
    reads as the guard working rather than as the bug it is."""
    assert scrub.audit(json.dumps({"ok": True}), ["", None or ""]) == []
