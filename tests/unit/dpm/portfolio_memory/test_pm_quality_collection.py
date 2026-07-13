from typing import Any

from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
)
from src.core.portfolio_memory.pm_quality_collection import pm_quality_memory_events
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    TENANT_ID,
    _pm_quality_review_action,
    _pm_quality_score_run,
    _pm_quality_summary_invocation,
)


def test_pm_quality_memory_events_reuses_one_score_run_scan_for_downstream_events() -> None:
    score_run_repository = _CountingScoreRunRepository()
    review_action_repository = _CountingReviewActionRepository()
    summary_invocation_repository = _CountingSummaryInvocationRepository()
    score_run_repository.save_score_run(tenant_id=TENANT_ID, score_run=_pm_quality_score_run())
    review_action_repository.save_review_action(
        tenant_id=TENANT_ID,
        action=_pm_quality_review_action(),
    )
    summary_invocation_repository.save_summary_invocation(
        tenant_id=TENANT_ID, invocation=_pm_quality_summary_invocation()
    )

    events = pm_quality_memory_events(
        portfolio_id=PORTFOLIO_ID,
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
        summary_invocation_repository=summary_invocation_repository,
        limit=100,
        tenant_id=TENANT_ID,
    )

    assert score_run_repository.list_score_runs_call_count == 1
    assert review_action_repository.list_review_actions_call_count == 1
    assert summary_invocation_repository.list_summary_invocations_call_count == 1
    assert [event.event_type for event in events] == [
        "PM_QUALITY_SCORE_RUN",
        "PM_QUALITY_REVIEW_ACTION",
        "PM_QUALITY_SUMMARY_INVOCATION",
    ]
    assert [event.source_id for event in events] == [
        _pm_quality_score_run().score_run_id,
        _pm_quality_review_action().review_action_id,
        _pm_quality_summary_invocation().summary_invocation_id,
    ]


def test_pm_quality_memory_events_skips_downstream_scans_without_portfolio_scope() -> None:
    score_run_repository = _CountingScoreRunRepository()
    review_action_repository = _CountingReviewActionRepository()
    summary_invocation_repository = _CountingSummaryInvocationRepository()
    score_run_repository.save_score_run(
        tenant_id=TENANT_ID,
        score_run=_pm_quality_score_run().model_copy(
            update={
                "score_run_id": "pmq_score_run_out_of_scope",
                "book_scope_evidence": None,
                "content_hash": "sha256:pmq-score-run-out-of-scope",
            }
        ),
    )

    events = pm_quality_memory_events(
        portfolio_id=PORTFOLIO_ID,
        score_run_repository=score_run_repository,
        review_action_repository=review_action_repository,
        summary_invocation_repository=summary_invocation_repository,
        limit=100,
        tenant_id=TENANT_ID,
    )

    assert events == []
    assert score_run_repository.list_score_runs_call_count == 1
    assert review_action_repository.list_review_actions_call_count == 0
    assert summary_invocation_repository.list_summary_invocations_call_count == 0


def test_pm_quality_memory_events_omits_unresolved_summary_lineage() -> None:
    score_run_repository = _CountingScoreRunRepository()
    summary_invocation_repository = _CountingSummaryInvocationRepository()
    score_run_repository.save_score_run(tenant_id=TENANT_ID, score_run=_pm_quality_score_run())
    summary_invocation_repository.save_summary_invocation(
        tenant_id=TENANT_ID,
        invocation=_pm_quality_summary_invocation().model_copy(
            update={
                "summary_invocation_id": "pmq_summary_orphan",
                "score_run_id": "pmq_score_run_missing",
                "content_hash": "sha256:pmq-summary-orphan",
            }
        ),
    )

    events = pm_quality_memory_events(
        portfolio_id=PORTFOLIO_ID,
        score_run_repository=score_run_repository,
        summary_invocation_repository=summary_invocation_repository,
        limit=100,
        tenant_id=TENANT_ID,
    )

    assert [event.event_type for event in events] == ["PM_QUALITY_SCORE_RUN"]
    assert summary_invocation_repository.list_summary_invocations_call_count == 1


class _CountingScoreRunRepository(InMemoryDpmPmQualityScoreRunRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_score_runs_call_count = 0

    def list_score_runs(self, **kwargs: Any) -> list[DpmPmOperatingQualityScoreRun]:
        self.list_score_runs_call_count += 1
        return super().list_score_runs(**kwargs)


class _CountingReviewActionRepository(InMemoryDpmPmQualityReviewActionRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_review_actions_call_count = 0

    def list_review_actions(self, **kwargs: Any) -> list[DpmPmQualityReviewAction]:
        self.list_review_actions_call_count += 1
        return super().list_review_actions(**kwargs)


class _CountingSummaryInvocationRepository(InMemoryDpmPmQualitySummaryInvocationRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_summary_invocations_call_count = 0

    def list_summary_invocations(self, **kwargs: Any) -> list[DpmPmQualitySummaryInvocation]:
        self.list_summary_invocations_call_count += 1
        return super().list_summary_invocations(**kwargs)
