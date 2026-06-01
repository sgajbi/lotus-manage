from src.api.services.outcome_review_search import (
    normalize_outcome_review_search_filter,
    review_matches_source_lineage_filters,
    search_outcome_review_page,
)
from src.core.outcomes import DpmOutcomeSourceRef
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from tests.unit.infrastructure.test_outcome_review_repository import _review


def _source_ref(*, source_system: str, source_type: str, source_id: str) -> DpmOutcomeSourceRef:
    return DpmOutcomeSourceRef(
        source_system=source_system,
        source_type=source_type,
        source_id=source_id,
        content_hash=f"sha256:{source_id}",
    )


def _review_with_sources(
    *,
    outcome_review_id: str,
    source_refs: list[DpmOutcomeSourceRef],
):
    return _review(
        outcome_review_id=outcome_review_id,
        content_hash=f"sha256:{outcome_review_id}",
        idempotency_key=f"idem_{outcome_review_id}",
    ).model_copy(update={"source_lineage": source_refs})


def test_normalize_outcome_review_search_filter_trims_and_drops_blanks() -> None:
    assert normalize_outcome_review_search_filter(None) is None
    assert normalize_outcome_review_search_filter("   ") is None
    assert normalize_outcome_review_search_filter(" lotus-risk ") == "lotus-risk"


def test_review_matches_source_lineage_filters_requires_all_requested_filters() -> None:
    review = _review_with_sources(
        outcome_review_id="dor_lineage",
        source_refs=[
            _source_ref(
                source_system="lotus-risk",
                source_type="RiskMetricsReport:v1",
                source_id="risk_001",
            )
        ],
    )

    assert review_matches_source_lineage_filters(
        review=review,
        source_system="lotus-risk",
        source_type="RiskMetricsReport:v1",
    )
    assert not review_matches_source_lineage_filters(
        review=review,
        source_system="lotus-performance",
        source_type="RiskMetricsReport:v1",
    )
    assert not review_matches_source_lineage_filters(
        review=review,
        source_system="lotus-risk",
        source_type="PerformanceWindowReturn:v1",
    )


def test_search_outcome_review_page_filters_counts_and_paginates_source_lineage() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    risk_ref = _source_ref(
        source_system="lotus-risk",
        source_type="RiskMetricsReport:v1",
        source_id="risk_001",
    )
    performance_ref = _source_ref(
        source_system="lotus-performance",
        source_type="PerformanceWindowReturn:v1",
        source_id="performance_001",
    )
    reviews = [
        _review_with_sources(outcome_review_id="dor_risk_1", source_refs=[risk_ref]),
        _review_with_sources(
            outcome_review_id="dor_risk_performance",
            source_refs=[risk_ref, performance_ref],
        ),
        _review_with_sources(outcome_review_id="dor_performance", source_refs=[performance_ref]),
    ]
    for review in reviews:
        repository.save_outcome_review(review=review, retention_expires_at=None)

    page = search_outcome_review_page(
        repository=repository,
        source_system=" lotus-risk ",
        limit=1,
        offset=1,
    )

    assert page.total == 2
    assert [review.outcome_review_id for review in page.items] == ["dor_risk_1"]
    assert page.normalized_source_system == "lotus-risk"
    assert page.normalized_source_type is None
    assert page.source_owner_counts == {
        "lotus-performance": 1,
        "lotus-risk": 2,
    }
    assert page.source_type_counts == {
        "PerformanceWindowReturn:v1": 1,
        "RiskMetricsReport:v1": 2,
    }


def test_search_outcome_review_page_honors_source_scan_limit_before_lineage_filtering() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(
        review=_review_with_sources(
            outcome_review_id="dor_first",
            source_refs=[
                _source_ref(
                    source_system="lotus-risk",
                    source_type="RiskMetricsReport:v1",
                    source_id="risk_001",
                )
            ],
        ),
        retention_expires_at=None,
    )
    repository.save_outcome_review(
        review=_review_with_sources(
            outcome_review_id="dor_second",
            source_refs=[
                _source_ref(
                    source_system="lotus-risk",
                    source_type="RiskMetricsReport:v1",
                    source_id="risk_002",
                )
            ],
        ),
        retention_expires_at=None,
    )

    page = search_outcome_review_page(
        repository=repository,
        source_system="lotus-risk",
        source_scan_limit=1,
    )

    assert page.total == 1
    assert [review.outcome_review_id for review in page.items] == ["dor_second"]
