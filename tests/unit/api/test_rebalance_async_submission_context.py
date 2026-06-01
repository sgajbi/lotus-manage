from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch

from src.api.services import rebalance_async_submission_context as async_context
from src.api.services import rebalance_simulation_service
from src.api.services.rebalance_async_submission_context import (
    DpmAsyncSubmissionContext,
    build_async_submission_context,
)
from src.api.services.rebalance_run_support_service import DpmRunSupportServiceUnavailableError
from src.api.services.rebalance_simulation_errors import (
    DpmRebalanceAsyncOperationSupportUnavailableError,
)


class _BatchRequest:
    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {"scenarios": {"baseline": {"options": {}}}}


def test_build_async_submission_context_resolves_service_policy_payload_and_mode(
    monkeypatch: MonkeyPatch,
) -> None:
    service = SimpleNamespace(name="support-service")
    captured: dict[str, object] = {}
    source_context = SimpleNamespace(model_dump=lambda mode: {"source": mode})

    def _resolve_policy(**kwargs: object) -> SimpleNamespace:
        captured["policy"] = kwargs
        return SimpleNamespace(
            resolution=SimpleNamespace(
                enabled=True,
                source="REQUEST",
                selected_policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
            )
        )

    monkeypatch.setattr(async_context, "resolve_execution_policy_pack_context", _resolve_policy)
    monkeypatch.setattr(async_context, "resolve_async_execution_mode", lambda: "ACCEPT_ONLY")

    context = build_async_submission_context(
        request=_BatchRequest(),  # type: ignore[arg-type]
        policy_pack_id="POLICY_DPM_SG_BALANCED_V1",
        tenant_default_policy_pack_id="POLICY_TENANT_DEFAULT",
        tenant_id="tenant_sg",
        source_context=source_context,  # type: ignore[arg-type]
        support_service_factory=lambda: service,  # type: ignore[return-value]
    )

    assert isinstance(context, DpmAsyncSubmissionContext)
    assert context.service is service
    assert context.execution_mode == "ACCEPT_ONLY"
    assert context.policy_resolution_enabled is True
    assert context.policy_resolution_source == "REQUEST"
    assert context.selected_policy_pack_id == "POLICY_DPM_SG_BALANCED_V1"
    assert context.request_json == {
        "batch_request": {"scenarios": {"baseline": {"options": {}}}},
        "policy_context": {
            "request_policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
            "tenant_default_policy_pack_id": "POLICY_TENANT_DEFAULT",
            "tenant_id": "tenant_sg",
        },
        "source_context": {"source": "json"},
    }
    assert captured["policy"]["surface"] == "analyze_async"
    assert captured["policy"]["load_definition"] is False


def test_build_async_submission_context_maps_support_service_unavailable() -> None:
    def _unavailable() -> object:
        raise DpmRunSupportServiceUnavailableError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")

    with pytest.raises(DpmRebalanceAsyncOperationSupportUnavailableError) as exc_info:
        build_async_submission_context(
            request=_BatchRequest(),  # type: ignore[arg-type]
            policy_pack_id=None,
            tenant_default_policy_pack_id=None,
            tenant_id=None,
            source_context=None,
            support_service_factory=_unavailable,  # type: ignore[arg-type]
        )

    assert exc_info.value.detail == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"


def test_rebalance_async_submission_context_exports_only_context_builder() -> None:
    assert async_context.__all__ == [
        "DpmAsyncSubmissionContext",
        "SupportServiceFactory",
        "build_async_submission_context",
    ]


def test_service_preserves_async_submission_context_import_surface() -> None:
    assert rebalance_simulation_service.DpmAsyncSubmissionContext is DpmAsyncSubmissionContext
