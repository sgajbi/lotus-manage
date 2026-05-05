"""Source-owned performance realized evidence adapters for RFC-0042."""

from decimal import Decimal, InvalidOperation
import re
from typing import Any, Literal

from src.core.outcomes.models import DpmRealizedSourceSnapshot

PerformanceReturnMeasure = Literal["period_return", "cumulative_return", "annualized_return"]
PerformanceBasis = Literal["net", "gross"]
ContributionOutcomeMeasure = Literal[
    "total_contribution",
    "total_portfolio_return",
    "summary_portfolio_contribution",
    "summary_local_contribution",
    "summary_fx_contribution",
]


class PerformanceOutcomeSourceError(ValueError):
    """Raised when a lotus-performance response cannot produce bounded outcome evidence."""


def realized_performance_source_from_workspace_summary(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    basis: PerformanceBasis = "net",
    return_measure: PerformanceReturnMeasure = "cumulative_return",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-performance workspace-summary output without recalculating performance truth.

    lotus-performance publishes return values in percentage-point units. RFC-0042 outcome
    comparisons use ratio units, so this adapter performs only a unit conversion and lineage
    wrapping; it does not compute returns, benchmark effects, or portfolio economics locally.
    """

    period_result = _workspace_period(response, period=period)
    portfolio_twr = _read_mapping(period_result.get("portfolio_twr"))
    basis_block = _read_mapping(portfolio_twr.get(basis))
    summary = _read_mapping(basis_block.get("summary"))
    return_value = _read_mapping(summary.get(return_measure))
    base_return = _decimal_from_percentage_points(
        return_value.get("base"),
        context="base return",
    )
    metadata = _workspace_metadata(response)
    source_id = f"{metadata['calculation_id']}:{period}:twr:{basis}:{return_measure}"
    reason_codes = [
        "PERFORMANCE_SOURCE_READY",
        f"PERFORMANCE_PERIOD_{period}",
        "PERFORMANCE_MEASURE_FAMILY_TWR",
        f"PERFORMANCE_BASIS_{basis.upper()}",
        f"PERFORMANCE_MEASURE_{return_measure.upper()}",
    ]
    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="WORKSPACE_SUMMARY_TWR_RETURN",
        source_id=source_id,
        value=base_return,
        unit="ratio",
        source_state="READY",
        quality="COMPLETE",
        observed_at=None,
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["calculation_hash"],
        reason_codes=reason_codes,
    )


def realized_active_performance_source_from_workspace_summary(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    basis: PerformanceBasis = "net",
    return_measure: PerformanceReturnMeasure = "cumulative_return",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-performance active return output without local relative-return math."""

    period_result = _workspace_period(response, period=period)
    active_summary = _read_mapping(_read_mapping(period_result.get("active")).get(basis))
    return_value = _read_mapping(active_summary.get(return_measure))
    base_return = _decimal_from_percentage_points(
        return_value.get("base"),
        context="active base return",
    )
    metadata = _workspace_metadata(response)
    source_id = f"{metadata['calculation_id']}:{period}:active:{basis}:{return_measure}"
    reason_codes = [
        "PERFORMANCE_SOURCE_READY",
        f"PERFORMANCE_PERIOD_{period}",
        "PERFORMANCE_MEASURE_FAMILY_ACTIVE",
        f"PERFORMANCE_BASIS_{basis.upper()}",
        f"PERFORMANCE_MEASURE_{return_measure.upper()}",
    ]
    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="WORKSPACE_SUMMARY_ACTIVE_RETURN",
        source_id=source_id,
        value=base_return,
        unit="ratio",
        source_state="READY",
        quality="COMPLETE",
        observed_at=None,
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["calculation_hash"],
        reason_codes=reason_codes,
    )


def realized_mwr_source_from_workspace_summary(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    return_measure: PerformanceReturnMeasure = "cumulative_return",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-performance workspace MWR output without local IRR or flow calculations."""

    period_result = _workspace_period(response, period=period)
    mwr_summary = _read_mapping(period_result.get("money_weighted_return"))
    base_return = _decimal_from_percentage_points(
        mwr_summary.get(return_measure),
        context="money-weighted return",
    )
    metadata = _workspace_metadata(response)
    method = _read_text(mwr_summary.get("method")) or "unknown"
    input_mode = _read_text(mwr_summary.get("input_mode")) or "unknown"
    source_id = (
        f"{metadata['calculation_id']}:{period}:mwr:{return_measure}:{_reason_token(method)}"
    )
    reason_codes = [
        "PERFORMANCE_SOURCE_READY",
        f"PERFORMANCE_PERIOD_{period}",
        "PERFORMANCE_MEASURE_FAMILY_MWR",
        f"PERFORMANCE_MEASURE_{return_measure.upper()}",
        f"PERFORMANCE_MWR_METHOD_{_reason_token(method)}",
        f"PERFORMANCE_MWR_INPUT_MODE_{_reason_token(input_mode)}",
    ]
    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="WORKSPACE_SUMMARY_MWR_RETURN",
        source_id=source_id,
        value=base_return,
        unit="ratio",
        source_state="READY",
        quality="COMPLETE",
        observed_at=None,
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["calculation_hash"],
        reason_codes=reason_codes,
    )


def realized_contribution_source_from_contribution_response(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    measure: ContributionOutcomeMeasure = "total_contribution",
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-performance contribution output without local contribution math."""

    period_result = _contribution_period(response, period=period)
    metadata = _performance_metadata(response)
    supportability_state, supportability_reason = _performance_supportability(response)
    value = _contribution_value(period_result=period_result, measure=measure)
    source_state, quality = _performance_source_posture(
        supportability_state=supportability_state,
        value=value,
    )
    if source_state == "READY" and value is None:
        raise PerformanceOutcomeSourceError(
            f"lotus-performance contribution response is missing a numeric {measure} for {period}"
        )

    input_mode = _read_text(response.get("input_mode")) or "unknown"
    source_id = f"{metadata['calculation_id']}:{period}:contribution:{measure}"
    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="PERFORMANCE_CONTRIBUTION",
        source_id=source_id,
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at=None,
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["calculation_hash"],
        reason_codes=[
            _performance_primary_reason(source_state),
            f"PERFORMANCE_SUPPORTABILITY_{_reason_token(supportability_state)}",
            f"PERFORMANCE_REASON_{_reason_token(supportability_reason)}",
            f"PERFORMANCE_PERIOD_{period}",
            "PERFORMANCE_MEASURE_FAMILY_CONTRIBUTION",
            f"PERFORMANCE_MEASURE_{measure.upper()}",
            f"PERFORMANCE_INPUT_MODE_{_reason_token(input_mode)}",
        ],
    )


