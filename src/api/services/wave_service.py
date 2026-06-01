from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import cast

from src.api.request_models import RebalanceRequest
from src.api.services import construction_service
from src.api.services.wave_aggregate_metrics import (
    aggregate_wave_items as _aggregate,
    simulation_result_state as _simulation_result_state,
)
from src.api.services.wave_event_evidence import (
    build_wave_event as _event,
    idempotency_key_hash as _idempotency_key_hash,
    request_hash as _request_hash,
)
from src.api.services.wave_detail_projection import wave_detail_payload, wave_items_payload
from src.api.services.wave_handoff_evidence import build_handoff_ref as _handoff_ref
from src.api.services.wave_item_transitions import (
    approve_item as _approve_item,
    cancel_item as _cancel_item,
    handoff_item as _handoff_item,
    stage_item as _stage_item,
)
from src.api.services.wave_item_builder import build_wave_item as _build_item
from src.api.services.wave_portfolio_sources import trigger_source_refs as _trigger_source_refs
from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_report_context import portfolio_memory_context_for_report
from src.api.services.wave_selection_item import (
    with_selection_and_proof_pack as _with_selection_and_proof_pack,
)
from src.api.services.wave_search import search_wave_summaries
from src.api.services.wave_simulation_item import (
    DpmWaveSimulationInput,
    simulate_item as _simulate_item,
)
from src.api.services.wave_source_readiness import (
    classify_item_source_readiness as _classify_item_source_readiness,
)
from src.api.services.wave_supportability_payload import (
    wave_supportability_payload as _wave_supportability_payload,
)
from src.api.services.wave_trigger_validation import trigger_validation_failure
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmRebalanceWaveEvent,
    DpmWaveAlreadyExistsError,
    DpmWaveIdempotencyConflictError,
    DpmWaveInvalidTransitionError,
    DpmWaveRepository,
    DpmWaveReportInputBoundaryError,
    DpmWaveReportInput,
    DpmWaveVersionConflictError,
    DpmWaveTrigger,
    WaveTriggerType,
    WaveState,
    apply_wave_transition,
    build_wave_report_input,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient


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
    _validate_trigger(trigger_type, portfolios=portfolios)
    validated_trigger_type = cast(WaveTriggerType, trigger_type)
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
            trigger_type=validated_trigger_type,
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
            metadata={"idempotency_key_hash": _idempotency_key_hash(idempotency_key)},
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
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
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


