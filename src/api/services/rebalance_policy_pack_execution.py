from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from src.api.observability import record_policy_pack_resolution
from src.api.services.rebalance_policy_pack_service import (
    DpmPolicyPackCatalogUnavailableError,
    resolve_dpm_policy_pack,
)
from src.api.services.rebalance_simulation_errors import (
    DpmRebalancePolicyPackCatalogUnavailableError,
)
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
    resolve_policy_pack_definition,
)

PolicyPackCatalogLoader = Callable[[], dict[str, DpmPolicyPackDefinition]]


@dataclass(frozen=True)
class DpmExecutionPolicyPackContext:
    resolution: DpmEffectivePolicyPackResolution
    definition: Optional[DpmPolicyPackDefinition]


def resolve_selected_policy_pack_definition(
    *,
    policy_pack: DpmEffectivePolicyPackResolution,
    catalog_loader: PolicyPackCatalogLoader,
) -> Optional[DpmPolicyPackDefinition]:
    if policy_pack.selected_policy_pack_id is None:
        return None
    try:
        catalog = catalog_loader()
    except DpmPolicyPackCatalogUnavailableError as exc:
        raise DpmRebalancePolicyPackCatalogUnavailableError(exc.detail) from exc
    return resolve_policy_pack_definition(resolution=policy_pack, catalog=catalog)


def record_policy_resolution(
    *,
    surface: str,
    policy_pack: DpmEffectivePolicyPackResolution,
) -> None:
    record_policy_pack_resolution(
        surface=surface,
        enabled=str(policy_pack.enabled).lower(),
        source=policy_pack.source.lower(),
        selected=str(policy_pack.selected_policy_pack_id is not None).lower(),
    )


def resolve_execution_policy_pack_context(
    *,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str],
    tenant_id: Optional[str],
    surface: str,
    catalog_loader: PolicyPackCatalogLoader,
    load_definition: bool = True,
) -> DpmExecutionPolicyPackContext:
    policy_pack = resolve_dpm_policy_pack(
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=tenant_default_policy_pack_id,
        tenant_id=tenant_id,
    )
    record_policy_resolution(surface=surface, policy_pack=policy_pack)
    definition = (
        resolve_selected_policy_pack_definition(
            policy_pack=policy_pack,
            catalog_loader=catalog_loader,
        )
        if load_definition
        else None
    )
    return DpmExecutionPolicyPackContext(resolution=policy_pack, definition=definition)


__all__ = [
    "DpmExecutionPolicyPackContext",
    "PolicyPackCatalogLoader",
    "record_policy_resolution",
    "resolve_execution_policy_pack_context",
    "resolve_selected_policy_pack_definition",
]
