"""Expected outcome snapshot assembly for RFC-0042."""

from src.core.construction.models import (
    ConstructionAlternative,
    ConstructionAlternativeSelection,
    ConstructionAlternativeSet,
)
from src.core.outcomes.models import (
    DpmExpectedOutcomeSnapshot,
    DpmOutcomeMetricValue,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    OutcomeDimension,
    OutcomeDimensionState,
)
from src.core.proof_packs.models import DpmPreTradeProofPack, DpmProofPackSourceRef
from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveHandoffRef


class DpmExpectedSnapshotAssemblyError(ValueError):
    """Raised when expected outcome evidence is missing or inconsistent."""


def assemble_expected_outcome_snapshot(
    *,
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
    proof_pack: DpmPreTradeProofPack,
    wave: DpmRebalanceWave | None = None,
    wave_item_id: str | None = None,
    handoff_ref_id: str | None = None,
) -> DpmExpectedOutcomeSnapshot:
    """Assemble expected outcome evidence from RFC-0039/0040/0041 manage artifacts."""

    selected_alternative = _select_alternative(alternative_set, selection)
    _validate_proof_pack_linkage(
        alternative_set=alternative_set,
        selection=selection,
        selected_alternative=selected_alternative,
        proof_pack=proof_pack,
    )
    wave_item = _resolve_wave_item(
        wave=wave,
        wave_item_id=wave_item_id,
        alternative_set=alternative_set,
        selection=selection,
        proof_pack=proof_pack,
    )
    handoff = _resolve_handoff(
        wave=wave,
        wave_item=wave_item,
        handoff_ref_id=handoff_ref_id,
    )
    expected_values = _expected_values_from_alternative(
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        proof_pack=proof_pack,
    )
    if not expected_values:
        msg = "selected alternative does not expose any expected outcome values"
        raise DpmExpectedSnapshotAssemblyError(msg)

    supportability = _roll_up_expected_supportability(
        alternative_set=alternative_set,
        selected_alternative=selected_alternative,
        proof_pack=proof_pack,
        wave_item=wave_item,
        handoff=handoff,
    )
    return DpmExpectedOutcomeSnapshot(
        portfolio_id=alternative_set.portfolio_id,
        mandate_id=proof_pack.mandate_id,
        rebalance_run_id=selected_alternative.rebalance_run_id or proof_pack.rebalance_run_id,
        alternative_set_id=alternative_set.alternative_set_id,
        selected_alternative_id=selection.alternative_id,
        proof_pack_id=proof_pack.proof_pack_id,
        wave_id=wave.wave_id if wave else None,
        wave_item_id=wave_item.wave_item_id if wave_item else None,
        operations_handoff_ref_id=handoff.handoff_ref_id if handoff else None,
        expected_values=expected_values,
        supportability=supportability,
        source_lineage=_source_lineage(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            proof_pack=proof_pack,
            wave=wave,
            wave_item=wave_item,
            handoff=handoff,
        ),
        source_hashes=proof_pack.source_hashes,
        section_hashes=_section_hashes(proof_pack),
        calculation_trace={
            "source": "RFC-0039_SELECTED_ALTERNATIVE_WITH_RFC-0040_PROOF_PACK",
            "selected_method": str(selected_alternative.method),
            "selected_method_status": str(selected_alternative.method_status),
            "proof_pack_status": proof_pack.status,
            "wave_item_state": wave_item.state if wave_item else None,
            "handoff_reason_code": handoff.reason_code if handoff else None,
            "defaulted_expected_values": [],
        },
    )


def _select_alternative(
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
) -> ConstructionAlternative:
    if selection.alternative_set_id != alternative_set.alternative_set_id:
        msg = "selection alternative_set_id does not match alternative set"
        raise DpmExpectedSnapshotAssemblyError(msg)
    for alternative in alternative_set.alternatives:
        if alternative.alternative_id == selection.alternative_id:
            return alternative
    msg = "selection alternative_id does not exist in alternative set"
    raise DpmExpectedSnapshotAssemblyError(msg)


