from types import SimpleNamespace
from typing import cast

import pytest

from src.api.request_models import RebalanceRequest
from src.api.services.construction_idempotency import (
    construction_request_hash,
    resolve_existing_construction_alternative_set,
)
from src.core.construction import build_alternative_set
from src.core.construction.repository import ConstructionIdempotencyConflictError
from src.core.construction.vocabulary import ConstructionMethod
from src.core.dpm_source_context import DpmResolvedSourceContext
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


def test_construction_idempotency_returns_replay_and_rejects_conflict() -> None:
    repository = InMemoryConstructionRepository()
    alternative_set = build_alternative_set(
        alternative_set_id="cas_idem_001",
        portfolio_id="PF_TEST",
        as_of="2026-06-01",
        alternatives=[],
    ).model_copy(update={"request_hash": "sha256:construction"})
    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-construction",
    )

    replay = resolve_existing_construction_alternative_set(
        repository=repository,
        idempotency_key="idem-construction",
        request_hash="sha256:construction",
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
        )
