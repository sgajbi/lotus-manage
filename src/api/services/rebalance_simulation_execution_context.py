from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Optional

from src.api.request_models import RebalanceRequest
from src.api.services.rebalance_async_config import env_flag
from src.api.services.rebalance_operation_identity import resolve_rebalance_correlation_id
from src.api.services.rebalance_policy_pack_execution import resolve_execution_policy_pack_context
from src.api.services.rebalance_policy_pack_service import load_dpm_policy_pack_catalog
from src.core.common.canonical import hash_canonical_payload
from src.core.rebalance.policy_packs import (
    DpmPolicyPackDefinition,
    resolve_policy_pack_replay_enabled,
)

RequestHasher = Callable[[object], str]


@dataclass(frozen=True)
class DpmSimulationExecutionContext:
    request_hash: str
    correlation_id: str
    policy_pack_definition: Optional[DpmPolicyPackDefinition]
    replay_enabled: bool
    policy_resolution_enabled: bool
    policy_resolution_source: str
    selected_policy_pack_id: str | None


def build_simulation_execution_context(
    *,
    request: RebalanceRequest,
    correlation_id: Optional[str],
    policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    tenant_id: Optional[str],
    request_hasher: RequestHasher = hash_canonical_payload,
) -> DpmSimulationExecutionContext:
    policy_context = resolve_execution_policy_pack_context(
        request_policy_pack_id=policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
        surface="simulate",
        catalog_loader=load_dpm_policy_pack_catalog,
    )
    return DpmSimulationExecutionContext(
        request_hash=request_hasher(request.model_dump(mode="json")),
        correlation_id=resolve_rebalance_correlation_id(correlation_id),
        policy_pack_definition=policy_context.definition,
        replay_enabled=resolve_policy_pack_replay_enabled(
            default_replay_enabled=env_flag("DPM_IDEMPOTENCY_REPLAY_ENABLED", True),
            policy_pack=policy_context.definition,
        ),
        policy_resolution_enabled=policy_context.resolution.enabled,
        policy_resolution_source=policy_context.resolution.source,
        selected_policy_pack_id=policy_context.resolution.selected_policy_pack_id,
    )


__all__ = [
    "DpmSimulationExecutionContext",
    "RequestHasher",
    "build_simulation_execution_context",
]
