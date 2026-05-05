"""Realized source snapshot adapter for RFC-0042."""

from collections import Counter

from src.core.outcomes.models import (
    DpmOutcomeMetricValue,
    DpmOutcomeReviewWindow,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmRealizedOutcomeSnapshot,
    DpmRealizedSourceSnapshot,
    OutcomeDimension,
    OutcomeDimensionState,
)

_BLOCKING_QUALITIES = {"MISSING", "MALFORMED", "CONFLICTING"}
_DEGRADED_QUALITIES = {"STALE", "UNAVAILABLE", "PARTIAL"}
_NOT_SUPPORTED_QUALITIES = {"NOT_SUPPORTED"}


def assemble_realized_outcome_snapshot(
    *,
    portfolio_id: str,
    review_window: DpmOutcomeReviewWindow,
    source_snapshots: list[DpmRealizedSourceSnapshot],
    required_dimensions: list[OutcomeDimension],
) -> DpmRealizedOutcomeSnapshot:
    """Assemble realized source evidence without computing source-owner truth locally."""

    indexed = _index_sources(source_snapshots)
    realized_values = {
        dimension: _metric_from_sources(
            dimension=dimension,
            review_window=review_window,
            snapshots=indexed.get(dimension, []),
        )
        for dimension in required_dimensions
    }
    states = [value.supportability.state for value in realized_values.values()]
    state = _roll_up_state(states)
    reason_codes = _roll_up_reason_codes(realized_values)
    lineage = _source_lineage(source_snapshots, realized_values)
    return DpmRealizedOutcomeSnapshot(
        portfolio_id=portfolio_id,
        review_window=review_window,
        realized_values=realized_values,
        supportability=DpmOutcomeSupportability(
            state=state,
            reason_codes=reason_codes,
            required_source=True,
            explanation="Realized snapshot supportability rolled up from source-owner evidence.",
        ),
        source_lineage=lineage,
        source_hashes={
            snapshot.source_id: snapshot.content_hash
            for snapshot in source_snapshots
            if snapshot.content_hash
        },
        quality_summary=dict(Counter(snapshot.quality for snapshot in source_snapshots)),
    )


def _index_sources(
    source_snapshots: list[DpmRealizedSourceSnapshot],
) -> dict[OutcomeDimension, list[DpmRealizedSourceSnapshot]]:
    indexed: dict[OutcomeDimension, list[DpmRealizedSourceSnapshot]] = {}
    for snapshot in source_snapshots:
        indexed.setdefault(snapshot.dimension, []).append(snapshot)
    return indexed


def _metric_from_sources(
    *,
    dimension: OutcomeDimension,
    review_window: DpmOutcomeReviewWindow,
    snapshots: list[DpmRealizedSourceSnapshot],
) -> DpmOutcomeMetricValue:
    if not snapshots:
        return _missing_metric(dimension=dimension, review_window=review_window)
    if len(snapshots) > 1:
        values = {snapshot.value for snapshot in snapshots}
        if len(values) > 1:
            return _conflicting_metric(dimension=dimension, snapshots=snapshots)
    snapshot = snapshots[0]
    state = _state_from_source(snapshot)
    reason_code = _reason_code(dimension=dimension, snapshot=snapshot, state=state)
    value = snapshot.value if state not in {"BLOCKED", "NOT_SUPPORTED"} else None
    if state == "READY" and value is None:
        state = "BLOCKED"
        reason_code = _blocked_reason(dimension)
    return DpmOutcomeMetricValue(
        value=value,
        unit=snapshot.unit,
        source_refs=[_source_ref(snapshot)],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at=snapshot.observed_at,
            as_of_date=snapshot.as_of_date or review_window.as_of_date,
            freshness_state="STALE" if snapshot.quality == "STALE" else "CURRENT",
        ),
        supportability=DpmOutcomeSupportability(
            state=state,
            reason_codes=[reason_code, *snapshot.reason_codes],
            required_source=True,
            explanation=_supportability_explanation(snapshot=snapshot, state=state),
        ),
    )


def _missing_metric(
    *,
    dimension: OutcomeDimension,
    review_window: DpmOutcomeReviewWindow,
) -> DpmOutcomeMetricValue:
    state = _missing_state(dimension)
    reason_code = _missing_reason(dimension)
    return DpmOutcomeMetricValue(
        value=None,
        unit="unknown",
        source_refs=[
            DpmOutcomeSourceRef(
                source_system=_expected_source_owner(dimension),
                source_type="MISSING_REALIZED_SOURCE",
                source_id=f"{dimension}:{review_window.as_of_date}",
                source_version=None,
                content_hash=None,
            )
        ],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at=None,
            as_of_date=review_window.as_of_date,
            freshness_state="UNKNOWN",
        ),
        supportability=DpmOutcomeSupportability(
            state=state,
            reason_codes=[reason_code],
            required_source=True,
            explanation="Required source-owner realized evidence was not supplied.",
        ),
    )


def _conflicting_metric(
    *,
    dimension: OutcomeDimension,
    snapshots: list[DpmRealizedSourceSnapshot],
) -> DpmOutcomeMetricValue:
    return DpmOutcomeMetricValue(
        value=None,
        unit=snapshots[0].unit,
        source_refs=[_source_ref(snapshot) for snapshot in snapshots],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at=None,
            as_of_date=snapshots[0].as_of_date,
            freshness_state="UNKNOWN",
        ),
        supportability=DpmOutcomeSupportability(
            state="BLOCKED",
            reason_codes=[_blocked_reason(dimension), "SOURCE_CONFLICTING"],
            required_source=True,
            explanation="Multiple source-owner values conflict for the same outcome dimension.",
        ),
    )


