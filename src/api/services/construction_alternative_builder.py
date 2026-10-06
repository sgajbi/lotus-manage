from typing import Optional

from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_restriction_supportability import (
    client_restriction_policy_required,
    client_restriction_status,
    with_client_restriction_constraint,
)
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
from src.core.integration_ports import RiskAuthorityClient
from src.core.construction.method_registry import resolve_method_plan
from src.core.construction.models import ConstructionAlternative, ConstructionAuthorityContext
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethod
from src.core.models import RebalanceResult
from src.core.rebalance_runs.service import DpmRunSupportService


def build_construction_alternative_for_method(
    *,
    request: RebalanceRequest,
    method: ConstructionMethod,
    base_result: RebalanceResult,
    correlation_id: Optional[str],
    request_hash: str,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    run_service: DpmRunSupportService | None,
    solver_available: bool | None = None,
    tenant_id: str | None = None,
    source_context: DpmResolvedSourceContext | None = None,
) -> ConstructionAlternative:
    if method == ConstructionMethod.DO_NOTHING_BASELINE:
        baseline = build_do_nothing_baseline(result=base_result)
        if not client_restriction_policy_required(authority_context):
            return baseline
        baseline = with_client_restriction_constraint(
            request=request,
            alternative=baseline,
            result=base_result.model_copy(update={"intents": []}),
            authority_context=authority_context,
        )
        return baseline.model_copy(
            update={
                "method_status": lowest_construction_status(
                    [
                        baseline.method_status,
                        client_restriction_status(
                            request=request,
                            result=base_result.model_copy(update={"intents": []}),
                            context=authority_context.client_restriction_context,
                        ),
                    ]
                )
            }
        )

    resolved_solver_available = (
        has_solver_dependencies() if solver_available is None else solver_available
    )
    plan = resolve_method_plan(method=method, solver_available=resolved_solver_available)
    result = base_result
    if plan.effective_method != ConstructionMethod.HEURISTIC_EXPLAINABLE:
        result = run_construction_method(
            request=request,
            method=plan.effective_method,
            correlation_id=correlation_id,
            request_hash=f"{request_hash}:{plan.effective_method.value}",
            run_service=run_service,
            tenant_id=tenant_id,
            source_context=source_context,
        )
    alternative = build_rebalance_result_alternative(
        result=result,
        method=method,
        alternative_id=f"alt_{method.value.lower()}",
    )
    return apply_construction_supportability(
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


def build_construction_alternatives(
    *,
    request: RebalanceRequest,
    method_set: list[ConstructionMethod],
    base_result: RebalanceResult,
    correlation_id: Optional[str],
    request_hash: str,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: RiskAuthorityClient | None,
    run_service: DpmRunSupportService | None,
    solver_available: bool | None = None,
    tenant_id: str | None = None,
    source_context: DpmResolvedSourceContext | None = None,
) -> list[ConstructionAlternative]:
    resolved_solver_available = (
        has_solver_dependencies() if solver_available is None else solver_available
    )
    return [
        build_construction_alternative_for_method(
            request=request,
            method=method,
            base_result=base_result,
            correlation_id=correlation_id,
            request_hash=request_hash,
            authority_context=authority_context,
            risk_authority_client=risk_authority_client,
            run_service=run_service,
            solver_available=resolved_solver_available,
            tenant_id=tenant_id,
            source_context=source_context,
        )
        for method in method_set
    ]


__all__ = [
    "build_construction_alternative_for_method",
    "build_construction_alternatives",
]
