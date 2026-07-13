from __future__ import annotations

from types import SimpleNamespace
from typing import Callable

from fastapi import HTTPException
import pytest

from src.api.routers import wave_campaign_launch_routes
from src.api.routers.wave_campaign_approval_decision_evidence_routes import (
    list_bulk_review_campaign_definition_approval_decisions,
    record_bulk_review_campaign_definition_approval_decision_endpoint,
)
from src.api.routers.wave_campaign_assignment_action_evidence_routes import (
    list_bulk_review_campaign_definition_assignment_actions,
    record_bulk_review_campaign_definition_assignment_action_endpoint,
)
from src.api.routers.wave_campaign_assignment_task_evidence_routes import (
    list_bulk_review_campaign_definition_assignment_tasks,
    open_bulk_review_campaign_definition_assignment_task_endpoint,
    transition_bulk_review_campaign_definition_assignment_task_endpoint,
)
from src.api.routers.wave_campaign_definition_lifecycle_routes import (
    retire_bulk_review_campaign_definition,
    supersede_bulk_review_campaign_definition,
)
from src.api.routers.wave_campaign_launch_routes import launch_bulk_review_campaign_definition
from src.api.routers.wave_campaign_maker_checker_evidence_routes import (
    list_bulk_review_campaign_definition_maker_checker_controls,
    record_bulk_review_campaign_definition_maker_checker_control_endpoint,
)
from src.api.routers.wave_campaign_models import (
    DpmBulkReviewCampaignDefinitionApprovalDecisionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentActionRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest,
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest,
    DpmBulkReviewCampaignDefinitionLaunchRequest,
    DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest,
    DpmBulkReviewCampaignDefinitionRetirementRequest,
    DpmBulkReviewCampaignDefinitionSupersessionRequest,
)
from src.api.routers.wave_campaign_problem_details import CampaignProblemDetailsException
from src.api.routers.wave_campaign_trusted_context import CampaignTrustedContext
from src.api.services import wave_service
from src.api.services.wave_campaign_application import DpmWaveCampaignApplicationNotFoundError
from src.core.waves import (
    DpmBulkReviewCampaignDefinitionConflictError,
    DpmBulkReviewCampaignDefinitionLaunchBlocked,
)
from src.core.waves.campaign_definition_lifecycle import (
    DpmBulkReviewCampaignDefinitionLifecycleError,
)


CAMPAIGN_ID = "campaign-holdings-review"
CAMPAIGN_VERSION = "2026.05"
TRUSTED_CONTEXT = CampaignTrustedContext(tenant_id="tenant-sg")


class _CampaignService:
    def __init__(self, outcome: object) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, object | None, dict[str, object]]] = []

    def __getattr__(self, name: str) -> Callable[..., object]:
        def _call(*, command: object | None = None, **kwargs: object) -> object:
            self.calls.append((name, command, kwargs))
            if isinstance(self.outcome, Exception):
                raise self.outcome
            return self.outcome

        return _call


def _write_result() -> SimpleNamespace:
    return SimpleNamespace(definition={"campaign_id": CAMPAIGN_ID}, replay=False)


def _approval_request() -> DpmBulkReviewCampaignDefinitionApprovalDecisionRequest:
    return DpmBulkReviewCampaignDefinitionApprovalDecisionRequest(
        decision_type="APPROVED",
        decision_ref="BRC-APPROVAL-2026-05-001",
        decided_by="cio_ops_committee",
        decision_reason="Campaign definition approved for bounded DPM review launch.",
        correlation_id="corr-campaign-approval-decision-001",
    )


def _assignment_action_request() -> DpmBulkReviewCampaignDefinitionAssignmentActionRequest:
    return DpmBulkReviewCampaignDefinitionAssignmentActionRequest(
        action_type="ASSIGNED",
        action_ref="BRC-ASSIGN-2026-05-001",
        recorded_by="ops",
        action_reason="Campaign routed to assigned PM with governance attention.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-action-001",
    )


def _assignment_task_open_request() -> DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest:
    return DpmBulkReviewCampaignDefinitionAssignmentTaskOpenRequest(
        task_ref="BRC-TASK-2026-05-001",
        task_type="ASSIGNMENT",
        opened_by="ops",
        task_reason="Campaign requires assigned PM acknowledgement before launch.",
        assigned_actor_ids=["pm_001"],
        escalation_tier="PM",
        sla_posture="ON_TRACK",
        correlation_id="corr-campaign-assignment-task-001",
    )


