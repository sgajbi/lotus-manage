from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.service import (
    DpmRunNotFoundError,
    DpmRunSupportService,
    DpmWorkflowDisabledError,
    DpmWorkflowTransitionError,
)
from src.core.rebalance_runs.workflow_projection import (
    build_workflow_action_response,
    build_workflow_decision_record,
    build_workflow_history_response,
    build_workflow_response,
    latest_workflow_decision,
)
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


def _simulate_result(*, pending_review: bool):
    options = EngineOptions(
        single_position_max_weight=Decimal("0.5" if pending_review else "1"),
    )
    return run_simulation(
        portfolio=portfolio_snapshot(cash_balances=[cash("USD", "10000")]),
        market_data=market_data_snapshot(prices=[price("EQ_1", "100", "USD")]),
        model=model_portfolio(targets=[target("EQ_1", "1")]),
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        request_hash="sha256:test",
        correlation_id="corr-test",
    )


def _build_service(*, workflow_enabled: bool, required_statuses: set[str] | None = None):
    return DpmRunSupportService(
        repository=InMemoryDpmRunRepository(),
        workflow_enabled=workflow_enabled,
        workflow_requires_review_for_statuses=required_statuses,
    )


def _workflow_run(*, status: str = "PENDING_REVIEW") -> DpmRunRecord:
    return DpmRunRecord(
        rebalance_run_id="rr_projection_1",
        correlation_id="corr_projection_1",
        request_hash="sha256:req-projection-1",
        idempotency_key="idem_projection_1",
        portfolio_id="pf_projection_1",
        created_at=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc),
        result_json={"status": status},
    )


def _workflow_decision(
    *,
    decision_id: str,
    action: str,
    decided_at: datetime,
) -> DpmRunWorkflowDecisionRecord:
    return DpmRunWorkflowDecisionRecord(
        decision_id=decision_id,
        run_id="rr_projection_1",
        action=action,
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_1",
        decided_at=decided_at,
        correlation_id=f"corr_{decision_id}",
    )


def test_workflow_projection_helpers_preserve_ordering_and_latest_decision():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    earlier = _workflow_decision(
        decision_id="dwd_earlier",
        action="REQUEST_CHANGES",
        decided_at=now,
    )
    later = _workflow_decision(
        decision_id="dwd_later",
        action="APPROVE",
        decided_at=now + timedelta(minutes=5),
    )

    assert latest_workflow_decision([later, earlier]) == later
    history = build_workflow_history_response(
        rebalance_run_id="rr_projection_1",
        decisions=[later, earlier],
    )

    assert [decision.decision_id for decision in history.decisions] == [
        "dwd_earlier",
        "dwd_later",
    ]


def test_workflow_projection_helpers_build_current_and_action_responses():
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = _workflow_run(status="PENDING_REVIEW")

    initial = build_workflow_response(
        run=run,
        latest_decision=None,
        workflow_enabled=True,
        requires_review_for_statuses={"PENDING_REVIEW"},
    )
    assert initial.workflow_status == "PENDING_REVIEW"
    assert initial.requires_review is True
    assert initial.latest_decision is None

    not_required = build_workflow_response(
        run=run,
        latest_decision=None,
        workflow_enabled=False,
        requires_review_for_statuses={"PENDING_REVIEW"},
    )
    assert not_required.workflow_status == "NOT_REQUIRED"
    assert not_required.requires_review is False

    decision = build_workflow_decision_record(
        rebalance_run_id=run.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_2",
        correlation_id="corr_projection_action",
        decided_at=now,
    )
    action_response = build_workflow_action_response(
        rebalance_run_id=run.rebalance_run_id,
        run_status="PENDING_REVIEW",
        workflow_status="APPROVED",
        decision=decision,
    )
    assert action_response.workflow_status == "APPROVED"
    assert action_response.requires_review is True
    assert action_response.latest_decision is not None
    assert action_response.latest_decision.action == "APPROVE"
    assert action_response.latest_decision.correlation_id == "corr_projection_action"


def test_workflow_disabled_returns_not_required_and_blocks_actions():
    service = _build_service(workflow_enabled=False, required_statuses={"PENDING_REVIEW"})
    result = _simulate_result(pending_review=True)
    assert result.status == "PENDING_REVIEW"
    service.record_run(
        result=result,
        request_hash="sha256:test",
        portfolio_id="pf_test",
        idempotency_key="idem-workflow-1",
    )

    workflow = service.get_workflow(rebalance_run_id=result.rebalance_run_id)
    assert workflow.workflow_status == "NOT_REQUIRED"
    assert workflow.requires_review is False
    assert workflow.latest_decision is None

    with pytest.raises(DpmWorkflowDisabledError, match="DPM_WORKFLOW_DISABLED"):
        service.apply_workflow_action(
            rebalance_run_id=result.rebalance_run_id,
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment="ok",
            actor_id="reviewer_1",
            correlation_id="corr-wf-1",
        )


