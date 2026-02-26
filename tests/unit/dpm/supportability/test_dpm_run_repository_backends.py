from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.infrastructure.dpm_runs import InMemoryDpmRunRepository, SqliteDpmRunRepository


@pytest.fixture(params=["IN_MEMORY", "SQLITE"])
def repository(request):
    if request.param == "IN_MEMORY":
        yield InMemoryDpmRunRepository()
        return
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "supportability.sqlite")
        yield SqliteDpmRunRepository(database_path=sqlite_path)


def test_repository_run_and_idempotency_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = DpmRunRecord(
        rebalance_run_id="rr_repo_1",
        correlation_id="corr_repo_1",
        request_hash="sha256:req1",
        idempotency_key="idem_repo_1",
        portfolio_id="pf_repo_1",
        created_at=now,
        result_json={"rebalance_run_id": "rr_repo_1", "status": "READY"},
    )
    repository.save_run(run)

    stored_run = repository.get_run(rebalance_run_id="rr_repo_1")
    assert stored_run is not None
    assert stored_run.rebalance_run_id == "rr_repo_1"
    assert stored_run.correlation_id == "corr_repo_1"
    assert stored_run.result_json["status"] == "READY"

    by_correlation = repository.get_run_by_correlation(correlation_id="corr_repo_1")
    assert by_correlation is not None
    assert by_correlation.rebalance_run_id == "rr_repo_1"
    by_request_hash = repository.get_run_by_request_hash(request_hash="sha256:req1")
    assert by_request_hash is not None
    assert by_request_hash.rebalance_run_id == "rr_repo_1"

    record = DpmRunIdempotencyRecord(
        idempotency_key="idem_repo_1",
        request_hash="sha256:req1",
        rebalance_run_id="rr_repo_1",
        created_at=now,
    )
    repository.save_idempotency_mapping(record)
    stored_idem = repository.get_idempotency_mapping(idempotency_key="idem_repo_1")
    assert stored_idem is not None
    assert stored_idem.rebalance_run_id == "rr_repo_1"


def test_repository_list_runs_filter_and_cursor_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_list_1",
            correlation_id="corr_repo_list_1",
            request_hash="sha256:req-list-1",
            idempotency_key="idem_repo_list_1",
            portfolio_id="pf_repo_list_1",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_list_1", "status": "READY"},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_list_2",
            correlation_id="corr_repo_list_2",
            request_hash="sha256:req-list-2",
            idempotency_key=None,
            portfolio_id="pf_repo_list_2",
            created_at=now + timedelta(minutes=1),
            result_json={"rebalance_run_id": "rr_repo_list_2", "status": "BLOCKED"},
        )
    )

    ready_rows, ready_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status="READY",
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in ready_rows] == ["rr_repo_list_1"]
    assert ready_cursor is None

    page_one, cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in page_one] == ["rr_repo_list_2"]
    assert cursor == "rr_repo_list_2"

    page_two, cursor_two = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=1,
        cursor=cursor,
    )
    assert [row.rebalance_run_id for row in page_two] == ["rr_repo_list_1"]
    assert cursor_two is None


def test_repository_list_runs_time_window_and_invalid_cursor_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_time_1",
            correlation_id="corr_repo_time_1",
            request_hash="sha256:req-time-1",
            idempotency_key=None,
            portfolio_id="pf_repo_time",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_time_1", "status": "READY"},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_time_2",
            correlation_id="corr_repo_time_2",
            request_hash="sha256:req-time-2",
            idempotency_key=None,
            portfolio_id="pf_repo_time",
            created_at=now + timedelta(minutes=2),
            result_json={"rebalance_run_id": "rr_repo_time_2", "status": "READY"},
        )
    )

    from_window_rows, from_window_cursor = repository.list_runs(
        created_from=now + timedelta(minutes=1),
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in from_window_rows] == ["rr_repo_time_2"]
    assert from_window_cursor is None

    to_window_rows, to_window_cursor = repository.list_runs(
        created_from=None,
        created_to=now + timedelta(minutes=1),
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in to_window_rows] == ["rr_repo_time_1"]
    assert to_window_cursor is None

    invalid_cursor_rows, invalid_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash=None,
        portfolio_id=None,
        limit=10,
        cursor="rr_missing_cursor",
    )
    assert invalid_cursor_rows == []
    assert invalid_cursor is None


