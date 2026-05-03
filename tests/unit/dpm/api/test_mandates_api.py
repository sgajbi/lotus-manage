from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import get_mandate_repository
from src.api.main import app
import src.api.routers.mandates as mandates_router
from src.api.routers.mandates import get_core_resolver_client
from src.core.dpm_source_context import (
    DpmCoreMandateBindingResponse,
    DpmCoreMarketDataCoverageWindowResponse,
    DpmCoreModelPortfolioTargetResponse,
)
from src.core.mandates import DpmMandateDigitalTwin, DpmMandateHealthInput
from src.infrastructure.core_sourcing import DpmCoreResolverError, DpmCoreResolverUnavailableError
from src.infrastructure.mandates import InMemoryDpmMandateRepository


AS_OF = date(2026, 5, 3)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
MANDATE_ID = "MANDATE_PB_SG_GLOBAL_BAL_001"


class FakeCoreResolver:
    def __init__(self, *, unavailable: bool = False, incomplete: bool = False) -> None:
        self.unavailable = unavailable
        self.incomplete = incomplete
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def resolve_mandate_binding(self, **kwargs: Any) -> DpmCoreMandateBindingResponse:
        self.calls.append(("mandate", kwargs))
        if self.unavailable:
            raise DpmCoreResolverUnavailableError("DPM_CORE_MANDATE_BINDING_UNAVAILABLE")
        if self.incomplete:
            raise DpmCoreResolverError("DPM_CORE_MANDATE_BINDING_INCOMPLETE")
        return DpmCoreMandateBindingResponse.model_validate(_mandate_binding_payload())

    def resolve_model_portfolio_targets(self, **kwargs: Any) -> DpmCoreModelPortfolioTargetResponse:
        self.calls.append(("model_targets", kwargs))
        return DpmCoreModelPortfolioTargetResponse.model_validate(_model_targets_payload())

    def resolve_market_data_coverage(
        self, **kwargs: Any
    ) -> DpmCoreMarketDataCoverageWindowResponse:
        self.calls.append(("market_data", kwargs))
        return DpmCoreMarketDataCoverageWindowResponse.model_validate(_market_data_payload())


def _mandate_binding_payload(*, binding_version: int = 3) -> dict[str, Any]:
    return {
        "product_name": "DiscretionaryMandateBinding",
        "product_version": "v1",
        "portfolio_id": PORTFOLIO_ID,
        "mandate_id": MANDATE_ID,
        "client_id": "CIF_SG_000184",
        "mandate_type": "discretionary",
        "discretionary_authority_status": "active",
        "booking_center_code": "Singapore",
        "jurisdiction_code": "SG",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "policy_pack_id": "POLICY_DPM_SG_BALANCED_V1",
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "leverage_allowed": False,
        "tax_awareness_allowed": True,
        "settlement_awareness_required": True,
        "rebalance_frequency": "quarterly",
        "rebalance_bands": {
            "default_band": "0.0250000000",
            "cash_reserve_weight": "0.0200000000",
        },
        "effective_from": "2026-04-01",
        "binding_version": binding_version,
        "supportability": {
            "state": "READY",
            "reason": "MANDATE_BINDING_READY",
            "missing_data_families": [],
        },
        "lineage": {"contract_version": "DiscretionaryMandateBinding:v1"},
        "data_quality_status": "READY",
        "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
    }


def _model_targets_payload() -> dict[str, Any]:
    return {
        "product_name": "DpmModelPortfolioTarget",
        "product_version": "v1",
        "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
        "model_portfolio_version": "2026.04",
        "as_of_date": "2026-05-03",
        "display_name": "Singapore Global Balanced DPM Model",
        "base_currency": "SGD",
        "risk_profile": "balanced",
        "mandate_type": "discretionary",
        "approval_status": "approved",
        "effective_from": "2026-04-01",
        "targets": [
            {
                "instrument_id": "EQ_US_AAPL",
                "target_weight": "0.6000000000",
                "min_weight": "0.5500000000",
                "max_weight": "0.6500000000",
                "target_status": "active",
                "quality_status": "accepted",
            },
            {
                "instrument_id": "FI_US_TREASURY_10Y",
                "target_weight": "0.4000000000",
                "min_weight": "0.3500000000",
                "max_weight": "0.4500000000",
                "target_status": "active",
                "quality_status": "accepted",
            },
        ],
        "supportability": {
            "state": "READY",
            "reason": "MODEL_TARGETS_READY",
            "target_count": 2,
            "total_target_weight": "1.0000000000",
        },
        "lineage": {"contract_version": "DpmModelPortfolioTarget:v1"},
        "data_quality_status": "READY",
        "latest_evidence_timestamp": "2026-05-03T01:00:00Z",
    }


def _market_data_payload() -> dict[str, Any]:
    return {
        "product_name": "MarketDataCoverageWindow",
        "product_version": "v1",
        "as_of_date": "2026-05-03",
        "valuation_currency": "SGD",
        "price_coverage": [],
        "fx_coverage": [],
        "supportability": {
            "state": "READY",
            "reason": "MARKET_DATA_READY",
            "requested_price_count": 2,
            "resolved_price_count": 2,
            "requested_fx_count": 0,
            "resolved_fx_count": 0,
        },
    }


