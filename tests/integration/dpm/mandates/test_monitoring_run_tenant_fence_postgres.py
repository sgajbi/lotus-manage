"""Monitoring-run read fencing, proven against PostgreSQL (#693).

The unit proofs in `tests/unit/dpm/mandates/test_monitoring_run_read_fence.py`
decide these questions in Python, and for the PostgreSQL adapter they decide
them against a hand-written fake that re-implements the SQL rather than
executing it. Falsification showed exactly what that costs: removing
`AND tenant_id = %s` from the direct-read query left every unit test passing,
because the fake never reads the query text. The predicate under test is not
observable there at all.

Four properties belong to the engine and are only really proven here:

1. the fence is a WHERE predicate - it either reached the statement or it did
   not, and no Python object can stand in for that,
2. a NULL `tenant_id` is matched by no equality predicate, because
   `NULL = 'anything'` evaluates to NULL rather than to false. The column has
   been nullable since migration 0003 and was never backfilled, so the
   quarantine claim rests on three-valued logic Python does not share,
3. the cursor subquery resolves the anchor row under the caller's tenant, so
   another tenant's run id cannot position the page,
4. filtering happens before LIMIT, which is an ordering the planner decides
   from the statement, not something the adapter can assert about itself.

Requires a real engine: set DPM_POSTGRES_INTEGRATION_DSN to a disposable
database. In the CI lane that owns one, an absent DSN fails rather than skips.
"""

from __future__ import annotations

import json
import uuid
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository
from src.api.main import app
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
    DpmMonitoringRun,
)
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository

from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip

_PROOF = "monitoring-run tenant fence proof"


@pytest.fixture
def repository() -> PostgresDpmMandateRepository:
    return PostgresDpmMandateRepository(dsn=postgres_dsn_or_skip(_PROOF))


@pytest.fixture
def tenants() -> tuple[str, str]:
    """A fresh tenant pair per test, against a database that is not reset.

    Isolating by tenant rather than by cleanup keeps the teardown honest: a
    test that deleted its rows by tenant would be exercising the predicate it
    is meant to be proving.
    """

    run = uuid.uuid4().hex[:12]
    return f"tenant-alpha-{run}", f"tenant-beta-{run}"


def _run(
    *,
    run_id: str,
    tenant_id: str | None,
    requested_at: datetime = datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
    status: str = "SUCCEEDED",
) -> DpmMonitoringRun:
    filters: dict[str, Any] = {"portfolio_manager_id": "PM_SG_DPM_001"}
    if tenant_id is not None:
        filters["tenant_id"] = tenant_id
    run = DpmMonitoringRun(
        monitoring_run_id=run_id,
        tenant_id=tenant_id or "legacy-unowned",
        as_of_date=date(2026, 5, 3),
        requested_at=requested_at,
        completed_at=requested_at + timedelta(seconds=2),
        status=status,
        mandate_ids=["MANDATE_PB_SG_GLOBAL_BAL_001"],
        filters=filters,
        total_mandates=1,
        health_distribution={"READY": 1},
        exception_count=0,
        source_readiness_summary={"READY": 1},
    )
    return run if tenant_id is not None else run.model_copy(update={"tenant_id": None})


def _mandate(*, mandate_id: str, portfolio_id: str) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version="1",
        as_of_date=date(2026, 5, 3),
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(turnover_budget=Decimal("0.15")),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


