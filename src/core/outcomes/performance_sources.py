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
AttributionOutcomeMeasure = Literal[
    "reconciliation_total_active_return",
    "reconciliation_sum_of_effects",
    "reconciliation_residual",
    "level_allocation_total",
    "level_selection_total",
    "level_interaction_total",
    "level_total_effect",
    "currency_local_allocation",
    "currency_local_selection",
    "currency_allocation",
    "currency_selection",
    "currency_total_effect",
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


def realized_attribution_source_from_attribution_response(
    response: dict[str, Any],
    *,
    period: str = "YTD",
    measure: AttributionOutcomeMeasure = "reconciliation_total_active_return",
    level_dimension: str | None = None,
    currency: str | None = None,
) -> DpmRealizedSourceSnapshot:
    """Adapt lotus-performance attribution output without local attribution math."""

    period_result = _attribution_period(response, period=period)
    metadata = _performance_metadata(response)
    supportability_state, supportability_reason = _performance_supportability(response)
    value, selector_reason, selector_token = _attribution_value(
        period_result=period_result,
        measure=measure,
        level_dimension=level_dimension,
        currency=currency,
    )
    source_state, quality = _performance_source_posture(
        supportability_state=supportability_state,
        value=value,
    )
    if source_state == "READY" and value is None:
        raise PerformanceOutcomeSourceError(
            f"lotus-performance attribution response is missing a numeric attribution {measure} for {period}"
        )

    input_mode = _read_text(response.get("input_mode")) or "unknown"
    model = _read_text(response.get("model")) or "unknown"
    linking = _read_text(response.get("linking")) or "unknown"
    benchmark = _read_mapping(response.get("benchmark_context"))
    benchmark_id = _read_text(benchmark.get("benchmark_id"))
    benchmark_source = _read_text(benchmark.get("return_source"))
    source_id = f"{metadata['calculation_id']}:{period}:attribution:{measure}:{selector_token}"
    reason_codes = [
        _performance_primary_reason(source_state),
        f"PERFORMANCE_SUPPORTABILITY_{_reason_token(supportability_state)}",
        f"PERFORMANCE_REASON_{_reason_token(supportability_reason)}",
        f"PERFORMANCE_PERIOD_{period}",
        "PERFORMANCE_MEASURE_FAMILY_ATTRIBUTION",
        f"PERFORMANCE_ATTRIBUTION_MEASURE_{measure.upper()}",
        selector_reason,
        f"PERFORMANCE_INPUT_MODE_{_reason_token(input_mode)}",
        f"PERFORMANCE_ATTRIBUTION_MODEL_{_reason_token(model)}",
        f"PERFORMANCE_ATTRIBUTION_LINKING_{_reason_token(linking)}",
    ]
    if benchmark_id is not None:
        reason_codes.append(f"PERFORMANCE_BENCHMARK_{_reason_token(benchmark_id)}")
    if benchmark_source is not None:
        reason_codes.append(
            f"PERFORMANCE_BENCHMARK_RETURN_SOURCE_{_reason_token(benchmark_source)}"
        )

    return DpmRealizedSourceSnapshot(
        dimension="PERFORMANCE",
        source_system="lotus-performance",
        source_type="PERFORMANCE_ATTRIBUTION",
        source_id=source_id,
        value=value if source_state != "NOT_SUPPORTED" else None,
        unit="ratio",
        source_state=source_state,
        quality=quality,
        observed_at=None,
        as_of_date=metadata["as_of_date"],
        content_hash=metadata["calculation_hash"],
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


def _workspace_period(response: dict[str, Any], *, period: str) -> dict[str, Any]:
    return _read_mapping(_read_mapping(response.get("results_by_period")).get(period))


def _contribution_period(response: dict[str, Any], *, period: str) -> dict[str, Any]:
    return _read_mapping(_read_mapping(response.get("results_by_period")).get(period))


def _attribution_period(response: dict[str, Any], *, period: str) -> dict[str, Any]:
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


def _attribution_value(
    *,
    period_result: dict[str, Any],
    measure: AttributionOutcomeMeasure,
    level_dimension: str | None,
    currency: str | None,
) -> tuple[Decimal | None, str, str]:
    if measure.startswith("reconciliation_"):
        reconciliation = _read_mapping(period_result.get("reconciliation"))
        source_field = {
            "reconciliation_total_active_return": "total_active_return",
            "reconciliation_sum_of_effects": "sum_of_effects",
            "reconciliation_residual": "residual",
        }[measure]
        value = reconciliation.get(source_field)
        return (
            _decimal_from_percentage_points(value, context=f"attribution {measure}")
            if value is not None
            else None,
            "PERFORMANCE_ATTRIBUTION_SELECTOR_RECONCILIATION",
            "reconciliation",
        )

    if measure.startswith("level_"):
        level, dimension = _attribution_level(
            period_result=period_result,
            level_dimension=level_dimension,
        )
        source_field = {
            "level_allocation_total": "allocation_total_pct",
            "level_selection_total": "selection_total_pct",
            "level_interaction_total": "interaction_total_pct",
            "level_total_effect": "total_effect_pct",
        }[measure]
        value = level.get(source_field)
        selector = _reason_token(dimension)
        return (
            _decimal_from_percentage_points(value, context=f"attribution {measure}")
            if value is not None
            else None,
            f"PERFORMANCE_ATTRIBUTION_LEVEL_{selector}",
            f"level:{selector.lower()}",
        )

    currency_result, currency_code = _attribution_currency(
        period_result=period_result,
        currency=currency,
    )
    effects = _read_mapping(currency_result.get("effects"))
    source_field = {
        "currency_local_allocation": "local_allocation",
        "currency_local_selection": "local_selection",
        "currency_allocation": "currency_allocation",
        "currency_selection": "currency_selection",
        "currency_total_effect": "total_effect",
    }[measure]
    value = effects.get(source_field)
    selector = _reason_token(currency_code)
    return (
        _decimal_from_percentage_points(value, context=f"attribution {measure}")
        if value is not None
        else None,
        f"PERFORMANCE_ATTRIBUTION_CURRENCY_{selector}",
        f"currency:{selector.lower()}",
    )


def _attribution_level(
    *,
    period_result: dict[str, Any],
    level_dimension: str | None,
) -> tuple[dict[str, Any], str]:
    levels = period_result.get("levels")
    if not isinstance(levels, list):
        return {}, level_dimension or "unknown"
    for level in levels:
        level_mapping = _read_mapping(level)
        dimension = _read_text(level_mapping.get("dimension"))
        if level_dimension is None or dimension == level_dimension:
            return level_mapping, dimension or level_dimension or "unknown"
    return {}, level_dimension or "unknown"


def _attribution_currency(
    *,
    period_result: dict[str, Any],
    currency: str | None,
) -> tuple[dict[str, Any], str]:
    currency_results = period_result.get("currency_attribution")
    if not isinstance(currency_results, list):
        return {}, currency or "unknown"
    for currency_result in currency_results:
        result_mapping = _read_mapping(currency_result)
        currency_code = _read_text(result_mapping.get("currency"))
        if currency is None or currency_code == currency:
            return result_mapping, currency_code or currency or "unknown"
    return {}, currency or "unknown"


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
