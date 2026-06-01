from src.api.request_models import RebalanceRequest
from src.api.services.wave_aggregate_metrics import (
    simulation_result_state,
)
from src.api.services.wave_approval_transition import build_approved_wave as _build_approved_wave
from src.api.services.wave_cancel_transition import build_cancelled_wave as _build_cancelled_wave
from src.api.services.wave_construction_selection import (
    select_construction_alternative_for_wave as _select_construction_alternative_for_wave,
)
from src.api.services.wave_creation import (
    create_created_wave_id as _create_created_wave_id,
    create_wave_request_hash as _create_wave_request_hash,
    promote_preview_to_created_wave as _promote_preview_to_created_wave,
)
from src.api.services.wave_errors import (
    DpmWaveLookupError as DpmWaveLookupError,
    DpmWaveValidationError as DpmWaveValidationError,
)
from src.api.services.wave_detail_projection import wave_detail_payload, wave_items_payload
from src.api.services.wave_event_append import append_same_state_event
from src.api.services.wave_event_evidence import build_wave_event
from src.api.services.wave_handoff_transition import (
    build_handoff_ready_wave as _build_handoff_ready_wave,
)
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_selection_transition import (
    build_wave_with_selected_item_alternative as _build_wave_with_selected_item_alternative,
)
from src.api.services.wave_lookup import get_wave_or_raise as _get_wave_or_raise
from src.api.services.wave_persistence import (
    save_wave_or_raise as _save_wave_or_raise,
    update_wave_or_raise,
)
from src.api.services.wave_preview import build_preview_wave
from src.api.services.wave_proof_pack_posture import proof_pack_posture_for_wave
from src.api.services.wave_report_input import build_report_input_for_wave
from src.api.services.wave_selection_guard import selectable_wave_item as _selectable_wave_item
from src.api.services.wave_search import search_wave_summaries
from src.api.services.wave_simulation import build_simulated_wave
from src.api.services.wave_simulation_item import (
    DpmWaveSimulationInput as DpmWaveSimulationInput,
)
from src.api.services.wave_source_check import build_source_checked_wave
from src.api.services.wave_state_guard import (
    require_wave_state,
    wave_state_is_idempotent,
)
from src.api.services.wave_stage_transition import build_staged_wave as _build_staged_wave
from src.api.services.wave_supportability_payload import (
    wave_supportability_payload as _wave_supportability_payload,
)
from src.api.services.wave_transition_execution import (
    persist_transitioned_wave,
    prepare_wave_transition,
)
from src.api.services.wave_trigger_validation import validate_trigger_or_raise
from src.api.services.wave_workflow_metadata import (
    approval_event_metadata,
    cancel_event_metadata,
    handoff_event_metadata,
    selection_event_metadata,
    stage_event_metadata,
)
from src.core.construction.repository import ConstructionRepository
from src.core.construction.vocabulary import ConstructionMethod
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves import (
    DpmRebalanceWave,
    DpmWaveRepository,
    DpmWaveReportInput,
)
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.infrastructure.risk_authority import LotusRiskAuthorityClient

_simulation_result_state = simulation_result_state
_wave_state_is_idempotent = wave_state_is_idempotent
_require_wave_state = require_wave_state
_update_wave_or_raise = update_wave_or_raise
_validate_trigger = validate_trigger_or_raise
_approval_event_metadata = approval_event_metadata
_stage_event_metadata = stage_event_metadata
_handoff_event_metadata = handoff_event_metadata
_cancel_event_metadata = cancel_event_metadata
_selection_event_metadata = selection_event_metadata
_event = build_wave_event
_append_event = append_same_state_event
_wave_with_items_and_aggregate = wave_with_items_and_aggregate
_prepare_wave_transition = prepare_wave_transition
_persist_transitioned_wave = persist_transitioned_wave


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
        wave_id=_create_created_wave_id(),
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"SOURCE_CHECKED"},
        allowed_states={"CREATED"},
        error_code="DPM_WAVE_SOURCE_CHECK_INVALID_STATE",
        action_phrase="be source-checked",
    )
    if prepared.replayed:
        return prepared.wave, True

    checked = build_source_checked_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=checked,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"SIMULATED", "PARTIALLY_SIMULATED", "SIMULATION_FAILED"},
        allowed_states={"SOURCE_CHECKED"},
        error_code="DPM_WAVE_SIMULATION_INVALID_STATE",
        action_phrase="be simulated",
    )
    if prepared.replayed:
        return prepared.wave, True

    completed = build_simulated_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        correlation_id=correlation_id,
        item_inputs=item_inputs,
        methods=methods,
        construction_repository=construction_repository,
        run_service=run_service,
        risk_authority_client=risk_authority_client,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=completed,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states=set(),
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED"},
        error_code="DPM_WAVE_SELECTION_INVALID_STATE",
        action_phrase="record alternative selection",
    )
    selected_item = _selectable_wave_item(wave=prepared.wave, wave_item_id=wave_item_id)
    assert selected_item.alternative_set_id is not None
    _select_construction_alternative_for_wave(
        repository=construction_repository,
        alternative_set_id=selected_item.alternative_set_id,
        alternative_id=alternative_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )

    updated = _build_wave_with_selected_item_alternative(
        wave=prepared.wave,
        selected_item=selected_item,
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
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=updated,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
        allowed_states={"SIMULATED", "PARTIALLY_SIMULATED", "REVIEW_REQUIRED"},
        error_code="DPM_WAVE_APPROVAL_INVALID_STATE",
        action_phrase="be approved",
    )
    if prepared.replayed:
        return prepared.wave, True

    approved = _build_approved_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=approved,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"STAGED", "HANDOFF_READY"},
        allowed_states={"APPROVED", "APPROVED_WITH_EXCEPTIONS"},
        error_code="DPM_WAVE_STAGE_INVALID_STATE",
        action_phrase="be staged",
    )
    if prepared.replayed:
        return prepared.wave, True

    staged = _build_staged_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=staged,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"HANDOFF_READY"},
        allowed_states={"STAGED"},
        error_code="DPM_WAVE_HANDOFF_INVALID_STATE",
        action_phrase="create handoff evidence",
    )
    if prepared.replayed:
        return prepared.wave, True

    handoff_ready = _build_handoff_ready_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=handoff_ready,
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
    prepared = _prepare_wave_transition(
        wave_id=wave_id,
        wave_repository=wave_repository,
        replay_states={"CANCELLED"},
        allowed_states=None,
        error_code="DPM_WAVE_CANCEL_INVALID_STATE",
        action_phrase="be cancelled",
    )
    if prepared.replayed:
        return prepared.wave, True

    cancelled = _build_cancelled_wave(
        wave=prepared.wave,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
    )
    _persist_transitioned_wave(
        wave_repository=wave_repository,
        source_wave=prepared.wave,
        transitioned_wave=cancelled,
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
    return build_report_input_for_wave(
        wave=wave,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )
