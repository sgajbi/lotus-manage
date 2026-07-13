from __future__ import annotations

import os

from src.api.enterprise_readiness import load_capability_rules
from src.api.services.rebalance_policy_pack_service import (
    policy_pack_catalog_backend_name,
)
from src.api.services.rebalance_run_support_config import (
    supportability_postgres_dsn,
    supportability_store_backend_name,
)

_PRODUCTION_PROFILE = "PRODUCTION"
_LOCAL_PROFILE = "LOCAL"


def app_persistence_profile_name() -> str:
    profile = os.getenv("APP_PERSISTENCE_PROFILE", _LOCAL_PROFILE).strip().upper()
    return _PRODUCTION_PROFILE if profile == _PRODUCTION_PROFILE else _LOCAL_PROFILE


def policy_pack_catalog_required_in_profile() -> bool:
    return _env_flag("DPM_POLICY_PACKS_ENABLED", False) or _env_flag(
        "DPM_POLICY_PACK_ADMIN_APIS_ENABLED", False
    )


def validate_persistence_profile_guardrails() -> None:
    if app_persistence_profile_name() != _PRODUCTION_PROFILE:
        return
    guardrail_error = _persistence_profile_guardrail_error()
    if guardrail_error is not None:
        raise RuntimeError(guardrail_error)


def _persistence_profile_guardrail_error() -> str | None:
    if supportability_store_backend_name() != "POSTGRES":
        return "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES"
    if not supportability_postgres_dsn():
        return "PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN"
    authz_error = _production_authz_guardrail_error()
    if authz_error is not None:
        return authz_error
    return _policy_pack_catalog_guardrail_error(required=policy_pack_catalog_required_in_profile())


def _production_authz_guardrail_error() -> str | None:
    if not _env_flag("ENTERPRISE_ENFORCE_AUTHZ", False):
        return "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_AUTHZ"
    if not os.getenv("ENTERPRISE_PRIMARY_KEY_ID", "").strip():
        return "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_PRIMARY_KEY_ID"
    if not load_capability_rules():
        return "PERSISTENCE_PROFILE_REQUIRES_ENTERPRISE_CAPABILITY_RULES"
    return None


def _policy_pack_catalog_guardrail_error(*, required: bool) -> str | None:
    if not required:
        return None
    if policy_pack_catalog_backend_name() != "POSTGRES":
        return "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES"
    if not _explicit_policy_pack_postgres_dsn():
        return "PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN"
    return None


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _explicit_policy_pack_postgres_dsn() -> str:
    return os.getenv("DPM_POLICY_PACK_POSTGRES_DSN", "").strip()
