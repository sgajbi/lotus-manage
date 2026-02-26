from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.core.dpm.engine import run_simulation
from src.core.dpm_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.models import EngineOptions
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository
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


def test_idempotency_history_records_multiple_events_for_same_key_when_replayed_disabled():
    service = DpmRunSupportService(repository=InMemoryDpmRunRepository())

    first = _simulate_result(
        request_hash="sha256:test-idem-history-1", correlation_id="corr-idem-1"
    )
    second = _simulate_result(
        request_hash="sha256:test-idem-history-2", correlation_id="corr-idem-2"
    )
    service.record_run(
        result=first,
        request_hash="sha256:test-idem-history-1",
        portfolio_id="pf_idem_history",
        idempotency_key="idem-history-1",
        created_at=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc),
    )
    service.record_run(
        result=second,
        request_hash="sha256:test-idem-history-2",
        portfolio_id="pf_idem_history",
        idempotency_key="idem-history-1",
        created_at=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc) + timedelta(seconds=1),
    )

    history = service.get_idempotency_history(idempotency_key="idem-history-1")
    assert history.idempotency_key == "idem-history-1"
    assert len(history.history) == 2
    assert history.history[0].rebalance_run_id == first.rebalance_run_id
    assert history.history[0].correlation_id == "corr-idem-1"
    assert history.history[0].request_hash == "sha256:test-idem-history-1"
    assert history.history[1].rebalance_run_id == second.rebalance_run_id
    assert history.history[1].correlation_id == "corr-idem-2"
    assert history.history[1].request_hash == "sha256:test-idem-history-2"


def test_idempotency_history_not_found_raises_consistent_error():
    service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    with pytest.raises(DpmRunNotFoundError, match="DPM_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_idempotency_history(idempotency_key="idem-history-missing")
