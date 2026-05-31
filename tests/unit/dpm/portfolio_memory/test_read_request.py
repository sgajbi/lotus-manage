import pytest

from src.core.portfolio_memory.read_request import (
    PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX,
    PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_MAX,
    PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT,
    PORTFOLIO_MEMORY_READ_LIMIT_MAX,
    PORTFOLIO_MEMORY_READ_LIMIT_MIN,
    validate_portfolio_memory_read_limit,
)


def test_portfolio_memory_read_limit_constants_document_api_bounds() -> None:
    assert PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT == 100
    assert PORTFOLIO_MEMORY_READ_LIMIT_MIN == 1
    assert PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX == 500
    assert PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_DEFAULT == 500
    assert PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_MAX == PORTFOLIO_MEMORY_READ_LIMIT_MAX


@pytest.mark.parametrize("limit", [PORTFOLIO_MEMORY_READ_LIMIT_MIN, 250])
def test_validate_portfolio_memory_read_limit_preserves_supported_limits(limit: int) -> None:
    assert validate_portfolio_memory_read_limit(limit=limit) == limit


@pytest.mark.parametrize("limit", [0, PORTFOLIO_MEMORY_READ_LIMIT_MAX + 1])
def test_validate_portfolio_memory_read_limit_rejects_unsafe_limits(limit: int) -> None:
    with pytest.raises(ValueError, match="portfolio-memory event limit"):
        validate_portfolio_memory_read_limit(limit=limit)
