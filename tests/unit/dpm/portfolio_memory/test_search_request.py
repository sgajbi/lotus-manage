from src.core.portfolio_memory.search_request import build_portfolio_memory_search_query


def test_build_portfolio_memory_search_query_normalizes_text_filters() -> None:
    query = build_portfolio_memory_search_query(
        portfolio_ids=[" PB_SEARCH_001 ", "", "PB_SEARCH_002"],
        event_type=" WAVE_HANDOFF_READY ",
        supportability_state=" READY ",
        source_system=" lotus-core ",
        source_type=" PortfolioManagerBookMembership ",
    )

    assert query.filters.event_type == "WAVE_HANDOFF_READY"
    assert query.filters.supportability_state == "READY"
    assert query.filters.source_system == "lotus-core"
    assert query.filters.source_type == "PortfolioManagerBookMembership"
    assert query.explicit_candidate_ids == {"PB_SEARCH_001", "PB_SEARCH_002"}


def test_build_portfolio_memory_search_query_treats_blank_filters_as_absent() -> None:
    query = build_portfolio_memory_search_query(
        portfolio_ids=None,
        event_type=" ",
        supportability_state=None,
        source_system="",
        source_type="   ",
    )

    assert query.filters.event_type is None
    assert query.filters.supportability_state is None
    assert query.filters.source_system is None
    assert query.filters.source_type is None
    assert query.explicit_candidate_ids == set()
