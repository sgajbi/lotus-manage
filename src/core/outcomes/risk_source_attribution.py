"""Source-owned lotus-risk historical attribution outcome adapter."""

from decimal import Decimal
from typing import Any, Literal

from src.core.outcomes.models import DpmRealizedSourceSnapshot
from src.core.outcomes.risk_source_common import (
    RiskOutcomeSourceError,
    _primary_reason,
    _quality_for_degraded_value,
    _read_list,
    _read_mapping,
    _read_text,
    _decimal_value,
    _RiskSourcePosture,
    _RiskSourceQuality,
    _RiskSourceState,
    _supportability,
    _supportability_source_posture,
)

HistoricalAttributionOutcomeMeasure = Literal[
    "total_value",
    "reconciled_sum",
    "residual",
    "contributor_weight_average",
    "contributor_marginal_contribution",
    "contributor_component_contribution",
    "contributor_percent_contribution",
]


def realized_historical_attribution_source_from_attribution_response(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    attribution_type: str = "ACTIVE_RISK",
    metric: str = "TRACKING_ERROR",
    grouping_dimension: str = "SECTOR",
    measure: HistoricalAttributionOutcomeMeasure = "total_value",
    contributor_group_key: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-risk historical attribution without recalculating attribution locally."""

    metadata = _read_mapping(response.get("metadata"))
    scope = _read_mapping(response.get("scope"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk historical attribution response is missing metadata.request_fingerprint"
        )

    period_result = _read_mapping(_read_mapping(response.get("results")).get(period))
    period_error = _read_text(period_result.get("error"))
    attribution_set = _historical_attribution_set(
        period_result=period_result,
        attribution_type=attribution_type,
        metric=metric,
        grouping_dimension=grouping_dimension,
    )
    supportability_state, supportability_reason = _supportability(metadata)
    quality_flags = _read_list(attribution_set.get("quality_flags"))
    value, measure_reason = _historical_attribution_value(
        attribution_set=attribution_set,
        measure=measure,
        contributor_group_key=contributor_group_key,
    )
    source_state, quality = _historical_attribution_source_posture(
        supportability_state=supportability_state,
        value=value,
        period_error=period_error,
        quality_flags=quality_flags,
    )
    _ensure_ready_historical_attribution_value(
        source_state=source_state,
        value=value,
        measure=measure,
        period=period,
        attribution_type=attribution_type,
        metric=metric,
        grouping_dimension=grouping_dimension,
    )

    input_mode = _read_text(response.get("input_mode")) or "unknown"

    return _historical_attribution_source_snapshot(
        request_fingerprint=request_fingerprint,
        period=period,
        attribution_type=attribution_type,
        metric=metric,
        grouping_dimension=grouping_dimension,
        measure=measure,
        contributor_group_key=contributor_group_key,
        value=value,
        source_state=source_state,
        quality=quality,
        observed_at=_read_text(period_result.get("end_date")),
        as_of_date=_read_text(scope.get("as_of_date")),
        supportability_state=supportability_state,
        supportability_reason=supportability_reason,
        input_mode=input_mode,
        metadata=metadata,
        measure_reason=measure_reason,
        quality_flags=quality_flags,
        period_error=period_error,
    )


def _historical_attribution_source_id(
    *,
    request_fingerprint: str,
    period: str,
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
    measure: HistoricalAttributionOutcomeMeasure,
    contributor_group_key: str | None,
) -> str:
    source_id_parts = [
        request_fingerprint,
        period,
        "historical-attribution",
        attribution_type,
        metric,
        grouping_dimension,
        measure,
    ]
    if contributor_group_key is not None:
        source_id_parts.append(contributor_group_key)
    return ":".join(source_id_parts)


def _historical_attribution_source_snapshot(
    *,
    request_fingerprint: str,
    period: str,
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
    measure: HistoricalAttributionOutcomeMeasure,
    contributor_group_key: str | None,
    value: Decimal | None,
    source_state: _RiskSourceState,
    quality: _RiskSourceQuality,
    observed_at: str | None,
    as_of_date: str | None,
    supportability_state: str,
    supportability_reason: str,
    input_mode: str,
    metadata: dict[str, Any],
    measure_reason: str,
    quality_flags: list[Any],
    period_error: str | None,
) -> DpmRealizedSourceSnapshot:
    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="HISTORICAL_RISK_ATTRIBUTION",
        source_id=_historical_attribution_source_id(
            request_fingerprint=request_fingerprint,
            period=period,
            attribution_type=attribution_type,
            metric=metric,
            grouping_dimension=grouping_dimension,
            measure=measure,
            contributor_group_key=contributor_group_key,
        ),
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at=observed_at,
        as_of_date=as_of_date,
        content_hash=request_fingerprint,
        reason_codes=_historical_attribution_reason_codes(
            source_state=source_state,
            supportability_state=supportability_state,
            supportability_reason=supportability_reason,
            period=period,
            attribution_type=attribution_type,
            metric=metric,
            grouping_dimension=grouping_dimension,
            measure=measure,
            input_mode=input_mode,
            metadata=metadata,
            measure_reason=measure_reason,
            quality_flags=quality_flags,
            period_error=period_error,
        ),
    )


def _historical_attribution_reason_codes(
    *,
    source_state: _RiskSourceState,
    supportability_state: str,
    supportability_reason: str,
    period: str,
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
    measure: HistoricalAttributionOutcomeMeasure,
    input_mode: str,
    metadata: dict[str, Any],
    measure_reason: str,
    quality_flags: list[Any],
    period_error: str | None,
) -> list[str]:
    return [
        _primary_reason(source_state),
        f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
        f"RISK_REASON_{supportability_reason.upper()}",
        f"RISK_PERIOD_{period}",
        f"RISK_ATTRIBUTION_TYPE_{attribution_type}",
        f"RISK_ATTRIBUTION_METRIC_{metric}",
        f"RISK_ATTRIBUTION_GROUPING_{grouping_dimension}",
        f"RISK_ATTRIBUTION_MEASURE_{measure.upper()}",
        f"RISK_ATTRIBUTION_INPUT_MODE_{input_mode.upper()}",
        _historical_attribution_support_reason(metadata),
        measure_reason,
        _quality_flags_reason(quality_flags),
        _period_error_reason(period_error),
    ]


def _ensure_ready_historical_attribution_value(
    *,
    source_state: _RiskSourceState,
    value: Decimal | None,
    measure: HistoricalAttributionOutcomeMeasure,
    period: str,
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
) -> None:
    if source_state != "READY" or value is not None:
        return
    raise RiskOutcomeSourceError(
        "lotus-risk historical attribution response is missing a numeric "
        f"{measure} value for {period} {attribution_type} {metric} {grouping_dimension}"
    )


def _historical_attribution_set(
    *,
    period_result: dict[str, Any],
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
) -> dict[str, Any]:
    attribution_sets = _historical_attribution_sets(period_result)
    if not attribution_sets:
        return {}
    for attribution_set in attribution_sets:
        set_mapping = _read_mapping(attribution_set)
        if _historical_attribution_set_matches(
            attribution_set=set_mapping,
            attribution_type=attribution_type,
            metric=metric,
            grouping_dimension=grouping_dimension,
        ):
            return set_mapping
    return {}


def _historical_attribution_sets(period_result: dict[str, Any]) -> list[Any]:
    attribution_sets = period_result.get("attribution_sets")
    return attribution_sets if isinstance(attribution_sets, list) else []


def _historical_attribution_set_matches(
    *,
    attribution_set: dict[str, Any],
    attribution_type: str,
    metric: str,
    grouping_dimension: str,
) -> bool:
    return (
        _read_text(attribution_set.get("attribution_type")) == attribution_type
        and _read_text(attribution_set.get("metric")) == metric
        and _read_text(attribution_set.get("grouping_dimension")) == grouping_dimension
    )


def _historical_attribution_value(
    *,
    attribution_set: dict[str, Any],
    measure: HistoricalAttributionOutcomeMeasure,
    contributor_group_key: str | None,
) -> tuple[Decimal | None, str]:
    if not measure.startswith("contributor_"):
        raw_value = attribution_set.get(measure)
        return (
            _decimal_value(raw_value) if raw_value is not None else None,
            "RISK_ATTRIBUTION_SET_LEVEL",
        )

    if contributor_group_key is None:
        raise RiskOutcomeSourceError(
            "lotus-risk historical attribution contributor measures require contributor_group_key"
        )
    source_field = measure.removeprefix("contributor_")
    contributor = _historical_attribution_contributor(
        attribution_set=attribution_set,
        contributor_group_key=contributor_group_key,
    )
    raw_value = contributor.get(source_field)
    return (
        _decimal_value(raw_value) if raw_value is not None else None,
        f"RISK_ATTRIBUTION_CONTRIBUTOR_{contributor_group_key}",
    )


def _historical_attribution_contributor(
    *,
    attribution_set: dict[str, Any],
    contributor_group_key: str,
) -> dict[str, Any]:
    contributors = attribution_set.get("contributors")
    if not isinstance(contributors, list):
        return {}
    for contributor in contributors:
        contributor_mapping = _read_mapping(contributor)
        if _read_text(contributor_mapping.get("group_key")) == contributor_group_key:
            return contributor_mapping
    return {}


def _historical_attribution_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    period_error: str | None,
    quality_flags: list[Any],
) -> _RiskSourcePosture:
    fail_closed_posture = _historical_attribution_fail_closed_posture(supportability_state)
    if fail_closed_posture is not None:
        return fail_closed_posture
    if _historical_attribution_period_blocked(period_error):
        return "BLOCKED", "MISSING"
    return _historical_attribution_quality_posture(
        supportability_state=supportability_state,
        value=value,
        quality_flags=quality_flags,
    )


def _historical_attribution_fail_closed_posture(
    supportability_state: str,
) -> _RiskSourcePosture | None:
    return _supportability_source_posture(supportability_state, include_stale=False)


def _historical_attribution_period_blocked(period_error: str | None) -> bool:
    return period_error is not None


def _historical_attribution_quality_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    quality_flags: list[Any],
) -> _RiskSourcePosture:
    supportability_posture = _supportability_source_posture(supportability_state)
    if supportability_posture is not None:
        return supportability_posture
    if supportability_state != "ready":
        return "DEGRADED", _quality_for_degraded_value(value)
    if quality_flags:
        return "DEGRADED", _quality_for_degraded_value(value)
    return "READY", "COMPLETE"


def _historical_attribution_support_reason(metadata: dict[str, Any]) -> str:
    supported = metadata.get("stateful_active_risk_supported_grouping_dimensions")
    gated = metadata.get("stateful_active_risk_gated_grouping_dimensions")
    gate_reason = _read_text(metadata.get("stateful_active_risk_gate_reason"))
    supported_count = len(supported) if isinstance(supported, list) else 0
    gated_count = len(gated) if isinstance(gated, list) else 0
    reason = (gate_reason or "none").upper().replace(" ", "_")
    return (
        "RISK_ATTRIBUTION_STATEFUL_ACTIVE_RISK_SUPPORT_"
        f"SUPPORTED_{supported_count}_GATED_{gated_count}_REASON_{reason}"
    )


def _quality_flags_reason(quality_flags: list[Any]) -> str:
    return f"RISK_ATTRIBUTION_QUALITY_FLAGS_{len(quality_flags)}"


def _period_error_reason(period_error: str | None) -> str:
    if period_error is None:
        return "RISK_ATTRIBUTION_PERIOD_OK"
    return f"RISK_ATTRIBUTION_PERIOD_ERROR_{period_error.upper().replace(' ', '_')}"
