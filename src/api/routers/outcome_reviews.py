from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.route_registration import register_route_modules

router = APIRouter(
    prefix="/rebalance/outcome-reviews",
    tags=["lotus-manage Outcome Reviews"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.outcome_review_preview_routes",
    "src.api.routers.outcome_review_create_routes",
    "src.api.routers.outcome_review_search_routes",
    "src.api.routers.outcome_review_lookup_routes",
    "src.api.routers.outcome_review_refresh_routes",
    "src.api.routers.outcome_review_supportability_routes",
    "src.api.routers.outcome_review_handoff_routes",
)

register_route_modules(_ROUTE_MODULES)


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


_CROSS_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.outcome_review_run_lookup_routes",
    "src.api.routers.outcome_review_wave_lookup_routes",
)

register_route_modules(_CROSS_ROUTE_MODULES)
