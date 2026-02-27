import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests


def _proposal_payload(
    *, portfolio_id: str = "pf_integration_1", title: str = "integration proposal"
) -> dict:
    return {
        "created_by": "advisor_integration",
        "simulate_request": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {"prices": [], "fx_rates": []},
            "shelf_entries": [],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [],
        },
        "metadata": {"title": title},
    }


@pytest.fixture(autouse=True)
def _reset_workflow_service() -> None:
    reset_proposal_workflow_service_for_tests()
    yield
    reset_proposal_workflow_service_for_tests()


def test_proposal_lifecycle_and_supportability_endpoints_roundtrip() -> None:
    payload = _proposal_payload()
    create_headers = {
        "Idempotency-Key": "integration-proposal-create-1",
        "X-Correlation-Id": "corr-integration-proposal-create-1",
    }

    with TestClient(app) as client:
        created = client.post("/api/v1/rebalance/proposals", json=payload, headers=create_headers)
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        fetched = client.get(f"/api/v1/rebalance/proposals/{proposal_id}?include_evidence=false")
        listed = client.get("/api/v1/rebalance/proposals?created_by=advisor_integration&limit=10")
        version = client.get(
            f"/api/v1/rebalance/proposals/{proposal_id}/versions/1?include_evidence=false"
        )
        transition = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {"ticket": "integration-1"},
            },
            headers={"Idempotency-Key": "integration-proposal-transition-1"},
        )
        approval = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_integration",
                "expected_state": "RISK_REVIEW",
                "details": {"channel": "API"},
            },
            headers={"Idempotency-Key": "integration-proposal-approval-1"},
        )
        timeline = client.get(f"/api/v1/rebalance/proposals/{proposal_id}/workflow-events")
        approvals = client.get(f"/api/v1/rebalance/proposals/{proposal_id}/approvals")
        lineage = client.get(f"/api/v1/rebalance/proposals/{proposal_id}/lineage")
        idem = client.get("/api/v1/rebalance/proposals/idempotency/integration-proposal-create-1")
        supportability = client.get("/api/v1/rebalance/proposals/supportability/config")

    assert fetched.status_code == 200
    assert fetched.json()["current_version"]["evidence_bundle"] == {}
    assert listed.status_code == 200
    assert any(item["proposal_id"] == proposal_id for item in listed.json()["items"])
    assert version.status_code == 200
    assert version.json()["version_no"] == 1
    assert transition.status_code == 200
    assert transition.json()["current_state"] == "RISK_REVIEW"
    assert approval.status_code == 200
    assert approval.json()["current_state"] == "AWAITING_CLIENT_CONSENT"
    assert timeline.status_code == 200
    assert [event["event_type"] for event in timeline.json()["events"]] == [
        "CREATED",
        "SUBMITTED_FOR_RISK_REVIEW",
        "RISK_APPROVED",
    ]
    assert approvals.status_code == 200
    assert approvals.json()["approvals"][0]["approval_type"] == "RISK"
    assert lineage.status_code == 200
    assert [item["version_no"] for item in lineage.json()["versions"]] == [1]
    assert idem.status_code == 200
    assert idem.json()["proposal_id"] == proposal_id
    assert supportability.status_code == 200
    assert supportability.json()["store_backend"] in {"INMEMORY", "POSTGRES"}


