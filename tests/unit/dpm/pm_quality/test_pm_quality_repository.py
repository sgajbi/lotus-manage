from decimal import Decimal

import pytest

from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityWeight,
    build_pm_operating_quality_score_run,
)
from src.infrastructure.pm_quality import InMemoryDpmPmQualityScoreRunRepository


def _score_run(*, pm_id: str = "pm_001", policy_id: str = "pmq_sg_dpm"):
    policy = DpmPmOperatingQualityPolicy(
        policy_id=policy_id,
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="OUTCOME_DISCIPLINE",
                weight=Decimal("100"),
                minimum_evidence_count=1,
            )
        ],
    )
    return build_pm_operating_quality_score_run(
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=policy,
        evidence_items=[],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id=f"corr-{pm_id}",
    )


def test_in_memory_pm_quality_repository_persists_immutable_score_runs() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run()

    repository.save_score_run(score_run=score_run)
    repository.save_score_run(score_run=score_run)

    stored = repository.get_score_run(score_run_id=score_run.score_run_id)
    assert stored == score_run

    changed = score_run.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityScoreRunConflictError):
        repository.save_score_run(score_run=changed)


def test_in_memory_pm_quality_repository_lists_with_bounded_filters() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    first = _score_run(pm_id="pm_001", policy_id="pmq_sg_dpm")
    second = _score_run(pm_id="pm_002", policy_id="pmq_hk_dpm")
    repository.save_score_run(score_run=first)
    repository.save_score_run(score_run=second)

    assert repository.list_score_runs(pm_id="pm_001") == [first]
    assert repository.list_score_runs(policy_id="pmq_hk_dpm") == [second]
    assert repository.list_score_runs(book_id="missing") == []
    assert repository.list_score_runs(limit=1, offset=1) == [first]
