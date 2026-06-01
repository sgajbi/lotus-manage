from typing import Optional

from src.api.request_models import RebalanceRequest
from src.api.services.construction_method_authority import authority_context_for_request_method
from src.api.services.construction_method_execution import run_construction_method
from src.api.services.construction_supportability_application import (
    apply_construction_supportability,
)
from src.core.common.capabilities import has_solver_dependencies
from src.core.construction.alternative_engine import (
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.construction.method_registry import resolve_method_plan
from src.core.construction.models import ConstructionAlternative, ConstructionAuthorityContext
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult
from src.core.rebalance_runs.service import DpmRunSupportService
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


def build_construction_alternatives(
    *,
    request: RebalanceRequest,
    method_set: list[ConstructionMethod],
    base_result: RebalanceResult,
    correlation_id: Optional[str],
    request_hash: str,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    run_service: DpmRunSupportService | None,
    solver_available: bool | None = None,
) -> list[ConstructionAlternative]:
    alternatives: list[ConstructionAlternative] = []
    resolved_solver_available = (
        has_solver_dependencies() if solver_available is None else solver_available
    )
    for method in method_set:
        if method == ConstructionMethod.DO_NOTHING_BASELINE:
            alternatives.append(build_do_nothing_baseline(result=base_result))
            continue
        plan = resolve_method_plan(method=method, solver_available=resolved_solver_available)
        result = base_result
        if plan.effective_method != ConstructionMethod.HEURISTIC_EXPLAINABLE:
            result = run_construction_method(
                request=request,
                method=plan.effective_method,
                correlation_id=correlation_id,
                request_hash=f"{request_hash}:{plan.effective_method.value}",
                run_service=run_service,
            )
        alternative = build_rebalance_result_alternative(
            result=result,
            method=method,
            alternative_id=f"alt_{method.value.lower()}",
        )
        alternatives.append(
            apply_construction_supportability(
                request=request,
                method=method,
                alternative=alternative,
                result=result,
                plan=plan,
                authority_context=authority_context_for_request_method(
                    request=request,
                    method=method,
                    result=result,
                    authority_context=authority_context,
                    risk_authority_client=risk_authority_client,
                    correlation_id=correlation_id,
                ),
            )
        )
    return alternatives


__all__ = ["build_construction_alternatives"]
