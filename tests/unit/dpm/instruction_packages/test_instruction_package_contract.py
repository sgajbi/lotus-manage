from __future__ import annotations

import json
from pathlib import Path

from src.api.main import app


ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "approved-instruction-packages"
    / "lotus-manage-approved-instruction-package.v1.json"
)


def test_approved_instruction_package_contract_tracks_served_routes_and_boundaries() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    openapi_paths = app.openapi()["paths"]

    assert contract["product_name"] == "ApprovedDpmInstructionPackage"
    assert contract["lifecycle_status"] == "implemented_not_certified"
    assert all(route.split(" ", 1)[1] in openapi_paths for route in contract["routes"].values())
    assert contract["partial_release_policy"] == "RELEASE_ELIGIBLE_ITEMS_ONLY"
    assert "approval material preview is not a released package" in contract["non_claims"]
    assert (
        "execution adapter submission and acknowledgement contract"
        in contract["external_owner_dependencies"]
    )
