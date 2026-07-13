import pytest

from src.core.waves.campaign_maker_checker_controls import (
    CampaignControlLifecycleState,
    _control_lifecycle_state,
    _normalize_control_request,
    _validate_control_shape,
    _validate_exception_raised_lifecycle,
    _validate_pending_submitter_matches,
    _validate_review_completed_lifecycle,
    _validate_required_control_fields,
    _validate_submission_lifecycle,
)
from src.core.waves.campaign_definitions import (
    DpmBulkReviewCampaignDefinitionMakerCheckerControl,
)


def test_normalize_control_request_trims_required_and_optional_fields() -> None:
    normalized = _normalize_control_request(
        control_ref=" BRC-MC-001 ",
        recorded_by=" ops ",
        control_reason=" Submitted for review. ",
        correlation_id=" corr-001 ",
        submitter_actor_id=" maker-1 ",
        reviewer_actor_id=" ",
        required_reviewer_role=None,
    )

    assert normalized.control_ref == "BRC-MC-001"
    assert normalized.recorded_by == "ops"
    assert normalized.control_reason == "Submitted for review."
    assert normalized.correlation_id == "corr-001"
    assert normalized.submitter_actor_id == "maker-1"
    assert normalized.reviewer_actor_id is None
    assert normalized.required_reviewer_role is None


def test_validate_required_control_fields_rejects_blank_core_fields() -> None:
    normalized = _normalize_control_request(
        control_ref=" ",
        recorded_by="ops",
        control_reason="reason",
        correlation_id="corr-001",
        submitter_actor_id=None,
        reviewer_actor_id=None,
        required_reviewer_role=None,
    )

    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_CONTROL_REF_REQUIRED",
    ):
        _validate_required_control_fields(normalized)


@pytest.mark.parametrize(
    (
        "control_action",
        "control_outcome",
        "submitter_actor_id",
        "reviewer_actor_id",
        "required_reviewer_role",
    ),
    [
        ("SUBMITTED_FOR_REVIEW", "PENDING", "maker-1", None, None),
        ("REVIEWER_ASSIGNED", "PENDING", None, "checker-1", "senior_reviewer"),
        ("REVIEW_COMPLETED", "PASSED", "maker-1", "checker-1", None),
        ("REVIEW_COMPLETED", "FAILED", "maker-1", "checker-1", None),
        ("CONTROL_EXCEPTION_RAISED", "EXCEPTION_OPEN", None, None, None),
        ("CONTROL_EXCEPTION_RESOLVED", "EXCEPTION_RESOLVED", None, None, None),
    ],
)
def test_validate_control_action_accepts_valid_action_outcome_pairs(
    control_action: str,
    control_outcome: str,
    submitter_actor_id: str | None,
    reviewer_actor_id: str | None,
    required_reviewer_role: str | None,
) -> None:
    _validate_control_shape(
        control_action=control_action,
        control_outcome=control_outcome,
        submitter_actor_id=submitter_actor_id,
        reviewer_actor_id=reviewer_actor_id,
        required_reviewer_role=required_reviewer_role,
    )


