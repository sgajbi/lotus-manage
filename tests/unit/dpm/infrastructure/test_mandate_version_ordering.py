"""The in-memory mandate version ordering must match PostgreSQL's (issue #646).

Both stores answer "which mandate version is current". If they order versions
differently, the same mandate resolves to different twins depending on which
backend is configured, and no test that exercises one store can detect it.

The PostgreSQL ordering under test is:

    CASE WHEN mandate_version ~ '^[0-9]+$'
         THEN mandate_version::numeric ELSE NULL END DESC NULLS LAST,
    mandate_version DESC

These tests pin the in-memory key against that expression element for element.
The equivalent PostgreSQL assertions live in
tests/integration/dpm/mandates/test_mandate_temporal_reads_postgres.py, which
runs against a real engine because a cast's behaviour is an engine claim.
"""

from __future__ import annotations

import sys

from src.infrastructure.mandates.in_memory import _mandate_version_sort_key
from tests.support.mandate_version_corpus import (
    EXPECTED_CORPUS_ORDER,
    SHARED_ORDERING_CORPUS,
)


def _newest_first(versions: list[str]) -> list[str]:
    """Order versions the way the repository does: by sort key, descending."""

    return sorted(versions, key=_mandate_version_sort_key, reverse=True)


def test_numeric_versions_order_by_value_not_by_text() -> None:
    # The defect this whole contract exists for: lexicographically '9' > '10'.
    assert _newest_first(["1", "2", "9", "10", "100"]) == ["100", "10", "9", "2", "1"]


def test_equal_valued_versions_are_separated_by_raw_text_as_sql_does() -> None:
    # '01'::numeric = '1'::numeric, so SQL falls through to mandate_version
    # DESC, which puts '1' first. A key that returns only the numeric value
    # leaves these tied, and Python's stable sort would then order them by
    # insertion - so the store that answers first would decide, not the data.
    assert _newest_first(["01", "1"]) == ["1", "01"]
    assert _newest_first(["1", "01"]) == ["1", "01"]

    # Ties are broken consistently however many share a value.
    assert _newest_first(["001", "1", "01"]) == ["1", "01", "001"]


def test_leading_zeros_do_not_change_which_version_is_newest() -> None:
    # '007' is seven, not a string sorting between '0' and '1'.
    assert _newest_first(["007", "10"]) == ["10", "007"]


def test_versions_longer_than_the_int_conversion_limit_still_order() -> None:
    # int(str) raises ValueError above sys.get_int_max_str_digits(), but
    # NUMERIC accepts far longer values, so a version PostgreSQL orders
    # without complaint must not crash this store.
    limit = sys.get_int_max_str_digits()
    over_limit = "9" * (limit + 1)
    longer_still = "1" + "0" * (limit + 1)  # One digit longer, so larger.

    assert len(over_limit) > limit
    assert len(longer_still) > len(over_limit)
    assert _newest_first([over_limit, "10", longer_still]) == [
        longer_still,
        over_limit,
        "10",
    ]


def test_non_numeric_versions_sort_last_and_deterministically() -> None:
    # NULLS LAST puts non-numeric versions after every numeric one, then
    # mandate_version DESC orders them among themselves.
    assert _newest_first(["v2", "1", "v10", "3"]) == ["3", "1", "v2", "v10"]


def test_unicode_digits_are_not_numeric_because_postgres_rejects_them() -> None:
    # str.isdigit() accepts these; PostgreSQL's [0-9] class does not. Treating
    # them as numeric here is how the two stores start disagreeing about which
    # mandate is current.
    arabic_indic = "٢"  # ARABIC-INDIC DIGIT TWO
    superscript = "²"  # SUPERSCRIPT TWO

    assert arabic_indic.isdigit()
    assert superscript.isdigit()
    assert _newest_first([arabic_indic, superscript, "1"])[0] == "1"


def test_the_key_shape_matches_the_three_sql_ordering_elements() -> None:
    # numeric-ness, then magnitude, then raw text - the same three decisions
    # the SQL expression makes, in the same order.
    numeric_rank, _, _, raw_text = _mandate_version_sort_key("042")
    assert numeric_rank == 1
    assert raw_text == "042"

    non_numeric_rank, _, _, raw_text = _mandate_version_sort_key("v2")
    assert non_numeric_rank == 0
    assert raw_text == "v2"
    assert non_numeric_rank < numeric_rank


def test_a_trailing_newline_does_not_make_a_version_numeric() -> None:
    """Python's '$' also matches immediately before a trailing newline.

    re.match(r'^[0-9]+$', '9\n') therefore succeeds, and the newline counts
    toward the key's length, so '9\n' would order above '10'. PostgreSQL's '~'
    anchors at the true end of the string and treats the value as non-numeric,
    sorting it last. The two stores would pick different latest snapshots for
    the same rows, which is the failure this whole contract exists to prevent.
    """

    assert _newest_first(["9\n", "10"]) == ["10", "9\n"]

    # It is non-numeric, so it sorts behind every well-formed digit string.
    assert _newest_first(["9\n", "1"]) == ["1", "9\n"]

    numeric_rank, _, _, _ = _mandate_version_sort_key("9\n")
    assert numeric_rank == 0


def test_the_shared_ordering_corpus_is_ordered_as_the_contract_states() -> None:
    """The corpus both backends are checked against, ordered here in memory.

    The PostgreSQL half asserts the same expected order in
    tests/integration/dpm/mandates/test_mandate_temporal_reads_postgres.py, so
    a change to either implementation that breaks the agreement fails on one
    side or the other rather than passing quietly on both.
    """

    assert _newest_first(list(SHARED_ORDERING_CORPUS)) == list(EXPECTED_CORPUS_ORDER)
