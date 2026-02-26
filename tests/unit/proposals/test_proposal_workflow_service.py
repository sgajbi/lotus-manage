import pytest
from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalIdempotencyRecord,
    ProposalCreateRequest,
    ProposalRecord,
    ProposalStateTransitionRequest,
    ProposalVersionRequest,
)
from src.core.proposals.service import (
    ProposalLifecycleError,
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
    ProposalWorkflowService,
)
from src.infrastructure.proposals import InMemoryProposalRepository


def _service(
    *,
    require_expected_state: bool = True,
    allow_portfolio_id_change_on_new_version: bool = False,
    require_proposal_simulation_flag: bool = True,
) -> ProposalWorkflowService:
    return ProposalWorkflowService(
        repository=InMemoryProposalRepository(),
        require_expected_state=require_expected_state,
        allow_portfolio_id_change_on_new_version=allow_portfolio_id_change_on_new_version,
        require_proposal_simulation_flag=require_proposal_simulation_flag,
    )


def _create_payload() -> ProposalCreateRequest:
    return ProposalCreateRequest.model_validate(
        {
            "created_by": "advisor_1",
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_1",
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "1000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            },
            "metadata": {"title": "Risk flow test"},
        }
    )


def _version_payload(*, portfolio_id: str = "pf_1", enable_simulation: bool = True) -> ProposalVersionRequest:
    return ProposalVersionRequest.model_validate(
        {
            "created_by": "advisor_1",
            "simulate_request": {
                "portfolio_snapshot": {
                    "portfolio_id": portfolio_id,
                    "base_currency": "USD",
                    "positions": [],
                    "cash_balances": [{"currency": "USD", "amount": "1000"}],
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": enable_simulation},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            },
        }
    )


def _create_draft(service: ProposalWorkflowService) -> str:
    created = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-create-1",
        correlation_id="corr-create-1",
    )
    return created.proposal.proposal_id


def _submit_for_risk_review(service: ProposalWorkflowService, proposal_id: str) -> None:
    service.transition_state(
        proposal_id=proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="SUBMITTED_FOR_RISK_REVIEW",
            actor_id="advisor_1",
            expected_state="DRAFT",
            reason={"ticket": "risk-123"},
        ),
    )


def test_risk_approval_transition_updates_state_and_audit_history():
    service = _service()
    proposal_id = _create_draft(service)
    _submit_for_risk_review(service, proposal_id)

    transition = service.record_approval(
        proposal_id=proposal_id,
        idempotency_key="idem-risk-approval-1",
        payload=ProposalApprovalRequest(
            approval_type="RISK",
            approved=True,
            actor_id="risk_officer_1",
            details={"channel": "IN_PERSON"},
            expected_state="RISK_REVIEW",
        ),
    )

    assert transition.current_state == "AWAITING_CLIENT_CONSENT"
    assert transition.latest_workflow_event.event_type == "RISK_APPROVED"
    assert transition.approval is not None
    assert transition.approval.approval_type == "RISK"
    assert transition.approval.approved is True

    timeline = service.get_workflow_timeline(proposal_id=proposal_id)
    assert timeline.current_state == "AWAITING_CLIENT_CONSENT"
    assert [event.event_type for event in timeline.events] == [
        "CREATED",
        "SUBMITTED_FOR_RISK_REVIEW",
        "RISK_APPROVED",
    ]

    approvals = service.get_approvals(proposal_id=proposal_id)
    assert len(approvals.approvals) == 1
    assert approvals.approvals[0].details["channel"] == "IN_PERSON"
    assert approvals.approvals[0].details["idempotency_key"] == "idem-risk-approval-1"


def test_record_approval_is_idempotent_and_rejects_payload_conflict():
    service = _service()
    proposal_id = _create_draft(service)
    _submit_for_risk_review(service, proposal_id)

    payload = ProposalApprovalRequest(
        approval_type="RISK",
        approved=True,
        actor_id="risk_officer_2",
        details={"source": "workflow_api"},
        expected_state="RISK_REVIEW",
    )
    first = service.record_approval(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-approval-2",
    )
    second = service.record_approval(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-approval-2",
    )

    assert second.latest_workflow_event.event_id == first.latest_workflow_event.event_id
    assert second.approval is not None and first.approval is not None
    assert second.approval.approval_id == first.approval.approval_id

    with pytest.raises(ProposalIdempotencyConflictError, match="IDEMPOTENCY_KEY_CONFLICT"):
        service.record_approval(
            proposal_id=proposal_id,
            payload=ProposalApprovalRequest(
                approval_type="RISK",
                approved=False,
                actor_id="risk_officer_2",
                details={"source": "workflow_api"},
                expected_state="RISK_REVIEW",
            ),
            idempotency_key="idem-approval-2",
        )