def _assignment_task_transition_request() -> (
    DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest
):
    return DpmBulkReviewCampaignDefinitionAssignmentTaskTransitionRequest(
        transition_type="ACKNOWLEDGED",
        transition_ref="BRC-TASK-2026-05-001:ack",
        transitioned_by="pm_001",
        transition_reason="Assigned PM acknowledged the campaign review task.",
        correlation_id="corr-campaign-assignment-task-transition-001",
    )


def _maker_checker_request() -> DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest:
    return DpmBulkReviewCampaignDefinitionMakerCheckerControlRequest(
        control_action="REVIEW_COMPLETED",
        control_ref="BRC-MC-2026-05-001",
        recorded_by="ops",
        submitter_actor_id="pm_001",
        reviewer_actor_id="cio_ops_committee",
        required_reviewer_role="CIO_OPERATIONS_REVIEWER",
        control_outcome="PASSED",
        control_reason="Independent reviewer approved the campaign definition control evidence.",
        correlation_id="corr-campaign-maker-checker-control-001",
    )


def _retirement_request() -> DpmBulkReviewCampaignDefinitionRetirementRequest:
    return DpmBulkReviewCampaignDefinitionRetirementRequest(
        retired_by="ops",
        retirement_reason="Campaign definition replaced by a newer governed version.",
        correlation_id="corr-campaign-retirement-001",
    )


def _supersession_request() -> DpmBulkReviewCampaignDefinitionSupersessionRequest:
    return DpmBulkReviewCampaignDefinitionSupersessionRequest(
        superseded_by_campaign_version="2026.06",
        superseded_by="ops",
        supersession_reason="Campaign definition superseded by the May revalidation pack.",
        correlation_id="corr-campaign-supersession-001",
    )


def _launch_request() -> DpmBulkReviewCampaignDefinitionLaunchRequest:
    return DpmBulkReviewCampaignDefinitionLaunchRequest(
        requested_as_of_date="2026-05-10",
        actor_id="pm_001",
        correlation_id="corr-campaign-launch-001",
    )


PostRoute = Callable[[_CampaignService], object]
ListRoute = Callable[[_CampaignService], object]
LifecycleRoute = Callable[[_CampaignService], object]
LaunchRoute = Callable[[_CampaignService], object]


