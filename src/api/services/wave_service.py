import uuid

from src.api.request_models import RebalanceRequest
from src.api.services import construction_service
from src.api.services.wave_aggregate_metrics import (
    simulation_result_state,
)
from src.api.services.wave_creation import (
    create_wave_request_hash as _create_wave_request_hash,
    promote_preview_to_created_wave as _promote_preview_to_created_wave,
)
from src.api.services.wave_event_evidence import (
    build_wave_event as _event,
)
from src.api.services.wave_event_append import append_same_state_event as _append_event
from src.api.services.wave_errors import (
    DpmWaveLookupError as DpmWaveLookupError,
    DpmWaveValidationError as DpmWaveValidationError,
)
from src.api.services.wave_detail_projection import wave_detail_payload, wave_items_payload
from src.api.services.wave_handoff_evidence import build_handoff_ref as _handoff_ref
from src.api.services.wave_item_transitions import (
    approve_item as _approve_item,
    cancel_item as _cancel_item,
    handoff_item as _handoff_item,
    stage_item as _stage_item,
)
from src.api.services.wave_item_collection import (
    wave_with_items_and_aggregate as _wave_with_items_and_aggregate,
)
from src.api.services.wave_lookup import get_wave_or_raise as _get_wave_or_raise
from src.api.services.wave_persistence import (
    save_wave_or_raise as _save_wave_or_raise,
    update_wave_or_raise as _update_wave_or_raise,
)
from src.api.services.wave_preview import build_preview_wave
from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_report_context import portfolio_memory_context_for_report
from src.api.services.wave_selection_item import (
    with_selection_and_proof_pack as _with_selection_and_proof_pack,
)
from src.api.services.wave_selection_guard import selectable_wave_item as _selectable_wave_item
from src.api.services.wave_search import search_wave_summaries
from src.api.services.wave_simulation import build_simulated_wave
from src.api.services.wave_simulation_item import (
    DpmWaveSimulationInput as DpmWaveSimulationInput,
)
from src.api.services.wave_source_check import build_source_checked_wave
from src.api.services.wave_state_guard import (
    require_wave_state as _require_wave_state,
    wave_state_is_idempotent as _wave_state_is_idempotent,
)
from src.api.services.wave_supportability_payload import (
    wave_supportability_payload as _wave_supportability_payload,
)
from src.api.services.wave_trigger_validation import validate_trigger_or_raise
from src.api.services.wave_workflow_metadata import (
    approval_event_metadata as _approval_event_metadata,
    cancel_event_metadata as _cancel_event_metadata,
    handoff_event_metadata as _handoff_event_metadata,
    stage_event_metadata as _stage_event_metadata,
)
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveInvalidTransitionError,
    DpmWaveRepository,
    DpmWaveReportInputBoundaryError,
    DpmWaveReportInput,
    WaveState,
    apply_wave_transition,
    build_wave_report_input,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient

