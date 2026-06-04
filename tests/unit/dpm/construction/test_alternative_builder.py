from src.api.request_models import RebalanceRequest
from src.api.services.construction_alternative_builder import (
    build_construction_alternative_for_method,
    build_construction_alternatives,
)
from src.api.services.construction_method_execution import run_construction_method
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult
from typing import Any
from tests.shared.factories import valid_api_payload


class _RunService:
    def __init__(self) -> None:
        self.recorded_hashes: list[str] = []

    def record_run(
        self,
        *,
        result: Any,
        request_hash: str,
        portfolio_id: str,
        idempotency_key: str | None,
    ) -> None:
        self.recorded_hashes.append(request_hash)


def _request_and_base_result() -> tuple[RebalanceRequest, RebalanceResult]:
    request = RebalanceRequest.model_validate(valid_api_payload())
    base_result = run_construction_method(
        request=request,
        method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        correlation_id="corr-builder",
        request_hash="hash-builder:heuristic_explainable",
        run_service=None,
    )
    return request, base_result


def test_build_construction_alternative_for_method_returns_do_nothing_baseline() -> None:
    request, base_result = _request_and_base_result()
    run_service = _RunService()

    alternative = build_construction_alternative_for_method(
        request=request,
        method=ConstructionMethod.DO_NOTHING_BASELINE,
        base_result=base_result,
        correlation_id="corr-builder",
        request_hash="hash-builder",
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=None,
        run_service=run_service,  # type: ignore[arg-type]
    )

    assert alternative.method == ConstructionMethod.DO_NOTHING_BASELINE
    assert alternative.intent_ids == []
    assert run_service.recorded_hashes == []


def test_build_construction_alternative_for_method_runs_effective_method() -> None:
    request, base_result = _request_and_base_result()
    run_service = _RunService()

    alternative = build_construction_alternative_for_method(
        request=request,
        method=ConstructionMethod.MIN_TURNOVER,
        base_result=base_result,
        correlation_id="corr-builder",
        request_hash="hash-builder",
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=None,
        run_service=run_service,  # type: ignore[arg-type]
    )

    assert alternative.method == ConstructionMethod.MIN_TURNOVER
    assert alternative.alternative_id == "alt_min_turnover"
    assert alternative.diagnostics["method_plan"]["effective_method"] == "MIN_TURNOVER"
    assert run_service.recorded_hashes == ["hash-builder:MIN_TURNOVER"]


def test_build_construction_alternatives_preserves_method_order_and_runs_effective_methods() -> (
    None
):
    request, base_result = _request_and_base_result()
    run_service = _RunService()

    alternatives = build_construction_alternatives(
        request=request,
        method_set=[
            ConstructionMethod.DO_NOTHING_BASELINE,
            ConstructionMethod.HEURISTIC_EXPLAINABLE,
            ConstructionMethod.MIN_TURNOVER,
        ],
        base_result=base_result,
        correlation_id="corr-builder",
        request_hash="hash-builder",
        authority_context=ConstructionAuthorityContext(),
        risk_authority_client=None,
        run_service=run_service,  # type: ignore[arg-type]
    )

    assert [alternative.method for alternative in alternatives] == [
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.MIN_TURNOVER,
    ]
    assert alternatives[0].intent_ids == []
    assert alternatives[1].alternative_id == "alt_heuristic_explainable"
    assert alternatives[2].diagnostics["method_plan"]["effective_method"] == "MIN_TURNOVER"
    assert run_service.recorded_hashes == ["hash-builder:MIN_TURNOVER"]