def test_repository_async_operations_and_ttl_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operation = DpmAsyncOperationRecord(
        operation_id="dop_repo_1",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr_op_1",
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    repository.create_operation(operation)
    stored = repository.get_operation(operation_id="dop_repo_1")
    assert stored is not None
    assert stored.status == "PENDING"

    operation.status = "SUCCEEDED"
    operation.started_at = now + timedelta(seconds=1)
    operation.finished_at = now + timedelta(seconds=2)
    operation.result_json = {"ok": True}
    operation.request_json = None
    repository.update_operation(operation)

    updated = repository.get_operation_by_correlation(correlation_id="corr_op_1")
    assert updated is not None
    assert updated.status == "SUCCEEDED"
    assert updated.result_json == {"ok": True}
    assert updated.request_json is None

    removed = repository.purge_expired_operations(
        ttl_seconds=1,
        now=now + timedelta(seconds=10),
    )
    assert removed == 1
    assert repository.get_operation(operation_id="dop_repo_1") is None


def test_repository_list_runs_request_hash_filter_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_hash_1",
            correlation_id="corr_repo_hash_1",
            request_hash="sha256:req-hash-1",
            idempotency_key=None,
            portfolio_id="pf_repo_hash",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_hash_1", "status": "READY"},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_hash_2",
            correlation_id="corr_repo_hash_2",
            request_hash="sha256:req-hash-2",
            idempotency_key=None,
            portfolio_id="pf_repo_hash",
            created_at=now + timedelta(minutes=1),
            result_json={"rebalance_run_id": "rr_repo_hash_2", "status": "READY"},
        )
    )

    matching_rows, matching_cursor = repository.list_runs(
        created_from=None,
        created_to=None,
        status=None,
        request_hash="sha256:req-hash-1",
        portfolio_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.rebalance_run_id for row in matching_rows] == ["rr_repo_hash_1"]
    assert matching_cursor is None


def test_repository_list_operations_filter_and_cursor_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_list_1",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_repo_list_1",
            created_at=now,
            started_at=now + timedelta(seconds=1),
            finished_at=now + timedelta(seconds=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_list_2",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id="corr_repo_list_2",
            created_at=now + timedelta(minutes=1),
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )

    pending, pending_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status="PENDING",
        correlation_id=None,
        limit=10,
        cursor=None,
    )
    assert [operation.operation_id for operation in pending] == ["dop_repo_list_2"]
    assert pending_cursor is None

    page_one, cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=None,
    )
    assert [operation.operation_id for operation in page_one] == ["dop_repo_list_2"]
    assert cursor == "dop_repo_list_2"

    page_two, cursor_two = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=cursor,
    )
    assert [operation.operation_id for operation in page_two] == ["dop_repo_list_1"]
    assert cursor_two is None


def test_repository_list_operations_time_window_and_invalid_cursor_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_time_1",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id="corr_repo_time_op_1",
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_time_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_repo_time_op_2",
            created_at=now + timedelta(minutes=2),
            started_at=now + timedelta(minutes=2, seconds=1),
            finished_at=now + timedelta(minutes=2, seconds=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )

    from_window_rows, from_window_cursor = repository.list_operations(
        created_from=now + timedelta(minutes=1),
        created_to=None,
        operation_type=None,
        status=None,
        correlation_id=None,
        limit=10,
        cursor=None,
    )
    assert [operation.operation_id for operation in from_window_rows] == ["dop_repo_time_2"]
    assert from_window_cursor is None

    to_window_rows, to_window_cursor = repository.list_operations(
        created_from=None,
        created_to=now + timedelta(minutes=1),
        operation_type=None,
        status=None,
        correlation_id=None,
        limit=10,
        cursor=None,
    )
    assert [operation.operation_id for operation in to_window_rows] == ["dop_repo_time_1"]
    assert to_window_cursor is None

    invalid_cursor_rows, invalid_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status=None,
        correlation_id=None,
        limit=10,
        cursor="dop_missing_cursor",
    )
    assert invalid_cursor_rows == []
    assert invalid_cursor is None


