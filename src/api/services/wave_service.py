from src.api.request_models import RebalanceRequest
from src.api.services.wave_construction_selection import select_construction_alternative_for_wave
from src.api.services.wave_create_command import create_persisted_wave
from src.api.services.wave_errors import (
    DpmWaveLookupError as DpmWaveLookupError,
    DpmWaveValidationError as DpmWaveValidationError,
)
from src.api.services.wave_event_append import append_same_state_event
from src.api.services.wave_item_collection import wave_with_items_and_aggregate
from src.api.services.wave_item_selection_transition import (
    build_wave_with_selected_item_alternative,
)
from src.api.services.wave_lifecycle_commands import (
    approve_persisted_wave,
    cancel_persisted_wave,
    handoff_persisted_wave,
    stage_persisted_wave,
)
from src.api.services.wave_lookup import get_wave_or_raise
from src.api.services.wave_persistence import save_wave_or_raise, update_wave_or_raise
from src.api.services.wave_preparation_commands import (
    simulate_persisted_wave,
    source_check_persisted_wave,
)
from src.api.services.wave_preview import build_preview_wave
from src.api.services.wave_read_model_queries import (
    wave_detail_for_id,
    wave_items_for_id,
    wave_proof_pack_posture_for_id,
    wave_report_input_for_id,
    wave_supportability_for_id,
)
from src.api.services.wave_selection_command import select_persisted_wave_item_alternative
from src.api.services.wave_selection_guard import selectable_wave_item
from src.api.services.wave_search import search_wave_summaries
from src.api.services.wave_simulation_item import (
    DpmWaveSimulationInput as DpmWaveSimulationInput,
)
from src.api.services.wave_state_guard import (
    require_wave_state,
    wave_state_is_idempotent,
)
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

_get_wave_or_raise = get_wave_or_raise
_wave_state_is_idempotent = wave_state_is_idempotent
_require_wave_state = require_wave_state
_save_wave_or_raise = save_wave_or_raise
_update_wave_or_raise = update_wave_or_raise
_validate_trigger = validate_trigger_or_raise
_select_construction_alternative_for_wave = select_construction_alternative_for_wave
_build_wave_with_selected_item_alternative = build_wave_with_selected_item_alternative
_selectable_wave_item = selectable_wave_item
_approval_event_metadata = approval_event_metadata
_stage_event_metadata = stage_event_metadata
_handoff_event_metadata = handoff_event_metadata
_cancel_event_metadata = cancel_event_metadata
_selection_event_metadata = selection_event_metadata
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
    return create_persisted_wave(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        idempotency_key=idempotency_key,
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
    )


def source_check_wave(
    *,
    wave_id: str,
    actor_id: str,
    correlation_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return source_check_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        mandate_repository=mandate_repository,
        wave_repository=wave_repository,
    )


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
    return simulate_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        item_inputs=item_inputs,
        methods=methods,
        construction_repository=construction_repository,
        run_service=run_service,
        wave_repository=wave_repository,
        risk_authority_client=risk_authority_client,
    )


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
    return select_persisted_wave_item_alternative(
        wave_id=wave_id,
        wave_item_id=wave_item_id,
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
        wave_repository=wave_repository,
    )


def approve_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return approve_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        wave_repository=wave_repository,
    )


def stage_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return stage_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        wave_repository=wave_repository,
    )


def handoff_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return handoff_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        wave_repository=wave_repository,
    )


def cancel_wave(
    *,
    wave_id: str,
    actor_id: str,
    reason_code: str,
    comment: str | None,
    correlation_id: str,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return cancel_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        wave_repository=wave_repository,
    )


def wave_supportability_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    return _wave_supportability_payload(wave)


def wave_supportability(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_supportability_for_id(wave_id=wave_id, wave_repository=wave_repository)


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
    return wave_detail_for_id(wave_id=wave_id, wave_repository=wave_repository)


def list_wave_items(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_items_for_id(wave_id=wave_id, wave_repository=wave_repository)


def proof_pack_posture(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_proof_pack_posture_for_id(wave_id=wave_id, wave_repository=wave_repository)


def get_report_input(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
) -> DpmWaveReportInput:
    return wave_report_input_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
    )
