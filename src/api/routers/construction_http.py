from __future__ import annotations

from fastapi import HTTPException, status

from src.core.construction.repository import (
    ConstructionAlternativeNotFoundError,
    ConstructionAlternativeSetNotFoundError,
    ConstructionIdempotencyConflictError,
)


def construction_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ConstructionIdempotencyConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(
        exc,
        (
            ConstructionAlternativeSetNotFoundError,
            ConstructionAlternativeNotFoundError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=type(exc).__name__,
    )
