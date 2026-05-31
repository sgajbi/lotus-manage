from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status

from src.api.services.mandate_service import (
    DpmMandateHealthNotFoundError,
    DpmMandateNotFoundError,
    DpmMonitoringRunNotFoundError,
)

MandateHttpResponse = TypeVar("MandateHttpResponse")
MandateHttpCallback = Callable[[], MandateHttpResponse]

_MANDATE_NOT_FOUND_ERRORS = (
    DpmMandateNotFoundError,
    DpmMandateHealthNotFoundError,
    DpmMonitoringRunNotFoundError,
)


def read_mandate_with_not_found_http_mapping(
    read_mandate: MandateHttpCallback[MandateHttpResponse],
) -> MandateHttpResponse:
    try:
        return read_mandate()
    except _MANDATE_NOT_FOUND_ERRORS as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
