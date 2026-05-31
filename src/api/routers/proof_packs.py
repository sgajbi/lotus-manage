from __future__ import annotations

import importlib

from fastapi import APIRouter


router = APIRouter(
    prefix="/rebalance/proof-packs",
    tags=["lotus-manage Proof Packs"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.proof_pack_generate_routes",
    "src.api.routers.proof_pack_read_routes",
    "src.api.routers.proof_pack_handoff_routes",
)

for route_module in _ROUTE_MODULES:
    importlib.import_module(route_module)
