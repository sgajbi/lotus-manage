from types import SimpleNamespace

from pytest import MonkeyPatch

from src.api.services import rebalance_simulation_execution_context as execution_context
from src.api.services import rebalance_simulation_service
from src.api.services.rebalance_simulation_execution_context import (
    DpmSimulationExecutionContext,
    build_simulation_execution_context,
)


class _Request:
    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "portfolio_snapshot": {"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            "options": {"max_turnover": "0.15"},
        }


def test_build_simulation_execution_context_resolves_hash_policy_and_replay(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    policy_definition = SimpleNamespace(policy_pack_id="POLICY_DPM_SG_BALANCED_V1")

    def _resolve_policy(**kwargs: object) -> SimpleNamespace:
        captured["policy"] = kwargs
        return SimpleNamespace(
            definition=policy_definition,
            resolution=SimpleNamespace(
                enabled=True,
                source="REQUEST",
                selected_policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
            ),
        )

    def _resolve_replay(**kwargs: object) -> bool:
        captured["replay"] = kwargs
        return False

    monkeypatch.setattr(
        execution_context,
        "resolve_execution_policy_pack_context",
        _resolve_policy,
    )
    monkeypatch.setattr(
        execution_context,
        "resolve_rebalance_correlation_id",
        lambda correlation_id: f"resolved-{correlation_id}",
    )
    monkeypatch.setattr(execution_context, "env_flag", lambda *_args: True)
    monkeypatch.setattr(execution_context, "resolve_policy_pack_replay_enabled", _resolve_replay)

    context = build_simulation_execution_context(
        request=_Request(),  # type: ignore[arg-type]
        correlation_id="corr-001",
        policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
        tenant_default_policy_pack_id="POLICY_TENANT_DEFAULT",
        tenant_id="tenant_sg",
        request_hasher=lambda payload: f"hash:{payload['portfolio_snapshot']}",
    )

    assert isinstance(context, DpmSimulationExecutionContext)
    assert context.request_hash == "hash:{'portfolio_id': 'PB_SG_GLOBAL_BAL_001'}"
    assert context.correlation_id == "resolved-corr-001"
    assert context.policy_pack_definition is policy_definition
    assert context.replay_enabled is False
    assert context.policy_resolution_enabled is True
    assert context.policy_resolution_source == "REQUEST"
    assert context.selected_policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert captured["policy"]["surface"] == "simulate"
    assert captured["policy"]["request_policy_pack_id"] == "POLICY_DPM_SG_BALANCED_V1"
    assert captured["replay"] == {
        "default_replay_enabled": True,
        "policy_pack": policy_definition,
    }


def test_rebalance_simulation_execution_context_exports_only_context_builder() -> None:
    assert execution_context.__all__ == [
        "DpmSimulationExecutionContext",
        "RequestHasher",
        "build_simulation_execution_context",
    ]


def test_service_preserves_simulation_execution_context_import_surface() -> None:
    assert (
        rebalance_simulation_service.DpmSimulationExecutionContext is DpmSimulationExecutionContext
    )