def simulate_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    item_inputs: dict[str, RebalanceRequest | DpmWaveSimulationInput],
    methods: list[ConstructionMethod] | None,
    construction_repository: ConstructionRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
    risk_authority_client: LotusRiskAuthorityClient | None = None,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"}:
        return wave, True
    if wave.state != "SOURCE_CHECKED":
        raise DpmWaveValidationError(
            "DPM_WAVE_SIMULATION_INVALID_STATE",
            f"Wave {wave_id} cannot be simulated from state {wave.state}.",
        )

    simulating = apply_wave_transition(
        wave=wave,
        to_state="SIMULATING",
        event=_event(
            wave_id=wave.wave_id,
            from_state="SOURCE_CHECKED",
            to_state="SIMULATING",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_STARTED",
            metadata={"ready_item_count": wave.aggregate_metrics.ready_item_count},
        ),
    )
    simulated_items = [
        _simulate_item(
            item=item,
            correlation_id=correlation_id,
            item_inputs=item_inputs,
            methods=methods,
            construction_repository=construction_repository,
            run_service=run_service,
            risk_authority_client=risk_authority_client,
        )
        for item in simulating.items
    ]
    candidate = simulating.model_copy(
        update={
            "items": simulated_items,
            "aggregate_metrics": _aggregate(simulated_items),
        },
        deep=True,
    )
    to_state = _simulation_result_state(simulated_items)
    completed = apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=_event(
            wave_id=wave.wave_id,
            from_state="SIMULATING",
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_SIMULATION_COMPLETED",
            metadata={
                "state_counts": candidate.aggregate_metrics.state_counts,
                "ready_item_count": candidate.aggregate_metrics.ready_item_count,
                "blocked_item_count": candidate.aggregate_metrics.blocked_item_count,
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=completed, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return completed, False


def select_wave_item_alternative(
    *,
    wave_id: str,
    wave_item_id: str,
    alternative_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state not in {"SIMULATED", "PARTIALLY_SIMULATED"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_SELECTION_INVALID_STATE",
            f"Wave {wave_id} cannot record alternative selection from state {wave.state}.",
        )
    selected_item = next((item for item in wave.items if item.wave_item_id == wave_item_id), None)
    if selected_item is None:
        raise DpmWaveLookupError("DPM_WAVE_ITEM_NOT_FOUND", f"Wave item {wave_item_id} not found.")
    if selected_item.alternative_set_id is None:
        raise DpmWaveValidationError(
            "DPM_WAVE_ITEM_ALTERNATIVES_MISSING",
            f"Wave item {wave_item_id} has no generated alternatives.",
        )
    try:
        construction_service.select_construction_alternative(
            repository=construction_repository,
            alternative_set_id=selected_item.alternative_set_id,
            alternative_id=alternative_id,
            actor_id=actor_id,
            reason_code=reason_code,
            comment=comment,
            correlation_id=correlation_id,
        )
    except Exception as exc:
        raise DpmWaveLookupError("DPM_CONSTRUCTION_ALTERNATIVE_NOT_FOUND", str(exc)) from exc

    updated_item = _with_selection_and_proof_pack(
        item=selected_item,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        generate_proof_pack=generate_proof_pack,
        construction_repository=construction_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )
    updated_items = [
        updated_item if item.wave_item_id == wave_item_id else item for item in wave.items
    ]
    updated = _append_event(
        wave=wave.model_copy(
            update={
                "items": updated_items,
                "aggregate_metrics": _aggregate(updated_items),
            },
            deep=True,
        ),
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=wave.state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_ITEM_ALTERNATIVE_SELECTED",
            event_type="ITEM_SELECTION",
            metadata={
                "wave_item_id": wave_item_id,
                "alternative_set_id": selected_item.alternative_set_id,
                "selected_alternative_id": alternative_id,
                "proof_pack_id": updated_item.proof_pack_id,
                "proof_pack_state": updated_item.diagnostics.get("proof_pack_state"),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=updated, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return updated


def approve_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"APPROVED", "APPROVED_WITH_EXCEPTIONS"}:
        return wave, True
    if wave.state not in {"SIMULATED", "PARTIALLY_SIMULATED", "REVIEW_REQUIRED"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_APPROVAL_INVALID_STATE",
            f"Wave {wave_id} cannot be approved from state {wave.state}.",
        )

    approved_items = [_approve_item(item, actor_id, reason_code, comment) for item in wave.items]
    approved_count = sum(1 for item in approved_items if item.state == "APPROVED")
    if approved_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_APPROVAL_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no selected or proof-pack-ready items to approve.",
        )

    to_state: WaveState = (
        "APPROVED" if approved_count == len(approved_items) else "APPROVED_WITH_EXCEPTIONS"
    )
    candidate = wave.model_copy(
        update={
            "items": approved_items,
            "aggregate_metrics": _aggregate(approved_items),
        },
        deep=True,
    )
    approved = apply_wave_transition(
        wave=candidate,
        to_state=to_state,
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state=to_state,
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_APPROVED",
            metadata={
                "approved_item_count": approved_count,
                "exception_item_count": len(approved_items) - approved_count,
                "approval_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=approved, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return approved, False


def stage_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state in {"STAGED", "HANDOFF_READY"}:
        return wave, True
    if wave.state not in {"APPROVED", "APPROVED_WITH_EXCEPTIONS"}:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_INVALID_STATE",
            f"Wave {wave_id} cannot be staged from state {wave.state}.",
        )

    staged_items = [_stage_item(item, actor_id, reason_code, comment) for item in wave.items]
    staged_count = sum(1 for item in staged_items if item.state == "STAGED")
    if staged_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no approved items to stage.",
        )

    candidate = wave.model_copy(
        update={
            "items": staged_items,
            "aggregate_metrics": _aggregate(staged_items),
        },
        deep=True,
    )
    staged = apply_wave_transition(
        wave=candidate,
        to_state="STAGED",
        event=_event(
            wave_id=wave.wave_id,
            from_state=wave.state,
            to_state="STAGED",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_STAGED",
            metadata={
                "staged_item_count": staged_count,
                "stage_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=staged, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return staged, False


def handoff_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state == "HANDOFF_READY":
        return wave, True
    if wave.state != "STAGED":
        raise DpmWaveValidationError(
            "DPM_WAVE_HANDOFF_INVALID_STATE",
            f"Wave {wave_id} cannot create handoff evidence from state {wave.state}.",
        )

    handoff_items = [_handoff_item(item, actor_id, reason_code, comment) for item in wave.items]
    handoff_item_ids = [
        item.wave_item_id for item in handoff_items if item.state == "HANDOFF_READY"
    ]
    if not handoff_item_ids:
        raise DpmWaveValidationError(
            "DPM_WAVE_HANDOFF_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no staged items for operations handoff.",
        )

    handoff_ref = _handoff_ref(
        wave_id=wave.wave_id,
        item_ids=handoff_item_ids,
        actor_id=actor_id,
        reason_code=reason_code,
        correlation_id=correlation_id,
        comment=comment,
    )
    candidate = wave.model_copy(
        update={
            "items": handoff_items,
            "aggregate_metrics": _aggregate(handoff_items),
            "handoff_refs": [*wave.handoff_refs, handoff_ref],
        },
        deep=True,
    )
    handoff_ready = apply_wave_transition(
        wave=candidate,
        to_state="HANDOFF_READY",
        event=_event(
            wave_id=wave.wave_id,
            from_state="STAGED",
            to_state="HANDOFF_READY",
            actor_id=actor_id,
            correlation_id=correlation_id,
            reason_code="WAVE_HANDOFF_READY",
            metadata={
                "handoff_ref_id": handoff_ref.handoff_ref_id,
                "handoff_item_count": len(handoff_item_ids),
                "external_execution_claimed": False,
                "handoff_reason_code": reason_code,
                **({"comment": comment} if comment else {}),
            },
        ),
    )
    try:
        wave_repository.update_wave(wave=handoff_ready, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return handoff_ready, False


def cancel_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    if wave.state == "CANCELLED":
        return wave, True

    cancelled_items = [_cancel_item(item, actor_id, reason_code, comment) for item in wave.items]
    candidate = wave.model_copy(
        update={
            "items": cancelled_items,
            "aggregate_metrics": _aggregate(cancelled_items),
        },
        deep=True,
    )
    try:
        cancelled = apply_wave_transition(
            wave=candidate,
            to_state="CANCELLED",
            event=_event(
                wave_id=wave.wave_id,
                from_state=wave.state,
                to_state="CANCELLED",
                actor_id=actor_id,
                correlation_id=correlation_id,
                reason_code="WAVE_CANCELLED",
                metadata={
                    "cancel_reason_code": reason_code,
                    "cancelled_item_count": len(cancelled_items),
                    "external_execution_claimed": False,
                    **({"comment": comment} if comment else {}),
                },
            ),
        )
    except DpmWaveInvalidTransitionError as exc:
        raise DpmWaveValidationError(
            "DPM_WAVE_CANCEL_INVALID_STATE",
            f"Wave {wave_id} cannot be cancelled from state {wave.state}.",
        ) from exc
    try:
        wave_repository.update_wave(wave=cancelled, expected_version=wave.version)
    except DpmWaveVersionConflictError as exc:
        raise DpmWaveValidationError("DPM_WAVE_VERSION_CONFLICT", str(exc)) from exc
    return cancelled, False


def wave_supportability_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    return _wave_supportability_payload(wave)


def wave_supportability(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_supportability_payload(wave)


def search_waves(
    *,
    wave_repository: DpmWaveRepository,
    state: str | None = None,
    trigger_type: str | None = None,
    as_of_date: str | None = None,
    supportability_state: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    return search_wave_summaries(
        wave_repository=wave_repository,
        state=state,
        trigger_type=trigger_type,
        as_of_date=as_of_date,
        supportability_state=supportability_state,
        limit=limit,
        offset=offset,
    )


def retrieve_wave_detail(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_detail_payload(wave)


def list_wave_items(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return wave_items_payload(wave)


def proof_pack_posture(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    return proof_pack_posture_for_wave(wave=wave)


def get_report_input(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmWaveReportInput:
    wave = _get_wave_or_raise(wave_id=wave_id, wave_repository=wave_repository)
    supportability = wave_supportability_payload(wave)
    proof_pack_posture_payload = proof_pack_posture_for_wave(wave=wave)
    try:
        return build_wave_report_input(
            wave=wave,
            supportability=supportability,
            proof_pack_posture=proof_pack_posture_payload,
            portfolio_memory_context=portfolio_memory_context_for_report(
                wave=wave,
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_review_repository,
                mandate_repository=mandate_repository,
            ),
        )
    except DpmWaveReportInputBoundaryError as exc:
        raise DpmWaveValidationError("DPM_WAVE_EXTERNAL_EXECUTION_BOUNDARY", str(exc)) from exc


def _get_wave_or_raise(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    wave = wave_repository.get_wave(wave_id=wave_id)
    if wave is None:
        raise DpmWaveLookupError("DPM_WAVE_NOT_FOUND", f"Wave {wave_id} was not found.")
    return wave


def _append_event(
    *,
    wave: DpmRebalanceWave,
    event: DpmRebalanceWaveEvent,
) -> DpmRebalanceWave:
    if event.wave_id != wave.wave_id:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_WAVE_MISMATCH", "Wave event mismatch.")
    if event.from_state != wave.state or event.to_state != wave.state:
        raise DpmWaveValidationError("DPM_WAVE_EVENT_STATE_MISMATCH", "Wave event state mismatch.")
    return wave.model_copy(
        update={"version": wave.version + 1, "events": [*wave.events, event]},
        deep=True,
    )


def _validate_trigger(trigger_type: str, *, portfolios: list[dict[str, object]]) -> None:
    failure = trigger_validation_failure(trigger_type, portfolios=portfolios)
    if failure is not None:
        code, message = failure
        raise DpmWaveValidationError(code, message)
