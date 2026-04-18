import json
from typing import Optional, Protocol


class DpmTenantPolicyPackResolver(Protocol):
    def resolve(self, *, tenant_id: Optional[str]) -> Optional[str]:
        """Resolve tenant-default policy-pack id for a tenant context."""


class DisabledDpmTenantPolicyPackResolver:
    def resolve(self, *, tenant_id: Optional[str]) -> Optional[str]:
        _ = tenant_id
        return None


class StaticMapDpmTenantPolicyPackResolver:
    def __init__(self, tenant_policy_pack_map: dict[str, str]) -> None:
        self._tenant_policy_pack_map = tenant_policy_pack_map

    def resolve(self, *, tenant_id: Optional[str]) -> Optional[str]:
        normalized_tenant_id = _normalize_optional_value(tenant_id)
        if normalized_tenant_id is None:
            return None
        return self._tenant_policy_pack_map.get(normalized_tenant_id)


def parse_tenant_policy_pack_map(mapping_json: Optional[str]) -> dict[str, str]:
    normalized_json = (mapping_json or "").strip()
    if not normalized_json:
        return {}
    try:
        raw = json.loads(normalized_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}
    mapping: dict[str, str] = {}
    for tenant_id, policy_pack_id in raw.items():
        if not isinstance(policy_pack_id, str):
            continue
        normalized_tenant_id = _normalize_optional_value(tenant_id)
        normalized_policy_pack_id = _normalize_optional_value(policy_pack_id)
        if normalized_tenant_id is None or normalized_policy_pack_id is None:
            continue
        mapping[normalized_tenant_id] = normalized_policy_pack_id
    return mapping


def build_tenant_policy_pack_resolver(
    *,
    enabled: bool,
    mapping_json: Optional[str],
) -> DpmTenantPolicyPackResolver:
    if not enabled:
        return DisabledDpmTenantPolicyPackResolver()
    return StaticMapDpmTenantPolicyPackResolver(
        tenant_policy_pack_map=parse_tenant_policy_pack_map(mapping_json)
    )


def _normalize_optional_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