def test_workflow_transitions_and_history_for_pending_review_run():
    service = _build_service(workflow_enabled=True, required_statuses={"PENDING_REVIEW"})
    result = _simulate_result(pending_review=True)
    assert result.status == "PENDING_REVIEW"
    service.record_run(
        result=result,
        request_hash="sha256:test",
        portfolio_id="pf_test",
        idempotency_key="idem-workflow-1",
    )

    initial = service.get_workflow(rebalance_run_id=result.rebalance_run_id)
    assert initial.workflow_status == "PENDING_REVIEW"
    assert initial.requires_review is True
    assert initial.latest_decision is None

    initial_by_correlation = service.get_workflow_by_correlation(correlation_id="corr-test")
    assert initial_by_correlation.run_id == result.rebalance_run_id
    assert initial_by_correlation.workflow_status == "PENDING_REVIEW"
    initial_by_idempotency = service.get_workflow_by_idempotency(idempotency_key="idem-workflow-1")
    assert initial_by_idempotency.run_id == result.rebalance_run_id
    assert initial_by_idempotency.workflow_status == "PENDING_REVIEW"

    request_changes = service.apply_workflow_action(
        rebalance_run_id=result.rebalance_run_id,
        action="REQUEST_CHANGES",
        reason_code="NEEDS_CLIENT_NOTE",
        comment="Please update rationale",
        actor_id="reviewer_1",
        correlation_id="corr-wf-2",
    )
    assert request_changes.workflow_status == "PENDING_REVIEW"
    assert request_changes.latest_decision is not None
    assert request_changes.latest_decision.action == "REQUEST_CHANGES"

    approved = service.apply_workflow_action(
        rebalance_run_id=result.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_2",
        correlation_id="corr-wf-3",
    )
    assert approved.workflow_status == "APPROVED"
    assert approved.latest_decision is not None
    assert approved.latest_decision.action == "APPROVE"
    assert approved.latest_decision.reason_code == "REVIEW_APPROVED"
    assert approved.latest_decision.actor_id == "reviewer_2"

    history = service.get_workflow_history(rebalance_run_id=result.rebalance_run_id)
    assert history.run_id == result.rebalance_run_id
    assert len(history.decisions) == 2
    assert history.decisions[0].action == "REQUEST_CHANGES"
    assert history.decisions[1].action == "APPROVE"

    history_by_correlation = service.get_workflow_history_by_correlation(correlation_id="corr-test")
    assert history_by_correlation.run_id == result.rebalance_run_id
    assert len(history_by_correlation.decisions) == 2
    history_by_idempotency = service.get_workflow_history_by_idempotency(
        idempotency_key="idem-workflow-1"
    )
    assert history_by_idempotency.run_id == result.rebalance_run_id
    assert len(history_by_idempotency.decisions) == 2


def test_workflow_rejects_invalid_transition_for_approved_run():
    service = _build_service(workflow_enabled=True, required_statuses={"PENDING_REVIEW"})
    result = _simulate_result(pending_review=True)
    service.record_run(
        result=result,
        request_hash="sha256:test",
        portfolio_id="pf_test",
        idempotency_key=None,
    )
    service.apply_workflow_action(
        rebalance_run_id=result.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_1",
        correlation_id="corr-wf-4",
    )

    with pytest.raises(DpmWorkflowTransitionError, match="DPM_WORKFLOW_INVALID_TRANSITION"):
        service.apply_workflow_action(
            rebalance_run_id=result.rebalance_run_id,
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_1",
            correlation_id="corr-wf-5",
        )


def test_workflow_actions_by_correlation_and_idempotency_resolve_same_run():
    service = _build_service(workflow_enabled=True, required_statuses={"PENDING_REVIEW"})
    result = _simulate_result(pending_review=True)
    service.record_run(
        result=result,
        request_hash="sha256:test",
        portfolio_id="pf_test",
        idempotency_key="idem-workflow-actions-1",
    )

    by_correlation = service.apply_workflow_action_by_correlation(
        correlation_id="corr-test",
        action="REQUEST_CHANGES",
        reason_code="MORE_DETAIL",
        comment="Please provide context",
        actor_id="reviewer_1",
        action_correlation_id="corr-action-1",
    )
    assert by_correlation.run_id == result.rebalance_run_id
    assert by_correlation.latest_decision is not None
    assert by_correlation.latest_decision.correlation_id == "corr-action-1"

    by_idempotency = service.apply_workflow_action_by_idempotency(
        idempotency_key="idem-workflow-actions-1",
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment=None,
        actor_id="reviewer_2",
        action_correlation_id="corr-action-2",
    )
    assert by_idempotency.run_id == result.rebalance_run_id
    assert by_idempotency.workflow_status == "APPROVED"
    assert by_idempotency.latest_decision is not None
    assert by_idempotency.latest_decision.correlation_id == "corr-action-2"


def test_workflow_blocks_actions_when_run_status_not_configured_for_review():
    service = _build_service(workflow_enabled=True, required_statuses={"PENDING_REVIEW"})
    result = _simulate_result(pending_review=False)
    assert result.status == "READY"
    service.record_run(
        result=result,
        request_hash="sha256:test",
        portfolio_id="pf_test",
        idempotency_key=None,
    )

    workflow = service.get_workflow(rebalance_run_id=result.rebalance_run_id)
    assert workflow.workflow_status == "NOT_REQUIRED"
    assert workflow.requires_review is False

    with pytest.raises(
        DpmWorkflowTransitionError,
        match="DPM_WORKFLOW_NOT_REQUIRED_FOR_RUN_STATUS",
    ):
        service.apply_workflow_action(
            rebalance_run_id=result.rebalance_run_id,
            action="APPROVE",
            reason_code="REVIEW_APPROVED",
            comment=None,
            actor_id="reviewer_1",
            correlation_id="corr-wf-6",
        )


def test_workflow_apis_raise_not_found_for_unknown_run():
    service = _build_service(workflow_enabled=True)

    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.get_workflow(rebalance_run_id="rr_missing")

    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.get_workflow_history(rebalance_run_id="rr_missing")

    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.get_workflow_by_correlation(correlation_id="corr-missing")

    with pytest.raises(DpmRunNotFoundError, match="DPM_RUN_NOT_FOUND"):
        service.get_workflow_history_by_correlation(correlation_id="corr-missing")

    with pytest.raises(DpmRunNotFoundError, match="DPM_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_workflow_by_idempotency(idempotency_key="idem-missing")

    with pytest.raises(DpmRunNotFoundError, match="DPM_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_workflow_history_by_idempotency(idempotency_key="idem-missing")
