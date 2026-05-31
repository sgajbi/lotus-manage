from __future__ import annotations

import importlib

from fastapi import APIRouter

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

for route_module in _ROUTE_MODULES:
    importlib.import_module(route_module)


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


_CROSS_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.outcome_review_run_lookup_routes",
    "src.api.routers.outcome_review_wave_lookup_routes",
)

for route_module in _CROSS_ROUTE_MODULES:
    importlib.import_module(route_module)
