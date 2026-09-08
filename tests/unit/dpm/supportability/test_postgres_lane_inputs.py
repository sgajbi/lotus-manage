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

import ast
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MAKEFILE = REPOSITORY_ROOT / "Makefile"
INTEGRATION_ROOT = REPOSITORY_ROOT / "tests" / "integration"

# Two questions, deliberately kept apart.
#
#   CANDIDATE  does this file import a PostgreSQL adapter?
#   PROOF      does it run that adapter against a REAL database?
#
# Collapsing them is wrong in both directions, and this module has now made
# both mistakes.
#
# Matching on the FILENAME would have been simpler and wrong -
# `test_mandate_temporal_reads_postgres.py` says so in its name, but nothing
# makes the next author repeat the convention. The first version then made the
# same mistake one level down, keying on the prerequisite helper names and one
# environment-variable string, so a proof reaching PostgreSQL through its own
# DSN variable was invisible.
#
# Widening to the adapter import alone is the opposite error.
# `tests/integration/dpm/pm_quality/test_pm_quality_endpoint_lifecycle.py`
# imports the adapter and then monkeypatches `has_psycopg` and
# `_import_psycopg` with a fake driver. It never opens a connection. Adding it
# to the database lane would demand a DSN it does not use, and routing it
# through the prerequisite would make it fail for want of a database it does
# not want. Both review rounds on PR #695 found one half of this.
#
# So: an import makes a file a candidate, and a candidate is a proof unless it
# stubs the driver. The exclusion is asserted rather than assumed - a candidate
# that is neither in the lane nor visibly stubbed fails, so "it uses a fake"
# has to be true in the file rather than believed about it.
#
# Imports are parsed, not pattern-matched: `from src.infrastructure.pm_quality
# import postgres as pm_quality_postgres` puts the word after the `import`
# keyword and defeats any regex anchored on the module path.
ADAPTER_MODULE_ROOT = "src.infrastructure"

# What a file does to run the adapter without a database. Naming these is the
# point: the exclusion is a statement about the file, checkable by reading it.
DRIVER_STUB_MARKERS = (
    "has_psycopg",
    "_import_psycopg",
    "_FakePsycopg",
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


def imports_a_postgres_adapter(source: str) -> bool:
    """True when the file imports a PostgreSQL adapter, in any import form.

    Parsed rather than pattern-matched, because the module path is not the only
    place the name appears: `from src.infrastructure.pm_quality import postgres
    as pm_quality_postgres` carries it as an imported NAME, and a regex anchored
    on the dotted path misses it entirely.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:  # pragma: no cover - a broken test file fails elsewhere
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name.startswith(ADAPTER_MODULE_ROOT) and "postgres" in alias.name
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if not module.startswith(ADAPTER_MODULE_ROOT):
                continue
            if "postgres" in module:
                return True
            if any("postgres" in alias.name for alias in node.names):
                return True
    return False


def stubs_the_driver(source: str) -> bool:
    return any(marker in source for marker in DRIVER_STUB_MARKERS)


def _candidate_files() -> list[Path]:
    """Files that import a PostgreSQL adapter, stubbed or not."""

    return sorted(
        path
        for path in INTEGRATION_ROOT.rglob("test_*.py")
        if imports_a_postgres_adapter(path.read_text(encoding="utf-8"))
        or any(marker in path.read_text(encoding="utf-8") for marker in MARKERS)
    )


def test_the_detector_reads_every_import_form_and_only_imports() -> None:
    """The discriminating cases, asserted directly.

    A detector that quietly stopped matching would pass every assertion below,
    because they all measure a set it produces. These measure the detector.
    """

    assert imports_a_postgres_adapter(
        "from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository\n"
    )
    assert imports_a_postgres_adapter(
        "from src.infrastructure.rebalance_runs.idea_management_actions_postgres import X\n"
    )
    # The form the previous regex missed: the name follows `import`, not the
    # module path. Present in this repository today.
    assert imports_a_postgres_adapter(
        "from src.infrastructure.pm_quality import postgres as pm_quality_postgres\n"
    )
    assert imports_a_postgres_adapter("import src.infrastructure.waves.postgres\n")

    assert not imports_a_postgres_adapter("from src.infrastructure.mandates.in_memory import X\n")
    # A mention in prose is not an import, and neither is an unrelated package.
    assert not imports_a_postgres_adapter('"""Talks about src.infrastructure.waves.postgres."""\n')
    assert not imports_a_postgres_adapter("from tests.helpers.postgres import thing\n")


def _postgres_proof_files() -> list[Path]:
    """Candidates that actually reach a database - stubs excluded."""

    return [
        path
        for path in _candidate_files()
        if not stubs_the_driver(path.read_text(encoding="utf-8"))
    ]


def test_every_candidate_is_either_in_the_lane_or_visibly_stubbed() -> None:
    """A candidate excluded for using a fake must SAY it uses a fake.

    Without this, "not a real proof" is a belief about a file rather than a
    property of it, and the exclusion becomes the hiding place: a genuine proof
    that simply forgot the prerequisite would be indistinguishable from one
    that deliberately runs against a stub.
    """

    lane = [(REPOSITORY_ROOT / path).resolve() for path in _lane_paths()]
    unexplained = []
    for path in _candidate_files():
        in_lane = any(path == entry or entry in path.parents for entry in lane)
        if in_lane or stubs_the_driver(path.read_text(encoding="utf-8")):
            continue
        unexplained.append(path.relative_to(REPOSITORY_ROOT).as_posix())

    assert not unexplained, (
        "these files import a PostgreSQL adapter, are not in the database lane, "
        "and do not visibly stub the driver - so nothing says whether they are "
        "unrun proofs or fake-backed tests: " + ", ".join(unexplained)
    )


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
