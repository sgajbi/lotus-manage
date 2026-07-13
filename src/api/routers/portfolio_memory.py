"""API routes for RFC-0040 portfolio memory."""

from fastapi import APIRouter

from src.api.dependencies import (
    get_portfolio_memory_source_repositories as get_portfolio_memory_source_repositories,
)
from src.api.routers.route_registration import register_route_modules


router = APIRouter(
    prefix="/rebalance/portfolio-memory",
    tags=["lotus-manage Portfolio Memory"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.portfolio_memory_search_routes",
    "src.api.routers.portfolio_memory_event_routes",
    "src.api.routers.portfolio_memory_detail_routes",
)

register_route_modules(_ROUTE_MODULES)
