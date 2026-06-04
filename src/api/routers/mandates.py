from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.route_registration import register_route_modules
from src.api.services.core_resolver_service import build_core_resolver_client
from src.api.services.core_resolver_service import CoreResolverClient


router = APIRouter(prefix="/mandates", tags=["lotus-manage Mandates"])


def get_core_resolver_client() -> CoreResolverClient:
    return build_core_resolver_client()


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.mandate_read_routes",
    "src.api.routers.mandate_refresh_routes",
    "src.api.routers.mandate_health_routes",
)

register_route_modules(_ROUTE_MODULES)
