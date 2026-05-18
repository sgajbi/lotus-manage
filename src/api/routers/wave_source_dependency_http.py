from __future__ import annotations

from fastapi import HTTPException, status


def upstream_unavailable_http_exception(
    exc: Exception,
    *,
    default_code: str,
) -> HTTPException:
    return source_unavailable_http_exception(code=str(exc) or default_code)


def upstream_dependency_failed_http_exception(
    exc: Exception,
    *,
    default_code: str,
) -> HTTPException:
    return source_dependency_failed_http_exception(code=str(exc) or default_code)


def source_authority_unavailable_http_exception(
    exc: Exception,
    *,
    default_code: str,
    rejected_code: str,
) -> HTTPException:
    error_code = str(exc) or default_code
    if error_code == rejected_code:
        return source_dependency_failed_http_exception(code=error_code)
    return source_unavailable_http_exception(code=error_code)


def source_unavailable_http_exception(
    *,
    code: str,
    message: str | None = None,
) -> HTTPException:
    return _source_dependency_http_exception(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code=code,
        message=message,
    )


def source_dependency_failed_http_exception(
    *,
    code: str,
    message: str | None = None,
    reason_codes: list[str] | None = None,
) -> HTTPException:
    return _source_dependency_http_exception(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        code=code,
        message=message,
        reason_codes=reason_codes,
    )


def _source_dependency_http_exception(
    *,
    status_code: int,
    code: str,
    message: str | None = None,
    reason_codes: list[str] | None = None,
) -> HTTPException:
    detail: dict[str, object] = {"code": code}
    if message is not None:
        detail["message"] = message
    if reason_codes is not None:
        detail["reason_codes"] = reason_codes
    return HTTPException(status_code=status_code, detail=detail)