def unavailable_performance_source(
    *,
    source_id: str,
    reason_code: str,
    as_of_date: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Return bounded unavailable performance evidence when lotus-performance cannot serve truth."""

    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="WORKSPACE_SUMMARY_TWR_RETURN",
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


def _read_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _workspace_period(response: dict[str, Any], *, period: str) -> dict[str, Any]:
    return _read_mapping(_read_mapping(response.get("results_by_period")).get(period))


def _contribution_period(response: dict[str, Any], *, period: str) -> dict[str, Any]:
    return _read_mapping(_read_mapping(response.get("results_by_period")).get(period))


def _workspace_metadata(response: dict[str, Any]) -> dict[str, str | None]:
    return _performance_metadata(response)


def _performance_metadata(response: dict[str, Any]) -> dict[str, str | None]:
    meta = _read_mapping(response.get("meta"))
    diagnostics = _read_mapping(response.get("diagnostics"))
    periods = _read_mapping(meta.get("periods"))
    calculation_id = _read_text(response.get("calculation_id")) or _read_text(
        meta.get("calculation_id")
    )
    if calculation_id is None:
        raise PerformanceOutcomeSourceError(
            "lotus-performance workspace summary is missing calculation_id"
        )
    return {
        "calculation_id": calculation_id,
        "calculation_hash": _read_text(meta.get("calculation_hash")),
        "as_of_date": _read_text(periods.get("master_end"))
        or _read_text(diagnostics.get("effective_period_start")),
    }


def _performance_supportability(response: dict[str, Any]) -> tuple[str, str]:
    supportability = _read_mapping(response.get("calculation_supportability"))
    return (
        _read_text(supportability.get("state")) or "ready",
        _read_text(supportability.get("reason")) or "calculation_complete",
    )


def _contribution_value(
    *,
    period_result: dict[str, Any],
    measure: ContributionOutcomeMeasure,
) -> Decimal | None:
    summary = _read_mapping(period_result.get("summary"))
    value_by_measure = {
        "total_contribution": period_result.get("total_contribution"),
        "total_portfolio_return": period_result.get("total_portfolio_return"),
        "summary_portfolio_contribution": summary.get("portfolio_contribution"),
        "summary_local_contribution": summary.get("local_contribution"),
        "summary_fx_contribution": summary.get("fx_contribution"),
    }[measure]
    if value_by_measure is None:
        return None
    return _decimal_from_percentage_points(
        value_by_measure,
        context=f"contribution {measure}",
    )


def _performance_source_posture(
    *,
    supportability_state: str,
    value: Decimal | None,
) -> tuple[
    Literal["READY", "DEGRADED", "BLOCKED", "NOT_SUPPORTED"],
    Literal["COMPLETE", "STALE", "UNAVAILABLE", "PARTIAL", "MISSING", "NOT_SUPPORTED"],
]:
    if supportability_state == "unsupported":
        return "NOT_SUPPORTED", "NOT_SUPPORTED"
    if supportability_state in {"error", "empty"}:
        return "BLOCKED", "MISSING"
    if supportability_state == "stale":
        return "DEGRADED", "STALE"
    if supportability_state != "ready":
        return "DEGRADED", "PARTIAL" if value is not None else "UNAVAILABLE"
    return "READY", "COMPLETE"


def _performance_primary_reason(source_state: str) -> str:
    if source_state == "READY":
        return "PERFORMANCE_SOURCE_READY"
    if source_state == "NOT_SUPPORTED":
        return "PERFORMANCE_SOURCE_NOT_SUPPORTED"
    if source_state == "BLOCKED":
        return "PERFORMANCE_SOURCE_BLOCKED"
    return "PERFORMANCE_SOURCE_DEGRADED"


def _decimal_from_percentage_points(value: Any, *, context: str) -> Decimal:
    try:
        return Decimal(str(value)) / Decimal("100")
    except (InvalidOperation, TypeError) as exc:
        raise PerformanceOutcomeSourceError(
            f"lotus-performance workspace summary is missing a numeric {context}"
        ) from exc


def _reason_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_") or "UNKNOWN"
