from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.api.services.rebalance_operation_identity import create_batch_analysis_id
from src.api.services.rebalance_policy_pack_execution import resolve_execution_policy_pack_context
from src.api.services.rebalance_policy_pack_service import load_dpm_policy_pack_catalog
from src.core.rebalance.policy_packs import DpmPolicyPackDefinition


@dataclass(frozen=True)
class DpmBatchExecutionContext:
    batch_id: str
    policy_pack_definition: Optional[DpmPolicyPackDefinition]
    policy_resolution_enabled: bool
    policy_resolution_source: str
    selected_policy_pack_id: str | None


def build_batch_execution_context(
    *,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    tenant_id: Optional[str],
) -> DpmBatchExecutionContext:
    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="analyze",
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    return DpmBatchExecutionContext(
        batch_id=create_batch_analysis_id(),
        policy_pack_definition=policy_context.definition,
        policy_resolution_enabled=policy_context.resolution.enabled,
        policy_resolution_source=policy_context.resolution.source,
        selected_policy_pack_id=policy_context.resolution.selected_policy_pack_id,
    )


__all__ = ["DpmBatchExecutionContext", "build_batch_execution_context"]
