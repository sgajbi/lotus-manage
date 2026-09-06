"""One mandate-version ordering corpus, asserted against both backends.

The in-memory store and the PostgreSQL store each answer "which mandate
version is current". If they answer differently, the same data resolves to
different twins depending on configuration, and a test that exercises only one
store cannot see it. Both are checked against the list below: the unit suite
orders it in memory, the database lane orders it in PostgreSQL, and both
assert EXPECTED_CORPUS_ORDER.

Keep the entries adversarial. Every case here comes from a defect that reached
review: lexicographic ordering, values past a cast's range, leading zeros that
compare equal, a trailing newline that Python's '$' accepts and PostgreSQL's
'~' does not, and Unicode digits that str.isdigit() accepts and [0-9] does not.
"""

from __future__ import annotations

# Deliberately not in sorted order: a corpus that arrives sorted cannot show
# that the ordering did anything.
SHARED_ORDERING_CORPUS: tuple[str, ...] = (
    "9",
    "10",
    "1",
    "01",
    "v2",
    "100",
    "007",
    "9\n",
    "٢",
    "2",
)

# Newest first, the order both stores must produce.
#
# Numeric versions lead, ordered by magnitude: 100, 10, 9, then 007 (which is
# seven, not a string starting with two zeros), then 2, then the two spellings
# of one. '1' precedes '01' because equal magnitudes fall through to the raw
# column descending.
#
# Non-numeric values sort last, also by raw text descending. That order is by
# code point in Python and by byte under COLLATE "C" in PostgreSQL, which agree
# here: the Arabic-Indic digit encodes to d9a2, 'v2' to 7632, and the
# newline-terminated value to 390a.
EXPECTED_CORPUS_ORDER: tuple[str, ...] = (
    "100",
    "10",
    "9",
    "007",
    "2",
    "1",
    "01",
    "٢",
    "v2",
    "9\n",
)
