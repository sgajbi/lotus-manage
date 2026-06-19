"""Source-owned risk realized evidence adapters for RFC-0042."""

from decimal import Decimal
from typing import Any, Literal

from src.core.outcomes.models import DpmRealizedSourceSnapshot
from src.core.outcomes.risk_source_attribution import (
    HistoricalAttributionOutcomeMeasure as HistoricalAttributionOutcomeMeasure,
    realized_historical_attribution_source_from_attribution_response as realized_historical_attribution_source_from_attribution_response,
)
from src.core.outcomes.risk_source_common import (
    RiskOutcomeSourceError as RiskOutcomeSourceError,
    _primary_reason,
    _quality_for_degraded_value,
    _read_mapping,
    _read_text,
    _decimal_value,
    _RiskSourcePosture,
    _RiskSourceQuality,
    _RiskSourceState,
    _risk_source_posture,
    _supportability,
    _supportability_source_posture,
)

__all__ = [
    "ConcentrationOutcomeMeasure",
    "DrawdownOutcomeMeasure",
    "HistoricalAttributionOutcomeMeasure",
    "RiskOutcomeMeasure",
    "RiskOutcomeSourceError",
    "RollingRiskOutcomeMetric",
    "RollingRiskOutcomeStatistic",
    "realized_concentration_source_from_concentration_response",
    "realized_drawdown_source_from_drawdown_response",
    "realized_historical_attribution_source_from_attribution_response",
    "realized_rolling_risk_source_from_rolling_response",
    "realized_risk_source_from_risk_metrics_report",
    "unavailable_risk_source",
]

RiskOutcomeMeasure = Literal[
    "VOLATILITY",
    "DRAWDOWN",
    "SHARPE",
    "SORTINO",
    "BETA",
    "TRACKING_ERROR",
    "INFORMATION_RATIO",
    "VAR",
]
DrawdownOutcomeMeasure = Literal[
    "max_drawdown",
    "relative_max_drawdown",
    "average_drawdown",
    "ulcer_index",
    "time_under_water_days",
]
ConcentrationOutcomeMeasure = Literal[
    "hhi_current",
    "hhi_proposed",
    "hhi_delta",
    "top_position_weight_current",
    "top_position_weight_proposed",
    "top_position_weight_delta",
    "top_n_cumulative_weight_current",
    "top_n_cumulative_weight_proposed",
    "top_n_cumulative_weight_delta",
    "issuer_hhi_current",
    "issuer_hhi_proposed",
    "issuer_hhi_delta",
    "top_issuer_weight_current",
    "top_issuer_weight_proposed",
    "top_issuer_weight_delta",
    "issuer_coverage_ratio_current",
    "issuer_coverage_ratio_proposed",
]
RollingRiskOutcomeMetric = Literal[
    "ROLLING_VOLATILITY",
    "ROLLING_SHARPE",
    "ROLLING_BETA",
    "ROLLING_TRACKING_ERROR",
    "ROLLING_INFORMATION_RATIO",
    "ROLLING_MAX_DRAWDOWN",
]
RollingRiskOutcomeStatistic = Literal[
    "latest",
    "average",
    "minimum",
    "maximum",
    "p05",
    "p50",
    "p95",
]