def _state_from_source(snapshot: DpmRealizedSourceSnapshot) -> OutcomeDimensionState:
    if snapshot.source_state == "NOT_SUPPORTED" or snapshot.quality in _NOT_SUPPORTED_QUALITIES:
        return "NOT_SUPPORTED"
    if snapshot.source_state == "BLOCKED" or snapshot.quality in _BLOCKING_QUALITIES:
        return "BLOCKED"
    if snapshot.source_state == "DEGRADED" or snapshot.quality in _DEGRADED_QUALITIES:
        return "DEGRADED"
    return "READY"


def _roll_up_state(states: list[OutcomeDimensionState]) -> OutcomeDimensionState:
    if not states:
        return "BLOCKED"
    if all(state == "NOT_SUPPORTED" for state in states):
        return "NOT_SUPPORTED"
    for candidate in ("BLOCKED", "DEGRADED", "NOT_SUPPORTED"):
        if candidate in states:
            return "DEGRADED" if candidate == "NOT_SUPPORTED" else candidate
    return "READY"


def _roll_up_reason_codes(
    realized_values: dict[OutcomeDimension, DpmOutcomeMetricValue],
) -> list[str]:
    reason_codes: list[str] = []
    for metric in realized_values.values():
        for reason_code in metric.supportability.reason_codes:
            if reason_code not in reason_codes:
                reason_codes.append(reason_code)
    return reason_codes or ["SOURCE_EVIDENCE_INCOMPLETE"]


def _source_lineage(
    source_snapshots: list[DpmRealizedSourceSnapshot],
    realized_values: dict[OutcomeDimension, DpmOutcomeMetricValue],
) -> list[DpmOutcomeSourceRef]:
    refs = [_source_ref(snapshot) for snapshot in source_snapshots]
    for metric in realized_values.values():
        refs.extend(metric.source_refs)
    deduped: list[DpmOutcomeSourceRef] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        key = (ref.source_system, ref.source_type, ref.source_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _source_ref(snapshot: DpmRealizedSourceSnapshot) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system=snapshot.source_system,
        source_type=snapshot.source_type,
        source_id=snapshot.source_id,
        source_version=None,
        content_hash=snapshot.content_hash,
    )


def _supportability_explanation(
    *,
    snapshot: DpmRealizedSourceSnapshot,
    state: OutcomeDimensionState,
) -> str:
    return (
        f"{snapshot.source_system} supplied {snapshot.source_type} with quality "
        f"{snapshot.quality}; dimension supportability is {state}."
    )


def _reason_code(
    *,
    dimension: OutcomeDimension,
    snapshot: DpmRealizedSourceSnapshot,
    state: OutcomeDimensionState,
) -> str:
    if state == "NOT_SUPPORTED":
        return _not_supported_reason(dimension)
    if state == "BLOCKED":
        return _blocked_reason(dimension)
    if state == "DEGRADED":
        return _degraded_reason(dimension, snapshot)
    return "SOURCE_READY"


def _missing_state(dimension: OutcomeDimension) -> OutcomeDimensionState:
    if dimension in {"RISK_REDUCTION", "PERFORMANCE"}:
        return "NOT_SUPPORTED"
    return "BLOCKED"


def _missing_reason(dimension: OutcomeDimension) -> str:
    if dimension == "EXECUTION_QUALITY":
        return "EXECUTION_EVIDENCE_BLOCKED"
    if dimension == "RISK_REDUCTION":
        return "RISK_OUTCOME_NOT_SUPPORTED"
    if dimension == "PERFORMANCE":
        return "PERFORMANCE_OUTCOME_NOT_SUPPORTED"
    return "SOURCE_EVIDENCE_INCOMPLETE"


def _not_supported_reason(dimension: OutcomeDimension) -> str:
    return _missing_reason(dimension)


def _blocked_reason(dimension: OutcomeDimension) -> str:
    if dimension == "EXECUTION_QUALITY":
        return "EXECUTION_EVIDENCE_BLOCKED"
    return "SOURCE_EVIDENCE_INCOMPLETE"


def _degraded_reason(
    dimension: OutcomeDimension,
    snapshot: DpmRealizedSourceSnapshot,
) -> str:
    if snapshot.quality == "STALE":
        return "SOURCE_EVIDENCE_INCOMPLETE"
    if dimension == "PERFORMANCE":
        return "PERFORMANCE_SOURCE_UNAVAILABLE"
    if dimension == "RISK_REDUCTION":
        return "RISK_SOURCE_UNAVAILABLE"
    return "SOURCE_EVIDENCE_INCOMPLETE"


def _expected_source_owner(dimension: OutcomeDimension) -> str:
    return {
        "DRIFT_REDUCTION": "lotus-core",
        "COST": "lotus-core",
        "TAX": "lotus-core",
        "EXECUTION_QUALITY": "execution-owner",
        "FX_RESIDUAL": "lotus-core",
        "CASH_RESIDUAL": "lotus-core",
        "RULE_OUTCOME": "lotus-core",
        "RISK_REDUCTION": "lotus-risk",
        "PERFORMANCE": "lotus-performance",
    }[dimension]
