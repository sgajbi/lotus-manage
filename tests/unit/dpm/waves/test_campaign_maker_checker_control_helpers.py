import pytest

from src.core.waves.campaign_maker_checker_controls import _validate_control_action


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
    _validate_control_action(
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
        _validate_control_action(
            control_action=control_action,
            control_outcome=control_outcome,
            submitter_actor_id=submitter_actor_id,
            reviewer_actor_id=reviewer_actor_id,
            required_reviewer_role=required_reviewer_role,
        )