_simulation_result_state = simulation_result_state
_validate_trigger = validate_trigger_or_raise


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
    return build_preview_wave(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        mandate_repository=mandate_repository,
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
    request_hash = _create_wave_request_hash(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        portfolios=portfolios,
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
    wave = _promote_preview_to_created_wave(
        preview=preview,
        wave_id=f"dwv_{uuid.uuid4().hex[:12]}",
        actor_id=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
    )
    _save_wave_or_raise(
        wave_repository=wave_repository,
        wave=wave,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
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
    if _wave_state_is_idempotent(wave, replay_states={"SOURCE_CHECKED"}):
        return wave, True
    _require_wave_state(
        wave,
        allowed_states={"CREATED"},
        error_code="DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
        action_phrase="be source-checked",
    )

    checked = build_source_checked_wave(
        wave=wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
    )
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=checked,
        expected_version=wave.version,
    )
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
    if _wave_state_is_idempotent(
        wave,
        replay_states={"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"},
    ):
        return wave, True
    _require_wave_state(
        wave,
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )

    completed = build_simulated_wave(
        wave=wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        item_inputs=item_inputs,
        methods=methods,
        construction_repository=construction_repository,
        run_service=run_service,
        risk_authority_client=risk_authority_client,
    )
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=completed,
        expected_version=wave.version,
    )
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
    _require_wave_state(
        wave,
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED"},
        error_code="DPM_WAVE_SELECTION_INVALID_STATE",
        action_phrase="record alternative selection",
    )
    selected_item = _selectable_wave_item(wave=wave, wave_item_id=wave_item_id)
    assert selected_item.alternative_set_id is not None
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
        wave=_wave_with_items_and_aggregate(wave=wave, items=updated_items),
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
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=updated,
        expected_version=wave.version,
    )
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
    if _wave_state_is_idempotent(
        wave,
        replay_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
    ):
        return wave, True
    _require_wave_state(
        wave,
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED", "REVIEW_REQUIRED"},
        error_code="DPM_WAVE_APPROVAL_INVALID_STATE",
        action_phrase="be approved",
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
    candidate = _wave_with_items_and_aggregate(wave=wave, items=approved_items)
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
            metadata=_approval_event_metadata(
                approved_item_count=approved_count,
                total_item_count=len(approved_items),
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=approved,
        expected_version=wave.version,
    )
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
    if _wave_state_is_idempotent(wave, replay_states={"STAGED", "HANDOFF_READY"}):
        return wave, True
    _require_wave_state(
        wave,
        allowed_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
        error_code="DPM_WAVE_STAGE_INVALID_STATE",
        action_phrase="be staged",
    )

    staged_items = [_stage_item(item, actor_id, reason_code, comment) for item in wave.items]
    staged_count = sum(1 for item in staged_items if item.state == "STAGED")
    if staged_count == 0:
        raise DpmWaveValidationError(
            "DPM_WAVE_STAGE_NO_ELIGIBLE_ITEMS",
            f"Wave {wave_id} has no approved items to stage.",
        )

    candidate = _wave_with_items_and_aggregate(wave=wave, items=staged_items)
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
            metadata=_stage_event_metadata(
                staged_item_count=staged_count,
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=staged,
        expected_version=wave.version,
    )
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
    if _wave_state_is_idempotent(wave, replay_states={"HANDOFF_READY"}):
        return wave, True
    _require_wave_state(
        wave,
        allowed_states={"STAGED"},
        error_code="DPM_WAVE_HANDOFF_INVALID_STATE",
        action_phrase="create handoff evidence",
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
    candidate = _wave_with_items_and_aggregate(
        wave=wave,
        items=handoff_items,
        extra_updates={"handoff_refs": [*wave.handoff_refs, handoff_ref]},
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
            metadata=_handoff_event_metadata(
                handoff_ref=handoff_ref,
                handoff_item_count=len(handoff_item_ids),
                reason_code=reason_code,
                comment=comment,
            ),
        ),
    )
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=handoff_ready,
        expected_version=wave.version,
    )
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
    if _wave_state_is_idempotent(wave, replay_states={"CANCELLED"}):
        return wave, True

    cancelled_items = [_cancel_item(item, actor_id, reason_code, comment) for item in wave.items]
    candidate = _wave_with_items_and_aggregate(wave=wave, items=cancelled_items)
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
                metadata=_cancel_event_metadata(
                    cancelled_item_count=len(cancelled_items),
                    reason_code=reason_code,
                    comment=comment,
                ),
            ),
        )
    except DpmWaveInvalidTransitionError as exc:
        raise DpmWaveValidationError(
            "DPM_WAVE_CANCEL_INVALID_STATE",
            f"Wave {wave_id} cannot be cancelled from state {wave.state}.",
        ) from exc
    _update_wave_or_raise(
        wave_repository=wave_repository,
        wave=cancelled,
        expected_version=wave.version,
    )
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
