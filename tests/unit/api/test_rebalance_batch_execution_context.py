from types import SimpleNamespace

from pytest import MonkeyPatch

from src.api.services import rebalance_batch_execution_context as batch_context
from src.api.services import rebalance_simulation_service
from src.api.services.rebalance_batch_execution_context import (
    DpmBatchExecutionContext,
    build_batch_execution_context,
)


def test_build_batch_execution_context_resolves_batch_id_and_policy(
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
                source="TENANT_DEFAULT",
                selected_policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
            ),
        )

    monkeypatch.setattr(batch_context, "create_batch_analysis_id", lambda: "batch_test123")
    monkeypatch.setattr(batch_context, "resolve_execution_policy_pack_context", _resolve_policy)

    context = build_batch_execution_context(
        request_policy_pack_id="POLICY_REQUEST",
        tenant_default_policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
        tenant_id="tenant_sg",
    )

    assert isinstance(context, DpmBatchExecutionContext)
    assert context.batch_id == "batch_test123"
    assert context.policy_pack_definition is policy_definition
    assert context.policy_resolution_enabled is True
    assert context.policy_resolution_source == "TENANT_DEFAULT"
    assert context.selected_policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert captured["policy"]["surface"] == "analyze"
    assert captured["policy"]["request_policy_pack_id"] == "POLICY_REQUEST"


def test_rebalance_batch_execution_context_exports_only_context_builder() -> None:
    assert batch_context.__all__ == [
        "DpmBatchExecutionContext",
        "build_batch_execution_context",
    ]


def test_service_preserves_batch_execution_context_import_surface() -> None:
    assert rebalance_simulation_service.DpmBatchExecutionContext is DpmBatchExecutionContext
