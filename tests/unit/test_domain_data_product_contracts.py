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


def test_manage_consumer_declaration_tracks_current_core_inputs() -> None:
    payload = _load_consumer_declaration()
    dependencies = payload["dependencies"]
    by_name = {dependency["product_name"]: dependency for dependency in dependencies}

    assert payload["consumer_repository"] == "lotus-manage"
    assert set(by_name) == {
        "PortfolioStateSnapshot",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
        "ExternalCurrencyExposure",
        "ExternalHedgePolicy",
        "ExternalFXForwardCurve",
        "ExternalHedgeExecutionReadiness",
        "RiskEventAffectedCohort",
        "TacticalHouseViewAffectedCohort",
        "PortfolioManagerBookMembership",
    }
    assert (
        by_name["PortfolioStateSnapshot"]["consumption_mode"] == "caller_supplied_contract_payload"
    )
    assert by_name["PortfolioStateSnapshot"]["failure_posture"] == "fail_closed"
    assert by_name["ClientRestrictionProfile"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ClientRestrictionProfile"]["failure_posture"] == "degrade_or_block"
    assert (
        by_name["SustainabilityPreferenceProfile"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert (
        by_name["SustainabilityPreferenceProfile"]["failure_posture"] == "degrade_or_pending_review"
    )
    assert by_name["ClientIncomeNeedsSchedule"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ClientIncomeNeedsSchedule"]["failure_posture"] == "degrade"
    assert by_name["LiquidityReserveRequirement"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["LiquidityReserveRequirement"]["failure_posture"] == "degrade_or_pending_review"
    assert by_name["PlannedWithdrawalSchedule"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["PlannedWithdrawalSchedule"]["failure_posture"] == "degrade_or_pending_review"
    assert by_name["ExternalCurrencyExposure"]["producer_repository"] == "lotus-core"
    assert by_name["ExternalCurrencyExposure"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ExternalCurrencyExposure"]["failure_posture"] == "fail_closed"
    assert by_name["ExternalHedgePolicy"]["producer_repository"] == "lotus-core"
    assert by_name["ExternalHedgePolicy"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ExternalHedgePolicy"]["failure_posture"] == "fail_closed"
    assert by_name["ExternalFXForwardCurve"]["producer_repository"] == "lotus-core"
    assert by_name["ExternalFXForwardCurve"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ExternalFXForwardCurve"]["failure_posture"] == "fail_closed"
    assert by_name["ExternalHedgeExecutionReadiness"]["producer_repository"] == "lotus-core"
    assert (
        by_name["ExternalHedgeExecutionReadiness"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert by_name["ExternalHedgeExecutionReadiness"]["failure_posture"] == "fail_closed"
    assert by_name["RiskEventAffectedCohort"]["producer_repository"] == "lotus-risk"
    assert by_name["RiskEventAffectedCohort"]["consumption_mode"] == "api_read"
    assert by_name["RiskEventAffectedCohort"]["failure_posture"] == "fail_closed"
    assert by_name["TacticalHouseViewAffectedCohort"]["producer_repository"] == "lotus-advise"
    assert by_name["TacticalHouseViewAffectedCohort"]["consumption_mode"] == "api_read"
    assert by_name["TacticalHouseViewAffectedCohort"]["failure_posture"] == "fail_closed"
    assert by_name["PortfolioManagerBookMembership"]["producer_repository"] == "lotus-core"
    assert by_name["PortfolioManagerBookMembership"]["consumption_mode"] == "api_read"
    assert by_name["PortfolioManagerBookMembership"]["failure_posture"] == "fail_closed"

    request_models = REQUEST_MODELS_PATH.read_text(encoding="utf-8")
    assert "portfolio_snapshot: PortfolioSnapshot" in request_models


def test_manage_declaration_limits_live_source_data_api_reads_to_approved_profiles() -> None:
    payload = _load_consumer_declaration()
    dependencies = payload["dependencies"]
    live_dependencies = {
        dependency["product_name"]
        for dependency in dependencies
        if dependency["consumption_mode"] == "stateful_core_sourcing"
    }
    upstream_family_map = UPSTREAM_FAMILY_MAP_PATH.read_text(encoding="utf-8")

    assert live_dependencies == {
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
        "ExternalCurrencyExposure",
        "ExternalHedgePolicy",
        "ExternalFXForwardCurve",
        "ExternalHedgeExecutionReadiness",
    }
    assert "modeled, feature-gated outbound resolver seam" in upstream_family_map
    assert (
        "RFC-087 rebaselines that seam to composed DPM source-data products" in upstream_family_map
    )
    assert "does not declare a promoted live" in upstream_family_map
    assert "execution-context product API-read dependency" in upstream_family_map


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


def test_manage_product_declaration_publishes_manage_owned_products() -> None:
    payload = _load_product_declaration()
    products = payload["products"]

    assert payload["producer_repository"] == "lotus-manage"
    by_name = {product["product_name"]: product for product in products}
    assert set(by_name) == {
        "PortfolioActionRegister",
        "BulkReviewCampaignMembership",
        "PmOperatingQualityScoreRun",
    }

    product = by_name["PortfolioActionRegister"]
    assert product["product_version"] == "v1"
    assert product["lifecycle_status"] == "active"
    assert product["approved_consumers"] == ["lotus-gateway"]
    assert product["serving_plane"] == "query_control_plane_service"
    assert product["current_routes"] == [
        "/api/v1/rebalance/supportability/summary",
        "/api/v1/rebalance/runs/{rebalance_run_id}/artifact",
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow",
        "/api/v1/rebalance/workflow/decisions",
    ]
    assert product["lineage_policy"]["lineage_required"] is True
    assert product["lineage_policy"]["lineage_bundle_class_ref"] == "customer_lineage_summary"

    campaign_membership = by_name["BulkReviewCampaignMembership"]
    assert campaign_membership["product_version"] == "v1"
    assert campaign_membership["lifecycle_status"] == "active"
    assert campaign_membership["request_scope"]["supports_bulk"] is True
    assert campaign_membership["approved_consumers"] == ["lotus-gateway"]
    assert campaign_membership["current_routes"] == [
        "/api/v1/rebalance/waves/campaign-definitions",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}",
        "/api/v1/rebalance/waves/preview",
        "/api/v1/rebalance/waves",
    ]
    assert campaign_membership["lineage_policy"]["lineage_required"] is True
    assert (
        "BulkReviewCampaignDefinition:v1"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )

    pm_quality = by_name["PmOperatingQualityScoreRun"]
    assert pm_quality["product_version"] == "v1"
    assert pm_quality["lifecycle_status"] == "active"
    assert pm_quality["request_scope"]["scope_level"] == "portfolio_manager_book"
    assert pm_quality["approved_consumers"] == ["lotus-gateway"]
    assert pm_quality["current_routes"] == [
        "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
        "/api/v1/rebalance/pm-operating-quality/policies",
        "/api/v1/rebalance/pm-operating-quality/policies/{policy_id}/versions/{policy_version}",
        "/api/v1/rebalance/pm-operating-quality/score-runs",
        "/api/v1/rebalance/pm-operating-quality/score-runs/{score_run_id}",
        "/api/v1/rebalance/portfolio-memory/{portfolio_id}",
    ]
    assert pm_quality["lineage_policy"]["lineage_required"] is True
    assert "portfolio_id" in pm_quality["identifier_refs"]
    assert (
        "bank approval and fairness-review evidence"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Portfolio memory projects bounded score-run lineage"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )


def test_manage_consumer_declaration_keeps_stateful_core_context_on_watchlist() -> None:
    payload = _load_consumer_declaration()
    dependency_names = {dependency["product_name"] for dependency in payload["dependencies"]}
    readme = DECLARATION_README_PATH.read_text(encoding="utf-8")

    assert "DpmExecutionContext" not in dependency_names
    assert "DpmCoreExecutionContext" not in dependency_names
    assert "New source products should be added here only after source-owner approval" in readme
