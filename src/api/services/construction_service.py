from __future__ import annotations

import uuid
from typing import Optional

from src.api.services.construction_alternative_set_assembly import (
    build_persistable_alternative_set,
)
from src.api.services.construction_idempotency import (
    construction_request_hash,
    resolve_existing_construction_alternative_set,
)
from src.api.services.construction_method_execution import (
    run_construction_method,
)
from src.api.services.construction_method_authority import authority_context_for_request_method
from src.api.services.construction_source_product_context import (
    authority_context_with_source_products,
)
from src.api.services.construction_supportability_application import (
    apply_construction_supportability,
)
from src.core.common.capabilities import has_solver_dependencies
from src.core.construction.alternative_engine import (
    build_do_nothing_baseline,
    build_rebalance_result_alternative,
)
from src.core.construction.method_registry import resolve_method_plan
from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
    ConstructionAuthorityContext,
)
from src.core.construction.repository import (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionRepository,
)
from src.core.construction.vocabulary import (
    ConstructionMethod,
    FIRST_WAVE_CONSTRUCTION_METHODS,
)
from src.core.dpm_source_context import (
    DpmResolvedSourceContext,
)
from src.core.models import RebalanceResult
from src.core.rebalance_runs.service import DpmRunSupportService
from src.api.request_models import RebalanceRequest
from src.infrastructure.risk_authority import (
    LotusRiskAuthorityClient,
)


def generate_construction_alternative_set(
    *,
    request: RebalanceRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    repository: ConstructionRepository,
    methods: list[ConstructionMethod] | None = None,
    source_context: Optional[DpmResolvedSourceContext] = None,
    authority_context: ConstructionAuthorityContext | None = None,
    risk_authority_client: LotusRiskAuthorityClient | None = None,
    run_service: DpmRunSupportService | None = None,
) -> ConstructionAlternativeSet:
    method_set = list(methods or FIRST_WAVE_CONSTRUCTION_METHODS)
    request_hash = construction_request_hash(
        request=request,
        methods=method_set,
        source_context=source_context,
    )
    existing = resolve_existing_construction_alternative_set(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if existing is not None:
        return existing

    base_result = run_construction_method(
        request=request,
        method=ConstructionMethod.HEURISTIC_EXPLAINABLE,
        correlation_id=correlation_id,
        request_hash=f"{request_hash}:{ConstructionMethod.HEURISTIC_EXPLAINABLE.value}",
        run_service=run_service,
    )
    resolved_authority_context = authority_context_with_source_products(
        authority_context=authority_context or ConstructionAuthorityContext(),
        source_context=source_context,
    )
    alternatives = _build_alternatives(
        request=request,
        method_set=method_set,
        base_result=base_result,
        correlation_id=correlation_id,
        request_hash=request_hash,
        authority_context=resolved_authority_context,
        risk_authority_client=risk_authority_client,
        run_service=run_service,
    )
    alternative_set = build_persistable_alternative_set(
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        alternatives=alternatives,
        request_hash=request_hash,
        source_context=source_context,
    )
    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key=idempotency_key,
    )
    return alternative_set


def get_construction_alternative_set(
    *,
    repository: ConstructionRepository,
    alternative_set_id: str,
) -> ConstructionAlternativeSet:
    alternative_set = repository.get_alternative_set(alternative_set_id=alternative_set_id)
    if alternative_set is None:
        raise ConstructionAlternativeSetNotFoundError("CONSTRUCTION_ALTERNATIVE_SET_NOT_FOUND")
    return alternative_set


def select_construction_alternative(
    *,
    repository: ConstructionRepository,
    alternative_set_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str | None,
) -> ConstructionAlternativeSelection:
    alternative_set = get_construction_alternative_set(
        repository=repository,
        alternative_set_id=alternative_set_id,
    )
    if alternative_id not in {
        alternative.alternative_id for alternative in alternative_set.alternatives
    }:
        raise ConstructionAlternativeNotFoundError("CONSTRUCTION_ALTERNATIVE_NOT_FOUND")
    selection = ConstructionAlternativeSelection(
        selection_id=f"casel_{uuid.uuid4().hex[:12]}",
        alternative_set_id=alternative_set_id,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    repository.save_selection(selection=selection)
    return selection


def _build_alternatives(
    *,
    request: RebalanceRequest,
    method_set: list[ConstructionMethod],
    base_result: RebalanceResult,
    correlation_id: Optional[str],
    request_hash: str,
    authority_context: ConstructionAuthorityContext,
    risk_authority_client: LotusRiskAuthorityClient | None,
    run_service: DpmRunSupportService | None,
) -> list[ConstructionAlternative]:
    alternatives: list[ConstructionAlternative] = []
    solver_available = has_solver_dependencies()
    for method in method_set:
        if method == ConstructionMethod.DO_NOTHING_BASELINE:
            alternatives.append(build_do_nothing_baseline(result=base_result))
            continue
        plan = resolve_method_plan(method=method, solver_available=solver_available)
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