def _twin(
    *, version: str = "3", turnover_budget: Decimal = Decimal("0.15")
) -> DpmMandateDigitalTwin:
    twin = DpmMandateDigitalTwin.model_validate(
        {
            "mandate_id": MANDATE_ID,
            "portfolio_id": PORTFOLIO_ID,
            "mandate_version": version,
            "as_of_date": AS_OF,
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "model_portfolio_version": "2026.04",
            "constraints": {
                "cash_band_min_weight": "0.02",
                "cash_band_max_weight": "0.10",
                "turnover_budget": turnover_budget,
            },
            "review_policy": {"review_frequency": "QUARTERLY"},
        }
    )
    return twin


def _client(
    repository: InMemoryDpmMandateRepository,
    resolver: FakeCoreResolver | None = None,
) -> TestClient:
    app.dependency_overrides[get_mandate_repository] = lambda: repository
    if resolver is not None:
        app.dependency_overrides[get_core_resolver_client] = lambda: resolver
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_refresh_from_core_sources_persists_and_returns_mandate_health() -> None:
    repository = InMemoryDpmMandateRepository()
    resolver = FakeCoreResolver()

    with _client(repository, resolver) as client:
        response = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/refresh-from-core",
            headers={"X-Correlation-Id": "corr_test_mandate"},
            json={
                "portfolio_id": PORTFOLIO_ID,
                "as_of_date": "2026-05-03",
                "tenant_id": "default",
                "reference_currency": "SGD",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "DpmMandateRefreshFromCoreResponse:v1"
    assert body["mandate"]["mandate_id"] == MANDATE_ID
    assert body["mandate"]["model_portfolio_version"] == "2026.04"
    assert body["health_snapshot"]["portfolio_id"] == PORTFOLIO_ID
    assert "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED" in body["field_gap_codes"]
    assert [name for name, _ in resolver.calls] == ["mandate", "model_targets", "market_data"]
    assert repository.get_latest_mandate(mandate_id=MANDATE_ID) is not None


def test_read_mandate_by_portfolio_and_by_id_use_persisted_state() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin(version="3"))

    with _client(repository) as client:
        by_portfolio = client.get(f"/api/v1/mandates/by-portfolio/{PORTFOLIO_ID}")
        by_id = client.get(f"/api/v1/mandates/{MANDATE_ID}")

    assert by_portfolio.status_code == 200
    assert by_portfolio.json()["mandate_version"] == "3"
    assert by_id.status_code == 200
    assert by_id.json()["portfolio_id"] == PORTFOLIO_ID


def test_missing_mandate_by_portfolio_returns_404() -> None:
    with _client(InMemoryDpmMandateRepository()) as client:
        response = client.get(f"/api/v1/mandates/by-portfolio/{PORTFOLIO_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_MANDATE_NOT_FOUND"


def test_mandate_versions_are_returned_newest_first() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin(version="2"))
    repository.save_mandate_snapshot(_twin(version="3"))

    with _client(repository) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}/versions")

    assert response.status_code == 200
    assert [row["mandate_version"] for row in response.json()] == ["3", "2"]


def test_missing_mandate_versions_return_404() -> None:
    with _client(InMemoryDpmMandateRepository()) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}/versions")

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_MANDATE_NOT_FOUND"


def test_mandate_diff_identifies_material_constraint_changes() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin(version="2", turnover_budget=Decimal("0.10")))
    repository.save_mandate_snapshot(_twin(version="3", turnover_budget=Decimal("0.15")))

    with _client(repository) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff")

    assert response.status_code == 200
    body = response.json()
    assert body["from_version"] == "2"
    assert body["to_version"] == "3"
    assert {
        "field_path": "constraints.turnover_budget",
        "previous_value": "0.10",
        "current_value": "0.15",
        "materiality": "HIGH",
    } in body["changed_fields"]


def test_mandate_diff_with_explicit_versions_and_missing_version_errors() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin(version="2", turnover_budget=Decimal("0.10")))
    repository.save_mandate_snapshot(_twin(version="3", turnover_budget=Decimal("0.15")))

    with _client(repository) as client:
        explicit = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff?from_version=2&to_version=3")
        missing = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff?from_version=1&to_version=3")
        partial = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff?from_version=2")

    assert explicit.status_code == 200
    assert explicit.json()["from_version"] == "2"
    assert missing.status_code == 409
    assert missing.json()["detail"] == "DPM_MANDATE_DIFF_VERSION_NOT_FOUND"
    assert partial.status_code == 409
    assert partial.json()["detail"] == "DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS"


def test_missing_mandate_diff_returns_404() -> None:
    with _client(InMemoryDpmMandateRepository()) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff")

    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_MANDATE_NOT_FOUND"


