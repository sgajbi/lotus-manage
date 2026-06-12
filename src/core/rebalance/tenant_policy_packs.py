import json
from typing import Any, Optional, Protocol


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
    raw_mapping = _load_tenant_policy_pack_json_map(mapping_json)
    if raw_mapping is None:
        return {}
    mapping: dict[str, str] = {}
    for tenant_id, policy_pack_id in raw_mapping.items():
        row = _tenant_policy_pack_mapping_row(tenant_id=tenant_id, policy_pack_id=policy_pack_id)
        if row is not None:
            normalized_tenant_id, normalized_policy_pack_id = row
            mapping[normalized_tenant_id] = normalized_policy_pack_id
    return mapping


def _load_tenant_policy_pack_json_map(mapping_json: Optional[str]) -> dict[str, Any] | None:
    normalized_json = (mapping_json or "").strip()
    if not normalized_json:
        return None
    try:
        raw = json.loads(normalized_json)
    except json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _tenant_policy_pack_mapping_row(
    *, tenant_id: Any, policy_pack_id: Any
) -> tuple[str, str] | None:
    if not isinstance(tenant_id, str) or not isinstance(policy_pack_id, str):
        return None
    normalized_tenant_id = _normalize_optional_value(tenant_id)
    normalized_policy_pack_id = _normalize_optional_value(policy_pack_id)
    if normalized_tenant_id is None or normalized_policy_pack_id is None:
        return None
    return normalized_tenant_id, normalized_policy_pack_id


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
