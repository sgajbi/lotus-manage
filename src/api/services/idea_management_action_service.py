from __future__ import annotations

from datetime import datetime

from src.core.rebalance_runs.idea_action_intake import (
    IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS,
    IdeaActionIntakeRequest,
    IdeaActionIntakeResponse,
    IdeaManagementActionOutcomeHistoryResponse,
    assert_idea_action_portfolio_scope,
    idea_action_idempotency_scope_hash,
    idea_action_intake_id,
    idea_action_received_at,
    idea_action_request_fingerprint,
    idea_action_trusted_scope,
    idea_management_action_history,
    safe_idea_action_idempotency_key_hash,
)
from src.core.rebalance_runs.idea_action_intake_authority import IdeaActionIntakePrincipal
from src.core.rebalance_runs.idea_management_action import (
    IdeaManagementAction,
    IdeaManagementActionConflictError,
    IdeaManagementActionNotFoundError,
    create_idea_management_action,
    record_idea_management_review_decision,
)
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepository,
    IdeaManagementActionRepositoryConflictError,
)
from src.core.rebalance_runs.models import DpmWorkflowActionType


class IdeaManagementActionService:
    def __init__(self, *, repository: IdeaManagementActionRepository) -> None:
        self._repository = repository

    def accept_intake(
        self,
        request: IdeaActionIntakeRequest,
        *,
        principal: IdeaActionIntakePrincipal,
        idempotency_key: str,
        correlation_id: str,
        received_at: datetime | None = None,
    ) -> IdeaActionIntakeResponse:
        assert_idea_action_portfolio_scope(request, principal=principal)
        timestamp = idea_action_received_at(received_at)
        intake_id = idea_action_intake_id(request, principal=principal)
        request_fingerprint = idea_action_request_fingerprint(request)
        idempotency_scope_hash = idea_action_idempotency_scope_hash(
            idempotency_key=idempotency_key,
            principal=principal,
            portfolio_id=request.portfolio_id,
        )
        idempotency_key_hash = safe_idea_action_idempotency_key_hash(idempotency_key)
        if request.intent_type != "REVIEW_FOR_REBALANCE":
            return _rejected_receipt(
                request=request,
                principal=principal,
                intake_id=intake_id,
                request_fingerprint=request_fingerprint,
                idempotency_key_hash=idempotency_key_hash,
                correlation_id=correlation_id,
                received_at=timestamp,
            )

        proposed = create_idea_management_action(
            intake_id=intake_id,
            tenant_id=principal.tenant_id,
            legal_entity_code=principal.legal_entity_code,
            portfolio_id=request.portfolio_id,
            idea_candidate_id=request.idea_candidate_id,
            conversion_intent_id=request.conversion_intent_id,
            source_refs=tuple(
                source_ref.model_dump(mode="json", exclude_none=False)
                for source_ref in request.source_refs
            ),
            request_fingerprint=request_fingerprint,
            idempotency_scope_hash=idempotency_scope_hash,
            actor_id=principal.actor_id,
            actor_role=principal.role,
            correlation_id=correlation_id,
            created_at=timestamp,
        )
        result = self._repository.create_or_replay(action=proposed)
        return _accepted_receipt(
            action=result.action,
            principal=principal,
            idempotency_key_hash=idempotency_key_hash,
            replayed=not result.created,
            correlation_id=correlation_id,
            received_at=timestamp,
        )

    def get_outcome_history(
        self,
        *,
        intake_id: str,
        principal: IdeaActionIntakePrincipal,
    ) -> IdeaManagementActionOutcomeHistoryResponse:
        action = self._load_scoped_action(intake_id=intake_id, principal=principal)
        return idea_management_action_history(action)

    def record_review_decision(
        self,
        *,
        intake_id: str,
        workflow_action: DpmWorkflowActionType,
        expected_source_event_version: int,
        reason_code: str,
        principal: IdeaActionIntakePrincipal,
        correlation_id: str,
        decided_at: datetime | None = None,
    ) -> IdeaManagementActionOutcomeHistoryResponse:
        current = self._load_scoped_action(intake_id=intake_id, principal=principal)
        updated = record_idea_management_review_decision(
            current,
            workflow_action=workflow_action,
            expected_source_event_version=expected_source_event_version,
            actor_id=principal.actor_id,
            actor_role=principal.role,
            reason_code=reason_code,
            correlation_id=correlation_id,
            decided_at=decided_at,
        )
        try:
            persisted = self._repository.update(
                action=updated,
                expected_source_event_version=expected_source_event_version,
            )
        except IdeaManagementActionRepositoryConflictError as exc:
            raise IdeaManagementActionConflictError(str(exc)) from exc
        return idea_management_action_history(persisted)

    def _load_scoped_action(
        self,
        *,
        intake_id: str,
        principal: IdeaActionIntakePrincipal,
    ) -> IdeaManagementAction:
        action = self._repository.get_by_intake_id(
            tenant_id=principal.tenant_id,
            legal_entity_code=principal.legal_entity_code,
            intake_id=intake_id,
        )
        if action is None or not principal.can_access_portfolio(action.portfolio_id):
            raise IdeaManagementActionNotFoundError("IDEA_MANAGEMENT_ACTION_NOT_FOUND")
        return action


