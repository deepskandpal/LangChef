"""Exit codes are a public contract. Renumbering one silently breaks every gate."""

from langchef.core.exits import REASON, Exit


def test_codes_are_stable():
    assert (Exit.OK, Exit.ERROR, Exit.REFUSED, Exit.ABSTAINED, Exit.BUDGET, Exit.PIN_MISMATCH) == (
        0,
        1,
        2,
        3,
        4,
        5,
    )


def test_every_code_has_a_reason():
    assert set(REASON) == set(Exit)
    assert all(REASON[code] for code in Exit)


def test_only_ok_is_zero():
    assert [c for c in Exit if c == 0] == [Exit.OK]