def test_repository_supportability_summary_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    empty_summary = repository.get_supportability_summary()
    assert empty_summary.run_count == 0
    assert empty_summary.operation_count == 0
    assert empty_summary.operation_status_counts == {}
    assert empty_summary.run_status_counts == {}
    assert empty_summary.workflow_decision_count == 0
    assert empty_summary.workflow_action_counts == {}
    assert empty_summary.workflow_reason_code_counts == {}
    assert empty_summary.lineage_edge_count == 0
    assert empty_summary.oldest_run_created_at is None
    assert empty_summary.newest_run_created_at is None
    assert empty_summary.oldest_operation_created_at is None
    assert empty_summary.newest_operation_created_at is None

    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_summary_1",
            correlation_id="corr_repo_summary_1",
            request_hash="sha256:req-summary-1",
            idempotency_key="idem_repo_summary_1",
            portfolio_id="pf_repo_summary_1",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_summary_1", "status": "READY"},
        )
    )
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_summary_2",
            correlation_id="corr_repo_summary_2",
            request_hash="sha256:req-summary-2",
            idempotency_key=None,
            portfolio_id="pf_repo_summary_2",
            created_at=now + timedelta(minutes=1),
            result_json={"rebalance_run_id": "rr_repo_summary_2", "status": "BLOCKED"},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_summary_1",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id="corr_repo_summary_op_1",
            created_at=now + timedelta(seconds=1),
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_repo_summary_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_repo_summary_op_2",
            created_at=now + timedelta(minutes=2),
            started_at=now + timedelta(minutes=2, seconds=1),
            finished_at=now + timedelta(minutes=2, seconds=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id="dwd_repo_summary_1",
            run_id="rr_repo_summary_1",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="ops_summary_1",
            decided_at=now + timedelta(minutes=3),
            correlation_id="corr_repo_summary_wf_1",
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id="corr_repo_summary_1",
            edge_type="CORRELATION_TO_RUN",
            target_entity_id="rr_repo_summary_1",
            created_at=now + timedelta(minutes=4),
            metadata_json={"request_hash": "sha256:req-summary-1"},
        )
    )

    summary = repository.get_supportability_summary()
    assert summary.run_count == 2
    assert summary.operation_count == 2
    assert summary.operation_status_counts == {"PENDING": 1, "SUCCEEDED": 1}
    assert summary.run_status_counts == {"READY": 1, "BLOCKED": 1}
    assert summary.workflow_decision_count == 1
    assert summary.workflow_action_counts == {"APPROVE": 1}
    assert summary.workflow_reason_code_counts == {"REVIEW_APPROVED": 1}
    assert summary.lineage_edge_count == 1
    assert summary.oldest_run_created_at == now
    assert summary.newest_run_created_at == now + timedelta(minutes=1)
    assert summary.oldest_operation_created_at == now + timedelta(seconds=1)
    assert summary.newest_operation_created_at == now + timedelta(minutes=2)


def test_repository_workflow_decision_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    decision_one = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_repo_1",
        run_id="rr_repo_1",
        action="REQUEST_CHANGES",
        reason_code="NEEDS_DETAIL",
        comment="Add details",
        actor_id="ops_1",
        decided_at=now,
        correlation_id="corr_wf_1",
    )
    decision_two = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_repo_2",
        run_id="rr_repo_1",
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="ops_2",
        decided_at=now + timedelta(seconds=1),
        correlation_id="corr_wf_2",
    )
    repository.append_workflow_decision(decision_one)
    repository.append_workflow_decision(decision_two)

    decisions = repository.list_workflow_decisions(rebalance_run_id="rr_repo_1")
    assert [decision.decision_id for decision in decisions] == ["dwd_repo_1", "dwd_repo_2"]
    assert decisions[0].action == "REQUEST_CHANGES"
    assert decisions[1].action == "APPROVE"


