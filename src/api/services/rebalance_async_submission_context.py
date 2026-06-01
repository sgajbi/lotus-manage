from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from src.api.services.rebalance_async_config import resolve_async_execution_mode
from src.api.services.rebalance_async_submission_payload import build_analyze_async_request_json
from src.api.services.rebalance_policy_pack_execution import (
    PolicyPackCatalogLoader,
    resolve_execution_policy_pack_context,
)
from src.api.services.rebalance_policy_pack_service import load_dpm_policy_pack_catalog
from src.api.services.rebalance_run_support_service import (
    DpmRunSupportServiceUnavailableError,
    get_dpm_run_support_service,
)
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncOperationSupportUnavailableError,
)
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.models import BatchRebalanceRequest
from src.core.rebalance_runs import DpmRunSupportService

SupportServiceFactory = Callable[[], DpmRunSupportService]


@dataclass(frozen=True)
class DpmAsyncSubmissionContext:
    service: DpmRunSupportService
    request_json: dict[str, object]
    execution_mode: str
    policy_resolution_enabled: bool
    policy_resolution_source: str
    selected_policy_pack_id: str | None


def build_async_submission_context(
    *,
    request: BatchRebalanceRequest,
    policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    tenant_id: Optional[str],
    source_context: Optional[DpmResolvedSourceContext],
    support_service_factory: SupportServiceFactory = get_dpm_run_support_service,
    catalog_loader: PolicyPackCatalogLoader = load_dpm_policy_pack_catalog,
) -> DpmAsyncSubmissionContext:
    try:
        service = support_service_factory()
    except DpmRunSupportServiceUnavailableError as exc:
        raise DpmRebalanceAsyncOperationSupportUnavailableError(exc.detail) from exc
    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="analyze_async",
        catalog_loader=catalog_loader,
        load_definition=False,
    )
    return DpmAsyncSubmissionContext(
        service=service,
        request_json=build_analyze_async_request_json(
            request=request,
            policy_pack_id=policy_pack_id,
            tenant_default_policy_pack_id=tenant_default_policy_pack_id,
            tenant_id=tenant_id,
            source_context=source_context,
        ),
        execution_mode=resolve_async_execution_mode(),
        policy_resolution_enabled=policy_context.resolution.enabled,
        policy_resolution_source=policy_context.resolution.source,
        selected_policy_pack_id=policy_context.resolution.selected_policy_pack_id,
    )


__all__ = [
    "DpmAsyncSubmissionContext",
    "SupportServiceFactory",
    "build_async_submission_context",
]
