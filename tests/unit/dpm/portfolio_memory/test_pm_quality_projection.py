from src.core.outcomes import DpmOutcomeSourceRef
from src.core.portfolio_memory.pm_quality_projection import (
    pm_quality_review_action_event,
    pm_quality_score_run_event,
    pm_quality_summary_invocation_event,
    score_run_includes_portfolio,
)
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    _pm_quality_review_action,
    _pm_quality_score_run,
    _pm_quality_summary_invocation,
)


def test_score_run_includes_portfolio_from_member_portfolio_ids() -> None:
    score_run = _pm_quality_score_run()

    assert score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)
    assert not score_run_includes_portfolio(
        score_run=score_run,
        portfolio_id="PB_NOT_IN_PM_BOOK",
    )


def test_score_run_includes_portfolio_from_pm_book_member_source_ref() -> None:
    score_run = _pm_quality_score_run().model_copy(
        update={
            "book_scope_evidence": _pm_quality_score_run().book_scope_evidence.model_copy(
                update={
                    "member_portfolio_ids": [],
                    "source_refs": [
                        DpmOutcomeSourceRef(
                            source_system="lotus-core",
                            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
                            source_id=f"pm-book:{PORTFOLIO_ID}",
                        )
                    ],
                }
            )
        }
    )

    assert score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)


def test_score_run_without_book_scope_does_not_project_to_portfolio() -> None:
    score_run = _pm_quality_score_run().model_copy(update={"book_scope_evidence": None})

    assert not score_run_includes_portfolio(score_run=score_run, portfolio_id=PORTFOLIO_ID)


def test_pm_quality_score_run_event_preserves_no_numeric_score_boundary() -> None:
    score_run = _pm_quality_score_run()

    event = pm_quality_score_run_event(score_run)

    assert event.event_type == "PM_QUALITY_SCORE_RUN"
    assert event.source_id == score_run.score_run_id
    assert event.metadata["numeric_score_projected"] is False
    assert "score" not in event.metadata
    assert event.artifact_refs[0].content_hash == score_run.content_hash


def test_pm_quality_review_action_event_preserves_no_review_reason_boundary() -> None:
    score_run = _pm_quality_score_run()
    action = _pm_quality_review_action()

    event = pm_quality_review_action_event(action=action, score_run=score_run)

    assert event.event_type == "PM_QUALITY_REVIEW_ACTION"
    assert event.supportability_state == "PENDING_REVIEW"
    assert event.metadata["review_reason_projected"] is False
    assert event.metadata["numeric_score_projected"] is False
    assert event.metadata["fairness_recomputed"] is False
    assert event.metadata["client_contact_claimed"] is False
    assert "review_reason" not in event.metadata
    assert event.artifact_refs[1].source_id == score_run.score_run_id


def test_pm_quality_summary_invocation_event_preserves_no_summary_text_boundary() -> None:
    score_run = _pm_quality_score_run()
    invocation = _pm_quality_summary_invocation()

    event = pm_quality_summary_invocation_event(invocation=invocation, score_run=score_run)

    assert event.event_type == "PM_QUALITY_SUMMARY_INVOCATION"
    assert event.supportability_state == "READY"
    assert event.metadata["summary_text_stored"] is False
    assert event.metadata["summary_text_exposed"] is False
    assert event.metadata["summary_text_projected"] is False
    assert event.metadata["prompt_reconstructed"] is False
    assert event.metadata["model_response_reconstructed"] is False
    assert event.metadata["numeric_score_projected"] is False
    assert event.metadata["summary_text_boundary_id"] == "PM_QUALITY_SUMMARY_TEXT_BOUNDARY"
    assert "summary_text" not in event.metadata
