from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def canonical_pm_quality_business_date(value: Any, *, field_name: str) -> str:
    error_code = f"INVALID_PM_QUALITY_BUSINESS_DATE:{field_name}"
    if isinstance(value, datetime):
        raise ValueError(error_code)
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError(error_code)
    candidate = value.strip()
    if not _ISO_DATE_PATTERN.fullmatch(candidate):
        raise ValueError(error_code)
    try:
        return date.fromisoformat(candidate).isoformat()
    except ValueError as exc:
        raise ValueError(error_code) from exc


def canonical_optional_pm_quality_business_date(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    return canonical_pm_quality_business_date(value, field_name=field_name)


def canonical_pm_quality_utc_timestamp(value: Any, *, field_name: str) -> str:
    instant = canonical_pm_quality_utc_datetime(value, field_name=field_name)
    timespec = "microseconds" if instant.microsecond else "seconds"
    return instant.isoformat(timespec=timespec).replace("+00:00", "Z")


def canonical_pm_quality_utc_datetime(value: Any, *, field_name: str) -> datetime:
    error_code = f"INVALID_PM_QUALITY_UTC_TIMESTAMP:{field_name}"
    if isinstance(value, datetime):
        instant = value
    elif isinstance(value, str):
        candidate = value.strip()
        if _ISO_DATE_PATTERN.fullmatch(candidate):
            raise ValueError(error_code)
        parse_candidate = f"{candidate[:-1]}+00:00" if candidate.endswith("Z") else candidate
        try:
            instant = datetime.fromisoformat(parse_candidate)
        except ValueError as exc:
            raise ValueError(error_code) from exc
    else:
        raise ValueError(error_code)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError(error_code)
    return instant.astimezone(timezone.utc)
