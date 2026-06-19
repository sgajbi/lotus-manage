from dataclasses import dataclass
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.construction.models import (
    AuthoritativeRegimeStressContext,
    ConstructionAlternative,
    ConstructionAlternativeSet,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.models import RebalanceResult
from src.core.proof_packs.models import DpmProofPackSourceRef
from src.core.proof_packs.source_analytics import (
    ProofPackAnalyticsFamily,
    ProofPackSourceAnalytics,
    source_analytics_for_alternative,
    source_analytics_for_context,
)
from src.core.rebalance_runs.models import DpmRunRecord


@dataclass(frozen=True)
class ProofPackSourceContext:
    source_hashes: dict[str, str]
    source_analytics: dict[str, ProofPackSourceAnalytics]
    source_refs: list[DpmProofPackSourceRef]


@dataclass(frozen=True)
class SourceHashCandidate:
    key: str
    content_hash: str


def proof_pack_source_context(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> ProofPackSourceContext:
    source_hashes = source_hashes_for_proof_pack(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )
    source_analytics = source_analytics_for_proof_pack(
        selected_alternative=selected_alternative,
        direct_regime_stress_context=direct_regime_stress_context,
    )
    for analytics in source_analytics.values():
        source_hashes[analytics.source_hash_key] = analytics.content_hash
    source_refs = source_refs_for_proof_pack(
        run=run,
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        source_hashes=source_hashes,
        mandate_twin=mandate_twin,
        mandate_health=mandate_health,
    )
    source_refs.extend(analytics.source_ref for analytics in source_analytics.values())
    return ProofPackSourceContext(
        source_hashes=source_hashes,
        source_analytics=source_analytics,
        source_refs=source_refs,
    )


def source_hashes_for_proof_pack(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> dict[str, str]:
    return {
        candidate.key: candidate.content_hash
        for candidate in source_hash_candidates(
            run=run,
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            mandate_twin=mandate_twin,
            mandate_health=mandate_health,
        )
    }


def source_hash_candidates(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> list[SourceHashCandidate]:
    return [
        candidate
        for candidate in [
            optional_source_hash("rebalance_run", run),
            optional_source_hash("alternative_set", alternative_set),
            optional_source_hash("selected_alternative", selected_alternative),
            optional_source_hash("mandate_twin", mandate_twin),
            optional_source_hash("mandate_health", mandate_health),
        ]
        if candidate is not None
    ]


def optional_source_hash(key: str, source: Any | None) -> SourceHashCandidate | None:
    if source is None:
        return None
    return SourceHashCandidate(
        key=key,
        content_hash=hash_canonical_payload(source.model_dump(mode="json")),
    )


def source_analytics_for_proof_pack(
    *,
    selected_alternative: ConstructionAlternative | None,
    direct_regime_stress_context: AuthoritativeRegimeStressContext | None,
) -> dict[str, ProofPackSourceAnalytics]:
    families: tuple[ProofPackAnalyticsFamily, ...] = (
        "risk",
        "performance",
        "transaction_cost",
        "client_restriction",
        "sustainability_preference",
        "regime_stress",
    )
    analytics_by_family: dict[str, ProofPackSourceAnalytics] = {
        family: analytics
        for family in families
        if (
            analytics := source_analytics_for_alternative(
                alternative=selected_alternative,
                family=family,
            )
        )
        is not None
    }
    if direct_regime_stress_context is not None and "regime_stress" not in analytics_by_family:
        direct_analytics = source_analytics_for_context(
            source_context=direct_regime_stress_context.model_dump(mode="json"),
            family="regime_stress",
        )
        if direct_analytics is not None:
            analytics_by_family["regime_stress"] = direct_analytics
    return analytics_by_family


def source_refs_for_proof_pack(
    *,
    run: DpmRunRecord | None,
    alternative_set: ConstructionAlternativeSet | None,
    selected_alternative: ConstructionAlternative | None,
    source_hashes: dict[str, str],
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> list[DpmProofPackSourceRef]:
    return present_source_refs(
        [
            optional_run_source_ref(run=run, source_hashes=source_hashes),
            optional_alternative_set_source_ref(
                alternative_set=alternative_set,
                source_hashes=source_hashes,
            ),
            optional_selected_alternative_source_ref(
                selected_alternative=selected_alternative,
                source_hashes=source_hashes,
            ),
            optional_mandate_twin_source_ref(
                mandate_twin=mandate_twin,
                source_hashes=source_hashes,
            ),
            optional_mandate_health_source_ref(
                mandate_health=mandate_health,
                source_hashes=source_hashes,
            ),
        ]
    )


def present_source_refs(
    refs: list[DpmProofPackSourceRef | None],
) -> list[DpmProofPackSourceRef]:
    return [ref for ref in refs if ref is not None]


def optional_run_source_ref(
    *, run: DpmRunRecord | None, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef | None:
    if run is None:
        return None
    return run_source_ref(run=run, source_hashes=source_hashes)


def optional_alternative_set_source_ref(
    *,
    alternative_set: ConstructionAlternativeSet | None,
    source_hashes: dict[str, str],
) -> DpmProofPackSourceRef | None:
    if alternative_set is None:
        return None
    return alternative_set_source_ref(alternative_set, source_hashes=source_hashes)


def optional_selected_alternative_source_ref(
    *,
    selected_alternative: ConstructionAlternative | None,
    source_hashes: dict[str, str],
) -> DpmProofPackSourceRef | None:
    if selected_alternative is None:
        return None
    return selected_alternative_source_ref(selected_alternative, source_hashes=source_hashes)


def optional_mandate_twin_source_ref(
    *,
    mandate_twin: DpmMandateDigitalTwin | None,
    source_hashes: dict[str, str],
) -> DpmProofPackSourceRef | None:
    if mandate_twin is None:
        return None
    return mandate_twin_source_ref(mandate_twin, source_hashes=source_hashes)


def optional_mandate_health_source_ref(
    *,
    mandate_health: DpmMandateHealthSnapshot | None,
    source_hashes: dict[str, str],
) -> DpmProofPackSourceRef | None:
    if mandate_health is None:
        return None
    return mandate_health_source_ref(mandate_health, source_hashes=source_hashes)


def run_source_ref(*, run: DpmRunRecord, source_hashes: dict[str, str]) -> DpmProofPackSourceRef:
    result = RebalanceResult.model_validate(run.result_json)
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_REBALANCE_RUN",
        source_id=run.rebalance_run_id,
        supportability_state=result.status,
        content_hash=source_hashes.get("rebalance_run"),
    )


def alternative_set_source_ref(
    alternative_set: ConstructionAlternativeSet, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE_SET",
        source_id=alternative_set.alternative_set_id,
        supportability_state=str(alternative_set.status),
        content_hash=source_hashes.get("alternative_set"),
    )


def selected_alternative_source_ref(
    selected_alternative: ConstructionAlternative, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_CONSTRUCTION_ALTERNATIVE",
        source_id=selected_alternative.alternative_id,
        supportability_state=str(selected_alternative.method_status),
        content_hash=source_hashes.get("selected_alternative"),
    )


def mandate_twin_source_ref(
    mandate_twin: DpmMandateDigitalTwin, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_MANDATE_DIGITAL_TWIN",
        source_id=mandate_twin.mandate_id,
        supportability_state="READY" if not mandate_twin.field_gap_codes else "DEGRADED",
        content_hash=source_hashes.get("mandate_twin"),
    )


def mandate_health_source_ref(
    mandate_health: DpmMandateHealthSnapshot, *, source_hashes: dict[str, str]
) -> DpmProofPackSourceRef:
    return DpmProofPackSourceRef(
        source_system="lotus-manage",
        source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
        source_id=mandate_health.health_snapshot_id,
        supportability_state=mandate_health.health_state.value,
        content_hash=source_hashes.get("mandate_health"),
    )