def _validate_proof_pack_linkage(
    *,
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
    selected_alternative: ConstructionAlternative,
    proof_pack: DpmPreTradeProofPack,
) -> None:
    _require_equal("proof_pack.portfolio_id", proof_pack.portfolio_id, alternative_set.portfolio_id)
    _require_equal(
        "proof_pack.alternative_set_id",
        proof_pack.alternative_set_id,
        alternative_set.alternative_set_id,
    )
    _require_equal(
        "proof_pack.selected_alternative_id",
        proof_pack.selected_alternative_id,
        selection.alternative_id,
    )
    if selected_alternative.rebalance_run_id and proof_pack.rebalance_run_id:
        _require_equal(
            "proof_pack.rebalance_run_id",
            proof_pack.rebalance_run_id,
            selected_alternative.rebalance_run_id,
        )


def _resolve_wave_item(
    *,
    wave: DpmRebalanceWave | None,
    wave_item_id: str | None,
    alternative_set: ConstructionAlternativeSet,
    selection: ConstructionAlternativeSelection,
    proof_pack: DpmPreTradeProofPack,
) -> DpmRebalanceWaveItem | None:
    if not wave and wave_item_id:
        msg = "wave_item_id cannot be supplied without wave"
        raise DpmExpectedSnapshotAssemblyError(msg)
    if not wave:
        return None
    if not wave_item_id:
        msg = "wave_item_id is required when wave evidence is supplied"
        raise DpmExpectedSnapshotAssemblyError(msg)
    wave_item = next((item for item in wave.items if item.wave_item_id == wave_item_id), None)
    if wave_item is None:
        msg = "wave_item_id does not exist in wave"
        raise DpmExpectedSnapshotAssemblyError(msg)
    _require_equal("wave_item.portfolio_id", wave_item.portfolio_id, alternative_set.portfolio_id)
    if proof_pack.mandate_id and wave_item.mandate_id:
        _require_equal("wave_item.mandate_id", wave_item.mandate_id, proof_pack.mandate_id)
    _require_equal(
        "wave_item.alternative_set_id",
        wave_item.alternative_set_id,
        alternative_set.alternative_set_id,
    )
    _require_equal(
        "wave_item.selected_alternative_id",
        wave_item.selected_alternative_id,
        selection.alternative_id,
    )
    _require_equal("wave_item.proof_pack_id", wave_item.proof_pack_id, proof_pack.proof_pack_id)
    return wave_item


def _resolve_handoff(
    *,
    wave: DpmRebalanceWave | None,
    wave_item: DpmRebalanceWaveItem | None,
    handoff_ref_id: str | None,
) -> DpmWaveHandoffRef | None:
    if not handoff_ref_id:
        return None
    if wave is None or wave_item is None:
        msg = "handoff_ref_id requires wave and wave_item evidence"
        raise DpmExpectedSnapshotAssemblyError(msg)
    handoff = next((ref for ref in wave.handoff_refs if ref.handoff_ref_id == handoff_ref_id), None)
    if handoff is None:
        msg = "handoff_ref_id does not exist in wave"
        raise DpmExpectedSnapshotAssemblyError(msg)
    _require_equal("handoff.wave_id", handoff.wave_id, wave.wave_id)
    if wave_item.wave_item_id not in handoff.item_ids:
        msg = "handoff_ref_id does not include the selected wave item"
        raise DpmExpectedSnapshotAssemblyError(msg)
    if handoff.external_execution_claimed:
        msg = "manage handoff evidence cannot claim external execution"
        raise DpmExpectedSnapshotAssemblyError(msg)
    return handoff


