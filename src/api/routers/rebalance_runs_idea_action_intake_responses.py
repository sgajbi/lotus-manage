from __future__ import annotations

from typing import Any

from fastapi import status

from src.core.rebalance_runs import IDEA_ACTION_INTAKE_ERROR_EXAMPLE
from src.core.rebalance_runs.idea_action_intake import IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE

IDEA_ACTION_INTAKE_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_202_ACCEPTED: {
        "description": (
            "Source-safe executable action-intake receipt. This is not rebalance execution, "
            "action-register creation, order, OMS, or client-publication proof."
        ),
        "content": {"application/json": {"example": IDEA_ACTION_INTAKE_RESPONSE_EXAMPLE}},
    },
    status.HTTP_401_UNAUTHORIZED: {
        "description": "Trusted Idea action-intake principal is missing or invalid."
    },
    status.HTTP_403_FORBIDDEN: {
        "description": (
            "Trusted Idea action-intake principal lacks the required role or intake capability."
        )
    },
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key was replayed with a different handoff payload.",
        "content": {
            "application/json": {"example": {"detail": "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"}}
        },
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "description": "Invalid payload or unsupported query parameters were supplied.",
        "content": {"application/json": {"example": IDEA_ACTION_INTAKE_ERROR_EXAMPLE}},
    },
}


__all__ = ["IDEA_ACTION_INTAKE_RESPONSES"]
