"""Tenant isolation for mandate evidence, proven against PostgreSQL (#648).

The defect this closes is that mandate snapshots and health snapshots were
stored and read with no tenant dimension at all, so the same mandate id under
two tenants resolved to one row and either tenant could read the other's
evidence.

These run against a real engine on purpose. The isolation is enforced by SQL
predicates and a unique constraint, and neither is a Python fact: an in-memory
store can be made to agree with any claim about them, including a false one.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import closing
from datetime import date

import pytest

from src.core.mandates import DpmMandateConstraintSet, DpmMandateDigitalTwin, DpmMandateReviewPolicy
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()

pytestmark = pytest.mark.skipif(
    not _DSN, reason="DPM_POSTGRES_INTEGRATION_DSN is required for the tenant isolation proof"
)

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


@pytest.fixture
def repository() -> PostgresDpmMandateRepository:
    return PostgresDpmMandateRepository(dsn=_DSN)


def _twin(
    *, mandate_id: str, portfolio_id: str, version: str, currency: str
) -> DpmMandateDigitalTwin:
    """A twin distinguishable by base_currency, so a leak is visible in the value."""

    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version=version,
        as_of_date=date(2026, 5, 3),
        source_system="lotus-core",
        base_currency=currency,
        reference_currency=currency,
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_TENANT_ISOLATION",
        constraints=DpmMandateConstraintSet(),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


def _clear(repository: PostgresDpmMandateRepository, mandate_id: str) -> None:
    with closing(repository._connect()) as connection:
        connection.execute("DELETE FROM dpm_mandate_snapshots WHERE mandate_id = %s", (mandate_id,))
        connection.commit()


def test_the_same_mandate_identifiers_under_two_tenants_stay_separate(
    repository: PostgresDpmMandateRepository,
) -> None:
    """The headline acceptance: identical identifiers, two tenants, no crossing.

    Same mandate id, same portfolio id, same version, same business date -
    everything that used to form the row's identity. Only the tenant differs.
    Before this change the second write would have overwritten the first,
    because the unique constraint was tenant-blind, and either tenant's read
    would have returned whichever row survived.
    """

    mandate_id = f"MANDATE_ISO_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_ISO_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="7", currency="SGD"),
            tenant_id=TENANT_A,
        )
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="7", currency="CHF"),
            tenant_id=TENANT_B,
        )

        # Both rows survive: the second write did not overwrite the first.
        alpha = repository.get_latest_mandate(mandate_id=mandate_id, tenant_id=TENANT_A)
        beta = repository.get_latest_mandate(mandate_id=mandate_id, tenant_id=TENANT_B)
        assert alpha is not None and beta is not None
        assert alpha.base_currency == "SGD"
        assert beta.base_currency == "CHF"

        # Portfolio-keyed reads separate too, since they carry the same filter.
        alpha_by_portfolio = repository.get_latest_mandate_by_portfolio(
            portfolio_id=portfolio_id, tenant_id=TENANT_A
        )
        beta_by_portfolio = repository.get_latest_mandate_by_portfolio(
            portfolio_id=portfolio_id, tenant_id=TENANT_B
        )
        assert alpha_by_portfolio is not None and beta_by_portfolio is not None
        assert alpha_by_portfolio.base_currency == "SGD"
        assert beta_by_portfolio.base_currency == "CHF"

        # And a version listing shows one tenant's history, not the union.
        alpha_versions = repository.list_mandate_versions(mandate_id=mandate_id, tenant_id=TENANT_A)
        assert [twin.base_currency for twin in alpha_versions] == ["SGD"]
    finally:
        _clear(repository, mandate_id)


def test_a_tenant_with_no_rows_reads_nothing_rather_than_another_tenants_rows(
    repository: PostgresDpmMandateRepository,
) -> None:
    """The failure mode that matters is the read that succeeds wrongly.

    A third tenant asking for a mandate it has no rows for must get nothing.
    Returning another tenant's row would be the original defect, and it would
    look like a working read to every caller and every log line.
    """

    mandate_id = f"MANDATE_ISO_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_ISO_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="1", currency="SGD"),
            tenant_id=TENANT_A,
        )

        assert (
            repository.get_latest_mandate(mandate_id=mandate_id, tenant_id="tenant-unrelated")
            is None
        )
        assert (
            repository.get_latest_mandate_by_portfolio(
                portfolio_id=portfolio_id, tenant_id="tenant-unrelated"
            )
            is None
        )
        assert (
            repository.list_mandate_versions(mandate_id=mandate_id, tenant_id="tenant-unrelated")
            == []
        )
    finally:
        _clear(repository, mandate_id)


def test_rows_that_could_not_be_attributed_are_unreachable_from_every_tenant(
    repository: PostgresDpmMandateRepository,
) -> None:
    """Quarantine, not a default tenant.

    Migration 0024 adds tenant_id without backfilling it, because no value
    would have been true: assigning pre-existing rows to a default tenant
    would hand one tenant's mandate evidence to whoever that default names.
    NULL matches no equality predicate, so an unattributed row is invisible to
    every tenant rather than visible to the wrong one. It is still present for
    an operator to attribute deliberately, which is the point of quarantining
    rather than deleting.
    """

    mandate_id = f"MANDATE_QUAR_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_QUAR_{uuid.uuid4().hex[:8]}"
    try:
        # A pre-upgrade row: written before tenant_id existed, so it has none.
        with closing(repository._connect()) as connection:
            connection.execute(
                """
                INSERT INTO dpm_mandate_snapshots (
                    mandate_snapshot_id, mandate_id, portfolio_id, mandate_version,
                    as_of_date, source_hash, source_lineage_json, payload_json,
                    created_at, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    f"ms_{uuid.uuid4().hex[:12]}",
                    mandate_id,
                    portfolio_id,
                    "1",
                    "2026-05-03",
                    "sha256:legacy",
                    "[]",
                    _twin(
                        mandate_id=mandate_id,
                        portfolio_id=portfolio_id,
                        version="1",
                        currency="SGD",
                    ).model_dump_json(),
                    "2026-05-03T01:00:00+00:00",
                    "lotus-manage",
                ),
            )
            connection.commit()

        # The row exists.
        with closing(repository._connect()) as connection:
            row = connection.execute(
                "SELECT tenant_id FROM dpm_mandate_snapshots WHERE mandate_id = %s",
                (mandate_id,),
            ).fetchone()
        assert row is not None
        stored_tenant = row["tenant_id"] if isinstance(row, dict) else row[0]
        assert stored_tenant is None, "the pre-upgrade row must not have been given a tenant"

        # And it is reachable from no tenant at all, including plausible ones.
        for tenant in (TENANT_A, TENANT_B, "default", ""):
            assert repository.get_latest_mandate(mandate_id=mandate_id, tenant_id=tenant) is None, (
                f"an unattributed row was reachable from {tenant!r}"
            )
            assert (
                repository.get_latest_mandate_by_portfolio(
                    portfolio_id=portfolio_id, tenant_id=tenant
                )
                is None
            )
    finally:
        _clear(repository, mandate_id)


