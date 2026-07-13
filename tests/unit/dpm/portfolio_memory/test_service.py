from datetime import datetime, timezone

import pytest

from src.core.outcomes.models import DpmOutcomeEvent, DpmPostTradeOutcomeReview
from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualitySummaryInvocation,
)
from src.core.portfolio_memory.service import (
    build_portfolio_memory_from_sources,
    search_portfolio_memory_from_sources,
)
from src.core.portfolio_memory.source_repositories import (
    build_portfolio_memory_source_repositories,
)
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.waves.models import DpmRebalanceWave
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.unit.dpm.api.test_portfolio_memory_api import (
    PORTFOLIO_ID,
    TENANT_ID,
    _pm_quality_score_run,
    _pm_quality_summary_invocation,
    _repositories,
    _wave,
)
from tests.unit.dpm.proof_packs.test_proof_pack_repository import _proof_pack
from tests.unit.infrastructure.test_outcome_review_repository import _review


class _CountingProofPackRepository(InMemoryDpmProofPackRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0

    def list_proof_packs(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPreTradeProofPack]:
        self.list_calls += 1
        return super().list_proof_packs(
            portfolio_id=portfolio_id,
            mandate_id=mandate_id,
            status=status,
            limit=limit,
            offset=offset,
        )


class _CountingWaveRepository(InMemoryDpmWaveRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0

    def list_waves(
        self,
        *,
        state: str | None = None,
        trigger_type: str | None = None,
        as_of_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmRebalanceWave]:
        self.list_calls += 1
        return super().list_waves(
            state=state,
            trigger_type=trigger_type,
            as_of_date=as_of_date,
            limit=limit,
            offset=offset,
        )


class _CountingOutcomeReviewRepository(InMemoryDpmOutcomeReviewRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0
        self.list_event_calls = 0

    def list_outcome_reviews(
        self,
        *,
        portfolio_id: str | None = None,
        mandate_id: str | None = None,
        wave_id: str | None = None,
        rebalance_run_id: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPostTradeOutcomeReview]:
        self.list_calls += 1
        return super().list_outcome_reviews(
            portfolio_id=portfolio_id,
            mandate_id=mandate_id,
            wave_id=wave_id,
            rebalance_run_id=rebalance_run_id,
            state=state,
            limit=limit,
            offset=offset,
        )

    def list_events(self, *, outcome_review_id: str) -> list[DpmOutcomeEvent]:
        self.list_event_calls += 1
        return super().list_events(outcome_review_id=outcome_review_id)


class _CountingScoreRunRepository(InMemoryDpmPmQualityScoreRunRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0

    def list_score_runs(
        self,
        *,
        tenant_id: str,
        pm_id: str | None = None,
        book_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmOperatingQualityScoreRun]:
        self.list_calls += 1
        return super().list_score_runs(
            tenant_id=tenant_id,
            pm_id=pm_id,
            book_id=book_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            state=state,
            limit=limit,
            offset=offset,
        )


class _CountingSummaryInvocationRepository(InMemoryDpmPmQualitySummaryInvocationRepository):
    def __init__(self) -> None:
        super().__init__()
        self.list_calls = 0

    def list_summary_invocations(
        self,
        *,
        tenant_id: str,
        score_run_id: str | None = None,
        review_action_id: str | None = None,
        policy_id: str | None = None,
        as_of_date: str | None = None,
        invocation_state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DpmPmQualitySummaryInvocation]:
        self.list_calls += 1
        return super().list_summary_invocations(
            tenant_id=tenant_id,
            score_run_id=score_run_id,
            review_action_id=review_action_id,
            policy_id=policy_id,
            as_of_date=as_of_date,
            invocation_state=invocation_state,
            limit=limit,
            offset=offset,
        )


def test_search_portfolio_memory_from_sources_uses_repository_bundle() -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    page = search_portfolio_memory_from_sources(
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            mandate_repository=mandate_repository,
        ),
        portfolio_ids=[PORTFOLIO_ID],
        event_type="PROOF_PACK_CREATED",
        generated_at=datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc),
    )

    assert page.returned_count == 1
    assert page.scanned_portfolio_count == 1
    assert page.items[0].portfolio_id == PORTFOLIO_ID
    assert page.items[0].latest_matching_event_type == "PROOF_PACK_CREATED"


def test_search_portfolio_memory_from_sources_batches_source_family_scans() -> None:
    proof_pack_repository = _CountingProofPackRepository()
    proof_pack_repository.save_proof_pack(
        proof_pack=_proof_pack().model_copy(update={"portfolio_id": PORTFOLIO_ID}),
        idempotency_key=None,
        retention_expires_at=None,
    )
    wave_repository = _CountingWaveRepository()
    wave_repository.save_wave(wave=_wave(), idempotency_key=None, request_hash=None)
    outcome_repository = _CountingOutcomeReviewRepository()
    outcome_repository.save_outcome_review(review=_review(), retention_expires_at=None)
    score_run_repository = _CountingScoreRunRepository()
    score_run_repository.save_score_run(tenant_id=TENANT_ID, score_run=_pm_quality_score_run())
    summary_invocation_repository = _CountingSummaryInvocationRepository()
    summary_invocation_repository.save_summary_invocation(
        tenant_id=TENANT_ID, invocation=_pm_quality_summary_invocation()
    )

    page = search_portfolio_memory_from_sources(
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=wave_repository,
            outcome_review_repository=outcome_repository,
            pm_quality_score_run_repository=score_run_repository,
            pm_quality_summary_invocation_repository=summary_invocation_repository,
        ),
        event_type="PM_QUALITY_SUMMARY_INVOCATION",
        generated_at=datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc),
        tenant_id=TENANT_ID,
    )

    assert page.returned_count == 2
    assert page.scanned_portfolio_count == 2
    assert {item.portfolio_id for item in page.items} == {
        PORTFOLIO_ID,
        "PB_SG_GLOBAL_INC_002",
    }
    assert proof_pack_repository.list_calls == 1
    assert wave_repository.list_calls == 1
    assert outcome_repository.list_calls == 1
    assert outcome_repository.list_event_calls == 1
    assert score_run_repository.list_calls == 1
    assert summary_invocation_repository.list_calls == 1


