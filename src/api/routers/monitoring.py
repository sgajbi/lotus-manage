from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.route_registration import register_route_modules
from src.api.services.rebalance_simulation_service import build_core_resolver_client
from src.infrastructure.core_sourcing import DpmCoreResolverClient


router = APIRouter(prefix="/dpm", tags=["lotus-manage Monitoring"])


def get_core_resolver_client() -> DpmCoreResolverClient:
    return build_core_resolver_client()


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.monitoring_command_center_routes",
    "src.api.routers.monitoring_run_once_routes",
    "src.api.routers.monitoring_run_read_routes",
    "src.api.routers.monitoring_exception_routes",
)

register_route_modules(_ROUTE_MODULES)
