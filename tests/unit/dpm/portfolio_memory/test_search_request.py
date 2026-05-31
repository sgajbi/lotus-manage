import pytest

from src.core.portfolio_memory.search_request import (
    PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX,
    PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN,
    PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
    PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX,
    PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN,
    build_portfolio_memory_search_query,
    validate_portfolio_memory_source_scan_limit,
)


def test_portfolio_memory_search_bounds_are_named_contract_constants() -> None:
    assert PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT == 50
    assert PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN == 1
    assert PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX == 200
    assert PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT == 0
    assert PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN == 0
    assert PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT == 500
    assert PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN == 1
    assert PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX == 1000


def test_build_portfolio_memory_search_query_normalizes_text_filters() -> None:
    query = build_portfolio_memory_search_query(
        portfolio_ids=[" PB_SEARCH_001 ", "", "PB_SEARCH_002"],
        event_type=" WAVE_HANDOFF_READY ",
        supportability_state=" READY ",
        source_system=" lotus-core ",
        source_type=" PortfolioManagerBookMembership ",
        limit=PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
        offset=PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT,
        source_scan_limit=PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
    )

    assert query.filters.event_type == "WAVE_HANDOFF_READY"
    assert query.filters.supportability_state == "READY"
    assert query.filters.source_system == "lotus-core"
    assert query.filters.source_type == "PortfolioManagerBookMembership"
    assert query.explicit_candidate_ids == {"PB_SEARCH_001", "PB_SEARCH_002"}
    assert query.limit == PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT
    assert query.offset == PORTFOLIO_MEMORY_SEARCH_OFFSET_DEFAULT
    assert query.source_scan_limit == PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT


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


def test_validate_portfolio_memory_source_scan_limit_preserves_supported_limit() -> None:
    assert (
        validate_portfolio_memory_source_scan_limit(
            source_scan_limit=PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT
        )
        == PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT
    )


@pytest.mark.parametrize(
    ("limit", "offset", "source_scan_limit", "expected_message"),
    [
        (
            PORTFOLIO_MEMORY_SEARCH_LIMIT_MIN - 1,
            0,
            PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
            "limit must be between 1 and 200",
        ),
        (
            PORTFOLIO_MEMORY_SEARCH_LIMIT_MAX + 1,
            0,
            PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
            "limit must be between 1 and 200",
        ),
        (
            PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
            PORTFOLIO_MEMORY_SEARCH_OFFSET_MIN - 1,
            PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_DEFAULT,
            "offset must be greater than or equal to 0",
        ),
        (
            PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
            0,
            PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MIN - 1,
            "source_scan_limit must be between 1 and 1000",
        ),
        (
            PORTFOLIO_MEMORY_SEARCH_LIMIT_DEFAULT,
            0,
            PORTFOLIO_MEMORY_SOURCE_SCAN_LIMIT_MAX + 1,
            "source_scan_limit must be between 1 and 1000",
        ),
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
