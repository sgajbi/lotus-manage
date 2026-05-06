"""Source-owned risk realized evidence adapters for RFC-0042."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from src.core.outcomes.models import DpmRealizedSourceSnapshot

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
DrawdownOutcomeMeasure = Literal["max_drawdown", "relative_max_drawdown"]
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


class RiskOutcomeSourceError(ValueError):
    """Raised when a lotus-risk response cannot produce bounded outcome evidence."""


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
    if source_state == "READY" and value is None:
        raise RiskOutcomeSourceError(
            f"lotus-risk metrics report is missing a numeric {metric} value for {period}"
        )

    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="RISK_METRICS_REPORT",
        source_id=f"{request_fingerprint}:{period}:{metric}",
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit=_metric_unit(metric),
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
            f"RISK_METRIC_{metric}",
        ],
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
        unit="ratio",
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

    reason_codes = [
        _primary_reason(source_state),
        f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
        f"RISK_REASON_{supportability_reason.upper()}",
        f"RISK_CONCENTRATION_MEASURE_{measure.upper()}",
        "RISK_CONCENTRATION_INPUT_MODE_"
        f"{(_read_text(response.get('input_mode')) or 'UNKNOWN').upper()}",
    ]
    if issuer_coverage_status is not None or _is_issuer_concentration_measure(measure):
        reason_codes.append(
            f"RISK_CONCENTRATION_ISSUER_COVERAGE_{(issuer_coverage_status or 'unknown').upper()}"
        )

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
        as_of_date=_read_text(metadata.get("as_of_date")),
        content_hash=request_fingerprint,
        reason_codes=reason_codes,
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
    value = (
        _decimal_value(metric_summary.get(statistic))
        if metric_summary.get(statistic) is not None
        else None
    )
    supportability_state, supportability_reason = _supportability(metadata)
    context_reason = _rolling_context_reason(period_result=period_result, metric=metric)
    source_state, quality = _rolling_source_posture(
        supportability_state=supportability_state,
        value=value,
        context_reason=context_reason,
    )
    if source_state == "READY" and value is None:
        raise RiskOutcomeSourceError(
            "lotus-risk rolling response is missing a numeric "
            f"{metric} {statistic} value for {period} window {resolved_window_length}"
        )

    input_mode = _read_text(response.get("input_mode")) or "unknown"
    return DpmRealizedSourceSnapshot(
        dimension="RISK_REDUCTION",
        source_system="lotus-risk",
        source_type="ROLLING_RISK_METRICS_REPORT",
        source_id=(
            f"{request_fingerprint}:{period}:rolling:{resolved_window_length}:{metric}:{statistic}"
        ),
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at=_read_text(metric_summary.get("latest_observation_date")),
        as_of_date=_read_text(scope.get("as_of_date")),
        content_hash=request_fingerprint,
        reason_codes=[
            _primary_reason(source_state),
            f"RISK_SUPPORTABILITY_{supportability_state.upper()}",
            f"RISK_REASON_{supportability_reason.upper()}",
            f"RISK_PERIOD_{period}",
            f"RISK_ROLLING_METRIC_{metric}",
            f"RISK_ROLLING_STATISTIC_{statistic.upper()}",
            f"RISK_ROLLING_WINDOW_{resolved_window_length}",
            f"RISK_ROLLING_INPUT_MODE_{input_mode.upper()}",
            context_reason,
        ],
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


def _supportability(metadata: dict[str, Any]) -> tuple[str, str]:
    supportability = _read_mapping(metadata.get("calculation_supportability"))
    return (
        _read_text(supportability.get("state")) or "ready",
        _read_text(supportability.get("reason")) or "calculation_complete",
    )


def _drawdown_value(
    *,
    result: dict[str, Any],
    measure: DrawdownOutcomeMeasure,
) -> tuple[Decimal | None, str]:
    if measure == "max_drawdown":
        summary = _read_mapping(result.get("summary"))
        return (
            _decimal_value(summary.get("max_drawdown"))
            if summary.get("max_drawdown") is not None
            else None,
            "RISK_DRAWDOWN_ABSOLUTE",
        )

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


def _rolling_window_result(
    *,
    period_result: dict[str, Any],
    window_length: int | None,
) -> tuple[dict[str, Any], int | str]:
    window_results = period_result.get("window_results")
    if not isinstance(window_results, list):
        return {}, window_length or "unknown"
    for window_result in window_results:
        window_mapping = _read_mapping(window_result)
        resolved_window = window_mapping.get("window_length")
        if window_length is None or resolved_window == window_length:
            return window_mapping, resolved_window if resolved_window is not None else "unknown"
    return {}, window_length or "unknown"


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
) -> tuple[
    Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    Literal["COMPLETE", "STALE", "UNAVAILABLE", "PARTIAL", "MISSING", "NOT_SUPPORTED"],
]:
    if supportability_state == "unsupported":
        return "NOT_SUPPORTED", "NOT_SUPPORTED"
    if supportability_state == "permission_blocked":
        return "BLOCKED", "MISSING"
    if supportability_state == "stale":
        return "DEGRADED", "STALE"
    if value is None and measure_reason != "RISK_DRAWDOWN_ABSOLUTE":
        return "DEGRADED", "UNAVAILABLE"
    if supportability_state != "ready":
        return "DEGRADED", "PARTIAL" if value is not None else "UNAVAILABLE"
    return "READY", "COMPLETE"


def _rolling_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
    context_reason: str,
) -> tuple[
    Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    Literal["COMPLETE", "STALE", "UNAVAILABLE", "PARTIAL", "MISSING", "NOT_SUPPORTED"],
]:
    if supportability_state == "unsupported":
        return "NOT_SUPPORTED", "NOT_SUPPORTED"
    if supportability_state == "permission_blocked":
        return "BLOCKED", "MISSING"
    if supportability_state == "stale":
        return "DEGRADED", "STALE"
    if (
        context_reason.endswith("_BENCHMARK_UNAVAILABLE")
        or context_reason.endswith("_RISK_FREE_UNAVAILABLE")
        or context_reason.endswith("_NO_ALIGNED_OBSERVATIONS")
    ):
        return "DEGRADED", "UNAVAILABLE"
    if supportability_state != "ready":
        return "DEGRADED", "PARTIAL" if value is not None else "UNAVAILABLE"
    return "READY", "COMPLETE"


def _is_issuer_concentration_measure(measure: ConcentrationOutcomeMeasure) -> bool:
    return measure.startswith("issuer_") or measure.startswith("top_issuer_")


def _risk_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
) -> tuple[
    Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    Literal["COMPLETE", "STALE", "UNAVAILABLE", "PARTIAL", "MISSING", "NOT_SUPPORTED"],
]:
    if supportability_state == "unsupported":
        return "NOT_SUPPORTED", "NOT_SUPPORTED"
    if supportability_state == "permission_blocked":
        return "BLOCKED", "MISSING"
    if supportability_state == "stale":
        return "DEGRADED", "STALE"
    if supportability_state != "ready":
        return "DEGRADED", "PARTIAL" if value is not None else "UNAVAILABLE"
    return "READY", "COMPLETE"


def _primary_reason(source_state: str) -> str:
    if source_state == "READY":
        return "RISK_SOURCE_READY"
    if source_state == "NOT_SUPPORTED":
        return "RISK_SOURCE_NOT_SUPPORTED"
    if source_state == "BLOCKED":
        return "RISK_SOURCE_BLOCKED"
    return "RISK_SOURCE_DEGRADED"


def _metric_unit(metric: RiskOutcomeMeasure) -> str:
    if metric == "VAR":
        return "percentage_point"
    if metric in {"SHARPE", "SORTINO", "BETA", "INFORMATION_RATIO"}:
        return "ratio"
    return "ratio"


def _concentration_unit(measure: ConcentrationOutcomeMeasure) -> str:
    if "hhi" in measure:
        return "hhi"
    return "ratio"


def _read_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise RiskOutcomeSourceError(
            "lotus-risk metrics report contains a non-numeric risk metric value"
        ) from exc