def test_proposal_lifecycle_error_contracts() -> None:
    payload = _proposal_payload()
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/rebalance/proposals",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-errors-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        conflicting_payload = _proposal_payload(title="changed-title")
        idempotency_conflict = client.post(
            "/api/v1/rebalance/proposals",
            json=conflicting_payload,
            headers={"Idempotency-Key": "integration-proposal-errors-1"},
        )
        missing = client.get("/api/v1/rebalance/proposals/pp_missing")
        invalid_transition = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "EXECUTED",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {},
            },
        )
        stale_state = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "COMPLIANCE_REVIEW",
                "reason": {},
            },
        )
        invalid_version = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/versions",
            json={
                "created_by": "advisor_integration",
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_different",
                        "base_currency": "USD",
                        "positions": [],
                        "cash_balances": [{"currency": "USD", "amount": "1000"}],
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                },
            },
        )
        missing_timeline = client.get("/api/v1/rebalance/proposals/pp_missing/workflow-events")
        missing_approvals = client.get("/api/v1/rebalance/proposals/pp_missing/approvals")
        missing_lineage = client.get("/api/v1/rebalance/proposals/pp_missing/lineage")
        missing_idem = client.get("/api/v1/rebalance/proposals/idempotency/missing-idem")

    assert idempotency_conflict.status_code == 409
    assert idempotency_conflict.json()["detail"].startswith("IDEMPOTENCY_KEY_CONFLICT")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "PROPOSAL_NOT_FOUND"
    assert invalid_transition.status_code == 422
    assert invalid_transition.json()["detail"] == "INVALID_TRANSITION"
    assert stale_state.status_code == 409
    assert stale_state.json()["detail"].startswith("STATE_CONFLICT")
    assert invalid_version.status_code == 422
    assert invalid_version.json()["detail"] == "PORTFOLIO_CONTEXT_MISMATCH"
    assert missing_timeline.status_code == 404
    assert missing_approvals.status_code == 404
    assert missing_lineage.status_code == 404
    assert missing_idem.status_code == 404


def test_async_proposal_endpoints_and_feature_flag_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _proposal_payload(portfolio_id="pf_async_1")
    with TestClient(app) as client:
        accepted = client.post(
            "/api/v1/rebalance/proposals/async",
            json=payload,
            headers={
                "Idempotency-Key": "integration-proposal-async-1",
                "X-Correlation-Id": "corr-integration-proposal-async-1",
            },
        )
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        by_operation = client.get(f"/api/v1/rebalance/proposals/operations/{operation_id}")
        by_correlation = client.get(
            "/api/v1/rebalance/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-1"
        )
        assert by_operation.status_code == 200
        assert by_correlation.status_code == 200
        assert by_operation.json()["operation_id"] == operation_id
        assert by_operation.json()["status"] == "SUCCEEDED"

    reset_proposal_workflow_service_for_tests()
    monkeypatch.setenv("PROPOSAL_ASYNC_OPERATIONS_ENABLED", "false")
    with TestClient(app) as client:
        async_disabled = client.get("/api/v1/rebalance/proposals/operations/op_missing")
    assert async_disabled.status_code == 404
    assert async_disabled.json()["detail"] == "PROPOSAL_ASYNC_OPERATIONS_DISABLED"

    reset_proposal_workflow_service_for_tests()
    monkeypatch.setenv("PROPOSAL_SUPPORT_APIS_ENABLED", "false")
    with TestClient(app) as client:
        support_disabled = client.get("/api/v1/rebalance/proposals/pp_missing/workflow-events")
    assert support_disabled.status_code == 404
    assert support_disabled.json()["detail"] == "PROPOSAL_SUPPORT_APIS_DISABLED"


def test_async_proposal_version_and_not_found_lookups() -> None:
    payload = _proposal_payload(portfolio_id="pf_async_version")
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/rebalance/proposals",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-async-version-base"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        accepted = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/versions/async",
            json={
                "created_by": "advisor_integration",
                "simulate_request": payload["simulate_request"],
            },
            headers={"X-Correlation-Id": "corr-integration-proposal-async-version"},
        )
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]
        by_operation = client.get(f"/api/v1/rebalance/proposals/operations/{operation_id}")
        by_correlation = client.get(
            "/api/v1/rebalance/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-version"
        )
        missing_operation = client.get("/api/v1/rebalance/proposals/operations/pop_missing")
        missing_correlation = client.get(
            "/api/v1/rebalance/proposals/operations/by-correlation/corr_missing"
        )

    assert by_operation.status_code == 200
    assert by_operation.json()["status"] == "SUCCEEDED"
    assert by_correlation.status_code == 200
    assert missing_operation.status_code == 404
    assert missing_operation.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"
    assert missing_correlation.status_code == 404
    assert missing_correlation.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"


