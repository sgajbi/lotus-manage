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
MESH_WIKI_PATH = ROOT / "wiki" / "Mesh-Data-Products.md"


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
        "DpmModelPortfolioTarget",
        "DiscretionaryMandateBinding",
        "InstrumentEligibilityProfile",
        "PortfolioTaxLotWindow",
        "MarketDataCoverageWindow",
        "DpmSourceReadiness",
        "BenchmarkAssignment",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "PortfolioCashflowProjection",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
        "ExternalCurrencyExposure",
        "ExternalHedgePolicy",
        "ExternalFXForwardCurve",
        "ExternalEligibleHedgeInstrument",
        "ExternalHedgeExecutionReadiness",
        "ExternalOrderExecutionAcknowledgement",
        "RiskEventAffectedCohort",
        "CioModelChangeAffectedCohort",
        "DpmPortfolioUniverseCandidate",
        "TacticalHouseViewAffectedCohort",
        "PortfolioManagerBookMembership",
        "TransactionCostCurve",
        "RegimeScenarioPackEvaluation",
        "MandateRiskHealthContext",
        "MandatePerformanceHealthContext",
    }
    assert (
        by_name["PortfolioStateSnapshot"]["consumption_mode"] == "caller_supplied_contract_payload"
    )
    assert by_name["PortfolioStateSnapshot"]["failure_posture"] == "fail_closed"
    assert by_name["DpmModelPortfolioTarget"]["producer_repository"] == "lotus-core"
    assert by_name["DpmModelPortfolioTarget"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["DpmModelPortfolioTarget"]["failure_posture"] == "fail_closed"
    assert by_name["DiscretionaryMandateBinding"]["producer_repository"] == "lotus-core"
    assert by_name["DiscretionaryMandateBinding"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["DiscretionaryMandateBinding"]["failure_posture"] == "fail_closed"
    assert by_name["InstrumentEligibilityProfile"]["producer_repository"] == "lotus-core"
    assert by_name["InstrumentEligibilityProfile"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["InstrumentEligibilityProfile"]["failure_posture"] == "fail_closed"
    assert by_name["PortfolioTaxLotWindow"]["producer_repository"] == "lotus-core"
    assert by_name["PortfolioTaxLotWindow"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["PortfolioTaxLotWindow"]["failure_posture"] == "degrade_or_block"
    assert by_name["MarketDataCoverageWindow"]["producer_repository"] == "lotus-core"
    assert by_name["MarketDataCoverageWindow"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["MarketDataCoverageWindow"]["failure_posture"] == "degrade_or_block"
    assert by_name["DpmSourceReadiness"]["producer_repository"] == "lotus-core"
    assert by_name["DpmSourceReadiness"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["DpmSourceReadiness"]["failure_posture"] == "fail_closed"
    assert by_name["BenchmarkAssignment"]["producer_repository"] == "lotus-core"
    assert by_name["BenchmarkAssignment"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["BenchmarkAssignment"]["failure_posture"] == "degrade_or_pending_review"
    assert "benchmark identity" in by_name["BenchmarkAssignment"]["business_purpose"]
    assert by_name["ClientRestrictionProfile"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["ClientRestrictionProfile"]["failure_posture"] == "degrade_or_block"
    assert (
        by_name["SustainabilityPreferenceProfile"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert (
        by_name["SustainabilityPreferenceProfile"]["failure_posture"] == "degrade_or_pending_review"
    )
    assert by_name["PortfolioCashflowProjection"]["producer_repository"] == "lotus-core"
    assert by_name["PortfolioCashflowProjection"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["PortfolioCashflowProjection"]["failure_posture"] == "degrade_or_pending_review"
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
    assert by_name["ExternalEligibleHedgeInstrument"]["producer_repository"] == "lotus-core"
    assert (
        by_name["ExternalEligibleHedgeInstrument"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert by_name["ExternalEligibleHedgeInstrument"]["failure_posture"] == "fail_closed"
    assert by_name["ExternalHedgeExecutionReadiness"]["producer_repository"] == "lotus-core"
    assert (
        by_name["ExternalHedgeExecutionReadiness"]["consumption_mode"] == "stateful_core_sourcing"
    )
    assert by_name["ExternalHedgeExecutionReadiness"]["failure_posture"] == "fail_closed"
    assert by_name["ExternalOrderExecutionAcknowledgement"]["producer_repository"] == "lotus-core"
    assert (
        by_name["ExternalOrderExecutionAcknowledgement"]["consumption_mode"]
        == "stateful_core_sourcing"
    )
    assert by_name["ExternalOrderExecutionAcknowledgement"]["failure_posture"] == "fail_closed"
    assert by_name["RiskEventAffectedCohort"]["producer_repository"] == "lotus-risk"
    assert by_name["RiskEventAffectedCohort"]["consumption_mode"] == "api_read"
    assert by_name["RiskEventAffectedCohort"]["failure_posture"] == "fail_closed"
    assert by_name["CioModelChangeAffectedCohort"]["producer_repository"] == "lotus-core"
    assert by_name["CioModelChangeAffectedCohort"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["CioModelChangeAffectedCohort"]["failure_posture"] == "fail_closed"
    assert by_name["DpmPortfolioUniverseCandidate"]["producer_repository"] == "lotus-core"
    assert by_name["DpmPortfolioUniverseCandidate"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["DpmPortfolioUniverseCandidate"]["failure_posture"] == "fail_closed"
    assert "content_hash" in by_name["DpmPortfolioUniverseCandidate"]["required_trust_metadata"]
    assert (
        "source_batch_fingerprint"
        not in by_name["DpmPortfolioUniverseCandidate"]["required_trust_metadata"]
    )
    assert (
        "relationship householding" in by_name["DpmPortfolioUniverseCandidate"]["business_purpose"]
    )
    assert by_name["TacticalHouseViewAffectedCohort"]["producer_repository"] == "lotus-advise"
    assert by_name["TacticalHouseViewAffectedCohort"]["consumption_mode"] == "api_read"
    assert by_name["TacticalHouseViewAffectedCohort"]["failure_posture"] == "fail_closed"
    assert by_name["PortfolioManagerBookMembership"]["producer_repository"] == "lotus-core"
    assert by_name["PortfolioManagerBookMembership"]["consumption_mode"] == "api_read"
    assert by_name["PortfolioManagerBookMembership"]["failure_posture"] == "fail_closed"
    assert by_name["TransactionCostCurve"]["producer_repository"] == "lotus-core"
    assert by_name["TransactionCostCurve"]["consumption_mode"] == "stateful_core_sourcing"
    assert by_name["TransactionCostCurve"]["failure_posture"] == "degrade"
    assert by_name["RegimeScenarioPackEvaluation"]["producer_repository"] == "lotus-risk"
    assert by_name["RegimeScenarioPackEvaluation"]["consumption_mode"] == "api_read"
    assert by_name["RegimeScenarioPackEvaluation"]["failure_posture"] == "degrade_or_pending_review"
    assert by_name["MandateRiskHealthContext"]["producer_repository"] == "lotus-risk"
    assert (
        by_name["MandateRiskHealthContext"]["consumption_mode"]
        == "caller_supplied_contract_payload"
    )
    assert by_name["MandateRiskHealthContext"]["failure_posture"] == ("degrade_or_pending_review")
    assert by_name["MandatePerformanceHealthContext"]["producer_repository"] == (
        "lotus-performance"
    )
    assert (
        by_name["MandatePerformanceHealthContext"]["consumption_mode"]
        == "caller_supplied_contract_payload"
    )
    assert by_name["MandatePerformanceHealthContext"]["failure_posture"] == (
        "degrade_or_pending_review"
    )

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
        "DpmModelPortfolioTarget",
        "DiscretionaryMandateBinding",
        "InstrumentEligibilityProfile",
        "PortfolioTaxLotWindow",
        "MarketDataCoverageWindow",
        "DpmSourceReadiness",
        "BenchmarkAssignment",
        "ClientRestrictionProfile",
        "SustainabilityPreferenceProfile",
        "PortfolioCashflowProjection",
        "ClientIncomeNeedsSchedule",
        "LiquidityReserveRequirement",
        "PlannedWithdrawalSchedule",
        "ExternalCurrencyExposure",
        "ExternalHedgePolicy",
        "ExternalFXForwardCurve",
        "ExternalEligibleHedgeInstrument",
        "ExternalHedgeExecutionReadiness",
        "ExternalOrderExecutionAcknowledgement",
        "CioModelChangeAffectedCohort",
        "DpmPortfolioUniverseCandidate",
        "TransactionCostCurve",
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
    assert "`BenchmarkAssignment:v1` is approved for bounded `lotus-manage`" in readme


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
    assert product["approved_consumers"] == ["lotus-gateway", "lotus-idea"]
    mesh_wiki = MESH_WIKI_PATH.read_text(encoding="utf-8")
    normalized_mesh_wiki = " ".join(mesh_wiki.split())
    assert "Approved consumers: `lotus-gateway`, `lotus-idea`" in mesh_wiki
    assert "it does not own rebalance execution" in normalized_mesh_wiki
    assert product["serving_plane"] == "query_control_plane_service"
    assert product["current_routes"] == [
        "/api/v1/rebalance/supportability/summary",
        "/api/v1/rebalance/runs/{rebalance_run_id}/artifact",
        "/api/v1/rebalance/runs/{rebalance_run_id}/workflow",
        "/api/v1/rebalance/workflow/decisions",
    ]
    route_foundations = product["route_foundations"]
    assert route_foundations == [
        {
            "route": "POST /api/v1/rebalance/idea-action-intake",
            "contract_ref": "contracts/idea-action-intake/lotus-manage-idea-action-intake.v1.json",
            "supportability_status": "not_certified",
            "supported_feature_promoted": False,
            "route_existence_proven": True,
            "runtime_action_receipt_proven": True,
            "principal_capability": "manage.idea_action_intake.accept",
            "action_register_created": False,
            "rebalance_execution_authority_granted": False,
            "order_created": False,
            "client_publication_authorized": False,
            "certification_blockers": [
                "rebalance_execution_authority_remains_lotus_manage",
                "action_register_persistence_not_certified",
                "oms_execution_not_certified",
                "client_publication_authority_blocked",
            ],
        }
    ]
    assert all(
        foundation["route"].removeprefix("POST ") not in product["current_routes"]
        for foundation in route_foundations
        if foundation["supportability_status"] == "not_certified"
        or foundation["supported_feature_promoted"] is False
        or foundation["certification_blockers"]
    )
    freshness_description = product["freshness_policy"]["max_allowed_age_description"]
    assert "Certified PortfolioActionRegister routes exclude" in freshness_description
    assert "not-certified route foundation" in freshness_description
    assert "handoff receipt evidence" in freshness_description
    assert "does not create action-register records" in freshness_description
    assert "grant rebalance authority" in freshness_description
    assert "create orders" in freshness_description
    assert "authorize client publication" in freshness_description
    assert "promote a supported feature" in freshness_description
    assert product["lineage_policy"]["lineage_required"] is True
    assert product["lineage_policy"]["lineage_bundle_class_ref"] == "customer_lineage_summary"

    campaign_membership = by_name["BulkReviewCampaignMembership"]
    assert campaign_membership["product_version"] == "v1"
    assert campaign_membership["lifecycle_status"] == "active"
    assert campaign_membership["request_scope"]["supports_bulk"] is True
    assert campaign_membership["approved_consumers"] == ["lotus-gateway"]
    assert "tenant_id" in campaign_membership["required_trust_metadata"]
    assert "tenant_id" in campaign_membership["identifier_refs"]
    assert campaign_membership["mesh_maturity_posture"] == {
        "maturity_state": "deferred",
        "maturity_wave": "future_wave",
        "platform_maturity_source": "lotus-platform/generated/enterprise-mesh-maturity-matrix.md",
        "consumer_interpretation": "catalog_visible_deferred_product_not_customer_reliance_ready",
        "missing_policy_refs": [
            "platform-contracts/mesh-slo/lotus-manage-bulk-review-campaign-membership.slo.v1.json",
            "platform-contracts/mesh-access/lotus-manage-bulk-review-campaign-membership.access.v1.json",
            (
                "platform-contracts/mesh-evidence/"
                "lotus-manage-bulk-review-campaign-membership.evidence-pack-policy.v1.json"
            ),
        ],
    }
    assert campaign_membership["current_routes"] == [
        "/api/v1/rebalance/waves/campaign-definitions",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch-package",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/launch",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/approval-decisions",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-actions",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/assignment-tasks/{task_ref}/transitions",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/maker-checker-controls",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/workflow-overview",
        "/api/v1/rebalance/waves/campaign-definitions/{campaign_id}/versions/{campaign_version}/preview-readiness",
        "/api/v1/rebalance/waves/campaign-operating-queue",
        "/api/v1/rebalance/waves/campaign-approval-inbox",
        "/api/v1/rebalance/waves/campaign-workflow-board",
        "/api/v1/rebalance/waves/campaign-assignment-plan",
        "/api/v1/rebalance/waves/campaign-workflow-automation",
        "/api/v1/rebalance/waves/preview",
        "/api/v1/rebalance/waves",
    ]
    assert campaign_membership["lineage_policy"]["lineage_required"] is True
    assert (
        "BulkReviewCampaignDefinition:v1"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "tenant-scoped source-backed candidate set"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "approved source contracts"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "READY supportability"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "required content hash or approved batch or definition fingerprint coverage"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "catalog-visible but mesh-deferred/future-wave"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "platform SLO, access, evidence-pack, and runtime certification evidence"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Preview-readiness evaluates persisted definition lifecycle"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Launch packages provide a bounded preview/create request draft"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Workflow overview composes discovery, preview-readiness, lifecycle-event, launch-history"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "The approval inbox classifies persisted definitions into approval-complete"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Approval decisions provide append-only campaign approval posture evidence"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "The workflow board composes the existing operating queue and approval inbox"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "The assignment plan derives read-only actor routing"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "The workflow automation projection composes assignment-plan and assignment-task state"
        in (campaign_membership["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Assignment actions provide append-only assignment"
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
        "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
        "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
        "/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_analysis_id}",
        "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
        "/api/v1/rebalance/pm-operating-quality/review-actions",
        "/api/v1/rebalance/pm-operating-quality/review-actions/{review_action_id}",
        "/api/v1/rebalance/pm-operating-quality/summary-invocations/preview",
        "/api/v1/rebalance/pm-operating-quality/summary-invocations",
        "/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_invocation_id}",
        "/api/v1/rebalance/portfolio-memory/search",
        "/api/v1/rebalance/portfolio-memory/{portfolio_id}",
    ]
    assert pm_quality["lineage_policy"]["lineage_required"] is True
    assert "tenant_id" in pm_quality["required_trust_metadata"]
    assert "tenant_id" in pm_quality["identifier_refs"]
    assert "portfolio_id" in pm_quality["identifier_refs"]
    assert (
        "bank approval and fairness-review evidence"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Portfolio memory projects bounded score-run lineage"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "Review actions are immutable tenant-scoped ledger rows"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "PM_QUALITY_SUMMARY_TEXT_BOUNDARY"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )
    assert (
        "without storing or exposing generated summary text"
        in (pm_quality["freshness_policy"]["max_allowed_age_description"])
    )


def test_manage_consumer_declaration_keeps_stateful_core_context_on_watchlist() -> None:
    payload = _load_consumer_declaration()
    dependency_names = {dependency["product_name"] for dependency in payload["dependencies"]}
    readme = DECLARATION_README_PATH.read_text(encoding="utf-8")

    assert "DpmExecutionContext" not in dependency_names
    assert "DpmCoreExecutionContext" not in dependency_names
    assert "New source products should be added here only after source-owner approval" in readme
