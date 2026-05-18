from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.core.outcomes import (
    DpmOutcomeDimensionInput,
    DpmOutcomeMetricValue,
    DpmOutcomeSourceFreshness,
    DpmOutcomeSourceRef,
    DpmOutcomeSupportability,
    DpmOutcomeTolerance,
    compare_outcome_dimension,
)
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.unit.infrastructure.test_outcome_review_repository import _review


def _request_payload() -> dict:
    review = _review()
    return {
        "expected_snapshot": review.expected_snapshot.model_dump(mode="json"),
        "realized_snapshot": review.realized_snapshot.model_dump(mode="json"),
        "dimension_configs": [
            {
                "dimension": "DRIFT_REDUCTION",
                "tolerance": {"soft": "0.0025", "hard": "0.0100"},
                "materiality": "0.0050",
                "direction": "LOWER_IS_BETTER",
            }
        ],
        "actor_id": "pm_001",
    }


def _refresh_payload() -> dict:
    payload = _request_payload()
    return {
        "actor_id": "system",
        "realized_snapshot": payload["realized_snapshot"],
        "dimension_configs": payload["dimension_configs"],
    }


def _override_repositories(repository: InMemoryDpmOutcomeReviewRepository) -> None:
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    app.dependency_overrides[get_proof_pack_repository] = lambda: InMemoryDpmProofPackRepository()
    app.dependency_overrides[get_wave_repository] = lambda: InMemoryDpmWaveRepository()
    app.dependency_overrides[get_mandate_repository] = lambda: InMemoryDpmMandateRepository()


def test_outcome_review_api_preview_create_lookup_supportability_and_events() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    _override_repositories(repository)
    try:
        with TestClient(app) as client:
            preview = client.post(
                "/api/v1/rebalance/outcome-reviews/preview", json=_request_payload()
            )
            assert preview.status_code == 200
            assert preview.json()["comparison"]["state"] == "READY"

            created = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-001", "X-Correlation-Id": "corr-001"},
            )
            assert created.status_code == 200
            outcome_review = created.json()["outcome_review"]
            outcome_review_id = outcome_review["outcome_review_id"]
            assert outcome_review["state"] == "READY"
            assert outcome_review["content_hash"].startswith("sha256:")

            replay = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-001", "X-Correlation-Id": "corr-001"},
            )
            assert replay.status_code == 200
            assert replay.json()["outcome_review"]["outcome_review_id"] == outcome_review_id

            conflicting_payload = _request_payload()
            conflicting_payload["realized_snapshot"]["realized_values"]["DRIFT_REDUCTION"][
                "value"
            ] = "0.0200"
            conflict = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=conflicting_payload,
                headers={"Idempotency-Key": "outcome-idem-001", "X-Correlation-Id": "corr-001"},
            )
            assert conflict.status_code == 409
            assert conflict.json()["detail"] == "DPM_OUTCOME_REVIEW_IDEMPOTENCY_CONFLICT"

            lookup = client.get(f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}")
            assert lookup.status_code == 200
            supportability = client.get(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability"
            )
            assert supportability.status_code == 200
            supportability_body = supportability.json()
            assert supportability_body["state"] == "READY"
            assert supportability_body["source_owners"] == ["lotus-manage"]
            assert supportability_body["dimension_state_counts"] == {"READY": 1}
            assert supportability_body["blocked_dimension_count"] == 0
            assert supportability_body["remediation_routes"] == []

            report = client.get(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input"
            )
            assert report.status_code == 200
            report_input = report.json()
            assert report_input["outcome_review_id"] == outcome_review_id
            assert report_input["outcome_review_content_hash"] == outcome_review["content_hash"]
            assert report_input["content_hash"].startswith("sha256:")
            assert report_input["evidence_ref"]["source_type"] == "DPM_OUTCOME_REPORT_INPUT"
            assert report_input["external_execution_boundary"]["boundary_id"] == (
                "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"
            )
            assert report_input["client_communication_boundary"]["boundary_id"] == (
                "DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY"
            )
            assert (
                report_input["client_communication_boundary"]["client_communication_projected"]
                is False
            )
            assert report_input["portfolio_memory_context"]["portfolio_id"] == (
                "PB_SG_GLOBAL_BAL_001"
            )
            assert any(
                event["event_type"] == "OUTCOME_REVIEW_CREATED"
                for event in report_input["portfolio_memory_context"]["event_refs"]
            )

            ai = client.get(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input"
            )
            assert ai.status_code == 200
            ai_input = ai.json()
            assert ai_input["outcome_review_id"] == outcome_review_id
            assert ai_input["outcome_review_content_hash"] == outcome_review["content_hash"]
            assert ai_input["content_hash"].startswith("sha256:")
            assert ai_input["evidence_ref"]["source_type"] == "DPM_OUTCOME_AI_EVIDENCE_INPUT"
            assert ai_input["external_execution_boundary"]["boundary_id"] == (
                "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"
            )
            assert ai_input["client_communication_boundary"]["boundary_id"] == (
                "DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY"
            )
            assert "place_orders" in ai_input["forbidden_actions"]
            assert "score_portfolio_manager" in ai_input["forbidden_actions"]

            refresh = client.post(
                f"/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources",
                json=_refresh_payload(),
            )
            assert refresh.status_code == 200
            assert refresh.json()["event"]["event_type"] == "OUTCOME_REVIEW_SOURCE_REFRESHED"
            assert refresh.json()["comparison"]["state"] == "READY"
    finally:
        app.dependency_overrides.clear()


