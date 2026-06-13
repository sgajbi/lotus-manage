from decimal import Decimal
from datetime import datetime, timezone

from src.core.rebalance.engine import run_simulation
import src.core.rebalance_runs.service as run_service_module
from src.core.rebalance_runs.models import DpmLineageEdgeRecord
from src.core.rebalance_runs.serializers import lineage_cursor
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.models import EngineOptions
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _edge(
    *,
    source: str,
    edge_type: str,
    target: str,
    created_at: datetime,
) -> DpmLineageEdgeRecord:
    return DpmLineageEdgeRecord(
        source_entity_id=source,
        edge_type=edge_type,
        target_entity_id=target,
        created_at=created_at,
        metadata_json={"source": source},
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


def test_lineage_helpers_sort_and_filter_edges():
    early = datetime(2026, 5, 1, 9, tzinfo=timezone.utc)
    middle = datetime(2026, 5, 1, 10, tzinfo=timezone.utc)
    late = datetime(2026, 5, 1, 11, tzinfo=timezone.utc)
    edges = [
        _edge(
            source="idem-1",
            edge_type="IDEMPOTENCY_TO_RUN",
            target="rr-2",
            created_at=late,
        ),
        _edge(
            source="corr-1",
            edge_type="CORRELATION_TO_RUN",
            target="rr-1",
            created_at=early,
        ),
        _edge(
            source="op-1",
            edge_type="OPERATION_TO_CORRELATION",
            target="corr-1",
            created_at=middle,
        ),
    ]

    sorted_edges = run_service_module._sort_lineage_edges(edges)  # noqa: SLF001
    filtered = run_service_module._filter_lineage_edges(  # noqa: SLF001
        edges=sorted_edges,
        edge_type="OPERATION_TO_CORRELATION",
        created_from=middle,
        created_to=late,
    )

    assert [edge.source_entity_id for edge in sorted_edges] == ["corr-1", "op-1", "idem-1"]
    assert filtered == [sorted_edges[1]]


def test_lineage_paging_uses_cursor_after_matching_edge():
    edges = [
        _edge(
            source="corr-1",
            edge_type="CORRELATION_TO_RUN",
            target="rr-1",
            created_at=datetime(2026, 5, 1, 9, tzinfo=timezone.utc),
        ),
        _edge(
            source="corr-2",
            edge_type="CORRELATION_TO_RUN",
            target="rr-2",
            created_at=datetime(2026, 5, 1, 10, tzinfo=timezone.utc),
        ),
        _edge(
            source="corr-3",
            edge_type="CORRELATION_TO_RUN",
            target="rr-3",
            created_at=datetime(2026, 5, 1, 11, tzinfo=timezone.utc),
        ),
    ]

    page, next_cursor = run_service_module._page_lineage_edges(  # noqa: SLF001
        edges=edges,
        cursor=lineage_cursor(edges[0]),
        limit=1,
    )
    missing_page, missing_cursor = run_service_module._page_lineage_edges(  # noqa: SLF001
        edges=edges,
        cursor="missing-cursor",
        limit=1,
    )

    assert page == [edges[1]]
    assert next_cursor == lineage_cursor(edges[1])
    assert missing_page == []
    assert missing_cursor is None
