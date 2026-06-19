from typing import Any

from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.proof_packs.models import ProofPackSectionState

MandateContextSectionPayload = tuple[
    ProofPackSectionState,
    str,
    dict[str, Any],
    dict[str, Any],
    list[str],
]


def mandate_context_section_payload(
    *,
    mandate_id: str | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    mandate_evidence_gap_codes: list[str],
) -> MandateContextSectionPayload:
    if not mandate_id:
        return (
            "BLOCKED",
            "Mandate identity is required before proof-pack promotion.",
            {"mandate_id": None},
            {},
            ["DPM_PROOF_PACK_MANDATE_ID_MISSING"],
        )
    if mandate_twin is None:
        reason_codes = mandate_evidence_gap_codes or ["DPM_MANDATE_TWIN_EVIDENCE_MISSING"]
        return (
            "DEGRADED",
            "Mandate identity is present, but no persisted mandate digital-twin evidence is attached.",
            {"mandate_id": mandate_id},
            {},
            reason_codes,
        )
    if mandate_health is None:
        return (
            "DEGRADED",
            "Mandate digital-twin evidence is attached, but latest mandate-health evidence is missing.",
            {
                "mandate_id": mandate_twin.mandate_id,
                "mandate_version": mandate_twin.mandate_version,
                "portfolio_id": mandate_twin.portfolio_id,
                "as_of_date": mandate_twin.as_of_date.isoformat(),
                "risk_profile": mandate_twin.risk_profile,
                "model_portfolio_id": mandate_twin.model_portfolio_id,
                "field_gap_codes": mandate_twin.field_gap_codes,
            },
            {},
            ["DPM_MANDATE_HEALTH_EVIDENCE_MISSING", *mandate_twin.field_gap_codes],
        )

    reason_codes = [reason.reason_code for reason in mandate_health.top_reasons]
    return (
        _mandate_health_state(mandate_health),
        "Mandate digital-twin and health evidence are attached from persisted RFC-0038 truth.",
        {
            "mandate_id": mandate_twin.mandate_id,
            "mandate_version": mandate_twin.mandate_version,
            "portfolio_id": mandate_twin.portfolio_id,
            "as_of_date": mandate_twin.as_of_date.isoformat(),
            "risk_profile": mandate_twin.risk_profile,
            "investment_objective": mandate_twin.investment_objective,
            "model_portfolio_id": mandate_twin.model_portfolio_id,
            "model_portfolio_version": mandate_twin.model_portfolio_version,
            "health_snapshot_id": mandate_health.health_snapshot_id,
            "health_state": mandate_health.health_state.value,
            "source_readiness_state": mandate_health.source_readiness_state,
            "field_gap_codes": mandate_twin.field_gap_codes,
        },
        {
            "health_score": mandate_health.health_score,
            "dimension_count": len(mandate_health.dimension_scores),
            "top_reason_count": len(mandate_health.top_reasons),
            "source_lineage_count": len(mandate_twin.source_lineage),
        },
        [*reason_codes, *mandate_twin.field_gap_codes],
    )


def _mandate_health_state(snapshot: DpmMandateHealthSnapshot) -> ProofPackSectionState:
    if snapshot.health_state.value == "BLOCKED":
        return "BLOCKED"
    if snapshot.health_state.value == "PENDING_REVIEW":
        return "PENDING_REVIEW"
    if snapshot.source_readiness_state not in {"READY", "ready"}:
        return "DEGRADED"
    return "READY"
