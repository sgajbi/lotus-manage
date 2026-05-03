from __future__ import annotations

import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timezone

from src.core.mandates import DpmMandateDigitalTwin
from src.core.mandate_repository import DpmMandateRepository
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmRebalanceWaveItem,
    DpmWaveAggregateMetrics,
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveRepository,
    DpmWaveSourceRef,
    DpmWaveVersionConflictError,
    DpmWaveTrigger,
    WaveItemState,
    WaveState,
    apply_wave_transition,
)
from src.core.waves.source_readiness import classify_wave_item_source_readiness


SUPPORTED_CREATE_TRIGGER_TYPES = {"EXPLICIT_PORTFOLIO_LIST"}


class DpmWaveValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DpmWaveLookupError(LookupError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def preview_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWave:
    _validate_trigger(trigger_type)
    items = [
        _build_item(
            index=index,
            portfolio=portfolio,
            mandate_repository=mandate_repository,
        )
        for index, portfolio in enumerate(portfolios, start=1)
    ]
    wave = DpmRebalanceWave(
        wave_id=f"dwv_preview_{uuid.uuid4().hex[:12]}",
        state="DRAFT",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id=trigger_id,
            rationale=rationale,
            source_refs=_trigger_source_refs(portfolios),
        ),
        as_of_date=as_of_date,
        created_at=datetime.now(timezone.utc),
        created_by=actor_id,
        correlation_id=correlation_id,
        items=items,
        aggregate_metrics=_aggregate(items),
    )
    return apply_wave_transition(
        wave=wave,
        to_state="PREVIEWED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="DRAFT",
            to_state="PREVIEWED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_PREVIEWED",
            metadata={"item_count": len(items)},
        ),
    )