def _expected_values_from_alternative(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative: ConstructionAlternative,
    proof_pack: DpmPreTradeProofPack,
) -> dict[OutcomeDimension, DpmOutcomeMetricValue]:
    source_ref = DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type="CONSTRUCTION_SELECTED_ALTERNATIVE",
        source_id=f"{alternative_set.alternative_set_id}:{selected_alternative.alternative_id}",
        source_version="RFC-0039",
        content_hash=proof_pack.source_hashes.get("selected_alternative")
        or proof_pack.source_hashes.get(alternative_set.alternative_set_id),
    )
    supportability = DpmOutcomeSupportability(
        state=_construction_state(alternative_set, selected_alternative),
        reason_codes=[f"CONSTRUCTION_{selected_alternative.method_status}"],
        required_source=True,
        explanation="Expected value supplied by RFC-0039 selected construction alternative.",
    )
    freshness = DpmOutcomeSourceFreshness(
        observed_at=selected_alternative.diagnostics.get("generated_at"),
        as_of_date=alternative_set.as_of,
        freshness_state="CURRENT",
    )
    metrics = selected_alternative.comparison_metrics
    expected_values: dict[OutcomeDimension, DpmOutcomeMetricValue] = {
        "DRIFT_REDUCTION": DpmOutcomeMetricValue(
            value=metrics.drift_after,
            unit="ratio",
            source_refs=[source_ref],
            source_freshness=freshness,
            supportability=supportability,
        ),
        "COST": DpmOutcomeMetricValue(
            value=metrics.estimated_transaction_cost.amount
            if metrics.estimated_transaction_cost
            else None,
            unit=metrics.estimated_transaction_cost.currency
            if metrics.estimated_transaction_cost
            else "base_currency",
            source_refs=[source_ref],
            source_freshness=freshness,
            supportability=supportability,
        ),
        "CASH_RESIDUAL": DpmOutcomeMetricValue(
            value=metrics.cash_weight_after,
            unit="ratio",
            source_refs=[source_ref],
            source_freshness=freshness,
            supportability=supportability,
        ),
    }
    return {
        dimension: value for dimension, value in expected_values.items() if value.value is not None
    }


def _roll_up_expected_supportability(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative: ConstructionAlternative,
    proof_pack: DpmPreTradeProofPack,
    wave_item: DpmRebalanceWaveItem | None,
    handoff: DpmWaveHandoffRef | None,
) -> DpmOutcomeSupportability:
    states: list[OutcomeDimensionState] = [
        _construction_state(alternative_set, selected_alternative),
        _proof_pack_state(proof_pack.status),
    ]
    if wave_item:
        states.append(_wave_item_state(wave_item))
    if handoff:
        states.append("READY")
    if "BLOCKED" in states:
        state: OutcomeDimensionState = "BLOCKED"
    elif "PENDING_REVIEW" in states:
        state = "PENDING_REVIEW"
    elif "DEGRADED" in states:
        state = "DEGRADED"
    else:
        state = "READY"
    return DpmOutcomeSupportability(
        state=state,
        reason_codes=_expected_reason_codes(
            alternative_set=alternative_set,
            selected_alternative=selected_alternative,
            proof_pack=proof_pack,
            wave_item=wave_item,
            handoff=handoff,
        ),
        required_source=True,
        explanation="Expected snapshot supportability rolled up from manage pre-trade artifacts.",
    )


def _source_lineage(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative: ConstructionAlternative,
    proof_pack: DpmPreTradeProofPack,
    wave: DpmRebalanceWave | None,
    wave_item: DpmRebalanceWaveItem | None,
    handoff: DpmWaveHandoffRef | None,
) -> list[DpmOutcomeSourceRef]:
    refs: list[DpmOutcomeSourceRef] = [
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="CONSTRUCTION_ALTERNATIVE_SET",
            source_id=alternative_set.alternative_set_id,
            source_version="RFC-0039",
            content_hash=alternative_set.request_hash,
        ),
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="CONSTRUCTION_SELECTED_ALTERNATIVE",
            source_id=selected_alternative.alternative_id,
            source_version="RFC-0039",
            content_hash=proof_pack.source_hashes.get("selected_alternative"),
        ),
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PRE_TRADE_PROOF_PACK",
            source_id=proof_pack.proof_pack_id,
            source_version=proof_pack.proof_pack_version,
            content_hash=proof_pack.content_hash,
        ),
    ]
    for section in proof_pack.sections:
        refs.extend(_proof_source_ref(ref) for ref in section.source_refs)
    if wave:
        refs.append(
            DpmOutcomeSourceRef(
                source_system="lotus-manage",
                source_type="REBALANCE_WAVE",
                source_id=wave.wave_id,
                source_version=wave.wave_version,
                content_hash=None,
            )
        )
    if wave_item:
        refs.append(
            DpmOutcomeSourceRef(
                source_system="lotus-manage",
                source_type="REBALANCE_WAVE_ITEM",
                source_id=wave_item.wave_item_id,
                source_version="RFC-0041",
                content_hash=None,
            )
        )
        refs.extend(
            DpmOutcomeSourceRef(
                source_system=source.source_system,
                source_type=source.source_type,
                source_id=source.source_id,
                source_version=source.source_version,
                content_hash=source.content_hash,
            )
            for source in wave_item.source_refs
        )
    if handoff:
        refs.append(
            DpmOutcomeSourceRef(
                source_system="lotus-manage",
                source_type="INTERNAL_OPERATIONS_HANDOFF",
                source_id=handoff.handoff_ref_id,
                source_version="RFC-0041",
                content_hash=handoff.content_hash,
            )
        )
    return _dedupe_refs(refs)