def test_mandate_diff_requires_two_versions() -> None:
    repository = InMemoryDpmMandateRepository()
    repository.save_mandate_snapshot(_twin(version="3"))

    with _client(repository) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}/diff")

    assert response.status_code == 409
    assert response.json()["detail"] == "DPM_MANDATE_DIFF_REQUIRES_TWO_VERSIONS"


def test_refresh_maps_core_unavailable_to_503() -> None:
    with _client(InMemoryDpmMandateRepository(), FakeCoreResolver(unavailable=True)) as client:
        response = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/refresh-from-core",
            json={"portfolio_id": PORTFOLIO_ID, "as_of_date": "2026-05-03"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "DPM_MANDATE_SOURCE_UNAVAILABLE"


def test_refresh_maps_core_incomplete_to_424() -> None:
    with _client(InMemoryDpmMandateRepository(), FakeCoreResolver(incomplete=True)) as client:
        response = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/refresh-from-core",
            json={"portfolio_id": PORTFOLIO_ID, "as_of_date": "2026-05-03"},
        )

    assert response.status_code == 424
    assert response.json()["detail"] == "DPM_MANDATE_SOURCE_INCOMPLETE"


def test_missing_mandate_returns_404() -> None:
    with _client(InMemoryDpmMandateRepository()) as client:
        response = client.get(f"/api/v1/mandates/{MANDATE_ID}")

    assert response.status_code == 404


def test_mandate_openapi_paths_are_documented() -> None:
    schema = app.openapi()
    expected_paths = {
        "/api/v1/mandates/by-portfolio/{portfolio_id}",
        "/api/v1/mandates/{mandate_id}",
        "/api/v1/mandates/{mandate_id}/versions",
        "/api/v1/mandates/{mandate_id}/diff",
        "/api/v1/mandates/{mandate_id}/refresh-from-core",
    }

    for path in expected_paths:
        operation = next(iter(schema["paths"][path].values()))
        assert operation["summary"]
        assert operation["description"]
        assert operation["tags"] == ["lotus-manage Mandates"]
        success_response = operation["responses"]["200"]
        assert "application/json" in success_response["content"]


def test_refresh_accepts_validation_errors_as_422() -> None:
    with _client(InMemoryDpmMandateRepository(), FakeCoreResolver()) as client:
        response = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/refresh-from-core",
            json={"portfolio_id": PORTFOLIO_ID, "as_of_date": "not-a-date"},
        )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_no_legacy_mandate_endpoint_alias_exists() -> None:
    with _client(InMemoryDpmMandateRepository()) as client:
        response = client.get(f"/mandates/{MANDATE_ID}")

    assert response.status_code == 404


def test_response_contract_is_json_serializable() -> None:
    repository = InMemoryDpmMandateRepository()
    resolver = FakeCoreResolver()

    with _client(repository, resolver) as client:
        response = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/refresh-from-core",
            json={"portfolio_id": PORTFOLIO_ID, "as_of_date": "2026-05-03"},
        )

    httpx.Response(200, json=response.json())


def test_health_recalculate_and_read_latest_health_snapshot() -> None:
    repository = InMemoryDpmMandateRepository()
    twin = _twin()
    health_input = DpmMandateHealthInput(
        twin=twin,
        current_weights={"EQ_US_AAPL": Decimal("0.60")},
        target_weights={"EQ_US_AAPL": Decimal("0.60")},
        cash_weight=Decimal("0.05"),
    )

    with _client(repository) as client:
        recalculated = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/health/recalculate",
            json=health_input.model_dump(mode="json"),
        )
        latest = client.get(f"/api/v1/mandates/{MANDATE_ID}/health")

    assert recalculated.status_code == 200
    assert recalculated.json()["health_state"] == "READY"
    assert latest.status_code == 200
    assert latest.json()["health_snapshot_id"] == recalculated.json()["health_snapshot_id"]


def test_health_read_and_recalculate_error_mapping() -> None:
    wrong_twin = _twin().model_copy(update={"mandate_id": "OTHER_MANDATE"})
    health_input = DpmMandateHealthInput(twin=wrong_twin, cash_weight=Decimal("0.05"))

    with _client(InMemoryDpmMandateRepository()) as client:
        missing = client.get(f"/api/v1/mandates/{MANDATE_ID}/health")
        mismatch = client.post(
            f"/api/v1/mandates/{MANDATE_ID}/health/recalculate",
            json=health_input.model_dump(mode="json"),
        )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_MANDATE_HEALTH_NOT_FOUND"
    assert mismatch.status_code == 424
    assert mismatch.json()["detail"] == "DPM_MANDATE_HEALTH_INPUT_MISMATCH"


def test_default_mandate_repository_dependency_is_available() -> None:
    assert get_mandate_repository() is not None


def test_default_core_resolver_dependency_delegates_to_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = FakeCoreResolver()
    monkeypatch.setattr(mandates_router, "build_core_resolver_client", lambda: resolver)

    result: object = get_core_resolver_client()
    assert result is resolver
