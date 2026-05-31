from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunArtifactResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/artifact",
    response_model=DpmRunArtifactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Artifact by Run Id",
    description=(
        "Returns the deterministic supportability artifact for a discretionary mandate rebalance "
        "run. Use this endpoint when an operator, auditor, or downstream incident tool needs the "
        "artifact payload only; use the support-bundle endpoint when workflow, lineage, async, or "
        "idempotency context is also required. The artifact is resolved using configured artifact "
        "mode (`DERIVED` or `PERSISTED`) and unsupported query parameters are rejected."
    ),
    responses={
        200: {"description": "Deterministic run artifact for audit and replay support."},
        404: {"description": "Support APIs/artifacts disabled or run id not found."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_artifact_by_run_id(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunArtifactResponse:
    shared._assert_support_apis_enabled()
    shared._assert_artifacts_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_run_artifact(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
