from __future__ import annotations

import os

from src.api.routers.dpm_policy_packs import (
    policy_pack_catalog_backend_name,
)
from src.api.routers.dpm_runs_config import (
    supportability_postgres_dsn,
    supportability_store_backend_name,
)
from src.api.routers.proposals_config import (
    proposal_postgres_dsn,
    proposal_store_backend_name,
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
    if supportability_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES")
    if not supportability_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_DPM_POSTGRES_DSN")
    if proposal_store_backend_name() != "POSTGRES":
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES")
    if not proposal_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_ADVISORY_POSTGRES_DSN")
    if (
        policy_pack_catalog_required_in_profile()
        and policy_pack_catalog_backend_name() != "POSTGRES"
    ):
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES")
    if policy_pack_catalog_required_in_profile() and not _explicit_policy_pack_postgres_dsn():
        raise RuntimeError("PERSISTENCE_PROFILE_REQUIRES_POLICY_PACK_POSTGRES_DSN")


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _explicit_policy_pack_postgres_dsn() -> str:
    return os.getenv("DPM_POLICY_PACK_POSTGRES_DSN", "").strip()
