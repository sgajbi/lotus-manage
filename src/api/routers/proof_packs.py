from __future__ import annotations

import importlib

from fastapi import APIRouter


router = APIRouter(
    prefix="/rebalance/proof-packs",
    tags=["lotus-manage Proof Packs"],
)


importlib.import_module("src.api.routers.proof_pack_generate_routes")
importlib.import_module("src.api.routers.proof_pack_read_routes")
importlib.import_module("src.api.routers.proof_pack_handoff_routes")