def _proof_source_ref(ref: DpmProofPackSourceRef) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system=ref.source_system,
        source_type=ref.source_type,
        source_id=ref.source_id,
        source_version=None,
        content_hash=ref.content_hash,
    )


def _dedupe_refs(refs: list[DpmOutcomeSourceRef]) -> list[DpmOutcomeSourceRef]:
    deduped: list[DpmOutcomeSourceRef] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        key = (ref.source_system, ref.source_type, ref.source_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _section_hashes(proof_pack: DpmPreTradeProofPack) -> dict[str, str]:
    hashes = dict(proof_pack.supportability.section_hashes)
    for section in proof_pack.sections:
        hashes.setdefault(section.section_id, section.content_hash)
    return hashes


def _expected_reason_codes(
    *,
    alternative_set: ConstructionAlternativeSet,
    selected_alternative: ConstructionAlternative,
    proof_pack: DpmPreTradeProofPack,
    wave_item: DpmRebalanceWaveItem | None,
    handoff: DpmWaveHandoffRef | None,
) -> list[str]:
    reason_codes = [
        f"CONSTRUCTION_{selected_alternative.method_status}",
        f"ALTERNATIVE_SET_{alternative_set.status}",
        f"PROOF_PACK_{proof_pack.status}",
    ]
    if proof_pack.supportability.reason_codes:
        reason_codes.extend(proof_pack.supportability.reason_codes)
    if wave_item:
        reason_codes.append(f"WAVE_ITEM_{wave_item.state}")
    if handoff:
        reason_codes.append(handoff.reason_code)
    return list(dict.fromkeys(reason_codes))


def _construction_state(
    alternative_set: ConstructionAlternativeSet,
    selected_alternative: ConstructionAlternative,
) -> OutcomeDimensionState:
    if (
        str(alternative_set.status) == "BLOCKED"
        or str(selected_alternative.method_status) == "BLOCKED"
    ):
        return "BLOCKED"
    if (
        str(alternative_set.status) == "PENDING_REVIEW"
        or str(selected_alternative.method_status) == "PENDING_REVIEW"
    ):
        return "PENDING_REVIEW"
    if (
        str(alternative_set.status) == "DEGRADED"
        or str(selected_alternative.method_status) == "DEGRADED"
    ):
        return "DEGRADED"
    if alternative_set.source_supportability_state == "DEGRADED":
        return "DEGRADED"
    return "READY"


def _proof_pack_state(status: str) -> OutcomeDimensionState:
    if status in {"READY", "PENDING_REVIEW", "DEGRADED", "BLOCKED"}:
        return status  # type: ignore[return-value]
    return "BLOCKED"


def _wave_item_state(wave_item: DpmRebalanceWaveItem) -> OutcomeDimensionState:
    if wave_item.state in {"SOURCE_BLOCKED", "SIMULATION_BLOCKED"}:
        return "BLOCKED"
    if wave_item.state in {"SOURCE_DEGRADED", "REVIEW_REQUIRED"}:
        return "DEGRADED"
    return "READY"


def _require_equal(label: str, actual: str | None, expected: str | None) -> None:
    if actual != expected:
        msg = f"{label} mismatch: expected {expected!r}, got {actual!r}"
        raise DpmExpectedSnapshotAssemblyError(msg)
