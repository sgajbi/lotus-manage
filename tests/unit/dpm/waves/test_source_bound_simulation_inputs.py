"""Stateful wave inputs select a mode, never restate server-owned financial scope."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.api.routers.wave_request_models import DpmWaveSimulationItemInput
from src.api.services.wave_inputs.resolution import (
    freeze_wave_inputs,
    simulation_input_from_payload,
)
from src.api.services.wave_simulation_operations import _simulation_inputs_for_claim
from src.api.services import wave_simulation_operations
from src.api.services.wave_errors import DpmWaveValidationError
from src.api.services.rebalance_simulation_errors import DpmRebalanceEnvelopeValidationError
from src.api.request_models import RebalanceRequest
from src.core.common.canonical import hash_canonical_payload
from src.core.dpm_source_context import DpmCoreExecutionContext, DpmResolvedSourceContext
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveTrigger,
)
from src.core.waves.simulation_operations import DpmWaveSimulationItemClaim
from src.infrastructure.waves.in_memory import InMemoryDpmWaveRepository
from src.infrastructure.construction import InMemoryConstructionRepository
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.construction.models import ConstructionAuthorityContext


def _wave():
    return DpmRebalanceWave(
        wave_id="wave-contract",
        tenant_id="tenant-contract",
        state="SOURCE_CHECKED",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="contract",
            rationale="Contract proof",
        ),
        as_of_date="2026-04-10",
        created_at=datetime(2026, 4, 10, tzinfo=UTC),
        created_by="pm",
        correlation_id="corr-contract",
        aggregate_metrics=DpmWaveAggregateMetrics(
            item_count=1,
            state_counts={"SOURCE_READY": 1},
            ready_item_count=1,
            blocked_item_count=0,
            review_required_item_count=0,
            source_degraded_item_count=0,
        ),
        items=[
            DpmRebalanceWaveItem(
                wave_item_id="item-contract",
                portfolio_id="portfolio-contract",
                mandate_id="mandate-contract",
                model_portfolio_id="model-contract",
                state="SOURCE_READY",
                source_refs=[
                    {
                        "source_system": "lotus-manage",
                        "source_type": "MANDATE_DIGITAL_TWIN",
                        "source_id": "mandate-contract",
                        "source_version": "7",
                    }
                ],
            )
        ],
    )


def _source():
    context = DpmCoreExecutionContext.model_validate(
        {
            **{key: value for key, value in _stateless_input().items() if key != "options"},
            "policy_context": {
                "tenant_id": "tenant-contract",
                "mandate_id": "mandate-contract",
                "mandate_binding_version": 7,
            },
            "source_lineage": {
                "portfolio_snapshot_id": "snapshot-contract",
                "market_data_snapshot_id": "prices-contract",
                "model_portfolio_id": "model-contract",
            },
            "supportability": {"state": "READY", "reason": "CONTROLLED_READY"},
        }
    )
    return DpmResolvedSourceContext(
        context=context,
        stateful_context_hash=hash_canonical_payload(context.model_dump(mode="json")),
    )


def _freeze(monkeypatch, *, wave=None, payload=None, source=None, retained=None):
    resolved_source = _source() if source is None else source
    calls = []

    def resolve(**kwargs):
        calls.append(kwargs)
        return RebalanceRequest.model_validate(_stateless_input()), resolved_source

    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.resolve_rebalance_request_envelope", resolve
    )
    result = freeze_wave_inputs(
        wave=wave or _wave(),
        item_inputs={
            "item-contract": payload or {"input_mode": "stateful", "options_override": {}}
        },
        tenant_id="tenant-contract",
        correlation_id="corr-contract",
        retained_inputs=retained,
    )
    return result["item-contract"], calls


def _stateless_input():
    return {
        "portfolio_snapshot": {
            "portfolio_id": "portfolio-contract",
            "base_currency": "USD",
            "positions": [],
            "cash_balances": [{"currency": "USD", "amount": "100000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "security-contract", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "security-contract", "weight": "1"}]},
        "shelf_entries": [{"instrument_id": "security-contract", "status": "APPROVED"}],
        "options": {},
    }


def test_stateful_item_refuses_mixed_caller_financial_inputs():
    with pytest.raises(ValidationError):
        DpmWaveSimulationItemInput.model_validate(
            {"input_mode": "stateful", "stateless_input": _stateless_input()}
        )


def test_legacy_stateless_item_retains_explicit_counterfactual_input():
    item = DpmWaveSimulationItemInput.model_validate({"stateless_input": _stateless_input()})
    assert item.input_mode == "stateless"
    assert item.stateless_input.portfolio_snapshot.portfolio_id == "portfolio-contract"


def test_stateful_item_needs_no_caller_snapshot_or_scope_assertion():
    item = DpmWaveSimulationItemInput.model_validate(
        {
            "wave_item_id": "item-source-bound",
            "input_mode": "stateful",
            "options_override": {"min_cash_buffer_pct": "0.03"},
        }
    )
    assert item.input_mode == "stateful"
    assert item.stateless_input is None
    assert item.options_override == {"min_cash_buffer_pct": "0.03"}


@pytest.mark.parametrize("field", ["source_context", "tenant_id", "as_of", "stateful_input"])
def test_stateful_item_refuses_caller_owned_source_or_scope_fields(field):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DpmWaveSimulationItemInput.model_validate(
            {"wave_item_id": "item-source-bound", "input_mode": "stateful", field: {}}
        )


def test_stateless_item_requires_explicit_financial_inputs():
    with pytest.raises(ValidationError):
        DpmWaveSimulationItemInput.model_validate({"wave_item_id": "item-source-bound"})


def test_wave_resolution_derives_scope_and_retains_source_hash(monkeypatch):
    payload, calls = _freeze(monkeypatch)
    assert len(calls) == 1
    stateful = calls[0]["envelope"].stateful_input
    assert (
        stateful.portfolio_id,
        stateful.tenant_id,
        stateful.mandate_id,
        stateful.model_portfolio_id,
    ) == ("portfolio-contract", "tenant-contract", "mandate-contract", "model-contract")
    assert stateful.as_of.isoformat() == "2026-04-10"
    assert calls[0]["admitted_tenant_id"] == "tenant-contract"
    assert simulation_input_from_payload(payload).source_context == _source()
    retained, calls = _freeze(monkeypatch, retained={"item-contract": payload})
    assert calls == [] and retained == payload and retained is not payload


def test_stateless_freezing_preserves_legacy_payload(monkeypatch):
    original = {"stateless_input": _stateless_input()}
    frozen, calls = _freeze(monkeypatch, payload=original)
    assert frozen == original and calls == []


@pytest.mark.parametrize(
    "mutation", ["portfolio", "tenant", "mandate", "model", "version", "missing_version"]
)
def test_resolution_refuses_different_checked_source_revision(monkeypatch, mutation):
    source, wave = _source(), _wave()
    if mutation == "portfolio":
        source.context.portfolio_snapshot.portfolio_id = "other"
    elif mutation == "model":
        source.context.source_lineage.model_portfolio_id = "other"
    elif mutation == "missing_version":
        wave.items[0].source_refs = []
    else:
        field = {
            "tenant": "tenant_id",
            "mandate": "mandate_id",
            "version": "mandate_binding_version",
        }[mutation]
        setattr(source.context.policy_context, field, 8 if mutation == "version" else "other")
    with pytest.raises(DpmWaveValidationError, match="differs"):
        _freeze(monkeypatch, wave=wave, source=source)


@pytest.mark.parametrize("options", [{"unknown": "secret"}, {"min_cash_buffer_pct": "invalid"}])
def test_resolution_refuses_unknown_and_invalid_options(monkeypatch, options):
    with pytest.raises(DpmRebalanceEnvelopeValidationError, match="OPTIONS_INVALID"):
        _freeze(monkeypatch, payload={"input_mode": "stateful", "options_override": options})


@pytest.mark.parametrize("mutation", ["state", "mandate", "model"])
def test_resolution_requires_checked_source_scope(monkeypatch, mutation):
    wave = _wave()
    if mutation == "state":
        wave.items[0].state = "REVIEW_REQUIRED"
    else:
        setattr(
            wave.items[0], f"{mutation}_id" if mutation == "mandate" else "model_portfolio_id", None
        )
    with pytest.raises(DpmWaveValidationError, match="source-ready"):
        _freeze(monkeypatch, wave=wave)


def test_retained_retry_rejects_changed_selectors_and_options(monkeypatch):
    frozen, _calls = _freeze(monkeypatch)
    frozen["source_request"]["options_override"] = {"min_cash_buffer_pct": "0.03"}
    with pytest.raises(DpmWaveValidationError, match="different immutable"):
        _freeze(monkeypatch, retained={"item-contract": frozen})


@pytest.mark.parametrize("mutation", ["hash", "missing_context"])
def test_retained_source_context_requires_matching_hash_and_evidence(monkeypatch, mutation):
    frozen, _calls = _freeze(monkeypatch)
    if mutation == "hash":
        frozen["source_context"]["stateful_context_hash"] = "sha256:changed"
    else:
        del frozen["source_context"]
    with pytest.raises(ValueError, match="SOURCE_CONTEXT"):
        simulation_input_from_payload(frozen)


def test_worker_refuses_mutated_frozen_financial_payload(monkeypatch):
    payload, _calls = _freeze(monkeypatch)
    claim = DpmWaveSimulationItemClaim(
        operation_id="op",
        tenant_id="tenant-contract",
        wave_id="wave-contract",
        wave_item_id="item-contract",
        portfolio_id="portfolio-contract",
        input_payload=deepcopy(payload),
        input_hash=hash_canonical_payload(payload),
        source_identity_hash="source",
        worker_id="worker",
        claim_token="token",
        claim_generation=1,
        attempt_count=1,
        lease_expires_at=datetime.now(UTC) + timedelta(minutes=1),
    )
    assert _simulation_inputs_for_claim(claim)["item-contract"].source_context == _source()
    claim.input_payload["stateless_input"]["portfolio_snapshot"]["cash_balances"][0]["amount"] = "1"
    with pytest.raises(ValueError, match="INPUT_HASH_CONFLICT"):
        _simulation_inputs_for_claim(claim)


def test_frozen_source_retains_authority_and_refuses_invalid_context(monkeypatch):
    authority = ConstructionAuthorityContext().model_dump(mode="json")
    frozen, _calls = _freeze(
        monkeypatch,
        payload={"input_mode": "stateful", "options_override": {}, "authority_context": authority},
    )
    assert simulation_input_from_payload(frozen).authority_context == ConstructionAuthorityContext()
    frozen["source_context"] = {"context": "ADVERSARIAL_MARKER"}
    with pytest.raises(ValueError, match="SOURCE_CONTEXT_INVALID"):
        simulation_input_from_payload(frozen)


def test_stateful_resolution_refuses_missing_resolver_evidence(monkeypatch):
    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.resolve_rebalance_request_envelope",
        lambda **_kwargs: (RebalanceRequest.model_validate(_stateless_input()), None),
    )
    with pytest.raises(DpmWaveValidationError, match="source evidence"):
        freeze_wave_inputs(
            wave=_wave(),
            item_inputs={"item-contract": {"input_mode": "stateful"}},
            tenant_id="tenant-contract",
            correlation_id="corr",
        )


def test_worker_publishes_non_retryable_corruption_without_financial_execution(monkeypatch):
    source = _source()
    monkeypatch.setattr(
        "src.api.services.rebalance_simulation_service.resolve_rebalance_request_envelope",
        lambda **_kwargs: (RebalanceRequest.model_validate(_stateless_input()), source),
    )
    repository = InMemoryDpmWaveRepository()
    repository.save_wave(
        wave=_wave(), tenant_id="tenant-contract", idempotency_key=None, request_hash=None
    )
    operation, _replay = wave_simulation_operations.admit_wave_simulation_operation(
        wave_id="wave-contract",
        tenant_id="tenant-contract",
        actor_id="pm",
        correlation_id="corr",
        idempotency_key="idempotency",
        item_payloads=[
            {"wave_item_id": "item-contract", "input_mode": "stateful", "options_override": {}}
        ],
        methods=None,
        max_concurrency=1,
        max_attempts=3,
        repository=repository,
    )
    now = datetime.now(UTC)
    claim = repository.claim_simulation_items(
        tenant_id="tenant-contract",
        operation_id=operation.operation_id,
        worker_id="worker",
        limit=1,
        claimed_at=now,
        lease_expires_at=now + timedelta(minutes=1),
    )[0]
    claim.input_payload["stateless_input"]["portfolio_snapshot"]["cash_balances"][0]["amount"] = "1"

    def unexpected(**_kwargs):
        pytest.fail("Corrupt admitted inputs must not enter financial calculation")

    monkeypatch.setattr(wave_simulation_operations, "simulate_item", unexpected)
    assert not wave_simulation_operations._execute_claim(
        claim=claim,
        repository=repository,
        construction_repository=InMemoryConstructionRepository(),
        run_service=DpmRunSupportService(repository=InMemoryDpmRunRepository()),
        risk_authority_client=None,
        methods=None,
    )
    failed = repository.list_simulation_items(
        tenant_id="tenant-contract", operation_id=operation.operation_id, limit=1, offset=0
    ).items[0]
    assert (failed.status, failed.retryable, failed.error_code) == (
        "FAILED",
        False,
        "DPM_WAVE_SIMULATION_INPUT_HASH_CONFLICT",
    )