@pytest.mark.parametrize(
    (
        "control_action",
        "control_outcome",
        "submitter_actor_id",
        "reviewer_actor_id",
        "required_reviewer_role",
        "expected_error",
    ),
    [
        (
            "SUBMITTED_FOR_REVIEW",
            "PASSED",
            "maker-1",
            None,
            None,
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMISSION_OUTCOME_INVALID",
        ),
        (
            "REVIEWER_ASSIGNED",
            "PENDING",
            None,
            "checker-1",
            None,
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_REQUIRED",
        ),
        (
            "REVIEW_COMPLETED",
            "PASSED",
            "actor-1",
            "actor-1",
            None,
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_ACTOR_SEPARATION_REQUIRED",
        ),
        (
            "CONTROL_EXCEPTION_RAISED",
            "PENDING",
            None,
            None,
            None,
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_OUTCOME_INVALID",
        ),
        (
            "CONTROL_EXCEPTION_RESOLVED",
            "EXCEPTION_OPEN",
            None,
            None,
            None,
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_EXCEPTION_RESOLUTION_INVALID",
        ),
    ],
)
def test_validate_control_action_rejects_invalid_action_outcome_pairs(
    control_action: str,
    control_outcome: str,
    submitter_actor_id: str | None,
    reviewer_actor_id: str | None,
    required_reviewer_role: str | None,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        _validate_control_shape(
            control_action=control_action,
            control_outcome=control_outcome,
            submitter_actor_id=submitter_actor_id,
            reviewer_actor_id=reviewer_actor_id,
            required_reviewer_role=required_reviewer_role,
        )


def _control(
    *,
    control_action: str,
    control_outcome: str,
    submitter_actor_id: str | None = None,
    reviewer_actor_id: str | None = None,
    required_reviewer_role: str | None = None,
) -> DpmBulkReviewCampaignDefinitionMakerCheckerControl:
    return DpmBulkReviewCampaignDefinitionMakerCheckerControl(
        control_id=f"brc_maker_checker_control_{control_action.lower()}",
        control_action=control_action,  # type: ignore[arg-type]
        control_ref=f"BRC-MC-{control_action}",
        recorded_by="ops",
        submitter_actor_id=submitter_actor_id,
        reviewer_actor_id=reviewer_actor_id,
        required_reviewer_role=required_reviewer_role,
        control_outcome=control_outcome,  # type: ignore[arg-type]
        control_reason="Campaign definition control lifecycle evidence.",
        correlation_id=f"corr-{control_action.lower()}",
        content_hash=f"sha256:{control_action.lower()}",
    )


def test_control_lifecycle_state_tracks_completed_reviews_and_resolved_exceptions() -> None:
    state = _control_lifecycle_state(
        [
            _control(
                control_action="SUBMITTED_FOR_REVIEW",
                control_outcome="PENDING",
                submitter_actor_id="pm_001",
            ),
            _control(
                control_action="REVIEWER_ASSIGNED",
                control_outcome="PENDING",
                reviewer_actor_id="cio_ops_committee",
                required_reviewer_role="CIO_OPERATIONS_REVIEWER",
            ),
            _control(
                control_action="REVIEW_COMPLETED",
                control_outcome="FAILED",
                submitter_actor_id="pm_001",
                reviewer_actor_id="cio_ops_committee",
                required_reviewer_role="CIO_OPERATIONS_REVIEWER",
            ),
            _control(
                control_action="CONTROL_EXCEPTION_RAISED",
                control_outcome="EXCEPTION_OPEN",
            ),
            _control(
                control_action="CONTROL_EXCEPTION_RESOLVED",
                control_outcome="EXCEPTION_RESOLVED",
            ),
        ]
    )

    assert state.has_pending_review is False
    assert state.has_open_exception is False
    assert state.latest_outcome == "EXCEPTION_RESOLVED"


def test_control_lifecycle_guards_reject_duplicate_submission() -> None:
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEW_ALREADY_PENDING",
    ):
        _validate_submission_lifecycle(
            CampaignControlLifecycleState(
                has_pending_review=True,
                pending_submitter_actor_id="pm_001",
                pending_reviewer_actor_id=None,
                pending_reviewer_role=None,
                has_open_exception=False,
                latest_outcome="PENDING",
            )
        )


@pytest.mark.parametrize(
    ("reviewer_actor_id", "reviewer_role", "expected_error"),
    [
        (
            "unexpected_reviewer",
            "CIO_OPERATIONS_REVIEWER",
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_MISMATCH",
        ),
        (
            "cio_ops_committee",
            "UNSUPPORTED_REVIEWER",
            "BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_REVIEWER_ROLE_MISMATCH",
        ),
    ],
)
def test_review_completed_lifecycle_guards_assigned_reviewer_and_role(
    reviewer_actor_id: str,
    reviewer_role: str,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        _validate_review_completed_lifecycle(
            state=CampaignControlLifecycleState(
                has_pending_review=True,
                pending_submitter_actor_id="pm_001",
                pending_reviewer_actor_id="cio_ops_committee",
                pending_reviewer_role="CIO_OPERATIONS_REVIEWER",
                has_open_exception=False,
                latest_outcome="PENDING",
            ),
            control=_control(
                control_action="REVIEW_COMPLETED",
                control_outcome="PASSED",
                submitter_actor_id="pm_001",
                reviewer_actor_id=reviewer_actor_id,
                required_reviewer_role=reviewer_role,
            ),
        )


def test_exception_lifecycle_requires_open_review_or_failed_outcome() -> None:
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_OPEN_REVIEW_REQUIRED",
    ):
        _validate_exception_raised_lifecycle(
            CampaignControlLifecycleState(
                has_pending_review=False,
                pending_submitter_actor_id=None,
                pending_reviewer_actor_id=None,
                pending_reviewer_role=None,
                has_open_exception=False,
                latest_outcome="PASSED",
            )
        )


def test_pending_submitter_guard_rejects_submitter_drift() -> None:
    with pytest.raises(
        ValueError,
        match="BULK_REVIEW_CAMPAIGN_MAKER_CHECKER_SUBMITTER_MISMATCH",
    ):
        _validate_pending_submitter_matches(
            state=CampaignControlLifecycleState(
                has_pending_review=True,
                pending_submitter_actor_id="pm_001",
                pending_reviewer_actor_id=None,
                pending_reviewer_role=None,
                has_open_exception=False,
                latest_outcome="PENDING",
            ),
            control=_control(
                control_action="REVIEW_COMPLETED",
                control_outcome="PASSED",
                submitter_actor_id="pm_002",
                reviewer_actor_id="cio_ops_committee",
            ),
        )
