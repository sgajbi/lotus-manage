"""Read request limits for portfolio-memory timelines and event lookup."""

PORTFOLIO_MEMORY_READ_LIMIT_DEFAULT = 100
PORTFOLIO_MEMORY_READ_LIMIT_MIN = 1
PORTFOLIO_MEMORY_READ_LIMIT_MAX = 1000
PORTFOLIO_MEMORY_DETAIL_LIMIT_MAX = 500
PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_DEFAULT = 500
PORTFOLIO_MEMORY_EVENT_LOOKUP_LIMIT_MAX = PORTFOLIO_MEMORY_READ_LIMIT_MAX


def validate_portfolio_memory_read_limit(*, limit: int) -> int:
    if limit < PORTFOLIO_MEMORY_READ_LIMIT_MIN or limit > PORTFOLIO_MEMORY_READ_LIMIT_MAX:
        raise ValueError(
            "portfolio-memory event limit must be between "
            f"{PORTFOLIO_MEMORY_READ_LIMIT_MIN} and {PORTFOLIO_MEMORY_READ_LIMIT_MAX}"
        )
    return limit
