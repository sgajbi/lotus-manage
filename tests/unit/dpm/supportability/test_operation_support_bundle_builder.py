"""Fail-closed selection of authoritative async scenario evidence."""

from datetime import datetime, timezone

import pytest

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunRecord,
)
from src.core.rebalance_runs.operation_support_bundle import (
    OperationEvidenceInvalidError,
    OperationSupportBundleBuilder,
)
from src.infrastructure.rebalance_runs.in_memory import InMemoryDpmRunRepository


NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _operation(
    *,
    request_json: dict | None = None,
    result_json: dict | None = None,
) -> DpmAsyncOperationRecord:
    return DpmAsyncOperationRecord(
        tenant_id="tenant-bundle",
        operation_id="dop_bundle",
        operation_type="ANALYZE_SCENARIOS",
        status="SUCCEEDED",
        correlation_id="shared-correlation",
        created_at=NOW,
        execution_attempt=1,
        request_json=request_json or {"scenarios": {"baseline": {"options": {}}}},
        result_json=result_json
        or {
            "results": {"baseline": {"rebalance_run_id": "rr_expected"}},
            "failed_scenarios": {},
        },
    )


def _builder(operation: DpmAsyncOperationRecord, repository=None) -> OperationSupportBundleBuilder:
    return OperationSupportBundleBuilder(
        repository=repository or InMemoryDpmRunRepository(),
        operation=operation,
        bundle_for_run=lambda run_id: pytest.fail(f"unexpected authoritative run: {run_id}"),
        include_async_operation=False,
    )


@pytest.mark.parametrize(
    ("request_json", "result_json"),
    [
        ({"scenarios": []}, None),
        ({"scenarios": {1: {"options": {}}}}, None),
        (None, {"results": [], "failed_scenarios": {}}),
        (None, {"results": {"unrequested": {"rebalance_run_id": "rr_unknown"}}}),
    ],
)
def test_malformed_operation_evidence_fails_closed(request_json, result_json):
    operation = _operation(request_json=request_json, result_json=result_json)
    with pytest.raises(OperationEvidenceInvalidError, match="DPM_ASYNC_OPERATION_EVIDENCE_INVALID"):
        _builder(operation).build()


def test_correlation_text_and_wrong_attempt_do_not_select_a_run():
    repository = InMemoryDpmRunRepository()
    run = DpmRunRecord(
        tenant_id="tenant-bundle",
        rebalance_run_id="rr_expected",
        correlation_id="shared-correlation:baseline",
        request_hash="batch:baseline",
        portfolio_id="pf-bundle",
        created_at=NOW,
        result_json={"status": "READY"},
    )
    repository.save_run(run)
    assert _builder(_operation(), repository).build().scenarios["baseline"].status == "missing"
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            tenant_id="tenant-bundle",
            source_entity_id="dop_bundle",
            edge_type="OPERATION_TO_RUN",
            target_entity_id="rr_expected",
            created_at=NOW,
            metadata_json={"scenario_key": "baseline", "execution_attempt": 2},
        )
    )
    evidence = _builder(_operation(), repository).build()
    assert evidence.scenarios["baseline"].status == "missing"
    assert evidence.historical_runs == []


def test_missing_and_invalid_historical_edges_never_invent_a_bundle():
    repository = InMemoryDpmRunRepository()
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            tenant_id="tenant-bundle",
            source_entity_id="dop_bundle",
            edge_type="OPERATION_TO_RUN",
            target_entity_id="rr_missing",
            created_at=NOW,
            metadata_json={"scenario_key": "baseline", "execution_attempt": 1},
        )
    )
    repository.save_run(
        DpmRunRecord(
            tenant_id="tenant-bundle",
            rebalance_run_id="rr_unrequested",
            correlation_id="shared-correlation:other",
            request_hash="batch:other",
            portfolio_id="pf-bundle",
            created_at=NOW,
            result_json={"status": "READY"},
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            tenant_id="tenant-bundle",
            source_entity_id="dop_bundle",
            edge_type="OPERATION_TO_RUN",
            target_entity_id="rr_unrequested",
            created_at=NOW,
            metadata_json={"scenario_key": "other", "execution_attempt": 1},
        )
    )
    evidence = _builder(_operation(), repository).build()
    assert evidence.scenarios["baseline"].status == "missing"
    assert evidence.historical_runs == []


def test_duplicate_terminal_run_id_is_not_selected_for_either_scenario():
    operation = _operation(
        request_json={"scenarios": {"baseline": {}, "alternative": {}}},
        result_json={
            "results": {
                "baseline": {"rebalance_run_id": "rr_shared"},
                "alternative": {"rebalance_run_id": "rr_shared"},
            },
            "failed_scenarios": {},
        },
    )
    outcomes = _builder(operation).build().scenarios
    assert {key: value.status for key, value in outcomes.items()} == {
        "baseline": "missing",
        "alternative": "missing",
    }