def test_transition_requires_expected_state_and_rejects_stale_state():
    service = _service(require_expected_state=True)
    proposal_id = _create_draft(service)

    with pytest.raises(ProposalStateConflictError, match="expected_state is required"):
        service.transition_state(
            proposal_id=proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_RISK_REVIEW",
                actor_id="advisor_1",
                reason={},
            ),
        )

    with pytest.raises(ProposalStateConflictError, match="expected_state mismatch"):
        service.transition_state(
            proposal_id=proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_RISK_REVIEW",
                actor_id="advisor_1",
                expected_state="COMPLIANCE_REVIEW",
                reason={},
            ),
        )


def test_client_consent_approval_is_rejected_when_state_is_not_awaiting_consent():
    service = _service()
    proposal_id = _create_draft(service)

    with pytest.raises(ProposalTransitionError, match="INVALID_APPROVAL_STATE"):
        service.record_approval(
            proposal_id=proposal_id,
            payload=ProposalApprovalRequest(
                approval_type="CLIENT_CONSENT",
                approved=True,
                actor_id="client_1",
                details={"channel": "EMAIL"},
                expected_state="DRAFT",
            ),
        )


def test_create_proposal_is_idempotent_and_conflict_safe():
    service = _service()
    payload = _create_payload()

    first = service.create_proposal(
        payload=payload,
        idempotency_key="idem-create-main",
        correlation_id="corr-main",
    )
    second = service.create_proposal(
        payload=payload,
        idempotency_key="idem-create-main",
        correlation_id="corr-other",
    )

    assert second.proposal.proposal_id == first.proposal.proposal_id
    assert second.version.proposal_version_id == first.version.proposal_version_id

    changed_payload = _create_payload()
    changed_payload.metadata.title = "Changed title"
    with pytest.raises(ProposalIdempotencyConflictError, match="IDEMPOTENCY_KEY_CONFLICT"):
        service.create_proposal(
            payload=changed_payload,
            idempotency_key="idem-create-main",
            correlation_id="corr-main",
        )


def test_get_proposal_hides_evidence_when_requested_and_lists_versions_in_lineage():
    service = _service()
    proposal_id = _create_draft(service)

    service.create_version(
        proposal_id=proposal_id,
        payload=_version_payload(),
        correlation_id="corr-v2",
    )

    detail = service.get_proposal(proposal_id=proposal_id, include_evidence=False)
    assert detail.current_version.version_no == 2
    assert detail.current_version.evidence_bundle == {}
    assert detail.last_gate_decision == detail.current_version.gate_decision

    lineage = service.get_lineage(proposal_id=proposal_id)
    assert [version.version_no for version in lineage.versions] == [1, 2]


def test_list_proposals_and_idempotency_lookup_surface_persisted_records():
    service = _service()
    first = service.create_proposal(
        payload=_create_payload(),
        idempotency_key="idem-list-1",
        correlation_id=None,
    )
    second_payload = _create_payload()
    second_payload.created_by = "advisor_2"
    second_payload.simulate_request.portfolio_snapshot.portfolio_id = "pf_2"
    second = service.create_proposal(
        payload=second_payload,
        idempotency_key="idem-list-2",
        correlation_id=None,
    )

    first_page = service.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=1,
        cursor=None,
    )
    assert len(first_page.items) == 1
    assert first_page.next_cursor is not None

    second_page = service.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=5,
        cursor=first_page.next_cursor,
    )
    assert len(second_page.items) == 1
    assert {first_page.items[0].proposal_id, second_page.items[0].proposal_id} == {
        first.proposal.proposal_id,
        second.proposal.proposal_id,
    }

    filtered = service.list_proposals(
        portfolio_id="pf_2",
        state="DRAFT",
        created_by="advisor_2",
        created_from=None,
        created_to=None,
        limit=10,
        cursor=None,
    )
    assert [item.proposal_id for item in filtered.items] == [second.proposal.proposal_id]

    idem_lookup = service.get_idempotency_lookup(idempotency_key="idem-list-1")
    assert idem_lookup.proposal_id == first.proposal.proposal_id


