"""Every PostgreSQL proof is reachable from the lane that owns a database (#693).

The lane's input is a hand-written list in the Makefile. A proof file absent
from it does not fail, does not skip and does not appear anywhere in the run -
it is indistinguishable from a proof that passed. That is not hypothetical:
issue #677's wave isolation proofs were cited as evidence for months while the
list named only the supportability suite and `dpm/mandates`, so they had never
executed in CI at all.

Aligning the list once fixes today's omission and nothing else. This test makes
the omission impossible to repeat: it enumerates the PostgreSQL proof files that
exist and asserts each is covered by a path the lane names.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MAKEFILE = REPOSITORY_ROOT / "Makefile"
INTEGRATION_ROOT = REPOSITORY_ROOT / "tests" / "integration"

# What makes a file a PostgreSQL proof: it imports a PostgreSQL ADAPTER.
#
# Matching on the FILENAME would have been simpler and wrong -
# `test_mandate_temporal_reads_postgres.py` says so in its name, but nothing
# makes the next author repeat the convention. The first version of this test
# then made the same mistake one level down: it matched the prerequisite helper
# names and one environment-variable string, so a proof reaching PostgreSQL
# through its own DSN variable and its own skip was invisible, and BOTH tests
# below passed while the lane omitted exactly the file they claim to cover.
# Raised in review on PR #695.
#
# The import is the thing that cannot be avoided: a test cannot exercise the
# PostgreSQL adapter without naming it. The helper and env-var markers are kept
# as a widening, not as the definition.
ADAPTER_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+src\.infrastructure\.[\w.]*postgres[\w.]*",
    re.MULTILINE,
)

MARKERS = (
    "postgres_dsn_or_skip",
    "postgres_dsn_or_fake",
    "DPM_POSTGRES_INTEGRATION_DSN",
)

# The two forms of the prerequisite. Either consults
# DPM_POSTGRES_INTEGRATION_REQUIRED; a file using neither decides its own fate
# and the lane cannot make it run.
PREREQUISITE_HELPERS = ("postgres_dsn_or_skip", "postgres_dsn_or_fake")


def _lane_paths() -> list[str]:
    """The paths named by POSTGRES_INTEGRATION_TESTS, following its line continuations."""

    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        r"^POSTGRES_INTEGRATION_TESTS\s*=\s*((?:.*\\\n)*.*)$",
        text,
        re.MULTILINE,
    )
    assert match, "the lane variable POSTGRES_INTEGRATION_TESTS is not defined in the Makefile"
    return [
        token
        for token in match.group(1).replace("\\\n", " ").split()
        if token and not token.startswith("$")
    ]


def _postgres_proof_files() -> list[Path]:
    def is_proof(path: Path) -> bool:
        text = path.read_text(encoding="utf-8")
        return bool(ADAPTER_IMPORT.search(text)) or any(marker in text for marker in MARKERS)

    return sorted(path for path in INTEGRATION_ROOT.rglob("test_*.py") if is_proof(path))


def test_the_detector_recognises_an_adapter_import_on_its_own() -> None:
    """The widened detector must actually widen.

    A detector that still keys on the helper names would pass every assertion
    below while missing the file they exist to catch, and nothing about a green
    run distinguishes the two. So this asserts the discriminating case directly:
    an adapter import, with no helper name and no environment variable
    anywhere.
    """

    assert ADAPTER_IMPORT.search(
        "from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository\n"
    )
    assert ADAPTER_IMPORT.search(
        "from src.infrastructure.rebalance_runs.idea_management_actions_postgres import X\n"
    )
    assert not ADAPTER_IMPORT.search("from src.infrastructure.mandates.in_memory import X\n")
    # A mention in prose or a docstring is not an import.
    assert not ADAPTER_IMPORT.search('"""Talks about src.infrastructure.waves.postgres."""\n')


def test_the_lane_names_every_postgres_proof_file() -> None:
    lane = [(REPOSITORY_ROOT / path).resolve() for path in _lane_paths()]
    proofs = _postgres_proof_files()

    assert proofs, "no PostgreSQL proof files were found; the detector below proves nothing"

    unreachable = [
        proof.relative_to(REPOSITORY_ROOT).as_posix()
        for proof in proofs
        if not any(proof == entry or entry in proof.parents for entry in lane)
    ]

    assert not unreachable, (
        "these PostgreSQL proofs are not reachable from POSTGRES_INTEGRATION_TESTS, "
        "so the database lane runs green without them: " + ", ".join(unreachable)
    )


def test_every_lane_path_exists() -> None:
    """A stale entry is the same defect read backwards.

    A path that no longer exists makes the list look larger than the coverage
    it buys, and pytest accepts a directory that is empty without complaint.
    """

    missing = [path for path in _lane_paths() if not (REPOSITORY_ROOT / path).exists()]

    assert not missing, f"POSTGRES_INTEGRATION_TESTS names paths that do not exist: {missing}"


def test_no_postgres_proof_gates_itself_on_a_bare_dsn_check() -> None:
    """The prerequisite must be consulted, not merely present in the environment.

    `DPM_POSTGRES_INTEGRATION_REQUIRED=1` is set in both workflows, but it only
    reaches files that route through `postgres_dsn_or_skip`. A file keeping its
    own `skipif(not DSN)` skips silently in the lane that declared the database
    a prerequisite - which is the exact shape of the defect the flag was added
    to close, surviving in the files that did not adopt it.
    """

    offenders = [
        proof.relative_to(REPOSITORY_ROOT).as_posix()
        for proof in _postgres_proof_files()
        if not any(helper in proof.read_text(encoding="utf-8") for helper in PREREQUISITE_HELPERS)
    ]

    assert not offenders, (
        "these PostgreSQL proofs decide their own skip and so ignore "
        "DPM_POSTGRES_INTEGRATION_REQUIRED: " + ", ".join(offenders)
    )
