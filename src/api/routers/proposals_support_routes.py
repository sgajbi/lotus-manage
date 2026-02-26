from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Path, status

from src.api.routers import proposals as shared
from src.core.proposals import (
    ProposalApprovalsResponse,
    ProposalIdempotencyLookupResponse,
    ProposalLineageResponse,
    ProposalNotFoundError,
    ProposalSupportabilityConfigResponse,
    ProposalWorkflowService,
    ProposalWorkflowTimelineResponse,
)


@shared.router.get(
    "/rebalance/proposals/supportability/config",
    response_model=ProposalSupportabilityConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Supportability Configuration",
    description=(
        "Returns proposal supportability runtime configuration and backend initialization status "
        "for operational diagnostics without direct database access."
    ),
)
def get_proposal_supportability_config() -> ProposalSupportabilityConfigResponse:
    backend_error: Optional[str] = None
    backend_ready = True
    try:
        shared.proposals_config.build_repository()
    except RuntimeError as exc:
        backend_ready = False
        backend_error = str(exc)
    except (TypeError, ValueError):
        backend_ready = False
        backend_error = "PROPOSAL_POSTGRES_CONNECTION_FAILED"

    return ProposalSupportabilityConfigResponse(
        store_backend=shared._proposal_store_backend_name(),
        backend_ready=backend_ready,
        backend_init_error=backend_error,
        lifecycle_enabled=shared.env_flag("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", True),
        support_apis_enabled=shared.env_flag("PROPOSAL_SUPPORT_APIS_ENABLED", True),
        async_operations_enabled=shared.env_flag("PROPOSAL_ASYNC_OPERATIONS_ENABLED", True),
        store_evidence_bundle=shared.env_flag("PROPOSAL_STORE_EVIDENCE_BUNDLE", True),
        require_expected_state=shared.env_flag("PROPOSAL_REQUIRE_EXPECTED_STATE", True),
        allow_portfolio_id_change_on_new_version=shared.env_flag(
            "PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION",
            False,
        ),
        require_proposal_simulation_flag=shared.env_flag("PROPOSAL_REQUIRE_SIMULATION_FLAG", True),
    )


@shared.router.get(
    "/rebalance/proposals/{proposal_id}/workflow-events",
    response_model=ProposalWorkflowTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Workflow Timeline",
    description=(
        "Returns append-only workflow event timeline for investigation, supportability, and audit."
    ),
)
def get_proposal_workflow_timeline(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalWorkflowTimelineResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_workflow_timeline(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/proposals/{proposal_id}/approvals",
    response_model=ProposalApprovalsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Approvals",
    description=(
        "Returns approval/consent records for support investigations and workflow audit traces."
    ),
)
def get_proposal_approvals(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalApprovalsResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_approvals(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/proposals/{proposal_id}/lineage",
    response_model=ProposalLineageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Lineage",
    description=(
        "Returns immutable version lineage metadata with hashes "
        "for reproducibility and root-cause analysis."
    ),
)
def get_proposal_lineage(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalLineageResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_lineage(proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/proposals/idempotency/{idempotency_key}",
    response_model=ProposalIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Lookup Proposal Idempotency Mapping",
    description=(
        "Returns idempotency-to-proposal mapping for support and retry investigation workflows."
    ),
)
def get_proposal_idempotency_lookup(
    idempotency_key: Annotated[
        str,
        Path(
            description="Proposal create idempotency key.",
            examples=["proposal-create-idem-001"],
        ),
    ],
    service: Annotated[
        ProposalWorkflowService,
        Depends(shared.get_proposal_workflow_service),
    ],
) -> ProposalIdempotencyLookupResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_support_apis_enabled()
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