def _accepted_receipt(
    *,
    action: IdeaManagementAction,
    principal: IdeaActionIntakePrincipal,
    idempotency_key_hash: str,
    replayed: bool,
    correlation_id: str,
    received_at: datetime,
) -> IdeaActionIntakeResponse:
    return IdeaActionIntakeResponse(
        intake_id=action.intake_id,
        intake_status="ACCEPTED_REPLAYED" if replayed else "ACCEPTED",
        supportability_status="not_certified",
        source_authority="lotus-idea",
        action_authority="lotus-manage",
        target_product="lotus-manage:PortfolioActionRegister:v1",
        route_existence_proven=True,
        action_receipt_accepted=True,
        idempotency_replay=replayed,
        idempotency_key_hash=idempotency_key_hash,
        request_fingerprint=action.request_fingerprint,
        trusted_scope=idea_action_trusted_scope(
            principal=principal,
            correlation_id=correlation_id,
        ),
        outcome_reason_codes=[
            "idea_action_replayed_for_management_review"
            if replayed
            else "idea_action_created_for_management_review"
        ],
        action_register_created=True,
        management_action_id=action.action_id,
        management_action_status=action.status,
        source_event_version=action.source_event_version,
        outcome_history_route=(
            f"/api/v1/rebalance/idea-action-intakes/{action.intake_id}/outcomes"
        ),
        outcome_history_contract_version="lotus-manage.idea-action-outcome-history.v1",
        rebalance_execution_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        certification_blockers=list(IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS),
        evidence_refs=_evidence_refs(),
        received_at=received_at.isoformat(),
        correlation_id=correlation_id,
    )


def _rejected_receipt(
    *,
    request: IdeaActionIntakeRequest,
    principal: IdeaActionIntakePrincipal,
    intake_id: str,
    request_fingerprint: str,
    idempotency_key_hash: str,
    correlation_id: str,
    received_at: datetime,
) -> IdeaActionIntakeResponse:
    return IdeaActionIntakeResponse(
        intake_id=intake_id,
        intake_status="REJECTED",
        supportability_status="not_certified",
        source_authority="lotus-idea",
        action_authority="lotus-manage",
        target_product="lotus-manage:PortfolioActionRegister:v1",
        route_existence_proven=True,
        action_receipt_accepted=False,
        idempotency_replay=False,
        idempotency_key_hash=idempotency_key_hash,
        request_fingerprint=request_fingerprint,
        trusted_scope=idea_action_trusted_scope(
            principal=principal,
            correlation_id=correlation_id,
        ),
        outcome_reason_codes=[
            "idea_action_intent_type_not_supported",
            "idea_action_intake_rejected_no_management_work_created",
        ],
        action_register_created=False,
        rebalance_execution_authority_granted=False,
        order_created=False,
        client_publication_authorized=False,
        certification_blockers=list(IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS),
        evidence_refs=_evidence_refs(),
        received_at=received_at.isoformat(),
        correlation_id=correlation_id,
    )


def _evidence_refs() -> list[str]:
    return [
        "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
        "src/core/rebalance_runs/idea_management_action.py",
        "src/infrastructure/rebalance_runs/idea_management_actions_postgres.py",
    ]


__all__ = ["IdeaManagementActionService"]
