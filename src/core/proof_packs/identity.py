"""Proof-pack identity, correlation, and source supportability helpers."""

from datetime import datetime
from typing import Any

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.models import RebalanceResult
from src.core.proof_packs.models import ProofPackSourceType
from src.core.rebalance_runs.models import DpmRunRecord


class ProofPackSourceValidationError(ValueError):
    pass


def proof_pack_id_for_rebalance_run(*, rebalance_run_id: str) -> str:
    return rebalance_run_id.replace("rr_", "dpp_", 1)


def proof_pack_id_for_selected_alternative(
    *, alternative_set_id: str, selected_alternative_id: str
) -> str:
    return f"dpp_{alternative_set_id}_{selected_alternative_id}"


def resolve_proof_pack_correlation_id(
    *,
    correlation_id: str | None,
    selection: ConstructionAlternativeSelection | None,
    run: DpmRunRecord | None,
    created_at: datetime,
) -> str:
    return next(
        candidate
        for candidate in [
            correlation_id,
            selection_correlation_id(selection),
            run_correlation_id(run),
            generated_proof_pack_correlation_id(created_at),
        ]
        if candidate
    )


def selection_correlation_id(
    selection: ConstructionAlternativeSelection | None,
) -> str | None:
    if selection is None or not selection.correlation_id:
        return None
    return selection.correlation_id


def run_correlation_id(run: DpmRunRecord | None) -> str | None:
    return run.correlation_id if run is not None else None


def generated_proof_pack_correlation_id(created_at: datetime) -> str:
    return f"proof-pack-{created_at.strftime('%Y%m%d%H%M%S')}"


def source_supportability(
    *,
    result: RebalanceResult | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> dict[str, Any]:
    return {
        **run_source_supportability(result),
        "alternative_set_status": alternative_set_status(alternative_set),
    }


def run_source_supportability(result: RebalanceResult | None) -> dict[str, Any]:
    if result is None:
        return {
            "run_status": None,
            "input_mode": None,
            "source_system": None,
            "source_supportability_state": None,
        }
    return {
        "run_status": result.status,
        "input_mode": result.lineage.input_mode,
        "source_system": result.lineage.source_system,
        "source_supportability_state": result.lineage.source_supportability_state,
    }


def alternative_set_status(alternative_set: ConstructionAlternativeSet | None) -> str | None:
    if alternative_set is None:
        return None
    return str(alternative_set.status)


def resolve_portfolio_id(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> str:
    if alternative_set is not None:
        return alternative_set.portfolio_id
    if run is not None:
        return run.portfolio_id
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")


def as_of_date(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
) -> str:
    if alternative_set is not None:
        return alternative_set.as_of
    if run is not None:
        return run.created_at.date().isoformat()
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")


def proof_pack_id(
    *,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
) -> str:
    candidate = candidate_proof_pack_id(
        source_type=source_type,
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
    )
    if candidate is not None:
        return candidate
    raise ProofPackSourceValidationError("DPM_PROOF_PACK_SOURCE_MISSING")


def candidate_proof_pack_id(
    *,
    source_type: ProofPackSourceType,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
) -> str | None:
    if source_type == "REBALANCE_RUN":
        return run_source_proof_pack_id(run)
    if source_type == "SELECTED_ALTERNATIVE":
        return selected_alternative_source_proof_pack_id(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
        )
    return None


def run_source_proof_pack_id(run: DpmRunRecord | None) -> str | None:
    if run is None:
        return None
    return proof_pack_id_for_rebalance_run(rebalance_run_id=run.rebalance_run_id)


def selected_alternative_source_proof_pack_id(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
) -> str | None:
    if alternative_set is None or selected_alternative is None:
        return None
    return proof_pack_id_for_selected_alternative(
        alternative_set_id=alternative_set.alternative_set_id,
        selected_alternative_id=selected_alternative.alternative_id,
    )
