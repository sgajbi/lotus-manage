from src.api.services import proof_pack_service
from src.api.services.wave_construction_diagnostics import proposed_changes_from_alternative_set
from src.core.construction.repository import ConstructionRepository
from src.core.mandate_repository import DpmMandateRepository
from src.core.proof_packs import ProofPackSourceValidationError
from src.core.proof_packs.repository import DpmProofPackConflictError, DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.waves import DpmRebalanceWaveItem

_PROOF_PACK_GENERATION_DEGRADATION_ERRORS = (
    DpmProofPackConflictError,
    DpmRunNotFoundError,
    ProofPackSourceValidationError,
)


def with_selection_and_proof_pack(
    *,
    item: DpmRebalanceWaveItem,
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
) -> DpmRebalanceWaveItem:
    alternative_set = construction_repository.get_alternative_set(
        alternative_set_id=str(item.alternative_set_id), tenant_id=tenant_id
    )
    if alternative_set is None:
        raise ProofPackSourceValidationError("DPM_ALTERNATIVE_SET_NOT_FOUND")
    item = item.model_copy(update={"proof_pack_id": None}, deep=True)
    diagnostics = {
        **item.diagnostics,
        "proposed_changes": proposed_changes_from_alternative_set(
            alternative_set, selected_alternative_id=alternative_id
        ),
        "selection_actor_id": actor_id,
        "selection_reason_code": reason_code,
    }
    if comment:
        diagnostics["selection_comment"] = comment
    if not generate_proof_pack:
        return item.model_copy(
            update={
                "state": "SELECTED",
                "selected_alternative_id": alternative_id,
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED"],
                "diagnostics": {
                    **diagnostics,
                    "proof_pack_state": "DEGRADED",
                    "proof_pack_reason_code": "PROOF_PACK_GENERATION_NOT_REQUESTED",
                },
            },
            deep=True,
        )
    try:
        proof_pack = proof_pack_service.generate_proof_pack_from_selected_alternative(
            tenant_id=tenant_id,
            alternative_set_id=str(item.alternative_set_id),
            selected_alternative_id=alternative_id,
            actor_id=actor_id,
            reason=reason_code,
            correlation_id=correlation_id,
            mandate_id=item.mandate_id,
            idempotency_key=f"wave:{item.wave_item_id}:proof-pack:{alternative_id}",
            construction_repository=construction_repository,
            run_service=run_service,
            mandate_repository=mandate_repository,
            proof_pack_repository=proof_pack_repository,
        )
    except _PROOF_PACK_GENERATION_DEGRADATION_ERRORS as exc:
        return item.model_copy(
            update={
                "state": "SELECTED",
                "selected_alternative_id": alternative_id,
                "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED"],
                "diagnostics": {
                    **diagnostics,
                    "proof_pack_state": "DEGRADED",
                    "proof_pack_reason_code": "PROOF_PACK_GENERATION_FAILED",
                    "proof_pack_error": type(exc).__name__,
                },
            },
            deep=True,
        )
    return item.model_copy(
        update={
            "state": "PROOF_PACK_READY",
            "selected_alternative_id": alternative_id,
            "proof_pack_id": proof_pack.proof_pack_id,
            "reason_codes": ["CONSTRUCTION_ALTERNATIVE_SELECTED", "PROOF_PACK_READY"],
            "diagnostics": {
                **diagnostics,
                "proof_pack_state": proof_pack.status,
            },
        },
        deep=True,
    )


__all__ = ["with_selection_and_proof_pack"]
