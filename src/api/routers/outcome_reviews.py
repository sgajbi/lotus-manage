from __future__ import annotations

import importlib

from fastapi import APIRouter

router = APIRouter(
    prefix="/rebalance/outcome-reviews",
    tags=["lotus-manage Outcome Reviews"],
)


importlib.import_module("src.api.routers.outcome_review_preview_routes")
importlib.import_module("src.api.routers.outcome_review_create_routes")
importlib.import_module("src.api.routers.outcome_review_search_routes")
importlib.import_module("src.api.routers.outcome_review_lookup_routes")
importlib.import_module("src.api.routers.outcome_review_refresh_routes")
importlib.import_module("src.api.routers.outcome_review_supportability_routes")
importlib.import_module("src.api.routers.outcome_review_handoff_routes")


run_lookup_router = APIRouter(prefix="/rebalance/runs", tags=["lotus-manage Outcome Reviews"])
wave_lookup_router = APIRouter(prefix="/rebalance/waves", tags=["lotus-manage Outcome Reviews"])


importlib.import_module("src.api.routers.outcome_review_run_lookup_routes")
importlib.import_module("src.api.routers.outcome_review_wave_lookup_routes")
