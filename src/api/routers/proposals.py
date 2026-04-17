import importlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status

from src.api.routers import proposals_config
from src.api.routers.runtime_utils import (
    assert_feature_enabled,
    env_flag,
    normalize_backend_init_error,
)
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.repository import ProposalRepository

router = APIRouter(tags=["Advisory Proposal Lifecycle"])

_REPOSITORY: Optional[ProposalRepository] = None
_SERVICE: Optional[ProposalWorkflowService] = None


def _reject_unexpected_query_params(request: Request, *, allowed_params: set[str]) -> None:
    for param_name in request.query_params.keys():
        if param_name not in allowed_params:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"UNSUPPORTED_QUERY_PARAMETER: {param_name} not supported for this endpoint",
            )


def _proposal_store_backend_name() -> str:
    return proposals_config.proposal_store_backend_name()


def _backend_init_error_detail(detail: str) -> str:
    return normalize_backend_init_error(
        detail=detail,
        required_detail="PROPOSAL_POSTGRES_DSN_REQUIRED",
        fallback_detail="PROPOSAL_POSTGRES_CONNECTION_FAILED",
    )


def get_proposal_workflow_service() -> ProposalWorkflowService:
    global _REPOSITORY
    global _SERVICE
    if _REPOSITORY is None:
        try:
            _REPOSITORY = proposals_config.build_repository()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_backend_init_error_detail(str(exc)),
            ) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PROPOSAL_POSTGRES_CONNECTION_FAILED",
            ) from exc
    if _SERVICE is None:
        _SERVICE = ProposalWorkflowService(
            repository=_REPOSITORY,
            store_evidence_bundle=env_flag("PROPOSAL_STORE_EVIDENCE_BUNDLE", True),
            require_expected_state=env_flag("PROPOSAL_REQUIRE_EXPECTED_STATE", True),
            allow_portfolio_id_change_on_new_version=env_flag(
                "PROPOSAL_ALLOW_PORTFOLIO_CHANGE_ON_NEW_VERSION",
                False,
            ),
            require_proposal_simulation_flag=env_flag("PROPOSAL_REQUIRE_SIMULATION_FLAG", True),
        )
    return _SERVICE


def get_proposal_repository() -> ProposalRepository:
    global _REPOSITORY
    if _REPOSITORY is None:
        try:
            _REPOSITORY = proposals_config.build_repository()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_backend_init_error_detail(str(exc)),
            ) from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PROPOSAL_POSTGRES_CONNECTION_FAILED",
            ) from exc
    return _REPOSITORY


def reset_proposal_workflow_service_for_tests() -> None:
    global _REPOSITORY
    global _SERVICE
    _REPOSITORY = None
    _SERVICE = None


def _assert_lifecycle_enabled() -> None:
    assert_feature_enabled(
        name="PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED",
        default=True,
        detail="PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED",
    )


def _assert_support_apis_enabled() -> None:
    assert_feature_enabled(
        name="PROPOSAL_SUPPORT_APIS_ENABLED",
        default=True,
        detail="PROPOSAL_SUPPORT_APIS_DISABLED",
    )


def _assert_async_operations_enabled() -> None:
    assert_feature_enabled(
        name="PROPOSAL_ASYNC_OPERATIONS_ENABLED",
        default=True,
        detail="PROPOSAL_ASYNC_OPERATIONS_DISABLED",
    )


importlib.import_module("src.api.routers.proposals_lifecycle_routes")
importlib.import_module("src.api.routers.proposals_async_routes")
importlib.import_module("src.api.routers.proposals_support_routes")

__all__ = [
    "env_flag",
    "proposals_config",
    "router",
    "_assert_async_operations_enabled",
    "_assert_lifecycle_enabled",
    "_assert_support_apis_enabled",
    "_proposal_store_backend_name",
    "get_proposal_repository",
    "get_proposal_workflow_service",
    "reset_proposal_workflow_service_for_tests",
]
