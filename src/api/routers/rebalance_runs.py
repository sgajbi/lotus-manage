import importlib
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from src.api.routers import rebalance_runs_config
from src.api.routers.runtime_utils import assert_feature_enabled, normalize_backend_init_error
from src.core.rebalance_runs import (
    DpmRunArtifactResponse,
    DpmRunIdempotencyHistoryResponse,
    DpmRunIdempotencyLookupResponse,
    DpmRunListResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportBundleResponse,
    DpmRunSupportService,
    DpmSupportabilitySummaryResponse,
)
from src.core.rebalance_runs.repository import DpmRunRepository
from src.core.models import RebalanceResult

router = APIRouter(tags=["lotus-manage Run Supportability"])

_REPOSITORY = None
_SERVICE: Optional[DpmRunSupportService] = None


def _backend_init_error_detail(detail: str) -> str:
    return normalize_backend_init_error(
        detail=detail,
        required_detail="DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED",
        fallback_detail="DPM_SUPPORTABILITY_POSTGRES_CONNECTION_FAILED",
    )


def _assert_support_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORT_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORT_APIS_DISABLED",
    )


def _assert_async_operations_enabled() -> None:
    assert_feature_enabled(
        name="DPM_ASYNC_OPERATIONS_ENABLED",
        default=True,
        detail="DPM_ASYNC_OPERATIONS_DISABLED",
    )


def _assert_artifacts_enabled() -> None:
    assert_feature_enabled(
        name="DPM_ARTIFACTS_ENABLED",
        default=True,
        detail="DPM_ARTIFACTS_DISABLED",
    )


def _assert_workflow_enabled() -> None:
    assert_feature_enabled(
        name="DPM_WORKFLOW_ENABLED",
        default=False,
        detail="DPM_WORKFLOW_DISABLED",
    )


def _assert_lineage_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_LINEAGE_APIS_ENABLED",
        default=False,
        detail="DPM_LINEAGE_APIS_DISABLED",
    )


def _assert_idempotency_history_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED",
        default=False,
        detail="DPM_IDEMPOTENCY_HISTORY_APIS_DISABLED",
    )


def _assert_supportability_summary_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORTABILITY_SUMMARY_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORTABILITY_SUMMARY_APIS_DISABLED",
    )


def _assert_support_bundle_apis_enabled() -> None:
    assert_feature_enabled(
        name="DPM_SUPPORT_BUNDLE_APIS_ENABLED",
        default=True,
        detail="DPM_SUPPORT_BUNDLE_APIS_DISABLED",
    )


def _supportability_store_backend_name() -> str:
    return rebalance_runs_config.supportability_store_backend_name()


def _reject_unexpected_query_params(
    request: Request,
    *,
    allowed_params: set[str],
) -> None:
    unexpected = sorted(name for name in request.query_params if name not in allowed_params)
    if unexpected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "UNSUPPORTED_QUERY_PARAMETER: "
                + ", ".join(unexpected)
                + " not supported for this endpoint"
            ),
        )


def _build_repository() -> DpmRunRepository:
    return rebalance_runs_config.build_repository()


def get_dpm_run_support_service() -> DpmRunSupportService:
    global _REPOSITORY
    global _SERVICE
    if _REPOSITORY is None:
        try:
            _REPOSITORY = _build_repository()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_backend_init_error_detail(str(exc)),
            ) from exc
    if _SERVICE is None:
        _SERVICE = DpmRunSupportService(
            repository=_REPOSITORY,
            async_operation_ttl_seconds=rebalance_runs_config.env_int(
                "DPM_ASYNC_OPERATIONS_TTL_SECONDS",
                86400,
            ),
            supportability_retention_days=rebalance_runs_config.env_non_negative_int(
                "DPM_SUPPORTABILITY_RETENTION_DAYS",
                0,
            ),
            workflow_enabled=rebalance_runs_config.env_flag("DPM_WORKFLOW_ENABLED", False),
            workflow_requires_review_for_statuses=rebalance_runs_config.env_csv_set(
                "DPM_WORKFLOW_REQUIRES_REVIEW_FOR_STATUSES",
                {"PENDING_REVIEW"},
            ),
            artifact_store_mode=rebalance_runs_config.artifact_store_mode(),
        )
    return _SERVICE


def record_dpm_run_for_support(
    *,
    result: RebalanceResult,
    request_hash: str,
    portfolio_id: str,
    idempotency_key: Optional[str],
) -> None:
    service = get_dpm_run_support_service()
    service.record_run(
        result=result,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
        idempotency_key=idempotency_key,
    )


