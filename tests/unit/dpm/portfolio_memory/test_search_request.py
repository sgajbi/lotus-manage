import pytest

from src.core.portfolio_memory.search_request import build_portfolio_memory_search_query


def test_build_portfolio_memory_search_query_normalizes_text_filters() -> None:
    query = build_portfolio_memory_search_query(
        portfolio_ids=[" PB_SEARCH_001 ", "", "PB_SEARCH_002"],
        event_type=" WAVE_HANDOFF_READY ",
        supportability_state=" READY ",
        source_system=" lotus-core ",
        source_type=" PortfolioManagerBookMembership ",
        limit=50,
        offset=0,
        source_scan_limit=500,
    )

    assert query.filters.event_type == "WAVE_HANDOFF_READY"
    assert query.filters.supportability_state == "READY"
    assert query.filters.source_system == "lotus-core"
    assert query.filters.source_type == "PortfolioManagerBookMembership"
    assert query.explicit_candidate_ids == {"PB_SEARCH_001", "PB_SEARCH_002"}
    assert query.limit == 50
    assert query.offset == 0
    assert query.source_scan_limit == 500


def test_build_portfolio_memory_search_query_treats_blank_filters_as_absent() -> None:
    query = build_portfolio_memory_search_query(
        portfolio_ids=None,
        event_type=" ",
        supportability_state=None,
        source_system="",
        source_type="   ",
        limit=25,
        offset=10,
        source_scan_limit=250,
    )

    assert query.filters.event_type is None
    assert query.filters.supportability_state is None
    assert query.filters.source_system is None
    assert query.filters.source_type is None
    assert query.explicit_candidate_ids == set()
    assert query.limit == 25
    assert query.offset == 10
    assert query.source_scan_limit == 250


@pytest.mark.parametrize(
    ("limit", "offset", "source_scan_limit", "expected_message"),
    [
        (0, 0, 500, "limit must be between 1 and 200"),
        (201, 0, 500, "limit must be between 1 and 200"),
        (50, -1, 500, "offset must be greater than or equal to 0"),
        (50, 0, 0, "source_scan_limit must be between 1 and 1000"),
        (50, 0, 1001, "source_scan_limit must be between 1 and 1000"),
    ],
)
def test_build_portfolio_memory_search_query_rejects_unsafe_pagination(
    limit: int,
    offset: int,
    source_scan_limit: int,
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        build_portfolio_memory_search_query(
            portfolio_ids=None,
            event_type=None,
            supportability_state=None,
            source_system=None,
            source_type=None,
            limit=limit,
            offset=offset,
            source_scan_limit=source_scan_limit,
        )
