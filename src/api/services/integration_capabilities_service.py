from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime

from typing import Any

EnvGetter = Callable[[str], str | None]


def env_bool(name: str, default: bool, *, env_get: EnvGetter) -> bool:
    value = env_get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def supported_input_modes(
    *,
    stateful_enabled: bool,
    stateless_enabled: bool,
) -> list[str]:
    supported_modes: list[str] = []
    if stateful_enabled:
        supported_modes.append("stateful")
    if stateless_enabled:
        supported_modes.append("stateless")
    return supported_modes


def stateful_execution_publishable(*, env_get: EnvGetter) -> bool:
    resolver_path_template = (env_get("DPM_CORE_RESOLVER_PATH_TEMPLATE") or "").strip()
    uses_legacy_monolithic_resolver = (
        bool(resolver_path_template) and "dpm-execution-context" in resolver_path_template
    )
    return (
        env_bool("DPM_CAP_INPUT_MODE_PORTFOLIO_ID_ENABLED", False, env_get=env_get)
        and env_bool("DPM_STATEFUL_CORE_SOURCING_ENABLED", False, env_get=env_get)
        and bool((env_get("DPM_CORE_BASE_URL") or "").strip())
        and not uses_legacy_monolithic_resolver
    )


def build_feature_capabilities(
    *,
    workflow_enabled: bool,
    stateful_enabled: bool,
    stateless_enabled: bool,
    solver_available: bool,
) -> list[dict[str, Any]]:
    return [
        {
            "key": "dpm.execution.stateful_portfolio_id",
            "enabled": stateful_enabled,
            "owner_service": "lotus-manage",
            "description": "Stateful lotus-manage rebalance execution using a governed portfolio identifier; enable only when a governed lotus-core resolver is configured.",
        },
        {
            "key": "dpm.execution.stateless",
            "enabled": stateless_enabled,
            "owner_service": "lotus-manage",
            "description": "Stateless lotus-manage rebalance execution using explicit request bundles.",
        },
        {
            "key": "dpm.workflow.review_gate",
            "enabled": workflow_enabled,
            "owner_service": "lotus-manage",
            "description": "Discretionary mandate run review gates for approve, reject, and request-changes decisions.",
        },
        {
            "key": "dpm.execution.solver_target_generation",
            "enabled": solver_available,
            "owner_service": "lotus-manage",
            "description": "Optional solver-backed target generation for discretionary mandate rebalance requests when solver dependencies are installed.",
        },
        {
            "key": "manage.observability.action_register_supportability",
            "enabled": True,
            "owner_service": "lotus-manage",
            "description": "Source-backed action register and supportability summary posture with bounded states, reasons, and metrics.",
        },
    ]


def build_workflow_capabilities(*, workflow_enabled: bool) -> list[dict[str, Any]]:
    return [
        {
            "workflow_key": "dpm_rebalance_lifecycle",
            "enabled": workflow_enabled,
            "required_features": ["dpm.workflow.review_gate"],
        },
    ]


def build_capabilities_response(
    *,
    consumer_system: str,
    tenant_id: str,
    solver_available: bool,
    env_get: EnvGetter,
) -> dict[str, Any]:
    workflow_enabled = env_bool("DPM_WORKFLOW_ENABLED", False, env_get=env_get)
    stateful_enabled = stateful_execution_publishable(env_get=env_get)
    stateless_enabled = env_bool("DPM_CAP_INPUT_MODE_STATELESS_ENABLED", True, env_get=env_get)

    return {
        "contract_version": "v1",
        "source_service": env_get("DPM_CAP_SOURCE_SERVICE") or "lotus-manage",
        "consumer_system": consumer_system,
        "tenant_id": tenant_id,
        "generated_at": datetime.now(UTC),
        "as_of_date": date.today(),
        "policy_version": env_get("DPM_POLICY_VERSION") or "dpm.policy.v1",
        "supported_input_modes": supported_input_modes(
            stateful_enabled=stateful_enabled,
            stateless_enabled=stateless_enabled,
        ),
        "features": build_feature_capabilities(
            workflow_enabled=workflow_enabled,
            stateful_enabled=stateful_enabled,
            stateless_enabled=stateless_enabled,
            solver_available=solver_available,
        ),
        "workflows": build_workflow_capabilities(workflow_enabled=workflow_enabled),
    }


__all__ = [
    "build_capabilities_response",
    "build_feature_capabilities",
    "build_workflow_capabilities",
    "env_bool",
    "stateful_execution_publishable",
    "supported_input_modes",
]
