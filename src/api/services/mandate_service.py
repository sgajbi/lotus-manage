from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.core.mandate_repository import DpmMandateRepository
from src.core.mandates import (
    DpmMandateDigitalTwin,
    DpmMandateHealthSnapshot,
    DpmMonitoringException,
    build_health_input_from_core_sources,
    calculate_mandate_health,
    compile_mandate_digital_twin_from_core,
    monitoring_exceptions_from_health,
)
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverError,
    DpmCoreResolverUnavailableError,
)


class DpmMandateNotFoundError(LookupError):
    pass


class DpmMandateDiffUnavailableError(LookupError):
    pass


class DpmMandateSourceUnavailableError(RuntimeError):
    pass


class DpmMandateSourceIncompleteError(RuntimeError):
    pass


class DpmMandateFieldChange(BaseModel):
    field_path: str = Field(
        description="Dot-separated mandate digital-twin field path that changed.",
        examples=["constraints.turnover_budget"],
    )
    previous_value: Any = Field(
        description="Value from the older mandate version.",
        examples=["0.1000000000"],
    )
    current_value: Any = Field(
        description="Value from the newer mandate version.",
        examples=["0.1500000000"],
    )
    materiality: str = Field(
        description="Business materiality of the field change for DPM oversight.",
        examples=["HIGH"],
    )


class DpmMandateDiff(BaseModel):
    mandate_id: str = Field(
        description="Discretionary mandate identifier whose versions were compared.",
        examples=["MANDATE_PB_SG_GLOBAL_BAL_001"],
    )
    compared_at: datetime = Field(
        description="UTC timestamp when lotus-manage generated the diff.",
        examples=["2026-05-03T08:30:00Z"],
    )
    from_version: str = Field(
        description="Older mandate version used as the comparison baseline.",
        examples=["2"],
    )
    to_version: str = Field(
        description="Newer mandate version used as the comparison target.",
        examples=["3"],
    )
    changed_fields: list[DpmMandateFieldChange] = Field(
        description="Changed mandate fields, ordered by field path for deterministic review.",
    )


@dataclass(frozen=True)
class DpmMandateRefreshResult:
    twin: DpmMandateDigitalTwin
    health_snapshot: DpmMandateHealthSnapshot
    monitoring_exceptions: list[DpmMonitoringException]


def refresh_mandate_from_core(
    *,
    repository: DpmMandateRepository,
    core_resolver: DpmCoreResolverClient,
    portfolio_id: str,
    mandate_id: str,
    as_of_date: date,
    tenant_id: Optional[str],
    booking_center_code: Optional[str],
    model_portfolio_id: Optional[str],
    reference_currency: Optional[str],
    include_market_data_coverage: bool,
    correlation_id: Optional[str],
) -> DpmMandateRefreshResult:
    try:
        mandate = core_resolver.resolve_mandate_binding(
            portfolio_id=portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
            mandate_id=mandate_id,
            booking_center_code=booking_center_code,
            include_policy_pack=True,
            correlation_id=correlation_id,
        )
        resolved_model_portfolio_id = model_portfolio_id or mandate.model_portfolio_id
        model_targets = core_resolver.resolve_model_portfolio_targets(
            model_portfolio_id=resolved_model_portfolio_id,
            as_of_date=as_of_date,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        )
        market_data_coverage = None
        if include_market_data_coverage:
            market_data_coverage = core_resolver.resolve_market_data_coverage(
                instrument_ids=[target.instrument_id for target in model_targets.targets],
                currency_pairs=[],
                as_of_date=as_of_date,
                valuation_currency=model_targets.base_currency,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
            )
    except DpmCoreResolverUnavailableError as exc:
        raise DpmMandateSourceUnavailableError("DPM_MANDATE_SOURCE_UNAVAILABLE") from exc
    except DpmCoreResolverError as exc:
        raise DpmMandateSourceIncompleteError("DPM_MANDATE_SOURCE_INCOMPLETE") from exc

    twin = compile_mandate_digital_twin_from_core(
        mandate=mandate,
        model_targets=model_targets,
        as_of_date=as_of_date,
        reference_currency=reference_currency,
    )
    health_input = build_health_input_from_core_sources(
        twin=twin,
        model_targets=model_targets,
        market_data_coverage=market_data_coverage,
    )
    health_snapshot = calculate_mandate_health(health_input)
    monitoring_exceptions = monitoring_exceptions_from_health(
        health_snapshot,
        source_lineage=twin.source_lineage,
    )

    repository.save_mandate_snapshot(twin)
    repository.save_health_snapshot(health_snapshot)
    for exception in monitoring_exceptions:
        repository.save_monitoring_exception(exception)

    return DpmMandateRefreshResult(
        twin=twin,
        health_snapshot=health_snapshot,
        monitoring_exceptions=monitoring_exceptions,
    )