def create_wave(
    *,
    trigger_type: str,
    trigger_id: str,
    rationale: str,
    as_of_date: str,
    actor_id: str,
    correlation_id: str,
    portfolios: list[dict[str, object]],
    idempotency_key: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    request_hash = _request_hash(
        {
            "trigger_type": trigger_type,
            "trigger_id": trigger_id,
            "rationale": rationale,
            "as_of_date": as_of_date,
            "actor_id": actor_id,
            "portfolios": portfolios,
        }
    )
    existing = wave_repository.get_wave_by_idempotency(idempotency_key=idempotency_key)
    if existing is not None:
        return existing, True

    preview = preview_wave(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        mandate_repository=mandate_repository,
    )
    wave = preview.model_copy(update={"wave_id": f"dwv_{uuid.uuid4().hex[:12]}"}, deep=True)
    wave = wave.model_copy(
        update={
            "events": [
                event.model_copy(update={"wave_id": wave.wave_id}, deep=True)
                for event in wave.events
            ]
        },
        deep=True,
    )
    wave = apply_wave_transition(
        wave=wave,
        to_state="CREATED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="PREVIEWED",
            to_state="CREATED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_CREATED",
            metadata={"idempotency_key_hash": hashlib.sha256(idempotency_key.encode()).hexdigest()},
        ),
    )
    try:
        wave_repository.save_wave(
            wave=wave,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except (DpmWaveAlreadyExistsError, DpmWaveIdempotencyConflictError) as exc:
        raise DpmWaveValidationError("WAVE_CREATE_CONFLICT", str(exc)) from exc
    return wave, False


def source_check_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = wave_repository.get_wave(wave_id=wave_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    if wave.state == "SOURCE_CHECKED":
        return wave, True
    if wave.state != "CREATED":
        raise DpmWaveValidationError(
            "DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
            f"Wave {wave_id} cannot be source-checked from state {wave.state}.",
        )

    classified_items = [
        _classify_item_source_readiness(
            item=item,
            wave_as_of_date=wave.as_of_date,
            mandate_repository=mandate_repository,
        )
        for item in wave.items
    ]
    candidate = wave.model_copy(
        update={
            "items": classified_items,
            "aggregate_metrics": _aggregate(classified_items),
        },
        deep=True,
    )
    checked = apply_wave_transition(
        wave=candidate,
        to_state="SOURCE_CHECKED",
        event=_event(
            wave_id=wave.wave_id,
            from_state="CREATED",
            to_state="SOURCE_CHECKED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SOURCE_CHECKED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
                "review_required_item_count": (
                    candidate.aggregate_metrics.review_required_item_count
                ),
                "source_degraded_item_count": (
                    candidate.aggregate_metrics.source_degraded_item_count
                ),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=checked, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return checked, False


def _build_item(
    *,
    index: int,
    portfolio: dict[str, object],
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWaveItem:
    portfolio_id = str(portfolio["portfolio_id"]).strip()
    mandate_id = _optional_str(portfolio.get("mandate_id"))
    source_refs = _source_refs_from_portfolio(portfolio)
    latest_mandate = mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if latest_mandate is not None:
        mandate_id = latest_mandate.mandate_id
        source_refs.append(
            DpmWaveSourceRef(
                source_system="lotus-manage",
                source_type="MANDATE_DIGITAL_TWIN",
                source_id=latest_mandate.mandate_id,
                source_version=latest_mandate.mandate_version,
                supportability_state="READY",
            )
        )

    if source_refs:
        state: WaveItemState = "CANDIDATE"
        reason_codes = ["AFFECTED_PORTFOLIO_SOURCE_READY"]
        diagnostics = {"source_posture": "candidate_evidence_available"}
    else:
        state = "SOURCE_BLOCKED"
        reason_codes = ["MISSING_AFFECTED_PORTFOLIO_SOURCE"]
        diagnostics = {
            "source_owner": "caller_or_lotus-core",
            "required_action": "SUPPLY_SOURCE_REF",
        }

    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{index:03d}_{uuid.uuid4().hex[:8]}",
        portfolio_id=portfolio_id,
        mandate_id=mandate_id,
        state=state,
        reason_codes=reason_codes,
        source_refs=source_refs,
        diagnostics=diagnostics,
    )


def _classify_item_source_readiness(
    *,
    item: DpmRebalanceWaveItem,
    wave_as_of_date: str,
    mandate_repository: DpmMandateRepository,
) -> DpmRebalanceWaveItem:
    twin = _resolve_mandate_twin(item=item, mandate_repository=mandate_repository)
    health = (
        mandate_repository.get_latest_health_snapshot(mandate_id=twin.mandate_id)
        if twin is not None
        else None
    )
    return classify_wave_item_source_readiness(
        item=item,
        wave_as_of_date=wave_as_of_date,
        mandate_twin=twin,
        mandate_health=health,
    )


def _resolve_mandate_twin(
    *,
    item: DpmRebalanceWaveItem,
    mandate_repository: DpmMandateRepository,
) -> DpmMandateDigitalTwin | None:
    if item.mandate_id:
        twin = mandate_repository.get_latest_mandate(mandate_id=item.mandate_id)
        if twin is not None and twin.portfolio_id == item.portfolio_id:
            return twin
    return mandate_repository.get_latest_mandate_by_portfolio(portfolio_id=item.portfolio_id)


def _aggregate(items: list[DpmRebalanceWaveItem]) -> DpmWaveAggregateMetrics:
    state_counts = Counter(item.state for item in items)
    state_count_map = {str(state): count for state, count in state_counts.items()}
    return DpmWaveAggregateMetrics(
        item_count=len(items),
        state_counts=state_count_map,
        ready_item_count=state_counts.get("SOURCE_READY", 0)
        + state_counts.get("SIMULATED", 0)
        + state_counts.get("SELECTED", 0)
        + state_counts.get("PROOF_PACK_READY", 0)
        + state_counts.get("APPROVED", 0)
        + state_counts.get("STAGED", 0)
        + state_counts.get("HANDOFF_READY", 0),
        blocked_item_count=state_counts.get("SOURCE_BLOCKED", 0)
        + state_counts.get("SIMULATION_BLOCKED", 0),
        review_required_item_count=state_counts.get("REVIEW_REQUIRED", 0),
        source_degraded_item_count=state_counts.get("SOURCE_DEGRADED", 0),
    )


def _trigger_source_refs(portfolios: list[dict[str, object]]) -> list[DpmWaveSourceRef]:
    refs: list[DpmWaveSourceRef] = []
    for portfolio in portfolios:
        refs.extend(_source_refs_from_portfolio(portfolio))
    return refs


def _source_refs_from_portfolio(portfolio: dict[str, object]) -> list[DpmWaveSourceRef]:
    source_refs = portfolio.get("source_refs", [])
    if not isinstance(source_refs, list):
        return []
    return [
        DpmWaveSourceRef.model_validate(source_ref)
        for source_ref in source_refs
        if isinstance(source_ref, dict)
    ]


def _event(
    *,
    wave_id: str,
    from_state: WaveState,
    to_state: WaveState,
    actor_id: str,
    correlation_id: str,
    reason_code: str,
    metadata: dict[str, object],
) -> DpmRebalanceWaveEvent:
    return DpmRebalanceWaveEvent(
        event_id=f"dwe_{uuid.uuid4().hex[:12]}",
        wave_id=wave_id,
        from_state=from_state,
        to_state=to_state,
        event_type="STATE_TRANSITION",
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        metadata=metadata,
    )


def _validate_trigger(trigger_type: str) -> None:
    if trigger_type not in SUPPORTED_CREATE_TRIGGER_TYPES:
        raise DpmWaveValidationError(
            "NOT_SUPPORTED_TRIGGER",
            f"Trigger type {trigger_type} is not supported for RFC-0041 Slice 4.",
    )


def _request_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
