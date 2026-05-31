from __future__ import annotations

import importlib

from fastapi import APIRouter

from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.infrastructure.core_sourcing import DpmCoreResolverClient


router = APIRouter(prefix="/mandates", tags=["lotus-manage Mandates"])


def get_core_resolver_client() -> DpmCoreResolverClient:
    return build_core_resolver_client()


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.mandate_read_routes",
    "src.api.routers.mandate_refresh_routes",
    "src.api.routers.mandate_health_routes",
)

for route_module in _ROUTE_MODULES:
    importlib.import_module(route_module)
