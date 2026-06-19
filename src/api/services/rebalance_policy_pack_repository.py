from __future__ import annotations

import os
from typing import cast

from src.core.common.postgres_errors import (
    postgres_connection_exception_types as common_postgres_connection_exception_types,
)
from src.core.rebalance.policy_pack_repository import DpmPolicyPackRepository
from src.infrastructure.dpm_policy_packs import (
    PostgresDpmPolicyPackRepository,
)


def build_policy_pack_repository() -> DpmPolicyPackRepository:
    dsn = os.getenv(
        "DPM_POLICY_PACK_POSTGRES_DSN", os.getenv("DPM_SUPPORTABILITY_POSTGRES_DSN", "")
    ).strip()
    if not dsn:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_DSN_REQUIRED")
    try:
        return cast(DpmPolicyPackRepository, PostgresDpmPolicyPackRepository(dsn=dsn))
    except RuntimeError:
        raise
    except postgres_connection_exception_types() as exc:
        raise RuntimeError("DPM_POLICY_PACK_POSTGRES_CONNECTION_FAILED") from exc


def postgres_connection_exception_types() -> tuple[type[BaseException], ...]:
    return common_postgres_connection_exception_types()


__all__ = [
    "build_policy_pack_repository",
    "PostgresDpmPolicyPackRepository",
    "postgres_connection_exception_types",
]