def test_create_version_enforces_state_and_portfolio_rules():
    service = _service()
    proposal_id = _create_draft(service)

    with pytest.raises(ProposalValidationError, match="PORTFOLIO_CONTEXT_MISMATCH"):
        service.create_version(
            proposal_id=proposal_id,
            payload=_version_payload(portfolio_id="pf_other"),
            correlation_id="corr-mismatch",
        )

    flexible = _service(allow_portfolio_id_change_on_new_version=True)
    flexible_id = _create_draft(flexible)
    created = flexible.create_version(
        proposal_id=flexible_id,
        payload=_version_payload(portfolio_id="pf_other"),
        correlation_id=None,
    )
    assert created.version.version_no == 2

    service.transition_state(
        proposal_id=proposal_id,
        payload=ProposalStateTransitionRequest(
            event_type="CANCELLED",
            actor_id="advisor_1",
            expected_state="DRAFT",
            reason={},
        ),
    )
    with pytest.raises(ProposalValidationError, match="PROPOSAL_TERMINAL_STATE"):
        service.create_version(
            proposal_id=proposal_id,
            payload=_version_payload(),
            correlation_id="corr-terminal",
        )


def test_transition_state_idempotency_replay_and_conflict():
    service = _service()
    proposal_id = _create_draft(service)

    payload = ProposalStateTransitionRequest(
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        actor_id="advisor_1",
        expected_state="DRAFT",
        reason={"source": "workflow"},
    )
    first = service.transition_state(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-transition-1",
    )
    replay = service.transition_state(
        proposal_id=proposal_id,
        payload=payload,
        idempotency_key="idem-transition-1",
    )

    assert first.latest_workflow_event.event_id == replay.latest_workflow_event.event_id
    assert replay.current_state == "RISK_REVIEW"

    with pytest.raises(ProposalIdempotencyConflictError, match="IDEMPOTENCY_KEY_CONFLICT"):
        service.transition_state(
            proposal_id=proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="SUBMITTED_FOR_COMPLIANCE_REVIEW",
                actor_id="advisor_1",
                expected_state="RISK_REVIEW",
                reason={"source": "workflow"},
            ),
            idempotency_key="idem-transition-1",
        )


def test_async_create_proposal_and_version_operations_report_status():
    service = _service()
    create_payload = _create_payload()

    accepted = service.submit_create_proposal_async(
        payload=create_payload,
        idempotency_key="idem-async-create",
        correlation_id=None,
    )
    service.execute_create_proposal_async(
        operation_id=accepted.operation_id,
        payload=create_payload,
        idempotency_key="idem-async-create",
        correlation_id=accepted.correlation_id,
    )
    create_status = service.get_async_operation(operation_id=accepted.operation_id)
    by_correlation = service.get_async_operation_by_correlation(
        correlation_id=accepted.correlation_id
    )
    assert create_status.status == "SUCCEEDED"
    assert by_correlation.operation_id == accepted.operation_id
    assert create_status.result is not None

    proposal_id = create_status.result.proposal.proposal_id
    version_accepted = service.submit_create_version_async(
        proposal_id=proposal_id,
        payload=_version_payload(),
        correlation_id="corr-async-v2",
    )
    service.execute_create_version_async(
        operation_id=version_accepted.operation_id,
        proposal_id=proposal_id,
        payload=_version_payload(),
        correlation_id="corr-async-v2",
    )
    version_status = service.get_async_operation(operation_id=version_accepted.operation_id)
    assert version_status.status == "SUCCEEDED"
    assert version_status.result is not None
    assert version_status.result.version.version_no == 2


def test_async_operation_failure_sets_structured_error_payload():
    service = _service(require_proposal_simulation_flag=True)
    proposal_id = _create_draft(service)

    bad_payload = _version_payload(enable_simulation=False)
    accepted = service.submit_create_version_async(
        proposal_id=proposal_id,
        payload=bad_payload,
        correlation_id="corr-bad-async-v2",
    )
    service.execute_create_version_async(
        operation_id=accepted.operation_id,
        proposal_id=proposal_id,
        payload=bad_payload,
        correlation_id="corr-bad-async-v2",
    )

    status = service.get_async_operation(operation_id=accepted.operation_id)
    assert status.status == "FAILED"
    assert status.error is not None
    assert status.error.code == "ProposalValidationError"


