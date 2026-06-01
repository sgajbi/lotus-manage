from __future__ import annotations

import os
from typing import Optional, cast

from src.core.common.capabilities import psycopg_error_type
from src.core.rebalance.policy_pack_repository import DpmPolicyPackRepository
from src.core.rebalance.policy_packs import (
    DpmEffectivePolicyPackResolution,
    DpmPolicyPackDefinition,
    resolve_effective_policy_pack,
)
from src.core.rebalance.tenant_policy_packs import build_tenant_policy_pack_resolver
from src.infrastructure.dpm_policy_packs import (
    PostgresDpmPolicyPackRepository,
)


class DpmPolicyPackCatalogUnavailableError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_dpm_policy_pack(
    *,
    request_policy_pack_id: Optional[str],
    tenant_default_policy_pack_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> DpmEffectivePolicyPackResolution:
    resolved_tenant_default_policy_pack_id = tenant_default_policy_pack_id
    if resolved_tenant_default_policy_pack_id is None:
        tenant_policy_pack_resolver = build_tenant_policy_pack_resolver(
            enabled=env_flag("DPM_TENANT_POLICY_PACK_RESOLUTION_ENABLED", False),
            mapping_json=os.getenv("DPM_TENANT_POLICY_PACK_MAP_JSON"),
        )
        resolved_tenant_default_policy_pack_id = tenant_policy_pack_resolver.resolve(
            tenant_id=tenant_id
        )
    return resolve_effective_policy_pack(
        policy_packs_enabled=env_flag("DPM_POLICY_PACKS_ENABLED", False),
        request_policy_pack_id=request_policy_pack_id,
        tenant_default_policy_pack_id=resolved_tenant_default_policy_pack_id,
        global_default_policy_pack_id=os.getenv("DPM_DEFAULT_POLICY_PACK_ID"),
    )


def load_dpm_policy_pack_catalog() -> dict[str, DpmPolicyPackDefinition]:
    repository = get_policy_pack_repository()
    items = repository.list_policy_packs()
    return {item.policy_pack_id: item for item in items}


def policy_pack_catalog_backend_name() -> str:
    value = os.getenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES").strip().upper()
    if value != "POSTGRES":
        raise RuntimeError("DPM_POLICY_PACK_CATALOG_BACKEND_UNSUPPORTED")
    return value


def policy_pack_postgres_dsn() -> str:
    return os.getenv(
        "DPM_POLICY_PACK_POSTGRES_DSN",
        os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", ""),
    ).strip()


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [
        ConnectionError,
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
    ]
    error_type = psycopg_error_type()
    if error_type is not None:
        types.append(error_type)
    return tuple(types)


def build_policy_pack_repository() -> DpmPolicyPackRepository:
    _ = policy_pack_catalog_backend_name()
    dsn = policy_pack_postgres_dsn()
    if not dsn:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED")
    try:
        return cast(DpmPolicyPackRepository, PostgresDpmPolicyPackRepository(dsn=dsn))
    except RuntimeError:
        raise
    except postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED") from exc


def policy_pack_catalog_error_detail(detail: str) -> str:
    if detail == "DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED":
        return detail
    return "DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED"


def get_policy_pack_repository() -> DpmPolicyPackRepository:
    try:
        return build_policy_pack_repository()
    except RuntimeError as exc:
        raise DpmPolicyPackCatalogUnavailableError(
            policy_pack_catalog_error_detail(str(exc))
        ) from exc


def reset_dpm_policy_pack_repository_for_tests() -> None:
    # no cached repository state is maintained in POSTGRES-only runtime mode
    return None


__all__ = [
    "DpmPolicyPackCatalogUnavailableError",
    "build_policy_pack_repository",
    "get_policy_pack_repository",
    "load_dpm_policy_pack_catalog",
    "policy_pack_catalog_backend_name",
    "policy_pack_catalog_error_detail",
    "policy_pack_postgres_dsn",
    "postgres_connection_exception_types",
    "reset_dpm_policy_pack_repository_for_tests",
    "resolve_dpm_policy_pack",
]
