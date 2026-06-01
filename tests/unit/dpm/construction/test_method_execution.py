from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_execution import (
    options_for_construction_method,
    run_construction_method,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import EngineOptions, TargetMethod
from tests.shared.factories import valid_api_payload


def test_construction_method_options_apply_bounded_method_overrides() -> None:
    base_options = EngineOptions(max_turnover_pct=Decimal("0.50"))

    min_turnover = options_for_construction_method(
        options=base_options,
        method=ConstructionMethod.MIN_TURNOVER,
    )
    solver = options_for_construction_method(
        options=base_options,
        method=ConstructionMethod.SOLVER_CONSTRAINED,
    )
    liquidity = options_for_construction_method(
        options=base_options,
        method=ConstructionMethod.LIQUIDITY_AWARE,
    )

    assert min_turnover.max_turnover_pct == Decimal("0.10")
    assert solver.target_method == TargetMethod.SOLVER
    assert solver.compare_target_methods is True
    assert liquidity.enable_settlement_awareness is True
    assert liquidity.min_cash_buffer_pct >= Decimal("0.03")


def test_run_construction_method_uses_method_specific_correlation_and_records_support() -> None:
    request = RebalanceRequest.model_validate(valid_api_payload())
    calls: list[tuple[str, str, str | None]] = []

    class _RunService:
        def record_run(self, *, result, request_hash, portfolio_id, idempotency_key) -> None:
            calls.append((result.correlation_id, request_hash, idempotency_key))

    result = run_construction_method(
        request=request,
        method=ConstructionMethod.MIN_TURNOVER,
        correlation_id="corr-construction",
        request_hash="hash-method",
        run_service=_RunService(),
    )

    assert result.correlation_id == "corr-construction:min_turnover"
    assert calls == [("corr-construction:min_turnover", "hash-method", None)]
