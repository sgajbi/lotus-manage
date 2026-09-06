from datetime import date, datetime, timezone
from typing import Any, cast

from pydantic import BaseModel, Field

from src.api.services.mandate_errors import DpmMandateDiffUnavailableError
from src.core.mandates import DpmMandateDigitalTwin

_IGNORED_DIFF_FIELDS = frozenset({"source_lineage"})


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
    from_as_of_date: date = Field(
        description=(
            "Business date of the observation used as the comparison baseline. A mandate "
            "version can be observed on several dates, so the version alone does not "
            "identify which row was compared."
        ),
        examples=["2026-04-30"],
    )
    to_as_of_date: date = Field(
        description="Business date of the observation used as the comparison target.",
        examples=["2026-05-03"],
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
        from_as_of_date=previous.as_of_date,
        to_as_of_date=current.as_of_date,
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
    previous, current = _mandate_diff_version_pair(
        versions=versions,
        from_version=from_version,
        to_version=to_version,
    )
    return build_mandate_diff(
        mandate_id=mandate_id,
        previous=previous,
        current=current,
    )


def _mandate_diff_version_pair(
    *,
    versions: list[DpmMandateDigitalTwin],
    from_version: str | None,
    to_version: str | None,
) -> tuple[DpmMandateDigitalTwin, DpmMandateDigitalTwin]:
    if from_version is not None or to_version is not None:
        return _requested_mandate_diff_version_pair(
            versions=versions,
            from_version=from_version,
            to_version=to_version,
        )
    return _latest_mandate_diff_version_pair(versions)


def _requested_mandate_diff_version_pair(
    *,
    versions: list[DpmMandateDigitalTwin],
    from_version: str | None,
    to_version: str | None,
) -> tuple[DpmMandateDigitalTwin, DpmMandateDigitalTwin]:
    if from_version is None or to_version is None:
        raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
    by_version = _mandate_version_index(versions)
    try:
        return by_version[from_version], by_version[to_version]
    except KeyError as exc:
        raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_VERSION_NOT_FOUND") from exc


def _latest_mandate_diff_version_pair(
    versions: list[DpmMandateDigitalTwin],
) -> tuple[DpmMandateDigitalTwin, DpmMandateDigitalTwin]:
    """The newest observation, against the newest observation of the previous
    DISTINCT version (issue #647).

    `versions` is ordered newest-first and may contain the same
    mandate_version more than once, because an unchanged binding can be
    re-observed on a later business date. Taking versions[1] blindly can
    compare a version against another observation of itself and report "no
    changes", which is indistinguishable from a mandate that genuinely did
    not change.
    """

    if not versions:
        raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
    current = versions[0]
    previous = next(
        (
            candidate
            for candidate in versions[1:]
            if candidate.mandate_version != current.mandate_version
        ),
        None,
    )
    if previous is None:
        # Every observation is of one version: there is no version change to
        # diff, and saying so is more truthful than an empty change list.
        raise DpmMandateDiffUnavailableError("DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS")
    return previous, current


def _mandate_version_index(
    versions: list[DpmMandateDigitalTwin],
) -> dict[str, DpmMandateDigitalTwin]:
    """Map each mandate version to its LATEST observation (issue #647).

    `versions` is ordered newest-first, so the first occurrence of a version
    is its most recent observation. A dict comprehension would let the last -
    that is, the oldest - entry win.
    """

    index: dict[str, DpmMandateDigitalTwin] = {}
    for version in versions:
        index.setdefault(version.mandate_version, version)
    return index


def iter_changed_fields(
    previous: dict[str, Any],
    current: dict[str, Any],
    *,
    prefix: str = "",
) -> list[tuple[str, Any, Any]]:
    changes: list[tuple[str, Any, Any]] = []
    for key in _diff_candidate_keys(previous=previous, current=current):
        field_path = _diff_field_path(prefix=prefix, key=key)
        previous_value = previous.get(key)
        current_value = current.get(key)
        if _nested_diff_values(previous_value=previous_value, current_value=current_value):
            changes.extend(
                iter_changed_fields(
                    cast(dict[str, Any], previous_value),
                    cast(dict[str, Any], current_value),
                    prefix=field_path,
                )
            )
            continue
        if previous_value != current_value:
            changes.append((field_path, previous_value, current_value))
    return changes


def _diff_candidate_keys(*, previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return sorted((set(previous) | set(current)) - _IGNORED_DIFF_FIELDS)


def _diff_field_path(*, prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _nested_diff_values(*, previous_value: Any, current_value: Any) -> bool:
    return isinstance(previous_value, dict) and isinstance(current_value, dict)


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