def test_run_once_persists_only_admitted_tenant_and_refuses_invalid_admission_before_writes(
    repository: PostgresDpmMandateRepository,
) -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-admitted-{suffix}"
    mandate_id = f"MANDATE_ADMISSION_{suffix}"
    repository.save_mandate_snapshot(
        _mandate(mandate_id=mandate_id, portfolio_id=f"PORTFOLIO_{suffix}"),
        tenant_id=tenant_id,
    )
    app.dependency_overrides[get_mandate_repository] = lambda: repository
    request = {
        "mandate_ids": [mandate_id],
        "as_of_date": "2026-05-03",
        "tenant_id": tenant_id,
    }
    try:
        with TestClient(app) as client:
            accepted = client.post(
                "/api/v1/dpm/monitoring/run-once",
                headers={"X-Tenant-Id": tenant_id},
                json=request,
            )
            mismatch = client.post(
                "/api/v1/dpm/monitoring/run-once",
                headers={"X-Tenant-Id": f"other-{tenant_id}"},
                json=request,
            )
            missing = client.post("/api/v1/dpm/monitoring/run-once", json=request)
    finally:
        app.dependency_overrides.clear()

    assert accepted.status_code == 200
    run_id = accepted.json()["monitoring_run_id"]
    assert accepted.json()["tenant_id"] == tenant_id
    assert accepted.json()["filters"]["tenant_id"] == tenant_id
    assert mismatch.status_code == 409
    assert missing.status_code == 422

    with closing(repository._connect()) as connection:  # noqa: SLF001
        row = connection.execute(
            """
            SELECT tenant_id, payload_json
            FROM dpm_monitoring_runs
            WHERE monitoring_run_id = %s
            """,
            (run_id,),
        ).fetchone()
        run_count = connection.execute(
            "SELECT COUNT(*) FROM dpm_monitoring_runs WHERE tenant_id = %s",
            (tenant_id,),
        ).fetchone()
    column_tenant = row["tenant_id"] if isinstance(row, dict) else row[0]
    payload = row["payload_json"] if isinstance(row, dict) else row[1]
    body = payload if isinstance(payload, dict) else json.loads(payload)
    count = run_count["count"] if isinstance(run_count, dict) else run_count[0]
    assert column_tenant == tenant_id
    assert body["tenant_id"] == tenant_id
    assert body["filters"]["tenant_id"] == tenant_id
    assert count == 1, "rejected admissions must not persist additional runs"


def test_a_run_is_readable_only_by_the_tenant_recorded_on_its_row(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    run_id = f"dmr_{uuid.uuid4().hex[:12]}"
    repository.save_monitoring_run(_run(run_id=run_id, tenant_id=tenant_b))

    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_a) is None
    owned = repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_b)
    assert owned is not None and owned.monitoring_run_id == run_id


def test_a_null_tenant_row_is_matched_by_no_caller(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """`NULL = 'anything'` is NULL, so the row is quarantined by the engine.

    This is the claim migration 0003's nullable column rests on, and it is a
    property of three-valued logic rather than of the adapter. Python's
    `None != tenant` reaches the same verdict by a different rule, so the
    in-memory agreement is not evidence for this one.
    """

    tenant_a, _ = tenants
    run_id = f"dmr_{uuid.uuid4().hex[:12]}"
    repository.save_monitoring_run(_run(run_id=run_id, tenant_id=None))

    with closing(repository._connect()) as connection:  # noqa: SLF001
        row = connection.execute(
            "SELECT tenant_id FROM dpm_monitoring_runs WHERE monitoring_run_id = %s",
            (run_id,),
        ).fetchone()
    stored = row["tenant_id"] if isinstance(row, dict) else row[0]
    assert stored is None, "the row must actually carry NULL for this proof to mean anything"

    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_a) is None
    page, _ = repository.list_monitoring_runs(
        status=None, limit=50, cursor=None, tenant_id=tenant_a
    )
    assert [item.monitoring_run_id for item in page] == []


