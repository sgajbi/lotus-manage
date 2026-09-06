from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path, Query, Request, status

from src.api.dependencies import get_idea_management_action_repository
from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_idea_action_intake_http import (
    IdeaActionProblemDetailsException,
    idea_action_problem,
    idea_action_problem_responses,
)
from src.api.routers.rebalance_runs_idea_action_intake_parameters import (
    IdeaActionIntakeCorrelationIdHeader,
    IdeaActionIntakeIdempotencyKeyHeader,
)
from src.api.routers.rebalance_runs_idea_action_intake_principal import (
    require_idea_action_intake_principal,
    require_idea_action_read_principal,
    require_idea_action_review_principal,
)
from src.api.services.idea_management_action_service import IdeaManagementActionService
from src.core.rebalance_runs.idea_action_intake import (
    IDEA_ACTION_INTAKE_REQUEST_EXAMPLE,
    IdeaActionIntakeInvalidIdempotencyKeyError,
    IdeaActionIntakeRequest,
    IdeaActionIntakeResponse,
    IdeaActionIntakeScopeError,
    IdeaManagementActionDecisionRequest,
    IdeaManagementActionOutcomeHistoryResponse,
    normalize_idea_action_identifier,
)
from src.core.rebalance_runs.idea_action_intake_authority import IdeaActionIntakePrincipal
from src.core.rebalance_runs.idea_management_action import (
    IdeaManagementActionConflictError,
    IdeaManagementActionNotFoundError,
)
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepository,
    IdeaManagementActionRepositoryConflictError,
    IdeaManagementActionRepositoryUnavailableError,
)


_INTAKE_DESCRIPTION = (
    "Accepts a source-safe lotus-idea conversion intent and, for REVIEW_FOR_REBALANCE, creates "
    "one durable Manage-owned PENDING_REVIEW management action. The exact receipt and owner "
    "history remain replay-safe and scoped to trusted local/dev tenant, legal-entity, and "
    "portfolio context. Acceptance is not rebalance approval or execution, an order/OMS "
    "instruction, suitability, or client publication."
)

_PROBLEM_RESPONSES = idea_action_problem_responses(
    {
        401: (
            "Trusted Idea action principal is missing or invalid.",
            "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED",
        ),
        403: (
            "Trusted principal lacks required capability or portfolio scope.",
            "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN",
        ),
        404: (
            "Scoped Idea-originated management action was not found.",
            "IDEA_MANAGEMENT_ACTION_NOT_FOUND",
        ),
        409: (
            "Request conflicts with immutable or concurrently updated management action state.",
            "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT",
        ),
        422: (
            "Idea management action request failed semantic validation.",
            "IDEA_ACTION_INTAKE_VALIDATION_FAILED",
        ),
        503: (
            "Manage persistence is unavailable for the action operation.",
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE",
        ),
    }
)


def _service() -> IdeaManagementActionService:
    try:
        repository: IdeaManagementActionRepository = get_idea_management_action_repository()
    except IdeaManagementActionRepositoryUnavailableError as exc:
        raise _persistence_unavailable() from exc
    return IdeaManagementActionService(repository=repository)


@shared.router.post(
    "/rebalance/idea-action-intake",
    response_model=IdeaActionIntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Realize lotus-idea Conversion Intent as Management Review Work",
    description=_INTAKE_DESCRIPTION,
    responses=_PROBLEM_RESPONSES,
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"example": IDEA_ACTION_INTAKE_REQUEST_EXAMPLE}}
        }
    },
)
def accept_idea_action_intake(
    request: Request,
    payload: IdeaActionIntakeRequest,
    idempotency_key: IdeaActionIntakeIdempotencyKeyHeader,
    x_correlation_id: IdeaActionIntakeCorrelationIdHeader = None,
    principal: IdeaActionIntakePrincipal = Depends(require_idea_action_intake_principal),
    service: IdeaManagementActionService = Depends(_service),
) -> IdeaActionIntakeResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    correlation_id = _correlation_id(x_correlation_id)
    try:
        return service.accept_intake(
            payload,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            principal=principal,
        )
    except IdeaActionIntakeInvalidIdempotencyKeyError as exc:
        raise idea_action_problem(
            status_code=422,
            reason_code=str(exc),
            detail="Idea action idempotency key is required.",
        ) from exc
    except IdeaActionIntakeScopeError as exc:
        raise idea_action_problem(
            status_code=403,
            reason_code=str(exc),
            detail="Trusted principal is not entitled to the requested portfolio.",
        ) from exc
    except IdeaManagementActionRepositoryConflictError as exc:
        raise idea_action_problem(
            status_code=409,
            reason_code=str(exc),
            detail="Idea action intake conflicts with immutable persisted state.",
        ) from exc
    except IdeaManagementActionRepositoryUnavailableError as exc:
        raise _persistence_unavailable() from exc