def test_outcome_review_openapi_contract_is_grouped_and_guided() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()

    expected_paths = [
        "/api/v1/rebalance/outcome-reviews/preview",
        "/api/v1/rebalance/outcome-reviews",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input",
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input",
        "/api/v1/rebalance/runs/{rebalance_run_id}/outcome-review",
        "/api/v1/rebalance/waves/{wave_id}/outcome-reviews",
    ]
    for path in expected_paths:
        assert path in schema["paths"]

    preview = schema["paths"]["/api/v1/rebalance/outcome-reviews/preview"]["post"]
    assert preview["tags"] == ["lotus-manage Outcome Reviews"]
    assert all(marker in preview["description"] for marker in ["What:", "When:", "How:"])
    assert "requestBody" in preview
    assert "200" in preview["responses"]

    create = schema["paths"]["/api/v1/rebalance/outcome-reviews"]["post"]
    assert create["tags"] == ["lotus-manage Outcome Reviews"]
    assert "Idempotency-Key" in str(create["parameters"])
    assert "same-key changed evidence" in create["description"]

    refresh = schema["paths"][
        "/api/v1/rebalance/outcome-reviews/{outcome_review_id}/refresh-sources"
    ]["post"]
    assert refresh["tags"] == ["lotus-manage Outcome Reviews"]
    assert all(marker in refresh["description"] for marker in ["What:", "When:", "How:"])
    assert "requestBody" in refresh
    assert "200" in refresh["responses"]

    report = schema["paths"]["/api/v1/rebalance/outcome-reviews/{outcome_review_id}/report-input"][
        "get"
    ]
    assert all(marker in report["description"] for marker in ["What:", "When:", "How:"])
    assert "DpmOutcomeClientCommunicationBoundaryEvidence" in schema["components"]["schemas"]
    report_schema = schema["components"]["schemas"]["DpmOutcomeReportInput"]
    assert "client_communication_boundary" in report_schema["properties"]
    ai = schema["paths"]["/api/v1/rebalance/outcome-reviews/{outcome_review_id}/ai-evidence-input"][
        "get"
    ]
    assert all(marker in ai["description"] for marker in ["What:", "When:", "How:"])
    ai_schema = schema["components"]["schemas"]["DpmOutcomeAiEvidenceInput"]
    assert "client_communication_boundary" in ai_schema["properties"]

    guided_get_paths = [
        ("/api/v1/rebalance/outcome-reviews", "get"),
        ("/api/v1/rebalance/outcome-reviews/{outcome_review_id}", "get"),
        ("/api/v1/rebalance/outcome-reviews/{outcome_review_id}/supportability", "get"),
        ("/api/v1/rebalance/runs/{rebalance_run_id}/outcome-review", "get"),
        ("/api/v1/rebalance/waves/{wave_id}/outcome-reviews", "get"),
    ]
    for path, method in guided_get_paths:
        operation = schema["paths"][path][method]
        assert all(marker in operation["description"] for marker in ["What:", "When:", "How:"])


