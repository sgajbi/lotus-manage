import uuid
from decimal import Decimal
from typing import Optional

from src.api.request_models import RebalanceRequest
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import EngineOptions, RebalanceResult, TargetMethod
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.service import DpmRunSupportService

_MIN_TURNOVER_DEFAULT = Decimal("0.10")


def run_construction_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    correlation_id: Optional[str],
    request_hash: str,
    run_service: DpmRunSupportService | None,
) -> RebalanceResult:
    options = options_for_construction_method(options=request.options, method=method)
    run_correlation_id = construction_method_correlation_id(
        method=method,
        correlation_id=correlation_id,
    )
    result = run_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        model=request.model_portfolio,
        shelf=request.shelf_entries,
        options=options,
        request_hash=request_hash,
        correlation_id=run_correlation_id,
    )
    if run_service is not None:
        run_service.record_run(
            result=result,
            request_hash=request_hash,
            portfolio_id=request.portfolio_snapshot.portfolio_id,
            idempotency_key=None,
        )
    return result


def construction_method_correlation_id(
    *,
    method: ConstructionMethod,
    correlation_id: str | None,
) -> str:
    if correlation_id:
        return f"{correlation_id}:{method.value.lower()}"
    return f"corr_construction_{method.value.lower()}_{uuid.uuid4().hex[:10]}"


def options_for_construction_method(
    *,
    options: EngineOptions,
    method: ConstructionMethod,
) -> EngineOptions:
    if method == ConstructionMethod.MIN_TURNOVER:
        max_turnover_pct = options.max_turnover_pct
        if max_turnover_pct is None or max_turnover_pct > _MIN_TURNOVER_DEFAULT:
            max_turnover_pct = _MIN_TURNOVER_DEFAULT
        return options.model_copy(update={"max_turnover_pct": max_turnover_pct})
    if method == ConstructionMethod.TAX_AWARE:
        return options.model_copy(update={"enable_tax_awareness": True})
    if method == ConstructionMethod.SOLVER_CONSTRAINED:
        return options.model_copy(
            update={"target_method": TargetMethod.SOLVER, "compare_target_methods": True}
        )
    if method == ConstructionMethod.LIQUIDITY_AWARE:
        return options.model_copy(
            update={
                "enable_settlement_awareness": True,
                "min_cash_buffer_pct": max(options.min_cash_buffer_pct, Decimal("0.03")),
            }
        )
    if method == ConstructionMethod.CURRENCY_OVERLAY:
        return options.model_copy(
            update={
                "block_on_missing_fx": True,
                "enable_settlement_awareness": True,
                "fx_buffer_pct": max(options.fx_buffer_pct, Decimal("0.01")),
            }
        )
    if method == ConstructionMethod.RISK_AWARE:
        max_weight = options.single_position_max_weight
        if max_weight is None or max_weight > Decimal("0.30"):
            max_weight = Decimal("0.30")
        return options.model_copy(update={"single_position_max_weight": max_weight})
    return options


__all__ = [
    "construction_method_correlation_id",
    "options_for_construction_method",
    "run_construction_method",
]