def test_health_evidence_is_scoped_with_its_mandate(
    repository: PostgresDpmMandateRepository,
) -> None:
    """Health snapshots carry the same identifiers and need the same fence.

    Scoping the twin and leaving its assessment shared would leak the more
    sensitive half: a health snapshot states scores, breaches and reason codes
    for a client's mandate.
    """

    mandate_id = f"MANDATE_HEALTH_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_HEALTH_{uuid.uuid4().hex[:8]}"
    try:
        with closing(repository._connect()) as connection:
            for tenant, score in ((TENANT_A, 91), (TENANT_B, 42)):
                connection.execute(
                    """
                    INSERT INTO dpm_mandate_health_snapshots (
                        health_snapshot_id, mandate_id, portfolio_id, as_of_date,
                        health_score, health_state, top_reason_code,
                        source_readiness_state, dimension_scores_json, payload_json,
                        created_at, tenant_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        f"hs_{uuid.uuid4().hex[:12]}",
                        mandate_id,
                        portfolio_id,
                        "2026-05-03",
                        score,
                        "READY",
                        "",
                        "COMPLETE",
                        "[]",
                        json.dumps({"health_score": score}),
                        "2026-05-03T01:00:00+00:00",
                        tenant,
                    ),
                )
            connection.commit()

        with closing(repository._connect()) as connection:
            for tenant, expected in ((TENANT_A, 91), (TENANT_B, 42)):
                found = connection.execute(
                    "SELECT health_score FROM dpm_mandate_health_snapshots"
                    " WHERE tenant_id = %s AND mandate_id = %s",
                    (tenant, mandate_id),
                ).fetchall()
                scores = [(r["health_score"] if isinstance(r, dict) else r[0]) for r in found]
                assert scores == [expected], f"{tenant} saw {scores}"
    finally:
        with closing(repository._connect()) as connection:
            connection.execute(
                "DELETE FROM dpm_mandate_health_snapshots WHERE mandate_id = %s", (mandate_id,)
            )
            connection.commit()