def realized_risk_source_from_risk_metrics_report(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    metric: RiskOutcomeMeasure = "VOLATILITY",
) -> DpmRealizedSourceSnapshot:
    """Adapt a lotus-risk RiskMetricsReport without recalculating risk truth locally."""

    result = _read_mapping(_read_mapping(response.get("results")).get(period))
    metric_result = _read_mapping(_read_mapping(result.get("metrics")).get(metric))
    metadata = _read_mapping(response.get("metadata"))
    scope = _read_mapping(response.get("scope"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk metrics report is missing metadata.request_fingerprint"
        )

    supportability_state, supportability_reason = _supportability(metadata)
    value = (
        _decimal_value(metric_result.get("value"))
        if metric_result.get("value") is not None
        else None
    )
    source_state, quality = _risk_source_posture(
        supportability_state=supportability_state,
        value=value,
    )
    _ensure_ready_risk_metric_value(
        source_state=source_state,
        value=value,
        metric=metric,
        period=period,
    )

    return _risk_metrics_source_snapshot(
        request_fingerprint=request_fingerprint,
        period=period,
        metric=metric,
        value=value if source_state != "NOT_SUPPORTED" else None,
        source_state=source_state,
        quality=quality,
        as_of_date=_read_text(scope.get("as_of_date")),
        supportability_state=supportability_state,
        supportability_reason=supportability_reason,
    )


def realized_drawdown_source_from_drawdown_response(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    measure: DrawdownOutcomeMeasure = "max_drawdown",
) -> DpmRealizedSourceSnapshot:
    """Adapt a lotus-risk DrawdownResponse without recalculating drawdown locally."""

    result = _read_mapping(_read_mapping(response.get("results")).get(period))
    metadata = _read_mapping(response.get("metadata"))
    scope = _read_mapping(response.get("scope"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk drawdown response is missing metadata.request_fingerprint"
        )

    supportability_state, supportability_reason = _supportability(metadata)
    value, measure_reason = _drawdown_value(result=result, measure=measure)
    source_state, quality = _drawdown_source_posture(
        supportability_state=supportability_state,
        value=value,
        measure_reason=measure_reason,
    )
    if source_state == "READY" and value is None:
        raise RiskOutcomeSourceError(
            f"lotus-risk drawdown response is missing a numeric {measure} value for {period}"
        )

    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="DRAWDOWN_RESPONSE",
        source_id=f"{request_fingerprint}:{period}:{measure}",
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit=_drawdown_unit(measure),
        source_state=source_state,
        quality=quality,
        observed_at=None,
        as_of_date=_read_text(scope.get("as_of_date")),
        content_hash=request_fingerprint,
        reason_codes=[
            _primary_reason(source_state),
            f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
            f"RISK_REASON_{supportability_reason.upper()}",
            f"RISK_PERIOD_{period}",
            f"RISK_DRAWDOWN_MEASURE_{measure.upper()}",
            measure_reason,
        ],
    )


def realized_concentration_source_from_concentration_response(
    response: dict[str, Any],
    *,
    measure: ConcentrationOutcomeMeasure = "hhi_current",
) -> DpmRealizedSourceSnapshot:
    """Adapt a lotus-risk concentration response without recalculating concentration locally."""

    metadata = _read_mapping(response.get("metadata"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk concentration response is missing metadata.request_fingerprint"
        )

    supportability_state, supportability_reason = _supportability(metadata)
    value = _concentration_value(response=response, measure=measure)
    issuer_coverage_status = _issuer_coverage_status(response)
    source_state, quality = _concentration_source_posture(
        supportability_state=supportability_state,
        value=value,
        measure=measure,
        issuer_coverage_status=issuer_coverage_status,
    )
    if source_state == "READY" and value is None:
        raise RiskOutcomeSourceError(
            f"lotus-risk concentration response is missing a numeric {measure} value"
        )

    return _concentration_source_snapshot(
        request_fingerprint=request_fingerprint,
        measure=measure,
        value=value,
        source_state=source_state,
        quality=quality,
        as_of_date=_read_text(metadata.get("as_of_date")),
        supportability_state=supportability_state,
        supportability_reason=supportability_reason,
        input_mode=_read_text(response.get("input_mode")),
        issuer_coverage_status=issuer_coverage_status,
    )


def realized_rolling_risk_source_from_rolling_response(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    metric: RollingRiskOutcomeMetric = "ROLLING_VOLATILITY",
    statistic: RollingRiskOutcomeStatistic = "latest",
    window_length: int | None = None,
) -> DpmRealizedSourceSnapshot:
    """Adapt a lotus-risk RollingResponse without recalculating rolling metrics locally."""

    metadata = _read_mapping(response.get("metadata"))
    scope = _read_mapping(response.get("scope"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk rolling response is missing metadata.request_fingerprint"
        )

    period_result = _read_mapping(_read_mapping(response.get("results")).get(period))
    selected_window, resolved_window_length = _rolling_window_result(
        period_result=period_result,
        window_length=window_length,
    )
    metric_summary = _read_mapping(
        _read_mapping(selected_window.get("metric_summaries")).get(metric)
    )
    value = _rolling_metric_value(metric_summary=metric_summary, statistic=statistic)
    supportability_state, supportability_reason = _supportability(metadata)
    context_reason = _rolling_context_reason(period_result=period_result, metric=metric)
    source_state, quality = _rolling_source_posture(
        supportability_state=supportability_state,
        value=value,
        context_reason=context_reason,
    )
    _ensure_ready_rolling_metric_value(
        source_state=source_state,
        value=value,
        metric=metric,
        statistic=statistic,
        period=period,
        resolved_window_length=resolved_window_length,
    )

    input_mode = _read_text(response.get("input_mode")) or "unknown"
    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="ROLLING_RISK_METRICS_REPORT",
        source_id=_rolling_source_id(
            request_fingerprint=request_fingerprint,
            period=period,
            resolved_window_length=resolved_window_length,
            metric=metric,
            statistic=statistic,
        ),
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at=_read_text(metric_summary.get("latest_observation_date")),
        as_of_date=_read_text(scope.get("as_of_date")),
        content_hash=request_fingerprint,
        reason_codes=_rolling_reason_codes(
            source_state=source_state,
            supportability_state=supportability_state,
            supportability_reason=supportability_reason,
            period=period,
            metric=metric,
            statistic=statistic,
            resolved_window_length=resolved_window_length,
            input_mode=input_mode,
            context_reason=context_reason,
        ),
    )


def unavailable_risk_source(
    *,
    source_id: str,
    reason_code: str,
    as_of_date: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Return bounded unavailable risk evidence when lotus-risk cannot serve truth."""

    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="RISK_METRICS_REPORT",
        source_id=source_id,
        value=None,
        unit="ratio",
        source_state="DEGRADED",
        quality="UNAVAILABLE",
        observed_at=None,
        as_of_date=as_of_date,
        content_hash=None,
        reason_codes=[reason_code],
    )


def _drawdown_value(
    *,
    result: dict[str, Any],
    measure: DrawdownOutcomeMeasure,
) -> tuple[Decimal | None, str]:
    summary = _read_mapping(result.get("summary"))
    absolute_drawdown = _absolute_drawdown_value(summary=summary, measure=measure)
    if absolute_drawdown is not None:
        return absolute_drawdown
    return _relative_drawdown_value(result=result)


def _ensure_ready_risk_metric_value(
    *,
    source_state: _RiskSourceState,
    value: Decimal | None,
    metric: RiskOutcomeMeasure,
    period: str,
) -> None:
    if source_state != "READY" or value is not None:
        return
    raise RiskOutcomeSourceError(
        f"lotus-risk metrics report is missing a numeric {metric} value for {period}"
    )


def _risk_metrics_source_snapshot(
    *,
    request_fingerprint: str,
    period: str,
    metric: RiskOutcomeMeasure,
    value: Decimal | None,
    source_state: _RiskSourceState,
    quality: _RiskSourceQuality,
    as_of_date: str | None,
    supportability_state: str,
    supportability_reason: str,
) -> DpmRealizedSourceSnapshot:
    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="RISK_METRICS_REPORT",
        source_id=f"{request_fingerprint}:{period}:{metric}",
        value=value,
        unit=_metric_unit(metric),
        source_state=source_state,
        quality=quality,
        observed_at=None,
        as_of_date=as_of_date,
        content_hash=request_fingerprint,
        reason_codes=[
            _primary_reason(source_state),
            f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
            f"RISK_REASON_{supportability_reason.upper()}",
            f"RISK_PERIOD_{period}",
            f"RISK_METRIC_{metric}",
        ],
    )


def _absolute_drawdown_value(
    *,
    summary: dict[str, Any],
    measure: DrawdownOutcomeMeasure,
) -> tuple[Decimal | None, str] | None:
    source_field_by_measure = {
        "max_drawdown": ("max_drawdown", "RISK_DRAWDOWN_ABSOLUTE"),
        "average_drawdown": ("average_drawdown", "RISK_DRAWDOWN_AVERAGE"),
        "ulcer_index": ("ulcer_index", "RISK_DRAWDOWN_ULCER_INDEX"),
        "time_under_water_days": (
            "time_under_water_days",
            "RISK_DRAWDOWN_TIME_UNDER_WATER",
        ),
    }
    source_field_and_reason = source_field_by_measure.get(measure)
    if source_field_and_reason is None:
        return None
    source_field, reason = source_field_and_reason
    raw_value = summary.get(source_field)
    return _decimal_value(raw_value) if raw_value is not None else None, reason


def _relative_drawdown_value(
    *,
    result: dict[str, Any],
) -> tuple[Decimal | None, str]:
    relative_context = _read_mapping(result.get("relative_to_benchmark_context"))
    applied = relative_context.get("applied") is True
    reason = _read_text(relative_context.get("reason")) or "UNKNOWN"
    if not applied:
        return None, f"RISK_DRAWDOWN_RELATIVE_{reason.upper()}"
    relative = _read_mapping(result.get("relative_to_benchmark"))
    return (
        _decimal_value(relative.get("max_drawdown"))
        if relative.get("max_drawdown") is not None
        else None,
        f"RISK_DRAWDOWN_RELATIVE_{reason.upper()}",
    )


def _concentration_value(
    *,
    response: dict[str, Any],
    measure: ConcentrationOutcomeMeasure,
) -> Decimal | None:
    risk_proxy = _read_mapping(response.get("risk_proxy"))
    single_position = _read_mapping(response.get("single_position_concentration"))
    issuer = _read_mapping(response.get("issuer_concentration"))
    value_by_measure = {
        "hhi_current": risk_proxy.get("hhi_current"),
        "hhi_proposed": risk_proxy.get("hhi_proposed"),
        "hhi_delta": risk_proxy.get("hhi_delta"),
        "top_position_weight_current": single_position.get("top_position_weight_current"),
        "top_position_weight_proposed": single_position.get("top_position_weight_proposed"),
        "top_position_weight_delta": single_position.get("top_position_weight_delta"),
        "top_n_cumulative_weight_current": single_position.get("top_n_cumulative_weight_current"),
        "top_n_cumulative_weight_proposed": single_position.get("top_n_cumulative_weight_proposed"),
        "top_n_cumulative_weight_delta": single_position.get("top_n_cumulative_weight_delta"),
        "issuer_hhi_current": issuer.get("hhi_current"),
        "issuer_hhi_proposed": issuer.get("hhi_proposed"),
        "issuer_hhi_delta": issuer.get("hhi_delta"),
        "top_issuer_weight_current": issuer.get("top_issuer_weight_current"),
        "top_issuer_weight_proposed": issuer.get("top_issuer_weight_proposed"),
        "top_issuer_weight_delta": issuer.get("top_issuer_weight_delta"),
        "issuer_coverage_ratio_current": issuer.get("coverage_ratio_current"),
        "issuer_coverage_ratio_proposed": issuer.get("coverage_ratio_proposed"),
    }[measure]
    return _decimal_value(value_by_measure) if value_by_measure is not None else None


def _concentration_source_snapshot(
    *,
    request_fingerprint: str,
    measure: ConcentrationOutcomeMeasure,
    value: Decimal | None,
    source_state: Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    quality: Literal[
        "COMPLETE",
        "STALE",
        "UNAVAILABLE",
        "PARTIAL",
        "MISSING",
        "NOT_SUPPORTED",
    ],
    as_of_date: str | None,
    supportability_state: str,
    supportability_reason: str,
    input_mode: str | None,
    issuer_coverage_status: str | None,
) -> DpmRealizedSourceSnapshot:
    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="CONCENTRATION_RESPONSE",
        source_id=f"{request_fingerprint}:{measure}",
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit=_concentration_unit(measure),
        source_state=source_state,
        quality=quality,
        observed_at=None,
        as_of_date=as_of_date,
        content_hash=request_fingerprint,
        reason_codes=_concentration_reason_codes(
            source_state=source_state,
            supportability_state=supportability_state,
            supportability_reason=supportability_reason,
            measure=measure,
            input_mode=input_mode,
            issuer_coverage_status=issuer_coverage_status,
        ),
    )


def _concentration_reason_codes(
    *,
    source_state: str,
    supportability_state: str,
    supportability_reason: str,
    measure: ConcentrationOutcomeMeasure,
    input_mode: str | None,
    issuer_coverage_status: str | None,
) -> list[str]:
    reason_codes = [
        _primary_reason(source_state),
        f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
        f"RISK_REASON_{supportability_reason.upper()}",
        f"RISK_CONCENTRATION_MEASURE_{measure.upper()}",
        f"RISK_CONCENTRATION_INPUT_MODE_{(input_mode or 'UNKNOWN').upper()}",
    ]
    if issuer_coverage_status is not None or _is_issuer_concentration_measure(measure):
        reason_codes.append(
            f"RISK_CONCENTRATION_ISSUER_COVERAGE_{(issuer_coverage_status or 'unknown').upper()}"
        )
    return reason_codes


def _rolling_window_result(
    *,
    period_result: dict[str, Any],
    window_length: int | None,
) -> tuple[dict[str, Any], int | str]:
    window_results = period_result.get("window_results")
    if not isinstance(window_results, list):
        return {}, _fallback_requested_window(window_length)
    for window_result in window_results:
        window_mapping = _read_mapping(window_result)
        resolved_window = window_mapping.get("window_length")
        if _rolling_window_matches_request(
            resolved_window=resolved_window,
            requested_window=window_length,
        ):
            return window_mapping, _resolved_window_length(resolved_window)
    return {}, _fallback_requested_window(window_length)


def _rolling_source_id(
    *,
    request_fingerprint: str,
    period: str,
    resolved_window_length: int | str,
    metric: RollingRiskOutcomeMetric,
    statistic: RollingRiskOutcomeStatistic,
) -> str:
    return f"{request_fingerprint}:{period}:rolling:{resolved_window_length}:{metric}:{statistic}"


def _rolling_metric_value(
    *,
    metric_summary: dict[str, Any],
    statistic: RollingRiskOutcomeStatistic,
) -> Decimal | None:
    raw_value = metric_summary.get(statistic)
    return _decimal_value(raw_value) if raw_value is not None else None


def _ensure_ready_rolling_metric_value(
    *,
    source_state: _RiskSourceState,
    value: Decimal | None,
    metric: RollingRiskOutcomeMetric,
    statistic: RollingRiskOutcomeStatistic,
    period: str,
    resolved_window_length: int | str,
) -> None:
    if source_state != "READY" or value is not None:
        return
    raise RiskOutcomeSourceError(
        "lotus-risk rolling response is missing a numeric "
        f"{metric} {statistic} value for {period} window {resolved_window_length}"
    )


def _rolling_reason_codes(
    *,
    source_state: _RiskSourceState,
    supportability_state: str,
    supportability_reason: str,
    period: str,
    metric: RollingRiskOutcomeMetric,
    statistic: RollingRiskOutcomeStatistic,
    resolved_window_length: int | str,
    input_mode: str,
    context_reason: str,
) -> list[str]:
    return [
        _primary_reason(source_state),
        f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
        f"RISK_REASON_{supportability_reason.upper()}",
        f"RISK_PERIOD_{period}",
        f"RISK_ROLLING_METRIC_{metric}",
        f"RISK_ROLLING_STATISTIC_{statistic.upper()}",
        f"RISK_ROLLING_WINDOW_{resolved_window_length}",
        f"RISK_ROLLING_INPUT_MODE_{input_mode.upper()}",
        context_reason,
    ]


def _rolling_window_matches_request(
    *,
    resolved_window: object,
    requested_window: int | None,
) -> bool:
    return requested_window is None or resolved_window == requested_window


def _fallback_requested_window(window_length: int | None) -> int | str:
    return window_length or "unknown"


def _resolved_window_length(window_length: Any) -> int | str:
    return window_length if window_length is not None else "unknown"


def _rolling_context_reason(
    *,
    period_result: dict[str, Any],
    metric: RollingRiskOutcomeMetric,
) -> str:
    if metric in {
        "ROLLING_BETA",
        "ROLLING_TRACKING_ERROR",
        "ROLLING_INFORMATION_RATIO",
    }:
        context = _read_mapping(period_result.get("benchmark_context"))
        reason = _read_text(context.get("reason")) or "UNKNOWN"
        return f"RISK_ROLLING_BENCHMARK_{reason.upper()}"
    if metric == "ROLLING_SHARPE":
        context = _read_mapping(period_result.get("risk_free_context"))
        reason = _read_text(context.get("reason")) or "UNKNOWN"
        return f"RISK_ROLLING_RISK_FREE_{reason.upper()}"
    return "RISK_ROLLING_CONTEXT_NOT_REQUIRED"


def _issuer_coverage_status(response: dict[str, Any]) -> str | None:
    issuer = _read_mapping(response.get("issuer_concentration"))
    return _read_text(issuer.get("coverage_status"))


def _concentration_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    measure: ConcentrationOutcomeMeasure,
    issuer_coverage_status: str | None,
) -> tuple[
    Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    Literal["COMPLETE", "STALE", "UNAVAILABLE", "PARTIAL", "MISSING", "NOT_SUPPORTED"],
]:
    source_state, quality = _risk_source_posture(
        supportability_state=supportability_state,
        value=value,
    )
    if source_state == "READY" and _is_issuer_concentration_measure(measure):
        if issuer_coverage_status != "complete":
            return "DEGRADED", "PARTIAL" if value is not None else "UNAVAILABLE"
    return source_state, quality


def _drawdown_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    measure_reason: str,
) -> _RiskSourcePosture:
    supportability_posture = _supportability_source_posture(supportability_state)
    if supportability_posture is not None:
        return supportability_posture
    if _drawdown_measure_unavailable(value=value, measure_reason=measure_reason):
        return "DEGRADED", "UNAVAILABLE"
    if supportability_state != "ready":
        return "DEGRADED", _quality_for_degraded_value(value)
    return "READY", "COMPLETE"


def _drawdown_measure_unavailable(*, value: Decimal | None, measure_reason: str) -> bool:
    return value is None and measure_reason != "RISK_DRAWDOWN_ABSOLUTE"


def _rolling_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    context_reason: str,
) -> _RiskSourcePosture:
    supportability_posture = _supportability_source_posture(supportability_state)
    if supportability_posture is not None:
        return supportability_posture
    if _rolling_context_unavailable(context_reason):
        return "DEGRADED", "UNAVAILABLE"
    if supportability_state != "ready":
        return "DEGRADED", _quality_for_degraded_value(value)
    return "READY", "COMPLETE"


def _rolling_context_unavailable(context_reason: str) -> bool:
    return (
        context_reason.endswith("_BENCHMARK_UNAVAILABLE")
        or context_reason.endswith("_RISK_FREE_UNAVAILABLE")
        or context_reason.endswith("_NO_ALIGNED_OBSERVATIONS")
    )


def _is_issuer_concentration_measure(measure: ConcentrationOutcomeMeasure) -> bool:
    return measure.startswith("issuer_") or measure.startswith("top_issuer_")


def _metric_unit(metric: RiskOutcomeMeasure) -> str:
    if metric == "VAR":
        return "percentage_point"
    if metric in {"SHARPE", "SORTINO", "BETA", "INFORMATION_RATIO"}:
        return "ratio"
    return "ratio"


def _drawdown_unit(measure: DrawdownOutcomeMeasure) -> str:
    if measure == "time_under_water_days":
        return "days"
    return "ratio"


def _concentration_unit(measure: ConcentrationOutcomeMeasure) -> str:
    if "hhi" in measure:
        return "hhi"
    return "ratio"
