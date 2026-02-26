import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory_engine import run_proposal_simulation
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.models import (
    ProposalApprovalRecord,
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalApprovalsResponse,
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationRecord,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDetailResponse,
    ProposalIdempotencyLookupResponse,
    ProposalIdempotencyRecord,
    ProposalLineageResponse,
    ProposalListResponse,
    ProposalRecord,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalVersionLineageItem,
    ProposalVersionRecord,
    ProposalVersionRequest,
    ProposalWorkflowEvent,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.repository import ProposalRepository

TERMINAL_STATES = {"EXECUTED", "REJECTED", "CANCELLED", "EXPIRED"}

TRANSITION_MAP: dict[tuple[ProposalWorkflowState, str], ProposalWorkflowState] = {
    ("DRAFT", "SUBMITTED_FOR_RISK_REVIEW"): "RISK_REVIEW",
    ("DRAFT", "SUBMITTED_FOR_COMPLIANCE_REVIEW"): "COMPLIANCE_REVIEW",
    ("RISK_REVIEW", "RISK_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("RISK_REVIEW", "REJECTED"): "REJECTED",
    ("COMPLIANCE_REVIEW", "COMPLIANCE_APPROVED"): "AWAITING_CLIENT_CONSENT",
    ("COMPLIANCE_REVIEW", "REJECTED"): "REJECTED",
    ("AWAITING_CLIENT_CONSENT", "CLIENT_CONSENT_RECORDED"): "EXECUTION_READY",
    ("AWAITING_CLIENT_CONSENT", "REJECTED"): "REJECTED",
    ("EXECUTION_READY", "EXECUTED"): "EXECUTED",
    ("EXECUTION_READY", "EXPIRED"): "EXPIRED",
}


class ProposalLifecycleError(Exception):
    pass


class ProposalNotFoundError(ProposalLifecycleError):
    pass


class ProposalValidationError(ProposalLifecycleError):
    pass


class ProposalIdempotencyConflictError(ProposalLifecycleError):
    pass


class ProposalStateConflictError(ProposalLifecycleError):
    pass


class ProposalTransitionError(ProposalLifecycleError):
    pass


class ProposalWorkflowService:
    def __init__(
        self,
        *,
        repository: ProposalRepository,
        store_evidence_bundle: bool = True,
        require_expected_state: bool = True,
        allow_portfolio_id_change_on_new_version: bool = False,
        require_proposal_simulation_flag: bool = True,
    ) -> None:
        self._repository = repository
        self._store_evidence_bundle = store_evidence_bundle
        self._require_expected_state = require_expected_state
        self._allow_portfolio_id_change_on_new_version = allow_portfolio_id_change_on_new_version
        self._require_proposal_simulation_flag = require_proposal_simulation_flag

    def create_proposal(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> ProposalCreateResponse:
        now = _utc_now()
        request_payload = payload.model_dump(mode="json")
        request_hash = hash_canonical_payload(request_payload)

        existing = self._repository.get_idempotency(idempotency_key=idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return self._read_create_response(
                proposal_id=existing.proposal_id,
                version_no=existing.proposal_version_no,
            )

        self._validate_simulation_flag(payload.simulate_request)
        proposal_result = self._run_simulation(
            request=payload.simulate_request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
        artifact = build_proposal_artifact(
            request=payload.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )

        proposal_id = f"pp_{uuid.uuid4().hex[:12]}"
        version_no = 1
        proposal = ProposalRecord(
            proposal_id=proposal_id,
            portfolio_id=payload.simulate_request.portfolio_snapshot.portfolio_id,
            mandate_id=payload.metadata.mandate_id,
            jurisdiction=payload.metadata.jurisdiction,
            created_by=payload.created_by,
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=version_no,
            title=payload.metadata.title,
            advisor_notes=payload.metadata.advisor_notes,
        )
        version = self._to_version_record(
            proposal_id=proposal_id,
            version_no=version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=artifact.evidence_bundle.model_dump(mode="json"),
            created_at=now,
        )
        created_event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id=payload.created_by,
            occurred_at=now,
            reason_json={"correlation_id": correlation_id} if correlation_id else {},
            related_version_no=version_no,
        )

        self._repository.create_proposal(proposal)
        self._repository.create_version(version)
        self._repository.append_event(created_event)
        self._repository.save_idempotency(
            ProposalIdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                proposal_id=proposal_id,
                proposal_version_no=version_no,
                created_at=now,
            )
        )

        return self._to_create_response(
            proposal=proposal, version=version, latest_event=created_event
        )

    def submit_create_proposal_async(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = ProposalAsyncOperationRecord(
            operation_id=f"pop_{uuid.uuid4().hex[:12]}",
            operation_type="CREATE_PROPOSAL",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            idempotency_key=idempotency_key,
            proposal_id=None,
            created_by=payload.created_by,
            created_at=_utc_now(),
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
        )
        self._repository.create_operation(operation)
        return self._to_async_accepted(operation)

    def execute_create_proposal_async(
        self,
        *,
        operation_id: str,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: str,
    ) -> None:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            return
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)
        try:
            response = self.create_proposal(
                payload=payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
            )
            operation.status = "SUCCEEDED"
            operation.proposal_id = response.proposal.proposal_id
            operation.result_json = response.model_dump(mode="json")
            operation.error_json = None
        except ProposalLifecycleError as exc:
            operation.status = "FAILED"
            operation.error_json = {"code": type(exc).__name__, "message": str(exc)}
            operation.result_json = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def get_proposal(
        self, *, proposal_id: str, include_evidence: bool = True
    ) -> ProposalDetailResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        version = self._repository.get_current_version(proposal_id=proposal_id)
        if version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        return ProposalDetailResponse(
            proposal=self._to_summary(proposal),
            current_version=self._to_version_detail(version, include_evidence=include_evidence),
            last_gate_decision=(
                self._to_version_detail(version, include_evidence=include_evidence).gate_decision
            ),
        )

    def list_proposals(
        self,
        *,
        portfolio_id: Optional[str],
        state: Optional[str],
        created_by: Optional[str],
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        limit: int,
        cursor: Optional[str],
    ) -> ProposalListResponse:
        rows, next_cursor = self._repository.list_proposals(
            portfolio_id=portfolio_id,
            state=state,
            created_by=created_by,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            cursor=cursor,
        )
        return ProposalListResponse(
            items=[self._to_summary(row) for row in rows], next_cursor=next_cursor
        )

    def get_workflow_timeline(self, *, proposal_id: str) -> ProposalWorkflowTimelineResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        events = self._repository.list_events(proposal_id=proposal_id)
        return ProposalWorkflowTimelineResponse(
            proposal_id=proposal_id,
            current_state=proposal.current_state,
            events=[self._to_event(event) for event in events],
        )

    def get_approvals(self, *, proposal_id: str) -> ProposalApprovalsResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        approvals = self._repository.list_approvals(proposal_id=proposal_id)
        return ProposalApprovalsResponse(
            proposal_id=proposal_id,
            approvals=[
                self._to_approval(approval) for approval in approvals if approval is not None
            ],
        )

    def get_lineage(self, *, proposal_id: str) -> ProposalLineageResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")

        versions: list[ProposalVersionLineageItem] = []
        for version_no in range(1, proposal.current_version_no + 1):
            version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
            if version is None:
                continue
            versions.append(
                ProposalVersionLineageItem(
                    proposal_version_id=version.proposal_version_id,
                    version_no=version.version_no,
                    created_at=version.created_at.isoformat(),
                    status_at_creation=version.status_at_creation,
                    request_hash=version.request_hash,
                    simulation_hash=version.simulation_hash,
                    artifact_hash=version.artifact_hash,
                )
            )

        return ProposalLineageResponse(proposal=self._to_summary(proposal), versions=versions)

    def get_idempotency_lookup(self, *, idempotency_key: str) -> ProposalIdempotencyLookupResponse:
        record = self._repository.get_idempotency(idempotency_key=idempotency_key)
        if record is None:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND")
        return ProposalIdempotencyLookupResponse(
            idempotency_key=record.idempotency_key,
            request_hash=record.request_hash,
            proposal_id=record.proposal_id,
            proposal_version_no=record.proposal_version_no,
            created_at=record.created_at.isoformat(),
        )

    def get_async_operation(self, *, operation_id: str) -> ProposalAsyncOperationStatusResponse:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return self._to_async_status(operation)

    def get_async_operation_by_correlation(
        self, *, correlation_id: str
    ) -> ProposalAsyncOperationStatusResponse:
        operation = self._repository.get_operation_by_correlation(correlation_id=correlation_id)
        if operation is None:
            raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
        return self._to_async_status(operation)

    def get_version(
        self,
        *,
        proposal_id: str,
        version_no: int,
        include_evidence: bool = True,
    ) -> ProposalVersionDetail:
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        if version is None:
            raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
        return self._to_version_detail(version, include_evidence=include_evidence)

    def create_version(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> ProposalCreateResponse:
        now = _utc_now()
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        if proposal.current_state in TERMINAL_STATES:
            raise ProposalValidationError("PROPOSAL_TERMINAL_STATE: cannot create version")

        self._validate_simulation_flag(payload.simulate_request)
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        if (
            not self._allow_portfolio_id_change_on_new_version
            and payload.simulate_request.portfolio_snapshot.portfolio_id != proposal.portfolio_id
        ):
            raise ProposalValidationError("PORTFOLIO_CONTEXT_MISMATCH")

        proposal_result = self._run_simulation(
            request=payload.simulate_request,
            request_hash=request_hash,
            idempotency_key=None,
            correlation_id=correlation_id,
        )
        artifact = build_proposal_artifact(
            request=payload.simulate_request,
            proposal_result=proposal_result,
            created_at=now.isoformat(),
        )

        next_version_no = proposal.current_version_no + 1
        version = self._to_version_record(
            proposal_id=proposal.proposal_id,
            version_no=next_version_no,
            request_hash=request_hash,
            proposal_result=proposal_result,
            artifact=artifact.model_dump(mode="json"),
            evidence_bundle=artifact.evidence_bundle.model_dump(mode="json"),
            created_at=now,
        )
        event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal.proposal_id,
            event_type="NEW_VERSION_CREATED",
            from_state=proposal.current_state,
            to_state=proposal.current_state,
            actor_id=payload.created_by,
            occurred_at=now,
            reason_json={"correlation_id": correlation_id} if correlation_id else {},
            related_version_no=next_version_no,
        )

        proposal.current_version_no = next_version_no
        proposal.last_event_at = now
        self._repository.create_version(version)
        self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return self._to_create_response(proposal=proposal, version=version, latest_event=event)

    def submit_create_version_async(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: Optional[str],
    ) -> ProposalAsyncAcceptedResponse:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        operation = ProposalAsyncOperationRecord(
            operation_id=f"pop_{uuid.uuid4().hex[:12]}",
            operation_type="CREATE_PROPOSAL_VERSION",
            status="PENDING",
            correlation_id=resolved_correlation_id,
            idempotency_key=None,
            proposal_id=proposal_id,
            created_by=payload.created_by,
            created_at=_utc_now(),
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
        )
        self._repository.create_operation(operation)
        return self._to_async_accepted(operation)

    def execute_create_version_async(
        self,
        *,
        operation_id: str,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: str,
    ) -> None:
        operation = self._repository.get_operation(operation_id=operation_id)
        if operation is None:
            return
        operation.status = "RUNNING"
        operation.started_at = _utc_now()
        self._repository.update_operation(operation)
        try:
            response = self.create_version(
                proposal_id=proposal_id,
                payload=payload,
                correlation_id=correlation_id,
            )
            operation.status = "SUCCEEDED"
            operation.proposal_id = response.proposal.proposal_id
            operation.result_json = response.model_dump(mode="json")
            operation.error_json = None
        except ProposalLifecycleError as exc:
            operation.status = "FAILED"
            operation.error_json = {"code": type(exc).__name__, "message": str(exc)}
            operation.result_json = None
        operation.finished_at = _utc_now()
        self._repository.update_operation(operation)

    def transition_state(
        self,
        *,
        proposal_id: str,
        payload: ProposalStateTransitionRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_event = self._get_replayed_event(
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_event is not None:
            return ProposalStateTransitionResponse(
                proposal_id=proposal_id,
                current_state=replay_event.to_state,
                latest_workflow_event=self._to_event(replay_event),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)

        to_state = self._resolve_transition_state(
            current_state=proposal.current_state,
            event_type=payload.event_type,
        )
        reason_json = dict(payload.reason)
        if idempotency_key:
            reason_json["idempotency_key"] = idempotency_key
            reason_json["idempotency_request_hash"] = request_hash
        event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            event_type=payload.event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=_utc_now(),
            reason_json=reason_json,
            related_version_no=payload.related_version_no,
        )
        proposal.current_state = to_state
        proposal.last_event_at = event.occurred_at

        result = self._repository.transition_proposal(proposal=proposal, event=event, approval=None)
        return ProposalStateTransitionResponse(
            proposal_id=proposal_id,
            current_state=result.proposal.current_state,
            latest_workflow_event=self._to_event(result.event),
        )

    def record_approval(
        self,
        *,
        proposal_id: str,
        payload: ProposalApprovalRequest,
        idempotency_key: Optional[str] = None,
    ) -> ProposalStateTransitionResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        if proposal is None:
            raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
        request_hash = hash_canonical_payload(payload.model_dump(mode="json"))
        replay_approval = self._get_replayed_approval(
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_approval is not None:
            replay_event = self._get_replayed_event(
                proposal_id=proposal_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay_event is None:
                raise ProposalLifecycleError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
            return ProposalStateTransitionResponse(
                proposal_id=proposal_id,
                current_state=replay_event.to_state,
                latest_workflow_event=self._to_event(replay_event),
                approval=self._to_approval(replay_approval),
            )
        self._validate_expected_state(proposal.current_state, payload.expected_state)

        details_json = dict(payload.details)
        if idempotency_key:
            details_json["idempotency_key"] = idempotency_key
            details_json["idempotency_request_hash"] = request_hash
        approval = ProposalApprovalRecordData(
            approval_id=f"pap_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            approval_type=payload.approval_type,
            approved=payload.approved,
            actor_id=payload.actor_id,
            occurred_at=_utc_now(),
            details_json=details_json,
            related_version_no=payload.related_version_no,
        )

        event_type, to_state = self._resolve_approval_transition(
            current_state=proposal.current_state,
            approval_type=payload.approval_type,
            approved=payload.approved,
        )
        reason_json = dict(payload.details)
        if idempotency_key:
            reason_json["idempotency_key"] = idempotency_key
            reason_json["idempotency_request_hash"] = request_hash
        event = ProposalWorkflowEventRecord(
            event_id=f"pwe_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            event_type=event_type,
            from_state=proposal.current_state,
            to_state=to_state,
            actor_id=payload.actor_id,
            occurred_at=approval.occurred_at,
            reason_json=reason_json,
            related_version_no=payload.related_version_no,
        )
        proposal.current_state = to_state
        proposal.last_event_at = event.occurred_at

        result = self._repository.transition_proposal(
            proposal=proposal, event=event, approval=approval
        )
        return ProposalStateTransitionResponse(
            proposal_id=proposal_id,
            current_state=result.proposal.current_state,
            latest_workflow_event=self._to_event(result.event),
            approval=self._to_approval(result.approval),
        )

    def _get_replayed_event(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalWorkflowEventRecord]:
        if not idempotency_key:
            return None
        for event in reversed(self._repository.list_events(proposal_id=proposal_id)):
            existing_key = event.reason_json.get("idempotency_key")
            if existing_key != idempotency_key:
                continue
            existing_hash = event.reason_json.get("idempotency_request_hash")
            if existing_hash is not None and existing_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return event
        return None

    def _get_replayed_approval(
        self, *, proposal_id: str, idempotency_key: Optional[str], request_hash: str
    ) -> Optional[ProposalApprovalRecordData]:
        if not idempotency_key:
            return None
        for approval in reversed(self._repository.list_approvals(proposal_id=proposal_id)):
            existing_key = approval.details_json.get("idempotency_key")
            if existing_key != idempotency_key:
                continue
            existing_hash = approval.details_json.get("idempotency_request_hash")
            if existing_hash is not None and existing_hash != request_hash:
                raise ProposalIdempotencyConflictError(
                    "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"
                )
            return approval
        return None

    def _read_create_response(self, *, proposal_id: str, version_no: int) -> ProposalCreateResponse:
        proposal = self._repository.get_proposal(proposal_id=proposal_id)
        version = self._repository.get_version(proposal_id=proposal_id, version_no=version_no)
        events = self._repository.list_events(proposal_id=proposal_id)
        if proposal is None or version is None or not events:
            raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
        return self._to_create_response(proposal=proposal, version=version, latest_event=events[-1])

    def _to_create_response(
        self,
        *,
        proposal: ProposalRecord,
        version: ProposalVersionRecord,
        latest_event: ProposalWorkflowEventRecord,
    ) -> ProposalCreateResponse:
        return ProposalCreateResponse(
            proposal=self._to_summary(proposal),
            version=self._to_version_detail(version, include_evidence=True),
            latest_workflow_event=self._to_event(latest_event),
        )

    def _to_summary(self, proposal: ProposalRecord) -> ProposalSummary:
        return ProposalSummary(
            proposal_id=proposal.proposal_id,
            portfolio_id=proposal.portfolio_id,
            mandate_id=proposal.mandate_id,
            jurisdiction=proposal.jurisdiction,
            created_by=proposal.created_by,
            created_at=proposal.created_at.isoformat(),
            last_event_at=proposal.last_event_at.isoformat(),
            current_state=proposal.current_state,
            current_version_no=proposal.current_version_no,
            title=proposal.title,
        )

    def _to_version_detail(
        self, version: ProposalVersionRecord, *, include_evidence: bool
    ) -> ProposalVersionDetail:
        evidence_bundle_json: dict[str, Any] = (
            version.evidence_bundle_json if include_evidence else {}
        )
        return ProposalVersionDetail(
            proposal_version_id=version.proposal_version_id,
            proposal_id=version.proposal_id,
            version_no=version.version_no,
            created_at=version.created_at.isoformat(),
            request_hash=version.request_hash,
            artifact_hash=version.artifact_hash,
            simulation_hash=version.simulation_hash,
            status_at_creation=version.status_at_creation,
            proposal_result=version.proposal_result_json,
            artifact=version.artifact_json,
            evidence_bundle=evidence_bundle_json,
            gate_decision=version.gate_decision_json,
        )

    def _to_event(self, event: ProposalWorkflowEventRecord) -> ProposalWorkflowEvent:
        return ProposalWorkflowEvent(
            event_id=event.event_id,
            proposal_id=event.proposal_id,
            event_type=event.event_type,
            from_state=event.from_state,
            to_state=event.to_state,
            actor_id=event.actor_id,
            occurred_at=event.occurred_at.isoformat(),
            reason=event.reason_json,
            related_version_no=event.related_version_no,
        )

    def _to_approval(
        self, approval: Optional[ProposalApprovalRecordData]
    ) -> Optional[ProposalApprovalRecord]:
        if approval is None:
            return None
        return ProposalApprovalRecord(
            approval_id=approval.approval_id,
            proposal_id=approval.proposal_id,
            approval_type=approval.approval_type,
            approved=approval.approved,
            actor_id=approval.actor_id,
            occurred_at=approval.occurred_at.isoformat(),
            details=approval.details_json,
            related_version_no=approval.related_version_no,
        )

    def _to_version_record(
        self,
        *,
        proposal_id: str,
        version_no: int,
        request_hash: str,
        proposal_result: ProposalResult,
        artifact: dict[str, Any],
        evidence_bundle: dict[str, Any],
        created_at: datetime,
    ) -> ProposalVersionRecord:
        simulation_payload = proposal_result.model_dump(mode="json")
        simulation_hash = hash_canonical_payload(simulation_payload)
        artifact_hash = artifact["evidence_bundle"]["hashes"]["artifact_hash"]
        return ProposalVersionRecord(
            proposal_version_id=f"ppv_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            version_no=version_no,
            created_at=created_at,
            request_hash=request_hash,
            artifact_hash=artifact_hash,
            simulation_hash=simulation_hash,
            status_at_creation=proposal_result.status,
            proposal_result_json=simulation_payload,
            artifact_json=artifact,
            evidence_bundle_json=evidence_bundle if self._store_evidence_bundle else {},
            gate_decision_json=(
                proposal_result.gate_decision.model_dump(mode="json")
                if proposal_result.gate_decision is not None
                else None
            ),
        )

    def _to_async_accepted(
        self, operation: ProposalAsyncOperationRecord
    ) -> ProposalAsyncAcceptedResponse:
        return ProposalAsyncAcceptedResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            created_at=operation.created_at.isoformat(),
            status_url=f"/rebalance/proposals/operations/{operation.operation_id}",
        )

    def _to_async_status(
        self, operation: ProposalAsyncOperationRecord
    ) -> ProposalAsyncOperationStatusResponse:
        return ProposalAsyncOperationStatusResponse(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            idempotency_key=operation.idempotency_key,
            proposal_id=operation.proposal_id,
            created_by=operation.created_by,
            created_at=operation.created_at.isoformat(),
            started_at=(operation.started_at.isoformat() if operation.started_at else None),
            finished_at=(operation.finished_at.isoformat() if operation.finished_at else None),
            result=(
                ProposalCreateResponse.model_validate(operation.result_json)
                if operation.result_json is not None
                else None
            ),
            error=operation.error_json,
        )

    def _run_simulation(
        self,
        *,
        request: ProposalSimulateRequest,
        request_hash: str,
        idempotency_key: Optional[str],
        correlation_id: Optional[str],
    ) -> ProposalResult:
        resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=resolved_correlation_id,
        )

    def _validate_simulation_flag(self, request: ProposalSimulateRequest) -> None:
        if (
            self._require_proposal_simulation_flag
            and not request.options.enable_proposal_simulation
        ):
            raise ProposalValidationError(
                "PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true"
            )

    def _validate_expected_state(
        self,
        current_state: ProposalWorkflowState,
        expected_state: Optional[ProposalWorkflowState],
    ) -> None:
        if expected_state is None and self._require_expected_state:
            raise ProposalStateConflictError("STATE_CONFLICT: expected_state is required")
        if expected_state is not None and expected_state != current_state:
            raise ProposalStateConflictError("STATE_CONFLICT: expected_state mismatch")

    def _resolve_transition_state(
        self,
        *,
        current_state: ProposalWorkflowState,
        event_type: str,
    ) -> ProposalWorkflowState:
        if event_type == "CANCELLED" and current_state not in TERMINAL_STATES:
            return "CANCELLED"
        next_state = TRANSITION_MAP.get((current_state, event_type))
        if next_state is None:
            raise ProposalTransitionError("INVALID_TRANSITION")
        return next_state

    def _resolve_approval_transition(
        self,
        *,
        current_state: ProposalWorkflowState,
        approval_type: str,
        approved: bool,
    ) -> tuple[str, ProposalWorkflowState]:
        if approval_type == "RISK":
            if current_state != "RISK_REVIEW":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "RISK_APPROVED" if approved else "REJECTED",
                "AWAITING_CLIENT_CONSENT" if approved else "REJECTED",
            )

        if approval_type == "COMPLIANCE":
            if current_state != "COMPLIANCE_REVIEW":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "COMPLIANCE_APPROVED" if approved else "REJECTED",
                "AWAITING_CLIENT_CONSENT" if approved else "REJECTED",
            )

        if approval_type == "CLIENT_CONSENT":
            if current_state != "AWAITING_CLIENT_CONSENT":
                raise ProposalTransitionError("INVALID_APPROVAL_STATE")
            return (
                "CLIENT_CONSENT_RECORDED" if approved else "REJECTED",
                "EXECUTION_READY" if approved else "REJECTED",
            )

        raise ProposalTransitionError("INVALID_APPROVAL_TYPE")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
