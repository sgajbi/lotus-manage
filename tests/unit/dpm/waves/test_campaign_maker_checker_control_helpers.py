import pytest

from src.core.waves.campaign_maker_checker_controls import (
    _normalize_control_request,
    _validate_control_shape,
    _validate_required_control_fields,
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
