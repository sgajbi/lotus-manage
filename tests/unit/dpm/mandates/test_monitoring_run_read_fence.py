"""Monitoring-run reads answer to one tenant (issue #693).

`get_monitoring_run` and `list_monitoring_runs` took no tenant at all. Every
persisted run - the mandates it covered, the health distribution across them,
the source-readiness summary and the failure reason - was readable by anyone
who could reach the route, and the list returned every tenant's runs in one
page. The tenant was already recorded on the row and simply never consulted.

Three properties are proved here, and the third is the one a parameter-threading
fix does not give you:

  1. a run belonging to another tenant is refused,
  2. a run with NO recorded tenant is matched by nobody rather than by whoever
     asks - the same quarantine the mandate, exception and wave columns use,
  3. the CURSOR is resolved under the caller's tenant. A fenced page whose
     cursor subquery is unfenced still leaks ordering position: another
     tenant's run id resolves to a `started_at` and silently decides where the
     caller's page begins.

Each is asserted against both adapters, because they answer the question from
different stores - the column for PostgreSQL, `filters` for in-memory - and a
fence that holds in one is not evidence about the other.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from src.core.mandates import DpmMonitoringRun
from src.infrastructure.mandates.in_memory import InMemoryDpmMandateRepository

from tests.unit.dpm.supportability.test_dpm_mandate_repository import (  # noqa: E501
    _postgres_repository,
)

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"


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
    return DpmMonitoringRun(
        monitoring_run_id=run_id,
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


@pytest.fixture(name="repositories")
def _repositories(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Both adapters, seeded identically, exercised by the same assertions."""

    postgres, _ = _postgres_repository(monkeypatch)
    return [InMemoryDpmMandateRepository(), postgres]


def test_a_run_belonging_to_another_tenant_is_not_readable(repositories: list[Any]) -> None:
    for repository in repositories:
        repository.save_monitoring_run(_run(run_id="dmr_b", tenant_id=TENANT_B))

        assert repository.get_monitoring_run(monitoring_run_id="dmr_b", tenant_id=TENANT_A) is None
        owned = repository.get_monitoring_run(monitoring_run_id="dmr_b", tenant_id=TENANT_B)
        assert owned is not None, "the fence must not cost the read it exists to scope"
        assert owned.monitoring_run_id == "dmr_b"


def test_a_run_with_no_recorded_tenant_is_matched_by_nobody(repositories: list[Any]) -> None:
    """Quarantine, not 'owned by whoever asks'.

    The `tenant_id` column has been nullable since 0003 and was never
    backfilled, so runs written before the tenant was recorded carry none. A
    fence that treated a missing owner as a wildcard would hand every one of
    them to the first caller who named any tenant.
    """

    for repository in repositories:
        repository.save_monitoring_run(_run(run_id="dmr_unowned", tenant_id=None))

        for caller in (TENANT_A, TENANT_B, "default"):
            assert (
                repository.get_monitoring_run(monitoring_run_id="dmr_unowned", tenant_id=caller)
                is None
            )
        page, _ = repository.list_monitoring_runs(
            status=None, limit=10, cursor=None, tenant_id=TENANT_A
        )
        assert page == []


def test_a_list_returns_only_the_callers_runs(repositories: list[Any]) -> None:
    for repository in repositories:
        repository.save_monitoring_run(_run(run_id="dmr_a", tenant_id=TENANT_A))
        repository.save_monitoring_run(
            _run(
                run_id="dmr_b",
                tenant_id=TENANT_B,
                requested_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
            )
        )

        page_a, _ = repository.list_monitoring_runs(
            status=None, limit=10, cursor=None, tenant_id=TENANT_A
        )
        page_b, _ = repository.list_monitoring_runs(
            status=None, limit=10, cursor=None, tenant_id=TENANT_B
        )

        assert [run.monitoring_run_id for run in page_a] == ["dmr_a"]
        assert [run.monitoring_run_id for run in page_b] == ["dmr_b"]


def test_a_cursor_naming_another_tenants_run_does_not_position_the_page(
    repositories: list[Any],
) -> None:
    """The subquery fence, asserted where its absence is observable.

    Tenant A holds two runs. Tenant B holds one, timed between them. If the
    cursor row is resolved WITHOUT the tenant predicate, B's run id resolves to
    its `started_at` and A's page silently continues from a position B chose -
    which is both a leak of B's ordering and a page A never asked for.
    """

    for repository in repositories:
        repository.save_monitoring_run(
            _run(
                run_id="dmr_a_late",
                tenant_id=TENANT_A,
                requested_at=datetime(2026, 5, 3, 12, 0, tzinfo=timezone.utc),
            )
        )
        repository.save_monitoring_run(
            _run(
                run_id="dmr_b_mid",
                tenant_id=TENANT_B,
                requested_at=datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc),
            )
        )
        repository.save_monitoring_run(
            _run(
                run_id="dmr_a_early",
                tenant_id=TENANT_A,
                requested_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            )
        )

        page, cursor = repository.list_monitoring_runs(
            status=None, limit=10, cursor="dmr_b_mid", tenant_id=TENANT_A
        )

        assert page == [], (
            "tenant B's run id resolved to an ordering position for tenant A: "
            "the cursor subquery is not fenced"
        )
        assert cursor is None

        # The caller's own cursor still pages, so the refusal above is the
        # tenant predicate and not a cursor that stopped working.
        first, own_cursor = repository.list_monitoring_runs(
            status=None, limit=1, cursor=None, tenant_id=TENANT_A
        )
        assert [run.monitoring_run_id for run in first] == ["dmr_a_late"]
        following, _ = repository.list_monitoring_runs(
            status=None, limit=10, cursor=own_cursor, tenant_id=TENANT_A
        )
        assert [run.monitoring_run_id for run in following] == ["dmr_a_early"]


def test_a_row_whose_column_and_payload_disagree_is_served_to_nobody(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fence reads the column; the caller receives the payload.

    `ON CONFLICT (monitoring_run_id) DO UPDATE` refreshes `payload_json` and
    `filters_json` and deliberately never `tenant_id`, so a later save carrying
    a different tenant rewrites the body while the column keeps naming the
    original owner. Fencing on the column alone then admits tenant A and hands
    back a run whose own body says tenant B.

    Neither value is trusted over the other: a row that contradicts itself is
    returned to no caller.
    """

    repository, store = _postgres_repository(monkeypatch)
    repository.save_monitoring_run(_run(run_id="dmr_split", tenant_id=TENANT_A))

    # The body now claims tenant B while the column still says tenant A -
    # reachable through the conflict clause, reproduced here directly.
    stored = store.monitoring_runs["dmr_split"]
    stored["payload_json"] = _run(run_id="dmr_split", tenant_id=TENANT_B).model_dump_json()

    assert repository.get_monitoring_run(monitoring_run_id="dmr_split", tenant_id=TENANT_A) is None
    assert repository.get_monitoring_run(monitoring_run_id="dmr_split", tenant_id=TENANT_B) is None
    page, _ = repository.list_monitoring_runs(
        status=None, limit=10, cursor=None, tenant_id=TENANT_A
    )
    assert page == []
