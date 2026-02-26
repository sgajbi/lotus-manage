from decimal import Decimal

from src.core.dpm.engine import run_simulation
from src.core.dpm_runs.service import DpmRunSupportService
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


def _simulate_result():
    options = EngineOptions(single_position_max_weight=Decimal("0.5"))
    return run_simulation(
        portfolio=portfolio_snapshot(cash_balances=[cash("USD", "10000")]),
        market_data=market_data_snapshot(prices=[price("EQ_1", "100", "USD")]),
        model=model_portfolio(targets=[target("EQ_1", "1")]),
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        request_hash="sha256:test-lineage",
        correlation_id="corr-lineage-1",
    )


def test_lineage_edges_are_recorded_for_run_idempotency_and_operation():
    service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    result = _simulate_result()
    service.record_run(
        result=result,
        request_hash="sha256:test-lineage",
        portfolio_id="pf_lineage",
        idempotency_key="idem-lineage-1",
    )
    accepted = service.submit_analyze_async(
        correlation_id="corr-op-lineage-1",
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )

    by_correlation = service.get_lineage(entity_id="corr-lineage-1")
    assert len(by_correlation.edges) == 1
    assert by_correlation.edges[0].edge_type == "CORRELATION_TO_RUN"
    assert by_correlation.edges[0].target_entity_id == result.rebalance_run_id

    by_idempotency = service.get_lineage(entity_id="idem-lineage-1")
    assert len(by_idempotency.edges) == 1
    assert by_idempotency.edges[0].edge_type == "IDEMPOTENCY_TO_RUN"
    assert by_idempotency.edges[0].target_entity_id == result.rebalance_run_id

    by_operation = service.get_lineage(entity_id=accepted.operation_id)
    assert len(by_operation.edges) == 1
    assert by_operation.edges[0].edge_type == "OPERATION_TO_CORRELATION"
    assert by_operation.edges[0].target_entity_id == "corr-op-lineage-1"