def test_a_list_page_is_filtered_before_it_is_limited(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """Filtering a page rather than the set presents as a SHORT result.

    Tenant B's run is the most recent, so a LIMIT applied before the tenant
    predicate would consume the page on a row tenant A may not see, and A would
    receive fewer of its own runs than it asked for rather than a leak.
    """

    tenant_a, tenant_b = tenants
    suffix = uuid.uuid4().hex[:12]
    repository.save_monitoring_run(
        _run(
            run_id=f"dmr_b_{suffix}",
            tenant_id=tenant_b,
            requested_at=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=f"dmr_a_{suffix}",
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        )
    )

    page, _ = repository.list_monitoring_runs(status=None, limit=1, cursor=None, tenant_id=tenant_a)

    assert [item.monitoring_run_id for item in page] == [f"dmr_a_{suffix}"]


def test_another_tenants_run_id_cannot_position_the_page(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """The cursor subquery is fenced, so the anchor row resolves for one tenant.

    An unfenced subquery leaks ordering position even when the page itself is
    fenced: tenant B's run id resolves to a `started_at`, and tenant A's page
    silently continues from a position B chose.
    """

    tenant_a, tenant_b = tenants
    suffix = uuid.uuid4().hex[:12]
    late = f"dmr_a_late_{suffix}"
    mid = f"dmr_b_mid_{suffix}"
    early = f"dmr_a_early_{suffix}"
    repository.save_monitoring_run(
        _run(
            run_id=late,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=mid,
            tenant_id=tenant_b,
            requested_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=early,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        )
    )

    foreign_page, foreign_cursor = repository.list_monitoring_runs(
        status=None, limit=50, cursor=mid, tenant_id=tenant_a
    )
    assert [item.monitoring_run_id for item in foreign_page] == []
    assert foreign_cursor is None

    # The caller's own cursor still pages, so the refusal above is the tenant
    # predicate rather than a cursor that stopped working at all.
    first, own_cursor = repository.list_monitoring_runs(
        status=None, limit=1, cursor=None, tenant_id=tenant_a
    )
    assert [item.monitoring_run_id for item in first] == [late]
    following, _ = repository.list_monitoring_runs(
        status=None, limit=50, cursor=own_cursor, tenant_id=tenant_a
    )
    assert [item.monitoring_run_id for item in following] == [early]


def test_a_row_whose_column_and_payload_disagree_is_served_to_nobody(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """`ON CONFLICT` refreshes the body and never the owner column.

    A re-save carrying a different tenant rewrites `payload_json` and
    `filters_json` while `tenant_id` keeps naming the original owner. Fencing
    on the column alone then admits the original tenant and hands back a body
    that says someone else. Neither record is trusted over the other.
    """

    tenant_a, tenant_b = tenants
    run_id = f"dmr_{uuid.uuid4().hex[:12]}"
    repository.save_monitoring_run(_run(run_id=run_id, tenant_id=tenant_a))
    repository.save_monitoring_run(_run(run_id=run_id, tenant_id=tenant_b))

    with closing(repository._connect()) as connection:  # noqa: SLF001
        row = connection.execute(
            "SELECT tenant_id, payload_json FROM dpm_monitoring_runs WHERE monitoring_run_id = %s",
            (run_id,),
        ).fetchone()
    column = row["tenant_id"] if isinstance(row, dict) else row[0]
    payload = row["payload_json"] if isinstance(row, dict) else row[1]
    # JSONB comes back decoded; a TEXT column would not.
    body = payload if isinstance(payload, dict) else json.loads(payload)
    body_tenant = body["filters"]["tenant_id"]
    assert column == tenant_a, "the conflict clause is expected to leave the owner column alone"
    assert body_tenant == tenant_b, "the conflict clause is expected to refresh the body"

    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_a) is None
    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_b) is None


@pytest.mark.parametrize("json_path", ["{tenant_id}", "{filters,tenant_id}"])
def test_each_payload_owner_record_must_agree_with_the_tenant_column(
    repository: PostgresDpmMandateRepository,
    tenants: tuple[str, str],
    json_path: str,
) -> None:
    tenant_a, tenant_b = tenants
    run_id = f"dmr_owner_guard_{uuid.uuid4().hex[:12]}"
    repository.save_monitoring_run(_run(run_id=run_id, tenant_id=tenant_a))

    with closing(repository._connect()) as connection:  # noqa: SLF001
        connection.execute(
            """
            UPDATE dpm_monitoring_runs
            SET payload_json = jsonb_set(payload_json, %s::text[], to_jsonb(%s::text), true)
            WHERE monitoring_run_id = %s
            """,
            (json_path, tenant_b, run_id),
        )
        connection.commit()

    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_a) is None
    assert repository.get_monitoring_run(monitoring_run_id=run_id, tenant_id=tenant_b) is None


