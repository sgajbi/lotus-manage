from __future__ import annotations

from typing import Annotated

from fastapi import Query

from src.api.routers.pm_operating_quality_http import pm_quality_validation_http_exception
from src.core.pm_quality.temporal import canonical_optional_pm_quality_business_date


def canonical_pm_quality_as_of_filter(as_of_date: object) -> str | None:
    try:
        return canonical_optional_pm_quality_business_date(
            as_of_date,
            field_name="as_of_date",
        )
    except ValueError as exc:
        raise pm_quality_validation_http_exception("INVALID_AS_OF_DATE") from exc


def pm_quality_as_of_date_filter(
    as_of_date: Annotated[
        str | None,
        Query(description="Filter by business as-of date in YYYY-MM-DD format."),
    ] = None,
) -> str | None:
    return canonical_pm_quality_as_of_filter(as_of_date)
