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
    supportability = _read_mapping(metadata.get("calculation_supportability"))
    request_fingerprint = _read_text(metadata.get("request_fingerprint"))
    if request_fingerprint is None:
        raise RiskOutcomeSourceError(
            "lotus-risk metrics report is missing metadata.request_fingerprint"
        )

    supportability_state = _read_text(supportability.get("state")) or "ready"
    supportability_reason = _read_text(supportability.get("reason")) or "calculation_complete"
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