def test_repository_list_workflow_decisions_filtered_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id="dwd_repo_filter_1",
            run_id="rr_repo_filter_1",
            action="REQUEST_CHANGES",
            reason_code="NEEDS_DETAIL",
            comment="Needs more context",
            actor_id="ops_filter_1",
            decided_at=now,
            correlation_id="corr_repo_filter_1",
        )
    )
    repository.append_workflow_decision(
        DpmRunWorkflowDecisionRecord(
            decision_id="dwd_repo_filter_2",
            run_id="rr_repo_filter_2",
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="ops_filter_2",
            decided_at=now + timedelta(seconds=1),
            correlation_id="corr_repo_filter_2",
        )
    )

    by_actor, actor_cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id="ops_filter_2",
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=10,
        cursor=None,
    )
    assert [decision.decision_id for decision in by_actor] == ["dwd_repo_filter_2"]
    assert actor_cursor is None

    page_one, cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=1,
        cursor=None,
    )
    assert [decision.decision_id for decision in page_one] == ["dwd_repo_filter_2"]
    assert cursor == "dwd_repo_filter_2"

    page_two, cursor_two = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=1,
        cursor=cursor,
    )
    assert [decision.decision_id for decision in page_two] == ["dwd_repo_filter_1"]
    assert cursor_two is None

    invalid_cursor_rows, invalid_cursor = repository.list_workflow_decisions_filtered(
        rebalance_run_id=None,
        action=None,
        actor_id=None,
        reason_code=None,
        decided_from=None,
        decided_to=None,
        limit=10,
        cursor="dwd_missing_cursor",
    )
    assert invalid_cursor_rows == []
    assert invalid_cursor is None


def test_repository_lineage_edge_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    edge = DpmLineageEdgeRecord(
        source_entity_id="corr_repo_1",
        edge_type="CORRELATION_TO_RUN",
        target_entity_id="rr_repo_1",
        created_at=now,
        metadata_json={"request_hash": "sha256:req1"},
    )
    repository.append_lineage_edge(edge)

    by_source = repository.list_lineage_edges(entity_id="corr_repo_1")
    assert len(by_source) == 1
    assert by_source[0].edge_type == "CORRELATION_TO_RUN"
    assert by_source[0].target_entity_id == "rr_repo_1"

    by_target = repository.list_lineage_edges(entity_id="rr_repo_1")
    assert len(by_target) == 1
    assert by_target[0].source_entity_id == "corr_repo_1"


def test_repository_idempotency_history_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    one = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_repo_history_1",
        rebalance_run_id="rr_repo_1",
        correlation_id="corr_repo_1",
        request_hash="sha256:req1",
        created_at=now,
    )
    two = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_repo_history_1",
        rebalance_run_id="rr_repo_2",
        correlation_id="corr_repo_2",
        request_hash="sha256:req2",
        created_at=now + timedelta(seconds=1),
    )
    repository.append_idempotency_history(one)
    repository.append_idempotency_history(two)

    history = repository.list_idempotency_history(idempotency_key="idem_repo_history_1")
    assert [entry.rebalance_run_id for entry in history] == ["rr_repo_1", "rr_repo_2"]
    assert [entry.correlation_id for entry in history] == ["corr_repo_1", "corr_repo_2"]
    assert [entry.request_hash for entry in history] == ["sha256:req1", "sha256:req2"]


