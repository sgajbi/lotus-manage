from src.api.request_models import RebalanceRequest
from src.api.services import wave_create_command
from src.api.services.wave_errors import (
    DpmWaveLookupError as DpmWaveLookupError,
    DpmWaveValidationError as DpmWaveValidationError,
)
from src.api.services import wave_lifecycle_commands
from src.api.services import wave_preparation_commands
from src.api.services import wave_preview
from src.api.services import wave_read_model_queries
from src.api.services import wave_selection_command
from src.api.services import wave_search
from src.api.services import wave_supportability_payload as wave_supportability_payload_module
from src.api.services.wave_simulation_item import (
    DpmWaveSimulationInput as DpmWaveSimulationInput,
)
from src.api.services.authority_client_service import RiskAuthorityClient
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
    tenant_id: str,
) -> DpmRebalanceWave:
    return wave_preview.build_preview_wave(
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        rationale=rationale,
        as_of_date=as_of_date,
        actor_id=actor_id,
        correlation_id=correlation_id,
        portfolios=portfolios,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
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
    tenant_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return wave_create_command.create_persisted_wave(
        tenant_id=tenant_id,
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
    tenant_id: str,
    mandate_repository: DpmMandateRepository,
    wave_repository: DpmWaveRepository,
) -> tuple[DpmRebalanceWave, bool]:
    return wave_preparation_commands.source_check_persisted_wave(
        tenant_id=tenant_id,
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
    risk_authority_client: RiskAuthorityClient | None = None,
) -> tuple[DpmRebalanceWave, bool]:
    return wave_preparation_commands.simulate_persisted_wave(
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
    tenant_id: str,
    generate_proof_pack: bool,
    construction_repository: ConstructionRepository,
    proof_pack_repository: DpmProofPackRepository,
    mandate_repository: DpmMandateRepository,
    run_service: DpmRunSupportService,
    wave_repository: DpmWaveRepository,
) -> DpmRebalanceWave:
    return wave_selection_command.select_persisted_wave_item_alternative(
        tenant_id=tenant_id,
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
    return wave_lifecycle_commands.approve_persisted_wave(
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
    return wave_lifecycle_commands.stage_persisted_wave(
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
    return wave_lifecycle_commands.handoff_persisted_wave(
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
    return wave_lifecycle_commands.cancel_persisted_wave(
        wave_id=wave_id,
        actor_id=actor_id,
        reason_code=reason_code,
        comment=comment,
        correlation_id=correlation_id,
        wave_repository=wave_repository,
    )


def wave_supportability_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    return wave_supportability_payload_module.wave_supportability_payload(wave)


def wave_supportability(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_read_model_queries.wave_supportability_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


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
    return wave_search.search_wave_summaries(
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
    return wave_read_model_queries.wave_detail_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


def list_wave_items(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_read_model_queries.wave_items_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


def proof_pack_posture(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
) -> dict[str, object]:
    return wave_read_model_queries.wave_proof_pack_posture_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
    )


def get_report_input(
    *,
    wave_id: str,
    wave_repository: DpmWaveRepository,
    proof_pack_repository: DpmProofPackRepository | None = None,
    outcome_review_repository: DpmOutcomeReviewRepository | None = None,
    mandate_repository: DpmMandateRepository | None = None,
    tenant_id: str | None = None,
) -> DpmWaveReportInput:
    return wave_read_model_queries.wave_report_input_for_id(
        wave_id=wave_id,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        outcome_review_repository=outcome_review_repository,
        mandate_repository=mandate_repository,
        tenant_id=tenant_id,
    )
