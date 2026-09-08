"""One place that decides whether a PostgreSQL suite may skip.

Both wave PostgreSQL suites gated on `skipif(not DSN)` alone, so they skipped
silently wherever the DSN was unset - which was everywhere in CI, because the
database lane's file list named only the supportability suite and
`dpm/mandates`. The proofs written for issue #677 had therefore never run in
CI at all, while being cited as evidence that the wave fence holds.

The DSN check is not the defect; skipping *quietly* is. In a lane that exists
to run these proofs, an absent prerequisite is a failure, not a reason to pass.
`DPM_POSTGRES_INTEGRATION_REQUIRED=1` turns every skip in this family into a
loud failure naming what was missing.
"""

from __future__ import annotations

import os

import pytest

DSN_ENV = "DPM_POSTGRES_INTEGRATION_DSN"
REQUIRED_ENV = "DPM_POSTGRES_INTEGRATION_REQUIRED"


def postgres_dsn_or_skip(proof: str, *, module_level: bool = False) -> str:
    """The DSN, or an outcome that is honest about why there is none.

    Returns the DSN when configured. Otherwise fails when the lane declared
    the database a prerequisite, and skips only when it did not - so a local
    run without a database still skips, and a CI lane that promised to run
    these proofs cannot report success without them.

    Pass `module_level=True` when calling this during import rather than from
    inside a test; pytest refuses a module-level skip otherwise, and the suite
    would report a collection error instead of a skip.
    """

    dsn = os.getenv(DSN_ENV, "").strip()
    if dsn:
        return dsn
    if os.getenv(REQUIRED_ENV, "").strip() == "1":
        pytest.fail(
            f"{DSN_ENV} is unset while {REQUIRED_ENV}=1: the {proof} did not run. "
            "A lane that declares the database a prerequisite must fail rather "
            "than skip, or an unrun proof is reported as a passing one."
        )
    pytest.skip(
        f"{DSN_ENV} is not configured, so the {proof} cannot run",
        allow_module_level=module_level,
    )
    raise AssertionError("unreachable")


def postgres_dsn_or_fake(proof: str) -> str | None:
    """The DSN, or None for a suite that legitimately runs against a fake.

    Two suites name every test `test_live_postgres_*` and fall back to an
    in-process fake when no DSN is set, so they always report a pass and never
    say which engine produced it. The fallback itself is defensible - the
    contracts they assert are worth running locally without a database - but
    two things about it were not:

    the fallback also fired on ANY exception while a DSN WAS configured, so a
    refused connection, a failed migration or a bad credential silently became
    a green run against the fake; and it consulted the DSN alone, so the lane
    that declares a database a prerequisite could not make it fail.

    Returning None says "no database was offered". A caller may then use its
    fake. Being handed a DSN means the real engine is expected to work, and a
    failure from it belongs to the test rather than to a fallback.
    """

    dsn = os.getenv(DSN_ENV, "").strip()
    if dsn:
        return dsn
    if os.getenv(REQUIRED_ENV, "").strip() == "1":
        pytest.fail(
            f"{DSN_ENV} is unset while {REQUIRED_ENV}=1: the {proof} would have run "
            "against its in-process fake and reported a pass. A lane that declares "
            "the database a prerequisite must fail rather than substitute one."
        )
    return None