def test_repository_run_retention_purge_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    old_time = now - timedelta(days=5)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_retention_old",
            correlation_id="corr_repo_retention_old",
            request_hash="sha256:req-old",
            idempotency_key="idem_repo_retention_old",
            portfolio_id="pf_repo_retention",
            created_at=old_time,
            result_json={"rebalance_run_id": "rr_repo_retention_old", "status": "READY"},
        )
    )
    repository.save_idempotency_mapping(
        DpmRunIdempotencyRecord(
            idempotency_key="idem_repo_retention_old",
            request_hash="sha256:req-old",
            rebalance_run_id="rr_repo_retention_old",
            created_at=old_time,
        )
    )
    repository.append_idempotency_history(
        DpmRunIdempotencyHistoryRecord(
            idempotency_key="idem_repo_retention_old",
            rebalance_run_id="rr_repo_retention_old",
            correlation_id="corr_repo_retention_old",
            request_hash="sha256:req-old",
            created_at=old_time,
        )
    )
    repository.append_lineage_edge(
        DpmLineageEdgeRecord(
            source_entity_id="idem_repo_retention_old",
            edge_type="IDEMPOTENCY_TO_RUN",
            target_entity_id="rr_repo_retention_old",
            created_at=old_time,
            metadata_json={},
        )
    )

    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_retention_new",
            correlation_id="corr_repo_retention_new",
            request_hash="sha256:req-new",
            idempotency_key="idem_repo_retention_new",
            portfolio_id="pf_repo_retention",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_retention_new", "status": "READY"},
        )
    )
    removed = repository.purge_expired_runs(retention_days=2, now=now)
    assert removed == 1

    assert repository.get_run(rebalance_run_id="rr_repo_retention_old") is None
    assert repository.get_idempotency_mapping(idempotency_key="idem_repo_retention_old") is None
    assert repository.list_idempotency_history(idempotency_key="idem_repo_retention_old") == []
    assert repository.list_lineage_edges(entity_id="rr_repo_retention_old") == []
    assert repository.get_run(rebalance_run_id="rr_repo_retention_new") is not None


def test_repository_run_retention_disabled_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    removed = repository.purge_expired_runs(retention_days=0, now=now)
    assert removed == 0


def test_repository_run_artifact_persistence_contract(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_artifact_1",
            correlation_id="corr_repo_artifact_1",
            request_hash="sha256:req-artifact-1",
            idempotency_key="idem_repo_artifact_1",
            portfolio_id="pf_repo_artifact_1",
            created_at=now,
            result_json={"rebalance_run_id": "rr_repo_artifact_1", "status": "READY"},
        )
    )
    artifact_json = {
        "artifact_id": "dra_repo_artifact_1",
        "rebalance_run_id": "rr_repo_artifact_1",
        "evidence": {"hashes": {"artifact_hash": "sha256:artifact-1"}},
    }
    repository.save_run_artifact(
        rebalance_run_id="rr_repo_artifact_1",
        artifact_json=artifact_json,
    )

    stored = repository.get_run_artifact(rebalance_run_id="rr_repo_artifact_1")
    assert stored == artifact_json
    assert repository.get_run_artifact(rebalance_run_id="rr_repo_artifact_missing") is None


def test_repository_run_retention_also_purges_artifacts(repository):
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    old_time = now - timedelta(days=5)
    repository.save_run(
        DpmRunRecord(
            rebalance_run_id="rr_repo_retention_artifact_old",
            correlation_id="corr_repo_retention_artifact_old",
            request_hash="sha256:req-old-artifact",
            idempotency_key=None,
            portfolio_id="pf_repo_retention",
            created_at=old_time,
            result_json={
                "rebalance_run_id": "rr_repo_retention_artifact_old",
                "status": "READY",
            },
        )
    )
    repository.save_run_artifact(
        rebalance_run_id="rr_repo_retention_artifact_old",
        artifact_json={"artifact_id": "dra_repo_retention_artifact_old"},
    )

    removed = repository.purge_expired_runs(retention_days=2, now=now)
    assert removed == 1
    assert repository.get_run_artifact(rebalance_run_id="rr_repo_retention_artifact_old") is None


def test_sqlite_repository_purge_expired_runs_noop_when_empty():
    with TemporaryDirectory() as tmp_dir:
        sqlite_path = str(Path(tmp_dir) / "supportability-empty.sqlite")
        repository = SqliteDpmRunRepository(database_path=sqlite_path)
        purged = repository.purge_expired_runs(
            retention_days=1,
            now=datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc),
        )
        assert purged == 0
