from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from src.api.routers import wave_campaign_assignment_action_http as assignment_action_http
from src.api.routers import wave_campaign_assignment_task_http as assignment_task_http
from src.api.routers import wave_campaign_maker_checker_http as maker_checker_http
from src.api.routers import wave_campaign_workflow_telemetry as workflow_telemetry
from src.core.waves import DpmBulkReviewCampaignDefinitionConflictError


def _request() -> SimpleNamespace:
    return SimpleNamespace(
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="pm_001",
        task_reason="Campaign requires PM acknowledgement.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        due_at=None,
        correlation_id="corr-campaign-task",
        source_refs=[],
        transition_type="ACKNOWLEDGED",
        transition_ref="BRC-TASK-2026-05-001:ack",
        transitioned_by="pm_001",
        transition_reason="Acknowledged.",
    )


def _assignment_action_request() -> SimpleNamespace:
    return SimpleNamespace(
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="pm_001",
        action_reason="Route ready campaign to assigned PM.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action",
        source_refs=[],
    )


def _maker_checker_request() -> SimpleNamespace:
    return SimpleNamespace(
        control_action="SUBMITTED_FOR_REVIEW",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="pm_001",
        submitter_actor_id="pm_001",
        reviewer_actor_id=None,
        required_reviewer_role="PM_SUPERVISOR",
        control_outcome="PENDING",
        control_reason="Submit for review.",
        correlation_id="corr-campaign-maker-checker",
        source_refs=[],
    )


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
        (HTTPException(status_code=422, detail="invalid"), ("validation_failed", "validation_error")),
        (HTTPException(status_code=500, detail=[1, {"message": "boom"}]), ("error", "unexpected_error")),
        (HTTPException(status_code=500, detail=[{"message": "boom"}]), ("error", "unexpected_error")),
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


def test_assignment_task_open_records_conflict_and_value_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        assignment_task_http,
        "get_campaign_definition_or_404",
        lambda **_: SimpleNamespace(content_hash="hash"),
    )
    monkeypatch.setattr(
        workflow_telemetry,
        "record_campaign_workflow",
        lambda **_: None,
    )

    def raise_conflict(**_: object) -> None:
        raise DpmBulkReviewCampaignDefinitionConflictError(
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_REF_CONFLICT"
        )

    monkeypatch.setattr(
        assignment_task_http,
        "open_bulk_review_campaign_definition_assignment_task",
        raise_conflict,
    )
    with pytest.raises(HTTPException) as conflict:
        assignment_task_http.open_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert conflict.value.status_code == 409

    def raise_value(**_: object) -> None:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND")

    monkeypatch.setattr(
        assignment_task_http,
        "open_bulk_review_campaign_definition_assignment_task",
        raise_value,
    )
    with pytest.raises(HTTPException) as not_found:
        assignment_task_http.open_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert not_found.value.status_code == 404


def test_assignment_task_transition_records_conflict_and_value_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow_telemetry, "record_campaign_workflow", lambda **_: None)
    monkeypatch.setattr(
        assignment_task_http,
        "get_campaign_definition_or_404",
        lambda **_: SimpleNamespace(content_hash="hash"),
    )

    def raise_conflict(**_: object) -> None:
        raise DpmBulkReviewCampaignDefinitionConflictError(
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_TRANSITION_REF_CONFLICT"
        )

    monkeypatch.setattr(
        assignment_task_http,
        "transition_bulk_review_campaign_definition_assignment_task",
        raise_conflict,
    )
    with pytest.raises(HTTPException) as conflict:
        assignment_task_http.transition_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            task_ref="BRC-TASK-2026-05-001",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert conflict.value.status_code == 409

    def raise_value(**_: object) -> None:
        raise ValueError("BULK_REVIEW_CAMPAIGN_ASSIGNMENT_TASK_NOT_FOUND")

    monkeypatch.setattr(
        assignment_task_http,
        "transition_bulk_review_campaign_definition_assignment_task",
        raise_value,
    )
    with pytest.raises(HTTPException) as not_found:
        assignment_task_http.transition_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            task_ref="BRC-TASK-2026-05-001",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert not_found.value.status_code == 404


