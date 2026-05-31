from __future__ import annotations

from fastapi import APIRouter

from src.api.routers.route_registration import register_route_modules


router = APIRouter(
    prefix="/rebalance/proof-packs",
    tags=["lotus-manage Proof Packs"],
)


_ROUTE_MODULES: tuple[str, ...] = (
    "src.api.routers.proof_pack_generate_routes",
    "src.api.routers.proof_pack_read_routes",
    "src.api.routers.proof_pack_handoff_routes",
)

register_route_modules(_ROUTE_MODULES)
