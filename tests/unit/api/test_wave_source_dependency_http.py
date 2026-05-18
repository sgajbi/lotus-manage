from __future__ import annotations

from fastapi import status

from src.api.routers.wave_source_dependency_http import (
    source_authority_unavailable_http_exception,
    source_dependency_failed_http_exception,
    source_unavailable_http_exception,
    upstream_dependency_failed_http_exception,
    upstream_unavailable_http_exception,
)


def test_upstream_unavailable_http_exception_uses_default_code_for_blank_exception() -> None:
    http_exc = upstream_unavailable_http_exception(Exception(), default_code="SOURCE_UNAVAILABLE")

    assert http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert http_exc.detail == {"code": "SOURCE_UNAVAILABLE"}


def test_upstream_dependency_failed_http_exception_preserves_exception_code() -> None:
    http_exc = upstream_dependency_failed_http_exception(
        RuntimeError("SOURCE_INCOMPLETE"),
        default_code="DEFAULT_INCOMPLETE",
    )

    assert http_exc.status_code == status.HTTP_424_FAILED_DEPENDENCY
    assert http_exc.detail == {"code": "SOURCE_INCOMPLETE"}


def test_source_authority_unavailable_http_exception_maps_rejection_to_dependency() -> None:
    http_exc = source_authority_unavailable_http_exception(
        RuntimeError("SOURCE_REJECTED"),
        default_code="SOURCE_UNAVAILABLE",
        rejected_code="SOURCE_REJECTED",
    )

    assert http_exc.status_code == status.HTTP_424_FAILED_DEPENDENCY
    assert http_exc.detail == {"code": "SOURCE_REJECTED"}


def test_source_authority_unavailable_http_exception_maps_other_errors_to_unavailable() -> None:
    http_exc = source_authority_unavailable_http_exception(
        RuntimeError("SOURCE_DOWN"),
        default_code="SOURCE_UNAVAILABLE",
        rejected_code="SOURCE_REJECTED",
    )

    assert http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert http_exc.detail == {"code": "SOURCE_DOWN"}


def test_source_unavailable_http_exception_includes_message_when_supplied() -> None:
    http_exc = source_unavailable_http_exception(
        code="SOURCE_URL_MISSING",
        message="Source base URL is not configured.",
    )

    assert http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert http_exc.detail == {
        "code": "SOURCE_URL_MISSING",
        "message": "Source base URL is not configured.",
    }


def test_source_dependency_failed_http_exception_includes_reason_codes() -> None:
    http_exc = source_dependency_failed_http_exception(
        code="SOURCE_NOT_READY",
        message="Source cohort is not ready.",
        reason_codes=["MISSING_SOURCE_REF"],
    )

    assert http_exc.status_code == status.HTTP_424_FAILED_DEPENDENCY
    assert http_exc.detail == {
        "code": "SOURCE_NOT_READY",
        "message": "Source cohort is not ready.",
        "reason_codes": ["MISSING_SOURCE_REF"],
    }
