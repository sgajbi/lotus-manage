from src.api.request_models import RebalanceRequest
from src.api.services.construction_alternative_builder import build_construction_alternatives
from src.api.services.construction_method_execution import run_construction_method
from src.core.construction.models import ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from tests.shared.factories import valid_api_payload


def test_build_construction_alternatives_preserves_method_order_and_runs_effective_methods() -> (
    None
):
    request = RebalanceRequest.model_validate(valid_api_payload())
    recorded_hashes: list[str] = []

    class _RunService:
        def record_run(self, *, result, request_hash, portfolio_id, idempotency_key) -> None:
            recorded_hashes.append(request_hash)

    base_result = run_construction_method(
        request=request,
        method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        correlation_id="corr-builder",
        request_hash="hash-builder:heuristic_explainable",
        run_service=None,
    )

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
        run_service=_RunService(),  # type: ignore[arg-type]
    )

    assert [alternative.method for alternative in alternatives] == [
        ConstructionMethod.DO_NOTHING_BASELINE,
        ConstructionMethod.HEURISTIC_EXPLAINABLE,
        ConstructionMethod.MIN_TURNOVER,
    ]
    assert alternatives[0].intent_ids == []
    assert alternatives[1].alternative_id == "alt_heuristic_explainable"
    assert alternatives[2].diagnostics["method_plan"]["effective_method"] == "MIN_TURNOVER"
    assert recorded_hashes == ["hash-builder:MIN_TURNOVER"]