def test_outcome_review_api_search_run_wave_and_missing_dimension_guardrail() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    _override_repositories(repository)
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=_request_payload(),
                headers={"Idempotency-Key": "outcome-idem-002"},
            )
            assert created.status_code == 200
            review_id = created.json()["outcome_review"]["outcome_review_id"]

            search = client.get(
                "/api/v1/rebalance/outcome-reviews",
                params={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
            )
            assert search.status_code == 200
            assert search.json()["items"][0]["outcome_review_id"] == review_id

            invalid_state = client.get(
                "/api/v1/rebalance/outcome-reviews",
                params={"state": "NOT_A_REVIEW_STATE"},
            )
            assert invalid_state.status_code == 422

            by_run = client.get("/api/v1/rebalance/runs/rr_001/outcome-review")
            assert by_run.status_code == 200
            by_wave = client.get("/api/v1/rebalance/waves/dwv_001/outcome-reviews")
            assert by_wave.status_code == 200
            assert by_wave.json()["items"][0]["outcome_review_id"] == review_id

            bad_payload = _request_payload()
            bad_payload["dimension_configs"][0]["dimension"] = "PERFORMANCE"
            bad = client.post("/api/v1/rebalance/outcome-reviews/preview", json=bad_payload)
            assert bad.status_code == 422
            assert "DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING" in bad.text
            bad_create = client.post(
                "/api/v1/rebalance/outcome-reviews",
                json=bad_payload,
                headers={"Idempotency-Key": "outcome-idem-bad"},
            )
            assert bad_create.status_code == 422
            assert "DPM_OUTCOME_DIMENSION_EVIDENCE_MISSING" in bad_create.text

            for path in [
                "/api/v1/rebalance/outcome-reviews/missing",
                "/api/v1/rebalance/outcome-reviews/missing/supportability",
                "/api/v1/rebalance/outcome-reviews/missing/report-input",
                "/api/v1/rebalance/outcome-reviews/missing/ai-evidence-input",
                "/api/v1/rebalance/runs/missing/outcome-review",
            ]:
                missing = client.get(path)
                assert missing.status_code == 404
                assert missing.json()["detail"] == "OUTCOME_REVIEW_NOT_FOUND"

            missing_refresh = client.post(
                "/api/v1/rebalance/outcome-reviews/missing/refresh-sources",
                json=_refresh_payload(),
            )
            assert missing_refresh.status_code == 404

            invalid_refresh_payload = _refresh_payload()
            invalid_refresh_payload["dimension_configs"][0]["dimension"] = "PERFORMANCE"
            invalid_refresh = client.post(
                f"/api/v1/rebalance/outcome-reviews/{review_id}/refresh-sources",
                json=invalid_refresh_payload,
            )
            assert invalid_refresh.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_outcome_review_supportability_routes_source_owner_remediation() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    repository.save_outcome_review(
        review=_review(
            state="DEGRADED",
            content_hash="sha256:degraded",
            idempotency_key="degraded-idem",
        ).model_copy(
            update={
                "supportability": _review().supportability.model_copy(
                    update={
                        "state": "DEGRADED",
                        "reason_codes": [
                            "RISK_SOURCE_UNAVAILABLE",
                            "PERFORMANCE_SOURCE_UNAVAILABLE",
                            "EXECUTION_EVIDENCE_BLOCKED",
                            "FX_SOURCE_STALE",
                        ],
                    }
                )
            }
        ),
        retention_expires_at=None,
    )
    app.dependency_overrides[get_outcome_review_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/rebalance/outcome-reviews/dor_001/supportability")

        assert response.status_code == 200
        assert response.json()["remediation_routes"] == [
            "execution-owner:certify-fill-and-order-evidence",
            "lotus-performance:refresh-post-trade-performance-source",
            "lotus-risk:refresh-post-trade-risk-source",
            "source-owner:refresh-realized-outcome-source",
        ]
    finally:
        app.dependency_overrides.clear()


def test_outcome_review_supportability_exposes_external_execution_boundary() -> None:
    repository = InMemoryDpmOutcomeReviewRepository()
    base_review = _review()
    source_ref = DpmOutcomeSourceRef(
        source_system="lotus-core",
        source_type="EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT",
        source_id="ExternalOrderExecutionAcknowledgement:v1:PB_SG_GLOBAL_BAL_001:2026-05-06",
        source_version="rfc_042_external_order_execution_acknowledgement_v1",
        content_hash="sha256:external-acknowledgement",
    )
    expected = DpmOutcomeMetricValue(
        value=Decimal("1"),
        unit="acknowledgements",
        source_refs=[source_ref],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at="2026-05-06T01:10:00Z",
            as_of_date="2026-05-06",
            freshness_state="CURRENT",
        ),
        supportability=DpmOutcomeSupportability(
            state="READY",
            reason_codes=["EXPECTED_EXECUTION_INTENT_READY"],
        ),
    )
    realized = DpmOutcomeMetricValue(
        value=Decimal("0"),
        unit="acknowledgements",
        source_refs=[source_ref],
        source_freshness=DpmOutcomeSourceFreshness(
            observed_at="2026-05-06T01:15:00Z",
            as_of_date="2026-05-06",
            freshness_state="CURRENT",
        ),
        supportability=DpmOutcomeSupportability(
            state="BLOCKED",
            reason_codes=[
                "CORE_EXECUTION_ACKNOWLEDGEMENT_FAIL_CLOSED",
                "EXECUTION_ACKNOWLEDGEMENT_SUPPORTABILITY_UNAVAILABLE",
                "EXTERNAL_OMS_SOURCE_NOT_INGESTED",
                "EXECUTION_ACKNOWLEDGEMENT_COUNT_0",
                "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_BEST_EXECUTION",
                "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_OMS_ACKNOWLEDGEMENT",
                "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_FILLS",
                "EXECUTION_ACKNOWLEDGEMENT_BLOCKED_CAPABILITY_SETTLEMENT",
            ],
        ),
    )
    execution_result = compare_outcome_dimension(
        DpmOutcomeDimensionInput(
            dimension="EXECUTION_QUALITY",
            expected=expected,
            realized=realized,
            tolerance=DpmOutcomeTolerance(soft=Decimal("0"), hard=Decimal("0")),
            materiality=Decimal("0"),
            direction="HIGHER_IS_BETTER",
        )
    )
    review = base_review.model_copy(
        update={
            "state": "BLOCKED",
            "realized_snapshot": base_review.realized_snapshot.model_copy(
                update={
                    "realized_values": {
                        **base_review.realized_snapshot.realized_values,
                        "EXECUTION_QUALITY": realized,
                    },
                    "supportability": DpmOutcomeSupportability(
                        state="BLOCKED",
                        reason_codes=["EXECUTION_EVIDENCE_BLOCKED"],
                    ),
                    "source_lineage": [*base_review.realized_snapshot.source_lineage, source_ref],
                    "source_hashes": {
                        **base_review.realized_snapshot.source_hashes,
                        "external_acknowledgement": "sha256:external-acknowledgement",
                    },
                    "quality_summary": {
                        **base_review.realized_snapshot.quality_summary,
                        "MISSING": 1,
                    },
                }
            ),
            "dimension_results": [*base_review.dimension_results, execution_result],
            "supportability": DpmOutcomeSupportability(
                state="BLOCKED",
                reason_codes=["SOURCE_READY", "EXECUTION_EVIDENCE_BLOCKED"],
            ),
            "source_lineage": [*base_review.source_lineage, source_ref],
            "source_hashes": {
                **base_review.source_hashes,
                "external_acknowledgement": "sha256:external-acknowledgement",
            },
            "content_hash": "sha256:blocked-execution-review",
        }
    )
    repository.save_outcome_review(review=review, retention_expires_at=None)
    _override_repositories(repository)
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/rebalance/outcome-reviews/dor_001/supportability")

        assert response.status_code == 200
        boundary = response.json()["external_execution_boundary"]
        client_boundary = response.json()["client_communication_boundary"]
        assert boundary["boundary_id"] == "DPM_OUTCOME_EXTERNAL_EXECUTION_BOUNDARY"
        assert boundary["supportability_state"] == "BLOCKED"
        assert boundary["source_product_present"] is True
        assert boundary["execution_quality_dimension_state"] == "BLOCKED"
        assert boundary["execution_acknowledgement_count_projected"] == 0
        assert boundary["required_owner"] == "future execution/OMS owner"
        assert boundary["required_source_product"] == "ExternalOrderExecutionAcknowledgement:v1"
        assert boundary["blocked_capabilities"] == [
            "best_execution",
            "fills",
            "oms_acknowledgement",
            "settlement",
        ]
        assert boundary["content_hash"].startswith("sha256:")
        assert client_boundary["boundary_id"] == "DPM_OUTCOME_CLIENT_COMMUNICATION_BOUNDARY"
        assert client_boundary["supportability_state"] == "BLOCKED"
        assert client_boundary["client_communication_projected"] is False
        assert client_boundary["client_approval_projected"] is False
        assert client_boundary["required_owner"] == "future client-communication owner"
        assert client_boundary["required_source_product"] == "ClientCommunicationRecord:v1"
        assert client_boundary["blocked_capabilities"] == [
            "client_approval",
            "client_contact",
            "client_message_generation",
            "communication_audit",
            "delivery_confirmation",
        ]
        assert client_boundary["content_hash"].startswith("sha256:")

        report = client.get("/api/v1/rebalance/outcome-reviews/dor_001/report-input")
        ai = client.get("/api/v1/rebalance/outcome-reviews/dor_001/ai-evidence-input")

        assert report.status_code == 200
        assert ai.status_code == 200
        assert report.json()["external_execution_boundary"] == boundary
        assert ai.json()["external_execution_boundary"] == boundary
        assert report.json()["client_communication_boundary"] == client_boundary
        assert ai.json()["client_communication_boundary"] == client_boundary
    finally:
        app.dependency_overrides.clear()
