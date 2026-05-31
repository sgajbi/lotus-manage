from __future__ import annotations

import importlib

from fastapi import APIRouter


router = APIRouter(
    prefix="/construction/alternative-sets",
    tags=["lotus-manage Construction Alternatives"],
)


importlib.import_module("src.api.routers.construction_generate_routes")
importlib.import_module("src.api.routers.construction_read_routes")
importlib.import_module("src.api.routers.construction_selection_routes")
