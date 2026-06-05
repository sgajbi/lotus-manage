from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_execution import (
    _currency_overlay_options,
    _min_turnover_options,
    _risk_aware_options,
    construction_method_correlation_id,
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


def test_construction_method_option_helpers_apply_bounded_caps_and_floors() -> None:
    base_options = EngineOptions(
        fx_buffer_pct=Decimal("0"),
        max_turnover_pct=Decimal("0.05"),
        single_position_max_weight=Decimal("0.40"),
    )

    min_turnover = _min_turnover_options(base_options)
    currency_overlay = _currency_overlay_options(base_options)
    risk_aware = _risk_aware_options(base_options)

    assert min_turnover.max_turnover_pct == Decimal("0.05")
    assert currency_overlay.block_on_missing_fx is True
    assert currency_overlay.enable_settlement_awareness is True
    assert currency_overlay.fx_buffer_pct == Decimal("0.01")
    assert risk_aware.single_position_max_weight == Decimal("0.30")


def test_construction_method_option_helpers_preserve_existing_stricter_risk_cap() -> None:
    base_options = EngineOptions(single_position_max_weight=Decimal("0.20"))

    risk_aware = _risk_aware_options(base_options)

    assert risk_aware.single_position_max_weight == Decimal("0.20")


def test_construction_method_correlation_id_preserves_caller_context() -> None:
    assert (
        construction_method_correlation_id(
            method=ConstructionMethod.MIN_TURNOVER,
            correlation_id="corr-construction",
        )
        == "corr-construction:min_turnover"
    )


def test_construction_method_correlation_id_generates_method_scoped_fallback() -> None:
    correlation_id = construction_method_correlation_id(
        method=ConstructionMethod.MIN_TURNOVER,
        correlation_id=None,
    )

    assert correlation_id.startswith("corr_construction_min_turnover_")
    assert len(correlation_id) == len("corr_construction_min_turnover_") + 10


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