@pytest.mark.parametrize(
    ("exception_obj", "expected_detail"),
    [
        (RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED"), "PROPOSAL_POSTGRES_DSN_REQUIRED"),
        (TypeError("boom"), "PROPOSAL_POSTGRES_CONNECTION_FAILED"),
    ],
)
def test_supportability_config_backend_init_error_mapping(
    monkeypatch: pytest.MonkeyPatch, exception_obj: Exception, expected_detail: str
) -> None:
    reset_proposal_workflow_service_for_tests()
    monkeypatch.setattr(
        "src.api.routers.proposals_config.build_repository",
        lambda: (_ for _ in ()).throw(exception_obj),
    )
    with TestClient(app) as client:
        response = client.get("/api/v1/rebalance/proposals/supportability/config")

    assert response.status_code == 200
    assert response.json()["backend_ready"] is False
    assert response.json()["backend_init_error"] == expected_detail


def test_create_proposal_validation_error_contract() -> None:
    payload = _proposal_payload()
    payload["simulate_request"]["options"]["enable_proposal_simulation"] = False
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/proposals",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-invalid-create"},
        )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("PROPOSAL_SIMULATION_DISABLED")


@pytest.mark.parametrize(
    ("method", "path", "body", "expected_status", "expected_detail"),
    [
        (
            "get",
            "/api/v1/rebalance/proposals/pp_missing/versions/1",
            None,
            404,
            "PROPOSAL_VERSION_NOT_FOUND",
        ),
        (
            "post",
            "/api/v1/rebalance/proposals/pp_missing/versions",
            {
                "created_by": "advisor_integration",
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_integration_1",
                        "base_currency": "USD",
                        "positions": [],
                        "cash_balances": [{"currency": "USD", "amount": "1000"}],
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                },
            },
            404,
            "PROPOSAL_NOT_FOUND",
        ),
        (
            "post",
            "/api/v1/rebalance/proposals/pp_missing/transitions",
            {
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {},
            },
            404,
            "PROPOSAL_NOT_FOUND",
        ),
        (
            "post",
            "/api/v1/rebalance/proposals/pp_missing/approvals",
            {
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_integration",
                "expected_state": "RISK_REVIEW",
                "details": {},
            },
            404,
            "PROPOSAL_NOT_FOUND",
        ),
    ],
)
def test_lifecycle_not_found_matrix(
    method: str, path: str, body: dict | None, expected_status: int, expected_detail: str
) -> None:
    with TestClient(app) as client:
        if method == "get":
            response = client.get(path)
        else:
            response = client.post(path, json=body)

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail


def test_transition_and_approval_conflict_error_contracts() -> None:
    payload = _proposal_payload(portfolio_id="pf_conflict")
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/rebalance/proposals",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-conflict-base"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        first_transition = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {"source": "api"},
            },
            headers={"Idempotency-Key": "integration-transition-conflict"},
        )
        assert first_transition.status_code == 200

        conflicting_transition = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "RISK_REVIEW",
                "reason": {"source": "api"},
            },
            headers={"Idempotency-Key": "integration-transition-conflict"},
        )
        stale_approval = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_integration",
                "expected_state": "COMPLIANCE_REVIEW",
                "details": {},
            },
        )
        invalid_approval_transition = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "CLIENT_CONSENT",
                "approved": True,
                "actor_id": "client_integration",
                "expected_state": "RISK_REVIEW",
                "details": {},
            },
        )
        first_approval = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_integration",
                "expected_state": "RISK_REVIEW",
                "details": {"source": "api"},
            },
            headers={"Idempotency-Key": "integration-approval-conflict"},
        )
        conflicting_approval = client.post(
            f"/api/v1/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": False,
                "actor_id": "risk_integration",
                "expected_state": "RISK_REVIEW",
                "details": {"source": "api"},
            },
            headers={"Idempotency-Key": "integration-approval-conflict"},
        )

    assert conflicting_transition.status_code == 409
    assert conflicting_transition.json()["detail"].startswith("IDEMPOTENCY_KEY_CONFLICT")
    assert stale_approval.status_code == 409
    assert stale_approval.json()["detail"].startswith("STATE_CONFLICT")
    assert invalid_approval_transition.status_code == 422
    assert invalid_approval_transition.json()["detail"] == "INVALID_APPROVAL_STATE"
    assert first_approval.status_code == 200
    assert conflicting_approval.status_code == 409
    assert conflicting_approval.json()["detail"].startswith("IDEMPOTENCY_KEY_CONFLICT")