@shared.router.get(
    "/rebalance/idea-action-intakes/{intake_id}/outcomes",
    response_model=IdeaManagementActionOutcomeHistoryResponse,
    summary="Get Manage-owned Idea Action Outcome History",
    description=(
        "Returns the append-only, Manage-owned management-review outcome history for one "
        "Idea conversion intake. Review approval is not rebalance execution or order proof."
    ),
    responses=_PROBLEM_RESPONSES,
)
def get_idea_management_action_outcomes(
    request: Request,
    intake_id: Annotated[str, Path(min_length=1, max_length=80)],
    principal: IdeaActionIntakePrincipal = Depends(require_idea_action_read_principal),
    service: IdeaManagementActionService = Depends(_service),
) -> IdeaManagementActionOutcomeHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_outcome_history(intake_id=intake_id, principal=principal)
    except IdeaManagementActionNotFoundError as exc:
        raise idea_action_problem(
            status_code=404,
            reason_code=str(exc),
            detail="Scoped Idea-originated management action was not found.",
        ) from exc
    except IdeaManagementActionRepositoryUnavailableError as exc:
        raise _persistence_unavailable() from exc


@shared.router.get(
    "/rebalance/idea-action-intakes/by-conversion-intent/{conversion_intent_id}/outcomes",
    response_model=IdeaManagementActionOutcomeHistoryResponse,
    summary="Get Manage-owned Outcome History by Idea Conversion Intent",
    description=(
        "Returns the current, append-only Manage-owned outcome history for the exact Idea "
        "conversion intent within trusted tenant, legal-entity, and portfolio scope. This is "
        "a read-only recovery route: it does not create or repeat management work and does "
        "not prove rebalance execution, order execution, or client publication."
    ),
    responses=_PROBLEM_RESPONSES,
)
def get_idea_management_action_outcomes_by_conversion_intent(
    request: Request,
    conversion_intent_id: Annotated[str, Path(min_length=1, max_length=160)],
    portfolio_id: Annotated[str, Query(min_length=1, max_length=160)],
    principal: IdeaActionIntakePrincipal = Depends(require_idea_action_read_principal),
) -> IdeaManagementActionOutcomeHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params={"portfolio_id"})
    try:
        portfolio_id = normalize_idea_action_identifier(portfolio_id)
        conversion_intent_id = normalize_idea_action_identifier(conversion_intent_id)
    except ValueError as exc:
        raise idea_action_problem(
            status_code=422,
            reason_code=str(exc),
            detail="Idea action recovery identifiers are required.",
        ) from exc
    if not principal.can_access_portfolio(portfolio_id):
        raise idea_action_problem(
            status_code=403,
            reason_code="IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN",
            detail="Trusted principal is not entitled to the requested portfolio.",
        )
    service = _service()
    try:
        return service.get_outcome_history_by_conversion_intent(
            portfolio_id=portfolio_id,
            conversion_intent_id=conversion_intent_id,
            principal=principal,
        )
    except IdeaActionIntakeScopeError as exc:
        raise idea_action_problem(
            status_code=403,
            reason_code=str(exc),
            detail="Trusted principal is not entitled to the requested portfolio.",
        ) from exc
    except IdeaManagementActionNotFoundError as exc:
        raise idea_action_problem(
            status_code=404,
            reason_code=str(exc),
            detail="Scoped Idea-originated management action was not found.",
        ) from exc
    except IdeaManagementActionRepositoryUnavailableError as exc:
        raise _persistence_unavailable() from exc


@shared.router.post(
    "/rebalance/idea-action-intakes/{intake_id}/outcomes",
    response_model=IdeaManagementActionOutcomeHistoryResponse,
    summary="Record Manage-owned Idea Action Review Outcome",
    description=(
        "Appends an authorized portfolio-manager review decision using optimistic source-event "
        "version fencing. The result records management-review posture only."
    ),
    responses=_PROBLEM_RESPONSES,
)
def record_idea_management_action_outcome(
    request: Request,
    intake_id: Annotated[str, Path(min_length=1, max_length=80)],
    payload: IdeaManagementActionDecisionRequest,
    x_correlation_id: IdeaActionIntakeCorrelationIdHeader = None,
    principal: IdeaActionIntakePrincipal = Depends(require_idea_action_review_principal),
    service: IdeaManagementActionService = Depends(_service),
) -> IdeaManagementActionOutcomeHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.record_review_decision(
            intake_id=intake_id,
            workflow_action=payload.workflow_action,
            expected_source_event_version=payload.expected_source_event_version,
            reason_code=payload.reason_code,
            principal=principal,
            correlation_id=_correlation_id(x_correlation_id),
        )
    except IdeaManagementActionNotFoundError as exc:
        raise idea_action_problem(
            status_code=404,
            reason_code=str(exc),
            detail="Scoped Idea-originated management action was not found.",
        ) from exc
    except IdeaManagementActionConflictError as exc:
        raise idea_action_problem(
            status_code=409,
            reason_code=str(exc),
            detail="Management review decision conflicts with current source event state.",
        ) from exc
    except IdeaManagementActionRepositoryUnavailableError as exc:
        raise _persistence_unavailable() from exc


def _correlation_id(value: str | None) -> str:
    return (value or "corr-idea-action-intake").strip() or "corr-idea-action-intake"


def _persistence_unavailable() -> IdeaActionProblemDetailsException:
    return idea_action_problem(
        status_code=503,
        reason_code="IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE",
        detail="Manage persistence is unavailable for the action operation.",
    )
