from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.routers import wave_campaign_workflow_telemetry as workflow_telemetry


def test_campaign_workflow_telemetry_records_bounded_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, str, str]] = []

    def record_campaign_workflow(*, surface: str, outcome: str, reason: str) -> None:
        events.append((surface, outcome, reason))

    monkeypatch.setattr(
        workflow_telemetry,
        "record_campaign_workflow",
        record_campaign_workflow,
    )

    workflow_telemetry.record_campaign_workflow_success(surface="task_open")
    workflow_telemetry.record_campaign_workflow_success(surface="task_open", replay=True)
    workflow_telemetry.record_campaign_workflow_readiness(
        surface="launch",
        blocked=False,
    )
    workflow_telemetry.record_campaign_workflow_readiness(
        surface="launch",
        blocked=True,
    )
    workflow_telemetry.record_campaign_workflow_unexpected_error(surface="launch")
    workflow_telemetry.record_campaign_workflow_validation_failure(
        surface="launch",
        reason="wave_validation_error",
    )

    assert events == [
        ("task_open", "success", "success"),
        ("task_open", "replay", "replay"),
        ("launch", "success", "success"),
        ("launch", "blocked", "launch_blocked"),
        ("launch", "error", "unexpected_error"),
        ("launch", "validation_failed", "wave_validation_error"),
    ]


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            HTTPException(
                status_code=404,
                detail={"code": "BULK_REVIEW_CAMPAIGN_DEFINITION_NOT_FOUND"},
            ),
            ("not_found", "definition_not_found"),
        ),
        (
            HTTPException(
                status_code=404,
                detail={"code": "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND"},
            ),
            ("not_found", "task_not_found"),
        ),
        (
            HTTPException(
                status_code=422,
                detail={"code": "BULK_REVIEW_CAMPAIGN_ACTOR_REQUIRED_FOR_ENTITLEMENT"},
            ),
            ("entitlement_failed", "entitlement_required"),
        ),
        (
            HTTPException(
                status_code=403,
                detail={"code": "BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED"},
            ),
            ("entitlement_failed", "entitlement_denied"),
        ),
        (
            HTTPException(
                status_code=422,
                detail={"code": "BULK_REVIEW_CAMPAIGN_DEFINITION_LAUNCH_BLOCKED"},
            ),
            ("blocked", "launch_blocked"),
        ),
        (
            HTTPException(
                status_code=409,
                detail=[{"code": "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT"}],
            ),
            ("conflict", "reference_conflict"),
        ),
        (HTTPException(status_code=404, detail="missing"), ("not_found", "definition_not_found")),
        (HTTPException(status_code=409, detail="conflict"), ("conflict", "definition_conflict")),
        (
            HTTPException(status_code=422, detail="invalid"),
            ("validation_failed", "validation_error"),
        ),
        (
            HTTPException(status_code=500, detail=[1, {"message": "boom"}]),
            ("error", "unexpected_error"),
        ),
        (
            HTTPException(status_code=500, detail=[{"message": "boom"}]),
            ("error", "unexpected_error"),
        ),
    ],
)
def test_campaign_workflow_http_exception_records_classified_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    exc: HTTPException,
    expected: tuple[str, str],
) -> None:
    events: list[tuple[str, str, str]] = []

    def record_campaign_workflow(*, surface: str, outcome: str, reason: str) -> None:
        events.append((surface, outcome, reason))

    monkeypatch.setattr(
        workflow_telemetry,
        "record_campaign_workflow",
        record_campaign_workflow,
    )

    returned = workflow_telemetry.campaign_workflow_http_exception(
        surface="task_open",
        exc=exc,
    )

    assert returned is exc
    assert events == [("task_open", expected[0], expected[1])]
