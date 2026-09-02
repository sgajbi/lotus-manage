from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.api.observability import correlation_id_var
from src.api.response_headers import apply_observability_headers


IDEA_ACTION_PROBLEM_DETAILS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "type",
        "title",
        "status",
        "detail",
        "reasonCode",
        "correlationId",
        "instance",
    ],
    "properties": {
        "type": {"type": "string", "example": "about:blank"},
        "title": {"type": "string", "example": "Conflict"},
        "status": {"type": "integer", "example": 409},
        "detail": {
            "type": "string",
            "example": "Idea management action request conflicts with durable state.",
        },
        "reasonCode": {
            "type": "string",
            "example": "IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT",
        },
        "correlationId": {"type": "string", "example": "corr-idea-action-001"},
        "instance": {
            "type": "string",
            "example": "/api/v1/rebalance/idea-action-intakes/iai_001/outcomes",
        },
    },
}


@dataclass(frozen=True)
class IdeaActionProblemDetailsException(Exception):
    status_code: int
    reason_code: str
    detail: str
    problem_type: str = "about:blank"

    def __post_init__(self) -> None:
        Exception.__init__(self, self.reason_code)


async def idea_action_problem_details_exception_handler(
    request: Request,
    exc: IdeaActionProblemDetailsException,
) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        content={
            "type": exc.problem_type,
            "title": _problem_title(exc.status_code),
            "status": exc.status_code,
            "detail": exc.detail,
            "reasonCode": exc.reason_code,
            "correlationId": correlation_id_var.get() or "",
            "instance": str(request.url.path),
        },
    )
    apply_observability_headers(response)
    return response


def idea_action_problem(
    *,
    status_code: int,
    reason_code: str,
    detail: str,
) -> IdeaActionProblemDetailsException:
    return IdeaActionProblemDetailsException(
        status_code=status_code,
        reason_code=reason_code.split(":", 1)[0],
        detail=detail,
    )


def idea_action_problem_responses(
    descriptions: dict[int, tuple[str, str]],
) -> dict[int | str, dict[str, Any]]:
    return {
        status_code: {
            "description": description,
            "content": {
                "application/problem+json": {
                    "schema": IDEA_ACTION_PROBLEM_DETAILS_SCHEMA,
                    "example": {
                        "type": "about:blank",
                        "title": _problem_title(status_code),
                        "status": status_code,
                        "detail": description,
                        "reasonCode": reason_code,
                        "correlationId": "corr-idea-action-001",
                        "instance": "/api/v1/rebalance/idea-action-intakes/iai_001/outcomes",
                    },
                }
            },
        }
        for status_code, (description, reason_code) in descriptions.items()
    }


def _problem_title(status_code: int) -> str:
    return {
        status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        status.HTTP_403_FORBIDDEN: "Forbidden",
        status.HTTP_404_NOT_FOUND: "Not Found",
        status.HTTP_409_CONFLICT: "Conflict",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation Error",
        status.HTTP_503_SERVICE_UNAVAILABLE: "Service Unavailable",
    }.get(status_code, "Error")


__all__ = [
    "IDEA_ACTION_PROBLEM_DETAILS_SCHEMA",
    "IdeaActionProblemDetailsException",
    "idea_action_problem",
    "idea_action_problem_details_exception_handler",
    "idea_action_problem_responses",
]
