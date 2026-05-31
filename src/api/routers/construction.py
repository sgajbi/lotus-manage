from __future__ import annotations

import importlib

from fastapi import APIRouter


router = APIRouter(
    prefix="/construction/alternative-sets",
    tags=["lotus-manage Construction Alternatives"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.construction_generate_routes",
    "src.api.routers.construction_read_routes",
    "src.api.routers.construction_selection_routes",
)

for route_module in _ROUTE_MODULES:
    importlib.import_module(route_module)
