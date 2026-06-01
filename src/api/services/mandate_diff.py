from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.api.services.mandate_errors import DpmMandateDiffUnavailableError
from src.core.mandates import DpmMandateDigitalTwin


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


def diff_payloads(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> list[DpmMandateFieldChange]:
    changes: list[DpmMandateFieldChange] = []
    for field_path, previous_value, current_value in iter_changed_fields(previous, current):
        changes.append(
            DpmMandateFieldChange(
                field_path=field_path,
                previous_value=previous_value,
                current_value=current_value,
                materiality=materiality_for_field(field_path),
            )
        )
    return sorted(changes, key=lambda change: change.field_path)


def build_mandate_diff(
    *,
    mandate_id: str,
    previous: DpmMandateDigitalTwin,
    current: DpmMandateDigitalTwin,
) -> DpmMandateDiff:
    return DpmMandateDiff(
        mandate_id=mandate_id,
        compared_at=datetime.now(timezone.utc),
        from_version=previous.mandate_version,
        to_version=current.mandate_version,
        changed_fields=diff_payloads(
            previous.model_dump(mode="json"),
            current.model_dump(mode="json"),
        ),
    )


def build_mandate_diff_for_versions(
    *,
    mandate_id: str,
    versions: list[DpmMandateDigitalTwin],
    from_version: str | None,
    to_version: str | None,
) -> DpmMandateDiff:
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

    return build_mandate_diff(
        mandate_id=mandate_id,
        previous=previous,
        current=current,
    )


def iter_changed_fields(
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
            changes.extend(iter_changed_fields(previous_value, current_value, prefix=field_path))
            continue
        if previous_value != current_value:
            changes.append((field_path, previous_value, current_value))
    return changes


def materiality_for_field(field_path: str) -> str:
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


__all__ = [
    "DpmMandateDiff",
    "DpmMandateFieldChange",
    "build_mandate_diff",
    "build_mandate_diff_for_versions",
    "diff_payloads",
    "iter_changed_fields",
    "materiality_for_field",
]