def test_search_portfolio_memory_from_sources_supplements_explicit_portfolio_sources() -> None:
    proof_pack_repository = _CountingProofPackRepository()
    proof_pack_repository.save_proof_pack(
        proof_pack=_proof_pack().model_copy(
            update={
                "proof_pack_id": "dpp_other_newer",
                "portfolio_id": "PB_OTHER_NEWER",
                "created_at": datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
            }
        ),
        idempotency_key=None,
        retention_expires_at=None,
    )
    proof_pack_repository.save_proof_pack(
        proof_pack=_proof_pack().model_copy(
            update={
                "proof_pack_id": "dpp_other_second",
                "portfolio_id": "PB_OTHER_SECOND",
                "created_at": datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
            }
        ),
        idempotency_key=None,
        retention_expires_at=None,
    )
    proof_pack_repository.save_proof_pack(
        proof_pack=_proof_pack().model_copy(
            update={
                "proof_pack_id": "dpp_explicit_older",
                "portfolio_id": PORTFOLIO_ID,
                "created_at": datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc),
            }
        ),
        idempotency_key=None,
        retention_expires_at=None,
    )
    outcome_repository = _CountingOutcomeReviewRepository()
    outcome_repository.save_outcome_review(
        review=_review(outcome_review_id="dor_other_newer").model_copy(
            update={
                "portfolio_id": "PB_OTHER_NEWER",
                "created_at": datetime(2026, 6, 2, 10, 0, tzinfo=timezone.utc),
                "idempotency_key": "idem_dor_other_newer",
            }
        ),
        retention_expires_at=None,
    )
    outcome_repository.save_outcome_review(
        review=_review(outcome_review_id="dor_other_second").model_copy(
            update={
                "portfolio_id": "PB_OTHER_SECOND",
                "created_at": datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
                "idempotency_key": "idem_dor_other_second",
            }
        ),
        retention_expires_at=None,
    )
    outcome_repository.save_outcome_review(
        review=_review(outcome_review_id="dor_explicit_older").model_copy(
            update={
                "portfolio_id": PORTFOLIO_ID,
                "created_at": datetime(2026, 5, 31, 10, 0, tzinfo=timezone.utc),
                "idempotency_key": "idem_dor_explicit_older",
            }
        ),
        retention_expires_at=None,
    )

    page = search_portfolio_memory_from_sources(
        repositories=build_portfolio_memory_source_repositories(
            proof_pack_repository=proof_pack_repository,
            wave_repository=InMemoryDpmWaveRepository(),
            outcome_review_repository=outcome_repository,
        ),
        portfolio_ids=[PORTFOLIO_ID],
        source_scan_limit=2,
        generated_at=datetime(2026, 5, 31, 11, 0, tzinfo=timezone.utc),
    )

    explicit_item = next(item for item in page.items if item.portfolio_id == PORTFOLIO_ID)
    assert explicit_item.event_type_counts["PROOF_PACK_CREATED"] == 1
    assert explicit_item.event_type_counts["OUTCOME_REVIEW_CREATED"] == 1
    assert proof_pack_repository.list_calls == 2
    assert outcome_repository.list_calls == 2
    assert outcome_repository.list_event_calls == 3


@pytest.mark.parametrize("limit", [0, 1001])
def test_build_portfolio_memory_from_sources_rejects_unsafe_event_limits(limit: int) -> None:
    proof_pack_repository, wave_repository, outcome_repository, mandate_repository = _repositories()

    with pytest.raises(ValueError, match="portfolio-memory event limit"):
        build_portfolio_memory_from_sources(
            portfolio_id=PORTFOLIO_ID,
            repositories=build_portfolio_memory_source_repositories(
                proof_pack_repository=proof_pack_repository,
                wave_repository=wave_repository,
                outcome_review_repository=outcome_repository,
                mandate_repository=mandate_repository,
            ),
            limit=limit,
        )
