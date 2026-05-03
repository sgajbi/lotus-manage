"""Pure RFC-0041 source-readiness classification for wave items."""

from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthSnapshot
from src.core.waves.models import DpmRebalanceWaveItem, DpmWaveSourceRef, WaveItemState


def classify_wave_item_source_readiness(
    *,
    item: DpmRebalanceWaveItem,
    wave_as_of_date: str,
    mandate_twin: DpmMandateDigitalTwin | None,
    mandate_health: DpmMandateHealthSnapshot | None,
) -> DpmRebalanceWaveItem:
    if mandate_twin is None:
        return item.model_copy(
            update={
                "state": "SOURCE_BLOCKED",
                "reason_codes": ["MANDATE_DIGITAL_TWIN_MISSING"],
                "source_refs": _dedupe_source_refs(item.source_refs),
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "lotus-manage",
                    "source_owner_upstream": "lotus-core",
                    "required_action": "REFRESH_MANDATE_DIGITAL_TWIN",
                    "missing_source_family": "MANDATE_DIGITAL_TWIN",
                },
            },
            deep=True,
        )

    refs = [
        *item.source_refs,
        _mandate_twin_ref(mandate_twin),
        *_core_lineage_refs(mandate_twin),
    ]
    if mandate_health is None:
        return item.model_copy(
            update={
                "mandate_id": mandate_twin.mandate_id,
                "model_portfolio_id": mandate_twin.model_portfolio_id,
                "state": "SOURCE_DEGRADED",
                "reason_codes": ["MANDATE_HEALTH_MISSING"],
                "source_refs": _dedupe_source_refs(refs),
                "diagnostics": {
                    **item.diagnostics,
                    "source_owner": "lotus-manage",
                    "required_action": "RUN_MANDATE_HEALTH_REFRESH",
                    "missing_source_family": "MANDATE_HEALTH",
                },
            },
            deep=True,
        )

    refs.extend([_mandate_health_ref(mandate_health), _source_readiness_ref(mandate_health)])
    state, reason_codes, diagnostics = _state_from_health(
        health=mandate_health,
        wave_as_of_date=wave_as_of_date,
    )
    return item.model_copy(
        update={
            "mandate_id": mandate_twin.mandate_id,
            "model_portfolio_id": mandate_twin.model_portfolio_id,
            "state": state,
            "reason_codes": reason_codes,
            "source_refs": _dedupe_source_refs(refs),
            "diagnostics": {**item.diagnostics, **diagnostics},
        },
        deep=True,
    )


def _state_from_health(
    *,
    health: DpmMandateHealthSnapshot,
    wave_as_of_date: str,
) -> tuple[WaveItemState, list[str], dict[str, object]]:
    if health.as_of_date.isoformat() < wave_as_of_date:
        return (
            "SOURCE_DEGRADED",
            ["MANDATE_HEALTH_STALE"],
            {
                "source_owner": "lotus-manage",
                "required_action": "REFRESH_MANDATE_HEALTH",
                "health_as_of_date": health.as_of_date.isoformat(),
                "wave_as_of_date": wave_as_of_date,
            },
        )
    health_state = health.health_state.value
    if health_state == "BLOCKED" or health.source_readiness_state in {
        "INCOMPLETE",
        "UNAVAILABLE",
    }:
        return (
            "SOURCE_BLOCKED",
            ["MANDATE_HEALTH_BLOCKED", f"SOURCE_READINESS_{health.source_readiness_state}"],
            {
                "source_owner": "lotus-manage",
                "source_owner_upstream": "lotus-core",
                "required_action": "FIX_SOURCE_DATA",
                "health_state": health_state,
                "source_readiness_state": health.source_readiness_state,
            },
        )
    if health.source_readiness_state == "DEGRADED":
        return (
            "SOURCE_DEGRADED",
            ["SOURCE_READINESS_DEGRADED"],
            {
                "source_owner": "lotus-manage",
                "source_owner_upstream": "lotus-core",
                "required_action": "REVIEW_SOURCE_DEGRADATION",
                "health_state": health_state,
                "source_readiness_state": health.source_readiness_state,
            },
        )
    if health_state == "PENDING_REVIEW":
        return (
            "REVIEW_REQUIRED",
            ["MANDATE_HEALTH_PENDING_REVIEW"],
            {
                "source_owner": "lotus-manage",
                "required_action": health.recommended_action.value,
                "health_state": health_state,
                "source_readiness_state": health.source_readiness_state,
            },
        )
    return (
        "SOURCE_READY",
        ["SOURCE_READINESS_READY"],
        {
            "source_owner": "lotus-manage",
            "health_state": health_state,
            "source_readiness_state": health.source_readiness_state,
        },
    )


def _mandate_twin_ref(twin: DpmMandateDigitalTwin) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="MANDATE_DIGITAL_TWIN",
        source_id=twin.mandate_id,
        source_version=twin.mandate_version,
        supportability_state="READY" if not twin.field_gap_codes else "DEGRADED",
    )


def _mandate_health_ref(health: DpmMandateHealthSnapshot) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="DPM_MANDATE_HEALTH_SNAPSHOT",
        source_id=health.health_snapshot_id,
        source_version=health.as_of_date.isoformat(),
        supportability_state=health.health_state.value,
    )


def _source_readiness_ref(health: DpmMandateHealthSnapshot) -> DpmWaveSourceRef:
    return DpmWaveSourceRef(
        source_system="lotus-manage",
        source_type="DPM_SOURCE_READINESS",
        source_id=health.health_snapshot_id,
        source_version=health.as_of_date.isoformat(),
        supportability_state=health.source_readiness_state,
    )


def _core_lineage_refs(twin: DpmMandateDigitalTwin) -> list[DpmWaveSourceRef]:
    refs: list[DpmWaveSourceRef] = []
    for lineage in twin.source_lineage:
        if not lineage.source_record_id:
            continue
        refs.append(
            DpmWaveSourceRef(
                source_system=lineage.source_system,
                source_type=lineage.product_name,
                source_id=lineage.source_record_id,
                source_version=lineage.product_version,
                supportability_state=lineage.data_quality_status,
            )
        )
    return refs


def _dedupe_source_refs(refs: list[DpmWaveSourceRef]) -> list[DpmWaveSourceRef]:
    deduped: dict[tuple[str, str, str, str | None], DpmWaveSourceRef] = {}
    for ref in refs:
        deduped[(ref.source_system, ref.source_type, ref.source_id, ref.source_version)] = ref
    return list(deduped.values())
