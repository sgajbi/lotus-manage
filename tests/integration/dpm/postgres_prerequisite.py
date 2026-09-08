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


def postgres_dsn_or_skip(proof: str) -> str:
    """The DSN, or an outcome that is honest about why there is none.

    Returns the DSN when configured. Otherwise fails when the lane declared
    the database a prerequisite, and skips only when it did not - so a local
    run without a database still skips, and a CI lane that promised to run
    these proofs cannot report success without them.
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
    pytest.skip(f"{DSN_ENV} is not configured, so the {proof} cannot run")
    raise AssertionError("unreachable")
