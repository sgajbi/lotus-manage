from types import SimpleNamespace
from typing import cast

import pytest

from src.api.request_models import RebalanceRequest
from src.api.services.construction_idempotency import (
    construction_request_hash,
    construction_request_hash_payload,
    resolve_existing_construction_alternative_set,
)
from src.core.construction import build_alternative_set
from src.core.construction.repository import ConstructionIdempotencyConflictError
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import DpmResolvedSourceContext
from src.core.common.canonical import hash_canonical_payload
from src.core.risk_authority.context import RiskAuthorityContext, RiskAuthorityGrant
from src.infrastructure.construction import InMemoryConstructionRepository
from tests.shared.factories import valid_api_payload


def _request() -> RebalanceRequest:
    return RebalanceRequest.model_validate(valid_api_payload())


def test_construction_request_hash_includes_methods_and_source_context() -> None:
    request = _request()

    heuristic_hash = construction_request_hash(
        request=request,
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        source_context=None,
    )
    baseline_hash = construction_request_hash(
        request=request,
        methods=[ConstructionMethod.DO_NOTHING_BASELINE],
        source_context=None,
    )
    source_context = cast(
        DpmResolvedSourceContext,
        SimpleNamespace(stateful_context_hash="stateful-construction-hash"),
    )
    stateful_hash = construction_request_hash(
        request=request,
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        source_context=source_context,
    )

    assert heuristic_hash != baseline_hash
    assert heuristic_hash != stateful_hash


def test_construction_request_hash_payload_preserves_methods_and_source_hash() -> None:
    request = _request()
    source_context = cast(
        DpmResolvedSourceContext,
        SimpleNamespace(stateful_context_hash="stateful-construction-hash"),
    )

    payload = construction_request_hash_payload(
        request=request,
        methods=[
            ConstructionMethod.HEURISTIC_EXPLAINABLE,
            ConstructionMethod.MIN_TURNOVER,
        ],
        source_context=source_context,
    )

    assert payload["methods"] == ["HEURISTIC_EXPLAINABLE", "MIN_TURNOVER"]
    assert payload["source_context_hash"] == "stateful-construction-hash"
    assert payload["request"] == request.model_dump(mode="json")


def test_construction_idempotency_returns_replay_and_rejects_conflict() -> None:
    repository = InMemoryConstructionRepository()
    alternative_set = build_alternative_set(
        alternative_set_id="cas_idem_001",
        portfolio_id="PF_TEST",
        as_of="2026-06-01",
        alternatives=[],
    ).model_copy(update={"tenant_id": "tenant_001", "request_hash": "sha256:construction"})
    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-construction",
    )

    replay = resolve_existing_construction_alternative_set(
        repository=repository,
        idempotency_key="idem-construction",
        request_hash="sha256:construction",
        tenant_id="tenant_001",
    )

    assert replay is not None
    assert replay.alternative_set_id == "cas_idem_001"
    with pytest.raises(
        ConstructionIdempotencyConflictError,
        match="CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT",
    ):
        resolve_existing_construction_alternative_set(
            repository=repository,
            idempotency_key="idem-construction",
            request_hash="sha256:other",
            tenant_id="tenant_001",
        )


def _risk_context():
    return RiskAuthorityContext(
        actor_id="pm-A",
        tenant_id="tenant_001",
        role="PM",
        correlation_id="original",
        service_identity="consumer",
        policy_fingerprint="sha256:policy",
        grants=(
            RiskAuthorityGrant(operation="concentration", capability="risk.concentration"),
            RiskAuthorityGrant(operation="regime_scenario", capability="risk.regime"),
        ),
    )


def test_risk_authority_business_binding_excludes_trace_but_retains_full_async_custody():
    context = _risk_context()
    changed_trace = context.model_copy(
        update={"correlation_id": "new-trace", "grants": tuple(reversed(context.grants))}
    )
    assert context.authority_fingerprint() == changed_trace.authority_fingerprint()
    assert context.fingerprint() != changed_trace.fingerprint()
    for field, value in [
        ("actor_id", "pm-B"),
        ("tenant_id", "foreign"),
        ("role", "CIO"),
        ("service_identity", "other-consumer"),
        ("policy_fingerprint", "sha256:changed-policy"),
        ("grants", ()),
    ]:
        assert (
            context.authority_fingerprint()
            != context.model_copy(update={field: value}).authority_fingerprint()
        )


@pytest.mark.parametrize(
    "method", [ConstructionMethod.RISK_AWARE, ConstructionMethod.REGIME_STRESS_AWARE]
)
def test_protected_construction_unknown_authority_is_explicit_and_legacy_hash_refuses(method):
    payload = construction_request_hash_payload(
        request=_request(), methods=[method], source_context=None, admitted_tenant_id="tenant_001"
    )
    assert payload["risk_authority_fingerprint"] is None
    legacy = {key: value for key, value in payload.items() if key != "risk_authority_fingerprint"}
    repository = InMemoryConstructionRepository()
    stored = build_alternative_set(
        alternative_set_id="cas_legacy_risk",
        portfolio_id="PF_TEST",
        as_of="2026-06-01",
        alternatives=[],
    ).model_copy(update={"tenant_id": "tenant_001", "request_hash": hash_canonical_payload(legacy)})
    repository.save_alternative_set(alternative_set=stored, idempotency_key="legacy-risk")
    with pytest.raises(
        ConstructionIdempotencyConflictError, match="CONSTRUCTION_IDEMPOTENCY_KEY_CONFLICT"
    ):
        resolve_existing_construction_alternative_set(
            repository=repository,
            idempotency_key="legacy-risk",
            request_hash=hash_canonical_payload(payload),
            tenant_id="tenant_001",
        )
    assert (
        repository.get_alternative_set(alternative_set_id="cas_legacy_risk", tenant_id="tenant_001")
        == stored
    )


def test_non_risk_construction_hash_is_unchanged_by_risk_authority():
    arguments = dict(
        request=_request(),
        methods=[ConstructionMethod.HEURISTIC_EXPLAINABLE],
        source_context=None,
        admitted_tenant_id="tenant_001",
    )
    assert construction_request_hash(
        **arguments, risk_authority_context=_risk_context()
    ) == construction_request_hash(**arguments)
    assert "risk_authority_fingerprint" not in construction_request_hash_payload(**arguments)


def test_construction_refuses_mismatched_context_tenant_before_engine():
    from src.api.services.construction_service import generate_construction_alternative_set

    with pytest.raises(
        ConstructionIdempotencyConflictError, match="CONSTRUCTION_RISK_AUTHORITY_SCOPE_CONFLICT"
    ):
        generate_construction_alternative_set(
            request=_request(),
            idempotency_key="scope-conflict",
            correlation_id="trace",
            repository=InMemoryConstructionRepository(),
            admitted_tenant_id="tenant_001",
            risk_authority_context=_risk_context().model_copy(update={"tenant_id": "foreign"}),
        )