def test_a_contradictory_row_does_not_shorten_the_page_it_is_excluded_from(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """The owner-agreement predicate must filter the SET, not the fetched page.

    The first version of this fence compared the payload's tenant in Python,
    after the query had already applied `LIMIT`. A contradictory row that sorts
    ahead of the caller's own runs then consumed the window and was dropped
    afterwards, so the caller received a SHORT page - here, an EMPTY one with
    no cursor - while its own older runs sat unread and unreachable.

    That is the same defect as filtering a page instead of a set, arriving
    through a second predicate rather than the tenant one. Raised in review on
    PR #695; this is the case it named.
    """

    tenant_a, tenant_b = tenants
    suffix = uuid.uuid4().hex[:12]
    contradictory = f"dmr_split_{suffix}"
    newer = f"dmr_valid_newer_{suffix}"
    older = f"dmr_valid_older_{suffix}"

    # Newest, and contradictory: the column says tenant A, the body says B.
    # Two saves, because that is how the row reaches this state in production -
    # ON CONFLICT refreshes the body and leaves the owner column alone.
    repository.save_monitoring_run(
        _run(
            run_id=contradictory,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=contradictory,
            tenant_id=tenant_b,
            requested_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        )
    )
    # Two valid runs, so a correct page still has a NEXT one. With a single
    # valid run the absent cursor is right for a different reason and the test
    # could not tell a preserved window from an exhausted one.
    repository.save_monitoring_run(
        _run(
            run_id=newer,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=older,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
        )
    )

    page, cursor = repository.list_monitoring_runs(
        status=None, limit=1, cursor=None, tenant_id=tenant_a
    )

    assert [item.monitoring_run_id for item in page] == [newer], (
        "the contradictory row consumed the page window and was filtered "
        "afterwards, so the caller's own run was never returned"
    )
    assert cursor == newer, "the window was consumed, so no next page was offered"

    following, _ = repository.list_monitoring_runs(
        status=None, limit=50, cursor=cursor, tenant_id=tenant_a
    )
    assert [item.monitoring_run_id for item in following] == [older]


def test_a_cursor_naming_an_invisible_contradictory_row_is_refused(
    repository: PostgresDpmMandateRepository, tenants: tuple[str, str]
) -> None:
    """The anchor resolves under the page's own visibility rule, both predicates.

    A contradictory row is invisible to every caller, but its `tenant_id`
    COLUMN still names one. That tenant could pass the row's id as a cursor and
    page from a position it cannot read, because the anchor subqueries checked
    only the column. The two adapters then disagreed about the consequence -
    PostgreSQL returned the valid runs older than the invisible row, the
    in-memory store returned nothing - which is its own signal that the rule
    was stated in two places and only one of them was complete.

    A cursor naming a row the caller cannot read is refused, exactly as it
    already is for another tenant's row. Raised in review on PR #695.
    """

    tenant_a, tenant_b = tenants
    suffix = uuid.uuid4().hex[:12]
    contradictory = f"dmr_split_{suffix}"
    older = f"dmr_older_{suffix}"

    repository.save_monitoring_run(
        _run(
            run_id=contradictory,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=contradictory,
            tenant_id=tenant_b,
            requested_at=datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc),
        )
    )
    repository.save_monitoring_run(
        _run(
            run_id=older,
            tenant_id=tenant_a,
            requested_at=datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc),
        )
    )

    # The column still names tenant A, which is what made this reachable.
    with closing(repository._connect()) as connection:  # noqa: SLF001
        row = connection.execute(
            "SELECT tenant_id FROM dpm_monitoring_runs WHERE monitoring_run_id = %s",
            (contradictory,),
        ).fetchone()
    column = row["tenant_id"] if isinstance(row, dict) else row[0]
    assert column == tenant_a, "the premise of this test is that the column still admits A"

    page, cursor = repository.list_monitoring_runs(
        status=None, limit=50, cursor=contradictory, tenant_id=tenant_a
    )

    assert page == [], (
        "a row the caller cannot read positioned its page; the anchor subquery "
        "applies the tenant predicate but not the owner agreement"
    )
    assert cursor is None
