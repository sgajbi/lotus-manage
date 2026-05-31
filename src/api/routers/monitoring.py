from __future__ import annotations

import importlib

from fastapi import APIRouter

from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.infrastructure.core_sourcing import DpmCoreResolverClient


router = APIRouter(prefix="/dpm", tags=["lotus-manage Monitoring"])


def get_core_resolver_client() -> DpmCoreResolverClient:
    return build_core_resolver_client()


importlib.import_module("src.api.routers.monitoring_command_center_routes")
importlib.import_module("src.api.routers.monitoring_run_once_routes")
importlib.import_module("src.api.routers.monitoring_run_read_routes")
importlib.import_module("src.api.routers.monitoring_exception_routes")