def _post_routes() -> list[PostRoute]:
    return [
        lambda service: record_bulk_review_campaign_definition_approval_decision_endpoint(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _approval_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: record_bulk_review_campaign_definition_assignment_action_endpoint(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _assignment_action_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: open_bulk_review_campaign_definition_assignment_task_endpoint(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _assignment_task_open_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: transition_bulk_review_campaign_definition_assignment_task_endpoint(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            "BRC-TASK-2026-05-001",
            _assignment_task_transition_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: record_bulk_review_campaign_definition_maker_checker_control_endpoint(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _maker_checker_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
    ]


def _list_routes() -> list[ListRoute]:
    return [
        lambda service: list_bulk_review_campaign_definition_approval_decisions(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            50,
            0,
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: list_bulk_review_campaign_definition_assignment_actions(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            50,
            0,
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: list_bulk_review_campaign_definition_assignment_tasks(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            None,
            50,
            0,
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: list_bulk_review_campaign_definition_maker_checker_controls(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            50,
            0,
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
    ]


def _lifecycle_routes() -> list[LifecycleRoute]:
    return [
        lambda service: retire_bulk_review_campaign_definition(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _retirement_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
        lambda service: supersede_bulk_review_campaign_definition(
            CAMPAIGN_ID,
            CAMPAIGN_VERSION,
            _supersession_request(),
            TRUSTED_CONTEXT,
            service,  # type: ignore[arg-type]
        ),
    ]


def _launch_route() -> LaunchRoute:
    return lambda service: launch_bulk_review_campaign_definition(
        CAMPAIGN_ID,
        CAMPAIGN_VERSION,
        _launch_request(),
        TRUSTED_CONTEXT,
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        service,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("route", _post_routes())
def test_campaign_evidence_post_routes_return_definitions(route: PostRoute) -> None:
    service = _CampaignService(_write_result())

    assert route(service) == {"campaign_id": CAMPAIGN_ID}
    assert service.calls


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [
        (DpmBulkReviewCampaignDefinitionConflictError("DUPLICATE_REF"), 409),
        (DpmWaveCampaignApplicationNotFoundError("missing"), 404),
        (ValueError("EVIDENCE_INVALID"), 422),
    ],
)
@pytest.mark.parametrize("route", _post_routes())
def test_campaign_evidence_post_routes_translate_expected_failures(
    route: PostRoute,
    exception: Exception,
    expected_status: int,
) -> None:
    with pytest.raises(CampaignProblemDetailsException) as exc_info:
        route(_CampaignService(exception))

    assert exc_info.value.status_code == expected_status


@pytest.mark.parametrize("route", _post_routes())
def test_campaign_evidence_post_routes_reraise_unexpected_failures(route: PostRoute) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        route(_CampaignService(RuntimeError("boom")))


@pytest.mark.parametrize("route", _list_routes())
def test_campaign_evidence_list_routes_translate_missing_definition(route: ListRoute) -> None:
    with pytest.raises(CampaignProblemDetailsException) as exc_info:
        route(_CampaignService(DpmWaveCampaignApplicationNotFoundError("missing")))

    assert exc_info.value.status_code == 404


@pytest.mark.parametrize("route", _lifecycle_routes())
def test_campaign_definition_lifecycle_routes_return_definitions(route: LifecycleRoute) -> None:
    service = _CampaignService({"campaign_id": CAMPAIGN_ID})

    assert route(service) == {"campaign_id": CAMPAIGN_ID}
    assert service.calls


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [
        (DpmBulkReviewCampaignDefinitionConflictError("DUPLICATE_REF"), 409),
        (
            DpmBulkReviewCampaignDefinitionLifecycleError(
                "BULK_REVIEW_CAMPAIGN_SUPERSESSION_REPLACEMENT_NOT_FOUND",
                "Replacement bulk-review campaign definition was not found.",
            ),
            404,
        ),
        (DpmWaveCampaignApplicationNotFoundError("missing"), 404),
        (ValueError("LIFECYCLE_INVALID"), 422),
    ],
)
@pytest.mark.parametrize("route", _lifecycle_routes())
def test_campaign_definition_lifecycle_routes_translate_expected_failures(
    route: LifecycleRoute,
    exception: Exception,
    expected_status: int,
) -> None:
    with pytest.raises(CampaignProblemDetailsException) as exc_info:
        route(_CampaignService(exception))

    assert exc_info.value.status_code == expected_status


def test_campaign_definition_launch_route_returns_observable_wave_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        wave_campaign_launch_routes,
        "record_campaign_workflow_success",
        lambda *, surface, replay=False: calls.append((surface, replay)),
    )
    monkeypatch.setattr(
        wave_campaign_launch_routes,
        "wave_response",
        lambda *, wave, durable, idempotent_replay=False: {
            "wave": wave,
            "durable": durable,
            "idempotent_replay": idempotent_replay,
        },
    )
    service = _CampaignService(SimpleNamespace(wave={"wave_id": "dwv_001"}, replay=True))

    response = _launch_route()(service)

    assert response == {
        "wave": {"wave_id": "dwv_001"},
        "durable": True,
        "idempotent_replay": True,
    }
    assert calls == [("launch", True)]
    assert service.calls


@pytest.mark.parametrize(
    ("exception", "expected_status"),
    [
        (
            DpmBulkReviewCampaignDefinitionLaunchBlocked(
                reason_codes=["BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY"],
                readiness=SimpleNamespace(
                    model_dump=lambda mode: {"preview_create_allowed": False},
                ),
            ),
            422,
        ),
        (DpmWaveCampaignApplicationNotFoundError("missing"), 404),
        (wave_service.DpmWaveValidationError("WAVE_INVALID", "Wave invalid."), 422),
        (DpmBulkReviewCampaignDefinitionConflictError("DUPLICATE_REF"), 409),
        (HTTPException(status_code=503, detail={"code": "SOURCE_UNAVAILABLE"}), 503),
    ],
)
def test_campaign_definition_launch_route_translates_expected_failures(
    exception: Exception,
    expected_status: int,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _launch_route()(_CampaignService(exception))

    assert exc_info.value.status_code == expected_status


def test_campaign_definition_launch_route_reraises_unexpected_failures() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        _launch_route()(_CampaignService(RuntimeError("boom")))