def reset_dpm_run_support_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    _REPOSITORY = None
    _SERVICE = None


@router.get(
    "/rebalance/runs",
    response_model=DpmRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Runs",
    description=(
        "Returns paginated lotus-manage runs filtered by creation time range, run status, "
        "canonical request hash, and portfolio id. Use the canonical query parameter "
        "`status_filter` for status filtering; unsupported aliases are rejected."
    ),
    responses={
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def list_runs(
    request: Request,
    created_from: Annotated[
        Optional[datetime],
        Query(
            description="Run creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            description="Run creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Query(
            description="Optional run status filter.",
            examples=["READY"],
        ),
    ] = None,
    request_hash: Annotated[
        Optional[str],
        Query(
            description="Optional canonical request hash filter.",
            examples=["sha256:abc123"],
        ),
    ] = None,
    portfolio_id: Annotated[
        Optional[str],
        Query(
            description="Optional portfolio identifier filter.",
            examples=["pf_123"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["rr_abc12345"],
        ),
    ] = None,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunListResponse:
    _assert_support_apis_enabled()
    _reject_unexpected_query_params(
        request,
        allowed_params={
            "created_from",
            "created_to",
            "status_filter",
            "request_hash",
            "portfolio_id",
            "limit",
            "cursor",
        },
    )
    return service.list_runs(
        created_from=created_from,
        created_to=created_to,
        status=status_filter,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
        limit=limit,
        cursor=cursor,
    )


@router.get(
    "/rebalance/supportability/summary",
    response_model=DpmSupportabilitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Supportability Summary",
    description=(
        "Returns supportability storage summary metrics (runs, operations, status counts, "
        "and temporal bounds) for operational investigation without direct database access. "
        "Use this endpoint when operators need a store-wide health and retention snapshot; "
        "it does not accept ad hoc query filters."
    ),
    responses={
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def get_dpm_supportability_summary(
    request: Request,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmSupportabilitySummaryResponse:
    _assert_support_apis_enabled()
    _assert_supportability_summary_apis_enabled()
    _reject_unexpected_query_params(request, allowed_params=set())
    return service.get_supportability_summary(
        store_backend=_supportability_store_backend_name(),
        retention_days=rebalance_runs_config.env_non_negative_int(
            "DPM_SUPPORTABILITY_RETENTION_DAYS", 0
        ),
    )


@router.get(
    "/rebalance/runs/by-correlation/{correlation_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Correlation Id",
    description="Returns the latest lotus-manage run mapped to a correlation id for investigation.",
)
def get_run_by_correlation(
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_run_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/by-request-hash/{request_hash}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Request Hash",
    description="Returns the latest lotus-manage run mapped to a canonical request hash for investigation.",
)
def get_run_by_request_hash(
    request_hash: Annotated[
        str,
        Path(
            description="Canonical request hash persisted for run supportability record.",
            examples=["sha256:abc123"],
        ),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_run_by_request_hash(request_hash=request_hash)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/idempotency/{idempotency_key}",
    response_model=DpmRunIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Idempotency Mapping",
    description="Returns lotus-manage idempotency key to run mapping for support investigations.",
)
def get_run_idempotency_lookup(
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunIdempotencyLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/idempotency/{idempotency_key}/history",
    response_model=DpmRunIdempotencyHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Idempotency History",
    description=(
        "Returns append-only run mapping history for one idempotency key, including request hash "
        "and correlation context for support investigations."
    ),
)
def get_run_idempotency_history(
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunIdempotencyHistoryResponse:
    _assert_support_apis_enabled()
    _assert_idempotency_history_apis_enabled()
    try:
        return service.get_idempotency_history(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Run Id",
    description="Returns one lotus-manage run payload and lineage metadata by run id.",
)
def get_run_by_run_id(
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    _assert_support_apis_enabled()
    try:
        return service.get_run(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle",
    description=(
        "Returns an aggregated supportability bundle for one run, including run payload, "
        "lineage, workflow history, optional deterministic artifact, and optional mapped async "
        "operation/idempotency history."
    ),
)
def get_dpm_run_support_bundle(
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    include_artifact: Annotated[
        bool,
        Query(
            description="Whether to include deterministic run artifact payload in response.",
            examples=[True],
        ),
    ] = True,
    include_async_operation: Annotated[
        bool,
        Query(
            description="Whether to include async operation mapped by run correlation id.",
            examples=[True],
        ),
    ] = True,
    include_idempotency_history: Annotated[
        bool,
        Query(
            description=(
                "Whether to include idempotency mapping history when run has idempotency key."
            ),
            examples=[True],
        ),
    ] = True,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    _assert_support_apis_enabled()
    _assert_support_bundle_apis_enabled()
    try:
        return service.get_run_support_bundle(
            rebalance_run_id=rebalance_run_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Correlation Id",
    description=(
        "Returns aggregated supportability bundle for run resolved by correlation id, "
        "including optional artifact, async operation, and idempotency history."
    ),
)
def get_dpm_run_support_bundle_by_correlation(
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    include_artifact: Annotated[
        bool,
        Query(
            description="Whether to include deterministic run artifact payload in response.",
            examples=[True],
        ),
    ] = True,
    include_async_operation: Annotated[
        bool,
        Query(
            description="Whether to include async operation mapped by run correlation id.",
            examples=[True],
        ),
    ] = True,
    include_idempotency_history: Annotated[
        bool,
        Query(
            description=(
                "Whether to include idempotency mapping history when run has idempotency key."
            ),
            examples=[True],
        ),
    ] = True,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    _assert_support_apis_enabled()
    _assert_support_bundle_apis_enabled()
    try:
        return service.get_run_support_bundle_by_correlation(
            correlation_id=correlation_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/idempotency/{idempotency_key}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Idempotency Key",
    description=(
        "Returns aggregated supportability bundle for run resolved by idempotency key mapping, "
        "including optional artifact, async operation, and idempotency history."
    ),
)
def get_dpm_run_support_bundle_by_idempotency(
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    include_artifact: Annotated[
        bool,
        Query(
            description="Whether to include deterministic run artifact payload in response.",
            examples=[True],
        ),
    ] = True,
    include_async_operation: Annotated[
        bool,
        Query(
            description="Whether to include async operation mapped by run correlation id.",
            examples=[True],
        ),
    ] = True,
    include_idempotency_history: Annotated[
        bool,
        Query(
            description=(
                "Whether to include idempotency mapping history when run has idempotency key."
            ),
            examples=[True],
        ),
    ] = True,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    _assert_support_apis_enabled()
    _assert_support_bundle_apis_enabled()
    try:
        return service.get_run_support_bundle_by_idempotency(
            idempotency_key=idempotency_key,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/by-operation/{operation_id}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Operation Id",
    description=(
        "Returns aggregated supportability bundle for run resolved by asynchronous operation id, "
        "including optional artifact, async operation, and idempotency history."
    ),
)
def get_dpm_run_support_bundle_by_operation(
    operation_id: Annotated[
        str,
        Path(
            description="Asynchronous operation identifier.",
            examples=["dop_001"],
        ),
    ],
    include_artifact: Annotated[
        bool,
        Query(
            description="Whether to include deterministic run artifact payload in response.",
            examples=[True],
        ),
    ] = True,
    include_async_operation: Annotated[
        bool,
        Query(
            description="Whether to include async operation mapped by run correlation id.",
            examples=[True],
        ),
    ] = True,
    include_idempotency_history: Annotated[
        bool,
        Query(
            description=(
                "Whether to include idempotency mapping history when run has idempotency key."
            ),
            examples=[True],
        ),
    ] = True,
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    _assert_support_apis_enabled()
    _assert_support_bundle_apis_enabled()
    try:
        return service.get_run_support_bundle_by_operation(
            operation_id=operation_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/rebalance/runs/{rebalance_run_id}/artifact",
    response_model=DpmRunArtifactResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Artifact by Run Id",
    description=(
        "Returns deterministic run artifact from supportability run data using configured "
        "artifact mode (`DERIVED` or `PERSISTED`)."
    ),
    responses={
        404: {"description": "Support APIs/artifacts disabled or run id not found."},
    },
)
def get_run_artifact_by_run_id(
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmRunArtifactResponse:
    _assert_support_apis_enabled()
    _assert_artifacts_enabled()
    try:
        return service.get_run_artifact(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


importlib.import_module("src.api.routers.rebalance_runs_operations_routes")
importlib.import_module("src.api.routers.rebalance_runs_workflow_routes")

__all__ = [
    "Depends",
    "datetime",
    "get_dpm_run_support_service",
    "record_dpm_run_for_support",
    "reset_dpm_run_support_service_for_tests",
    "router",
    "_assert_artifacts_enabled",
    "_assert_async_operations_enabled",
    "_assert_idempotency_history_apis_enabled",
    "_assert_lineage_apis_enabled",
    "_assert_support_apis_enabled",
    "_assert_support_bundle_apis_enabled",
    "_assert_supportability_summary_apis_enabled",
    "_assert_workflow_enabled",
]
