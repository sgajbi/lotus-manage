from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_domain_data_product_contracts import (
    LOCAL_DECLARATION_DIR,
    platform_validation_dependencies_available,
    validate_repo_native_contracts,
)


ROOT = Path(__file__).resolve().parents[2]
CONSUMER_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-consumers.v1.json"
)
PRODUCT_DECLARATION_PATH = (
    ROOT / "contracts" / "domain-data-products" / "lotus-manage-products.v1.json"
)
REQUEST_MODELS_PATH = ROOT / "src" / "api" / "request_models.py"
UPSTREAM_FAMILY_MAP_PATH = ROOT / "docs" / "standards" / "RFC-0082-upstream-contract-family-map.md"
DECLARATION_README_PATH = ROOT / "contracts" / "domain-data-products" / "README.md"


def _load_consumer_declaration() -> dict:
    return json.loads(CONSUMER_DECLARATION_PATH.read_text(encoding="utf-8"))


def _load_product_declaration() -> dict:
    return json.loads(PRODUCT_DECLARATION_PATH.read_text(encoding="utf-8"))


def test_repo_native_domain_data_product_validation_passes_when_platform_is_available() -> None:
    if not platform_validation_dependencies_available(LOCAL_DECLARATION_DIR):
        pytest.skip("sibling lotus-platform contract validator is not available")

    assert validate_repo_native_contracts() == []


def test_manage_consumer_declaration_tracks_current_portfolio_snapshot_input() -> None:
    payload = _load_consumer_declaration()
    dependencies = payload["dependencies"]

    assert payload["consumer_repository"] == "lotus-manage"
    assert dependencies == [
        {
            "product_name": "PortfolioStateSnapshot",
            "producer_repository": "lotus-core",
            "required_product_version": "v1",
            "required_trust_metadata": [
                "generated_at",
                "as_of_date",
                "reconciliation_status",
                "data_quality_status",
                "correlation_id",
            ],
            "migration_posture": {"status": "current"},
            "consumption_mode": "caller_supplied_contract_payload",
            "business_purpose": (
                "Run discretionary rebalance simulation and what-if analysis from a governed "
                "portfolio-state snapshot supplied through the current management request contract."
            ),
            "validation_lanes": ["feature", "pr-merge"],
            "failure_posture": "fail_closed",
        }
    ]

    request_models = REQUEST_MODELS_PATH.read_text(encoding="utf-8")
    assert "portfolio_snapshot: PortfolioSnapshot" in request_models


def test_manage_declaration_does_not_claim_live_source_data_api_reads() -> None:
    payload = _load_consumer_declaration()
    consumption_modes = {dependency["consumption_mode"] for dependency in payload["dependencies"]}
    upstream_family_map = UPSTREAM_FAMILY_MAP_PATH.read_text(encoding="utf-8")

    assert consumption_modes == {"caller_supplied_contract_payload"}
    assert "does not contain an active outbound HTTP client" in upstream_family_map


def test_manage_declaration_keeps_unapproved_market_data_on_the_watchlist() -> None:
    dependencies = _load_consumer_declaration()["dependencies"]
    product_names = {dependency["product_name"] for dependency in dependencies}
    readme = DECLARATION_README_PATH.read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.split())

    assert "MarketDataWindow" not in product_names
    assert "`MarketDataWindow`" in readme
    assert "not currently approved for `lotus-manage`" in normalized_readme


def test_manage_declaration_directory_contains_consumer_and_owned_product_contracts() -> None:
    declaration_paths = sorted(path.name for path in LOCAL_DECLARATION_DIR.glob("*.json"))

    assert declaration_paths == [
        "lotus-manage-consumers.v1.json",
        "lotus-manage-products.v1.json",
    ]


def test_manage_product_declaration_publishes_portfolio_action_register() -> None:
    payload = _load_product_declaration()
    products = payload["products"]

    assert payload["producer_repository"] == "lotus-manage"
    assert [product["product_name"] for product in products] == ["PortfolioActionRegister"]

    product = products[0]
    assert product["product_version"] == "v1"
    assert product["lifecycle_status"] == "active"
    assert product["approved_consumers"] == ["lotus-gateway"]
    assert product["lineage_policy"]["lineage_required"] is True
    assert product["lineage_policy"]["lineage_bundle_class_ref"] == "customer_lineage_summary"
