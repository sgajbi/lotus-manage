from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.core.dpm.engine import run_simulation
from src.core.dpm_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.models import EngineOptions
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository, SqliteDpmRunRepository
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _simulate_result(*, request_hash: str, correlation_id: str):
    options = EngineOptions(single_position_max_weight=Decimal("0.5"))
    return run_simulation(
        portfolio=portfolio_snapshot(cash_balances=[cash("USD", "10000")]),
        market_data=market_data_snapshot(prices=[price("EQ_1", "100", "USD")]),
        model=model_portfolio(targets=[target("EQ_1", "1")]),
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        request_hash=request_hash,
        correlation_id=correlation_id,
    )


@pytest.fixture(params=["IN_MEMORY", "SQLITE"])
def repository(request):
    if request.param == "IN_MEMORY":
        yield InMemoryDpmRunRepository()
        return
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "supportability.sqlite")
        yield SqliteDpmRunRepository(database_path=sqlite_path)


def test_supportability_retention_purges_expired_run_records(repository):
    service = DpmRunSupportService(
        repository=repository,
        supportability_retention_days=1,
    )
    now = datetime.now(timezone.utc)
    old_result = _simulate_result(
        request_hash="sha256:retention-old",
        correlation_id="corr-retention-old",
    )
    new_result = _simulate_result(
        request_hash="sha256:retention-new",
        correlation_id="corr-retention-new",
    )

    service.record_run(
        result=old_result,
        request_hash="sha256:retention-old",
        portfolio_id="pf_retention",
        idempotency_key="idem-retention-old",
        created_at=now - timedelta(days=2),
    )
    service.record_run(
        result=new_result,
        request_hash="sha256:retention-new",
        portfolio_id="pf_retention",
        idempotency_key="idem-retention-new",
        created_at=now,
    )

    listed = service.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id="pf_retention",
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in listed.items] == [new_result.rebalance_run_id]

    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.get_run(rebalance_run_id=old_result.rebalance_run_id)

    with pytest.raises(DpmRunNotFoundError, match="DPM_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_idempotency_lookup(idempotency_key="idem-retention-old")

    with pytest.raises(DpmRunNotFoundError, match="DPM_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_idempotency_history(idempotency_key="idem-retention-old")