def get_latest_mandate_by_portfolio(
    *,
    repository: DpmMandateRepository,
    portfolio_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id)
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def get_latest_mandate(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
) -> DpmMandateDigitalTwin:
    twin = repository.get_latest_mandate(mandate_id=mandate_id)
    if twin is None:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return twin


def list_mandate_versions(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
) -> list[DpmMandateDigitalTwin]:
    versions = repository.list_mandate_versions(mandate_id=mandate_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")
    return versions


def diff_mandate_versions(
    *,
    repository: DpmMandateRepository,
    mandate_id: str,
    from_version: Optional[str],
    to_version: Optional[str],
) -> DpmMandateDiff:
    versions = repository.list_mandate_versions(mandate_id=mandate_id)
    if not versions:
        raise DpmMandateNotFoundError("DPM_MANDATE_NOT_FOUND")

    by_version = {version.mandate_version: version for version in versions}
    if from_version is not None or to_version is not None:
        if from_version is None or to_version is None:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
        if from_version not in by_version or to_version not in by_version:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_VERSION_NOT_FOUND")
        previous = by_version[from_version]
        current = by_version[to_version]
    else:
        if len(versions) < 2:
            raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
        current, previous = versions[0], versions[1]

    return DpmMandateDiff(
        mandate_id=mandate_id,
        compared_at=datetime.now(timezone.utc),
        from_version=previous.mandate_version,
        to_version=current.mandate_version,
        changed_fields=_diff_payloads(
            previous.model_dump(mode="json"),
            current.model_dump(mode="json"),
        ),
    )


def _diff_payloads(
    previous: dict[str, Any], current: dict[str, Any]
) -> list[DpmMandateFieldChange]:
    changes: list[DpmMandateFieldChange] = []
    for field_path, previous_value, current_value in _iter_changed_fields(previous, current):
        changes.append(
            DpmMandateFieldChange(
                field_path=field_path,
                previous_value=previous_value,
                current_value=current_value,
                materiality=_materiality_for_field(field_path),
            )
        )
    return sorted(changes, key=lambda change: change.field_path)


def _iter_changed_fields(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    prefix: str = "",
) -> list[tuple[str, Any, Any]]:
    ignored = {"source_lineage"}
    changes: list[tuple[str, Any, Any]] = []
    keys = sorted((set(previous) | set(current)) - ignored)
    for key in keys:
        field_path = f"{prefix}.{key}" if prefix else key
        previous_value = previous.get(key)
        current_value = current.get(key)
        if isinstance(previous_value, dict) and isinstance(current_value, dict):
            changes.extend(_iter_changed_fields(previous_value, current_value, prefix=field_path))
            continue
        if previous_value != current_value:
            changes.append((field_path, previous_value, current_value))
    return changes


def _materiality_for_field(field_path: str) -> str:
    high_prefixes = (
        "constraints.",
        "risk_profile",
        "investment_objective",
        "model_portfolio_id",
        "model_portfolio_version",
        "time_horizon",
    )
    if field_path.startswith(high_prefixes):
        return "HIGH"
    if field_path in {"mandate_version", "as_of_date", "field_gap_codes"}:
        return "MEDIUM"
    return "LOW"
