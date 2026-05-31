from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/runs/by-request-hash/{request_hash}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Request Hash",
    description=(
        "Returns the latest discretionary mandate rebalance run mapped to one canonical request "
        "hash. Use this endpoint for retry, replay, or support investigations where the caller "
        "has the `sha256:` request fingerprint but not the run id. URL-encode the request hash "
        "when calling through a path segment. Use `/rebalance/runs` for filtered inventory search "
        "and support-bundle routes when broader investigation evidence is required. This endpoint "
        "does not accept query parameters."
    ),
    responses={
        200: {"description": "Latest run supportability record mapped to the request hash."},
        404: {"description": "Support APIs disabled or no run is mapped to the request hash."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_by_request_hash(
    request: Request,
    request_hash: Annotated[
        str,
        Path(
            description="Canonical request hash persisted for run supportability record.",
            examples=["sha256:abc123"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_run_by_request_hash(request_hash=request_hash)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
