from collections.abc import Sequence

from src.api.request_models import RebalanceRequest
from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import ConstructionAlternativeSet
from src.core.construction.repository import (
    ConstructionIdempotencyConflictError,
    ConstructionRepository,
)
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.risk_authority.context import RiskAuthorityContext


def construction_request_hash(
    *,
    request: RebalanceRequest,
    methods: Sequence[ConstructionMethod],
    source_context: DpmResolvedSourceContext | None,
    admitted_tenant_id: str | None = None,
    risk_authority_context: RiskAuthorityContext | None = None,
) -> str:
    return hash_canonical_payload(
        construction_request_hash_payload(
            request=request,
            methods=methods,
            source_context=source_context,
            admitted_tenant_id=admitted_tenant_id,
            risk_authority_context=risk_authority_context,
        )
    )


def construction_request_hash_payload(
    *,
    request: RebalanceRequest,
    methods: Sequence[ConstructionMethod],
    source_context: DpmResolvedSourceContext | None,
    admitted_tenant_id: str | None = None,
    risk_authority_context: RiskAuthorityContext | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "request": request.model_dump(mode="json"),
        "methods": [method.value for method in methods],
        "source_context_hash": (
            source_context.stateful_context_hash if source_context is not None else None
        ),
    }
    if admitted_tenant_id is not None:
        payload["admitted_tenant_id"] = admitted_tenant_id
    if any(
        method in {ConstructionMethod.RISK_AWARE, ConstructionMethod.REGIME_STRESS_AWARE}
        for method in methods
    ):
        # Explicit null distinguishes unknown authority from historical unbound hashes.
        # Neither a new trace nor an unchanged non-Risk command changes business identity.
        payload["risk_authority_fingerprint"] = (
            risk_authority_context.authority_fingerprint()
            if risk_authority_context is not None
            else None
        )
    return payload


def resolve_existing_construction_alternative_set(
    *,
    repository: ConstructionRepository,
    idempotency_key: str,
    request_hash: str,
    tenant_id: str,
) -> ConstructionAlternativeSet | None:
    existing = repository.get_alternative_set_by_idempotency(
        idempotency_key=idempotency_key,
        tenant_id=tenant_id,
    )
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise ConstructionIdempotencyConflictError("CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT")
    return existing


__all__ = [
    "construction_request_hash",
    "construction_request_hash_payload",
    "resolve_existing_construction_alternative_set",
]
