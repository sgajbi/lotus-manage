from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.observability import correlation_id_var
from src.api.response_headers import apply_observability_headers


CAMPAIGN_PROBLEM_DETAILS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "type",
        "title",
        "status",
        "detail",
        "reasonCode",
        "code",
        "correlationId",
        "instance",
    ],
    "properties": {
        "type": {"type": "string", "example": "about:blank"},
        "title": {"type": "string", "example": "Validation Error"},
        "status": {"type": "integer", "example": 422},
        "detail": {
            "type": "string",
            "example": "Campaign workflow request failed semantic validation.",
        },
        "reasonCode": {
            "type": "string",
            "example": "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT",
        },
        "code": {
            "type": "string",
            "example": "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT",
        },
        "correlationId": {"type": "string", "example": "corr_1234abcd"},
        "instance": {
            "type": "string",
            "example": "/api/v1/rebalance/waves/campaign-definitions/example/versions/2026.05",
        },
    },
}


class CampaignProblemDetailsException(HTTPException):
    def __init__(
        self,
        *,
        status_code: int,
        reason_code: str,
        detail: str,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={
                "code": reason_code,
                "message": detail,
                **(extensions or {}),
            },
        )
        self.reason_code = reason_code
        self.problem_detail = detail
        self.title = _problem_title(status_code)
        self.problem_type = "about:blank"
        self.extensions = extensions or {}


async def campaign_problem_details_exception_handler(
    request: Request,
    exc: CampaignProblemDetailsException,
) -> JSONResponse:
    content = {
        "type": exc.problem_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.problem_detail,
        "reasonCode": exc.reason_code,
        "code": exc.reason_code,
        "correlationId": correlation_id_var.get() or "",
        "instance": str(request.url.path),
    }
    content.update(_problem_extensions(exc.extensions))
    response = JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content=content,
    )
    apply_observability_headers(response)
    return response


def campaign_problem_details_exception(
    *,
    status_code: int,
    reason_code: str,
    detail: str,
    extensions: dict[str, Any] | None = None,
) -> CampaignProblemDetailsException:
    return CampaignProblemDetailsException(
        status_code=status_code,
        reason_code=_reason_code(reason_code),
        detail=detail,
        extensions=extensions,
    )


def campaign_problem_responses(descriptions: dict[int, str]) -> dict[int | str, dict[str, Any]]:
    return {
        status_code: _campaign_problem_response(
            status_code=status_code,
            description=description,
            reason_code=_example_reason_code(status_code),
        )
        for status_code, description in descriptions.items()
    }


def _reason_code(code: str) -> str:
    return code.split(":", 1)[0]


def _problem_title(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "Bad Request",
        status.HTTP_403_FORBIDDEN: "Forbidden",
        status.HTTP_404_NOT_FOUND: "Not Found",
        status.HTTP_409_CONFLICT: "Conflict",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation Error",
        status.HTTP_424_FAILED_DEPENDENCY: "Failed Dependency",
        status.HTTP_503_SERVICE_UNAVAILABLE: "Service Unavailable",
    }.get(status_code, "Error")


def _problem_extensions(extensions: dict[str, Any]) -> dict[str, Any]:
    problem_extensions: dict[str, Any] = {}
    if "reason_codes" in extensions:
        problem_extensions["reasonCodes"] = extensions["reason_codes"]
    if "readiness" in extensions:
        problem_extensions["readiness"] = extensions["readiness"]
    return problem_extensions


def _campaign_problem_response(
    *,
    status_code: int,
    description: str,
    reason_code: str,
) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/problem+json": {
                "schema": CAMPAIGN_PROBLEM_DETAILS_SCHEMA,
                "example": {
                    "type": "about:blank",
                    "title": _problem_title(status_code),
                    "status": status_code,
                    "detail": description,
                    "reasonCode": reason_code,
                    "code": reason_code,
                    "correlationId": "corr_1234abcd",
                    "instance": (
                        "/api/v1/rebalance/waves/campaign-definitions/example/versions/2026.05"
                    ),
                },
            }
        },
    }


def _example_reason_code(status_code: int) -> str:
    return {
        status.HTTP_400_BAD_REQUEST: "BULK_REVIEW_CAMPAIGN_TRUSTED_TENANT_REQUIRED",
        status.HTTP_404_NOT_FOUND: "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND",
        status.HTTP_409_CONFLICT: "BULK_REVIEW_CAMPAIGN_DEFINITION_IMMUTABLE_CONFLICT",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "BULK_REVIEW_CAMPAIGN_VALIDATION_FAILED",
    }.get(status_code, "BULK_REVIEW_CAMPAIGN_REQUEST_FAILED")