def test_missing_entities_raise_not_found_contract_errors():
    service = _service()

    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.get_proposal(proposal_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.get_workflow_timeline(proposal_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.get_approvals(proposal_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.get_lineage(proposal_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND"):
        service.get_idempotency_lookup(idempotency_key="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_ASYNC_OPERATION_NOT_FOUND"):
        service.get_async_operation(operation_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_ASYNC_OPERATION_NOT_FOUND"):
        service.get_async_operation_by_correlation(correlation_id="missing")
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_VERSION_NOT_FOUND"):
        service.get_version(proposal_id="missing", version_no=1)
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.transition_state(
            proposal_id="missing",
            payload=ProposalStateTransitionRequest(
                event_type="CANCELLED",
                actor_id="advisor_1",
                expected_state="DRAFT",
                reason={},
            ),
        )
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.record_approval(
            proposal_id="missing",
            payload=ProposalApprovalRequest(
                approval_type="RISK",
                approved=True,
                actor_id="risk_1",
                details={},
                expected_state="RISK_REVIEW",
            ),
        )


def test_record_approval_replay_requires_corresponding_replayed_event(monkeypatch):
    service = _service()
    proposal_id = _create_draft(service)

    approval = ProposalApprovalRecordData(
        approval_id="pap_missing_event",
        proposal_id=proposal_id,
        approval_type="RISK",
        approved=True,
        actor_id="risk_1",
        occurred_at=service._repository.get_proposal(proposal_id=proposal_id).created_at,
        details_json={"idempotency_key": "idem-x", "idempotency_request_hash": "hash-x"},
        related_version_no=1,
    )
    monkeypatch.setattr(service, "_get_replayed_approval", lambda **_: approval)
    monkeypatch.setattr(service, "_get_replayed_event", lambda **_: None)

    with pytest.raises(ProposalLifecycleError, match="PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND"):
        service.record_approval(
            proposal_id=proposal_id,
            payload=ProposalApprovalRequest(
                approval_type="RISK",
                approved=True,
                actor_id="risk_1",
                details={},
                expected_state="DRAFT",
            ),
            idempotency_key="idem-x",
        )


def test_approval_paths_cover_rejection_and_client_consent_execution_ready():
    service = _service()
    proposal_id = _create_draft(service)
    _submit_for_risk_review(service, proposal_id)

    rejected = service.record_approval(
        proposal_id=proposal_id,
        payload=ProposalApprovalRequest(
            approval_type="RISK",
            approved=False,
            actor_id="risk_2",
            details={"reason": "constraint breach"},
            expected_state="RISK_REVIEW",
        ),
    )
    assert rejected.current_state == "REJECTED"
    assert rejected.latest_workflow_event.event_type == "REJECTED"

    second_service = _service()
    second_proposal = _create_draft(second_service)
    _submit_for_risk_review(second_service, second_proposal)
    second_service.record_approval(
        proposal_id=second_proposal,
        payload=ProposalApprovalRequest(
            approval_type="RISK",
            approved=True,
            actor_id="risk_3",
            details={},
            expected_state="RISK_REVIEW",
        ),
    )
    consent = second_service.record_approval(
        proposal_id=second_proposal,
        payload=ProposalApprovalRequest(
            approval_type="CLIENT_CONSENT",
            approved=True,
            actor_id="client_2",
            details={"channel": "DIGITAL_SIGNATURE"},
            expected_state="AWAITING_CLIENT_CONSENT",
        ),
    )
    assert consent.current_state == "EXECUTION_READY"
    assert consent.latest_workflow_event.event_type == "CLIENT_CONSENT_RECORDED"


def test_invalid_transition_and_missing_async_operation_are_non_destructive():
    service = _service()
    proposal_id = _create_draft(service)

    with pytest.raises(ProposalTransitionError, match="INVALID_TRANSITION"):
        service.transition_state(
            proposal_id=proposal_id,
            payload=ProposalStateTransitionRequest(
                event_type="EXECUTED",
                actor_id="ops_1",
                expected_state="DRAFT",
                reason={},
            ),
        )

    # Unknown operations are ignored by executor methods to preserve idempotent worker behavior.
    service.execute_create_proposal_async(
        operation_id="pop_missing",
        payload=_create_payload(),
        idempotency_key="idem-missing-op",
        correlation_id="corr-missing-op",
    )
    service.execute_create_version_async(
        operation_id="pop_missing",
        proposal_id=proposal_id,
        payload=_version_payload(),
        correlation_id="corr-missing-op-v2",
    )


def test_async_create_proposal_failure_records_error_details():
    service = _service(require_proposal_simulation_flag=True)
    invalid_payload = _create_payload()
    invalid_payload.simulate_request.options.enable_proposal_simulation = False

    accepted = service.submit_create_proposal_async(
        payload=invalid_payload,
        idempotency_key="idem-async-create-fail",
        correlation_id="corr-async-create-fail",
    )
    service.execute_create_proposal_async(
        operation_id=accepted.operation_id,
        payload=invalid_payload,
        idempotency_key="idem-async-create-fail",
        correlation_id="corr-async-create-fail",
    )

    status = service.get_async_operation(operation_id=accepted.operation_id)
    assert status.status == "FAILED"
    assert status.error is not None
    assert status.error.code == "ProposalValidationError"


def test_get_proposal_requires_current_version_record():
    service = _service()
    now = datetime.now(timezone.utc)

    orphan = ProposalRecord(
        proposal_id="pp_orphan_1",
        portfolio_id="pf_orphan",
        mandate_id=None,
        jurisdiction=None,
        created_by="advisor_1",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="orphan",
        advisor_notes=None,
    )
    service._repository.create_proposal(orphan)

    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_VERSION_NOT_FOUND"):
        service.get_proposal(proposal_id="pp_orphan_1")


def test_lineage_skips_missing_version_numbers():
    service = _service()
    proposal_id = _create_draft(service)
    proposal = service._repository.get_proposal(proposal_id=proposal_id)
    assert proposal is not None
    proposal.current_version_no = 3
    service._repository.update_proposal(proposal)

    lineage = service.get_lineage(proposal_id=proposal_id)
    assert [item.version_no for item in lineage.versions] == [1]
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_VERSION_NOT_FOUND"):
        service.get_version(proposal_id=proposal_id, version_no=3)


def test_create_version_requires_existing_proposal():
    service = _service()
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_NOT_FOUND"):
        service.create_version(
            proposal_id="pp_missing",
            payload=_version_payload(),
            correlation_id="corr-missing-proposal",
        )


def test_internal_helpers_cover_remaining_error_contracts():
    service = _service()
    proposal_id = _create_draft(service)

    assert service._to_approval(None) is None

    assert (
        service._get_replayed_approval(
            proposal_id=proposal_id,
            idempotency_key="idem-none",
            request_hash="hash-none",
        )
        is None
    )
    service._repository.create_approval(
        ProposalApprovalRecordData(
            approval_id="pap_target_key",
            proposal_id=proposal_id,
            approval_type="RISK",
            approved=True,
            actor_id="risk_officer",
            occurred_at=datetime.now(timezone.utc),
            details_json={"idempotency_key": "idem-target", "idempotency_request_hash": "hash-target"},
            related_version_no=1,
        )
    )
    service._repository.create_approval(
        ProposalApprovalRecordData(
            approval_id="pap_other_key",
            proposal_id=proposal_id,
            approval_type="RISK",
            approved=True,
            actor_id="risk_officer",
            occurred_at=datetime.now(timezone.utc),
            details_json={"idempotency_key": "idem-other", "idempotency_request_hash": "hash-other"},
            related_version_no=1,
        )
    )
    matched = service._get_replayed_approval(
        proposal_id=proposal_id,
        idempotency_key="idem-target",
        request_hash="hash-target",
    )
    assert matched is not None
    assert matched.approval_id == "pap_target_key"

    with pytest.raises(ProposalTransitionError, match="INVALID_APPROVAL_TYPE"):
        service._resolve_approval_transition(
            current_state="RISK_REVIEW",
            approval_type="UNKNOWN",
            approved=True,
        )

    service._repository.save_idempotency(
        ProposalIdempotencyRecord(
            idempotency_key="idem-bad-ref",
            request_hash="hash-1",
            proposal_id="pp_missing_ref",
            proposal_version_no=99,
            created_at=datetime.now(timezone.utc),
        )
    )
    with pytest.raises(ProposalNotFoundError, match="PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND"):
        service._read_create_response(proposal_id="pp_missing_ref", version_no=99)
