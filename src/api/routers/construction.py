from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.route_registration import register_route_modules


router = APIRouter(
    prefix="/construction/alternative-sets",
    tags=["lotus-manage Construction Alternatives"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.construction_generate_routes",
    "src.api.routers.construction_read_routes",
    "src.api.routers.construction_selection_routes",
)

register_route_modules(_ROUTE_MODULES)
