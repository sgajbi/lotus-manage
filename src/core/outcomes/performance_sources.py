"""Source-owned performance realized evidence adapters for RFC-0042."""

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from src.core.outcomes.models import DpmRealizedSourceSnapshot

PerformanceReturnMeasure = Literal["period_return", "cumulative_return", "annualized_return"]
PerformanceBasis = Literal["net", "gross"]


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

    period_result = _read_mapping(_read_mapping(response.get("results_by_period")).get(period))
    portfolio_twr = _read_mapping(period_result.get("portfolio_twr"))
    basis_block = _read_mapping(portfolio_twr.get(basis))
    summary = _read_mapping(basis_block.get("summary"))
    return_value = _read_mapping(summary.get(return_measure))
    base_return = _decimal_from_percentage_points(return_value.get("base"))
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

    calculation_hash = _read_text(meta.get("calculation_hash"))
    source_id = f"{calculation_id}:{period}:{basis}:{return_measure}"
    reason_codes = [
        "PERFORMANCE_SOURCE_READY",
        f"PERFORMANCE_PERIOD_{period}",
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
        as_of_date=_read_text(periods.get("master_end"))
        or _read_text(diagnostics.get("effective_period_start")),
        content_hash=calculation_hash,
        reason_codes=reason_codes,
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


def _decimal_from_percentage_points(value: Any) -> Decimal:
    try:
        return Decimal(str(value)) / Decimal("100")
    except (InvalidOperation, TypeError) as exc:
        raise PerformanceOutcomeSourceError(
            "lotus-performance workspace summary is missing a numeric base return"
        ) from exc
