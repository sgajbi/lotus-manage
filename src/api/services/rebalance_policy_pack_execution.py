from collections.abc import Callable
from typing import Optional

from src.api.observability import record_policy_pack_resolution
from src.api.services.rebalance_policy_pack_service import (
    DpmPolicyPackCatalogUnavailableError,
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


__all__ = [
    "PolicyPackCatalogLoader",
    "record_policy_resolution",
    "resolve_selected_policy_pack_definition",
]