def test_assignment_task_open_and_transition_record_http_and_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unexpected_surfaces: list[str] = []
    monkeypatch.setattr(workflow_telemetry, "record_campaign_workflow", lambda **_: None)
    monkeypatch.setattr(
        assignment_task_http,
        "record_campaign_workflow_unexpected_error",
        lambda *, surface: unexpected_surfaces.append(surface),
    )

    monkeypatch.setattr(
        assignment_task_http,
        "get_campaign_definition_or_404",
        lambda **_: (_ for _ in ()).throw(HTTPException(status_code=404)),
    )
    with pytest.raises(HTTPException) as open_not_found:
        assignment_task_http.open_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert open_not_found.value.status_code == 404

    monkeypatch.setattr(
        assignment_task_http,
        "get_campaign_definition_or_404",
        lambda **_: SimpleNamespace(content_hash="hash"),
    )
    monkeypatch.setattr(
        assignment_task_http,
        "open_bulk_review_campaign_definition_assignment_task",
        lambda **_: (_ for _ in ()).throw(RuntimeError("storage unavailable")),
    )
    with pytest.raises(RuntimeError, match="storage unavailable"):
        assignment_task_http.open_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            request=_request(),
            repository=SimpleNamespace(),
        )

    monkeypatch.setattr(
        assignment_task_http,
        "transition_bulk_review_campaign_definition_assignment_task",
        lambda **_: (_ for _ in ()).throw(HTTPException(status_code=409)),
    )
    with pytest.raises(HTTPException) as transition_conflict:
        assignment_task_http.transition_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            task_ref="BRC-TASK-2026-05-001",
            request=_request(),
            repository=SimpleNamespace(),
        )
    assert transition_conflict.value.status_code == 409

    monkeypatch.setattr(
        assignment_task_http,
        "transition_bulk_review_campaign_definition_assignment_task",
        lambda **_: (_ for _ in ()).throw(RuntimeError("transition failed")),
    )
    with pytest.raises(RuntimeError, match="transition failed"):
        assignment_task_http.transition_campaign_definition_assignment_task_response(
            campaign_id="campaign",
            campaign_version="v1",
            task_ref="BRC-TASK-2026-05-001",
            request=_request(),
            repository=SimpleNamespace(),
        )

    assert unexpected_surfaces == ["assignment_task_open", "assignment_task_transition"]


@pytest.mark.parametrize(
    ("module", "mutation_name", "response_name", "request_factory", "surface"),
    [
        (
            assignment_action_http,
            "record_bulk_review_campaign_definition_assignment_action",
            "record_campaign_definition_assignment_action_response",
            _assignment_action_request,
            "assignment_action",
        ),
        (
            maker_checker_http,
            "record_bulk_review_campaign_definition_maker_checker_control",
            "record_campaign_definition_maker_checker_control_response",
            _maker_checker_request,
            "maker_checker_control",
        ),
    ],
)
def test_campaign_workflow_peer_http_adapters_record_error_paths(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    mutation_name: str,
    response_name: str,
    request_factory: object,
    surface: str,
) -> None:
    unexpected_surfaces: list[str] = []
    monkeypatch.setattr(workflow_telemetry, "record_campaign_workflow", lambda **_: None)
    monkeypatch.setattr(
        module,
        "record_campaign_workflow_unexpected_error",
        lambda *, surface: unexpected_surfaces.append(surface),
    )
    monkeypatch.setattr(
        module,
        "get_campaign_definition_or_404",
        lambda **_: SimpleNamespace(content_hash="hash"),
    )

    def raise_conflict(**_: object) -> None:
        raise DpmBulkReviewCampaignDefinitionConflictError(
            "BULK_REVIEW_CAMPAIGN_ASSIGNMENT_ACTION_REF_CONFLICT"
        )

    monkeypatch.setattr(module, mutation_name, raise_conflict)
    response = getattr(module, response_name)
    with pytest.raises(HTTPException) as conflict:
        response(
            campaign_id="campaign",
            campaign_version="v1",
            request=request_factory(),
            repository=SimpleNamespace(),
        )
    assert conflict.value.status_code == 409

    monkeypatch.setattr(
        module,
        mutation_name,
        lambda **_: (_ for _ in ()).throw(ValueError("BULK_REVIEW_CAMPAIGN_ACTOR_NOT_ENTITLED")),
    )
    with pytest.raises(HTTPException) as value_error:
        response(
            campaign_id="campaign",
            campaign_version="v1",
            request=request_factory(),
            repository=SimpleNamespace(),
        )
    assert value_error.value.status_code == 422

    monkeypatch.setattr(
        module,
        mutation_name,
        lambda **_: (_ for _ in ()).throw(HTTPException(status_code=404)),
    )
    with pytest.raises(HTTPException) as http_error:
        response(
            campaign_id="campaign",
            campaign_version="v1",
            request=request_factory(),
            repository=SimpleNamespace(),
        )
    assert http_error.value.status_code == 404

    monkeypatch.setattr(
        module,
        mutation_name,
        lambda **_: (_ for _ in ()).throw(RuntimeError("store failed")),
    )
    with pytest.raises(RuntimeError, match="store failed"):
        response(
            campaign_id="campaign",
            campaign_version="v1",
            request=request_factory(),
            repository=SimpleNamespace(),
        )

    assert unexpected_surfaces == [surface]
