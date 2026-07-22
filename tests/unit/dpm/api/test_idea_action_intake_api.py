from fastapi.testclient import TestClient

from src.api.main import app
from src.core.rebalance_runs import (
    IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS,
    IdeaActionIntakeRequest,
    acknowledge_idea_action_intake,
    reset_idea_action_intake_idempotency_for_tests,
)


def _payload() -> dict[str, object]:
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "idea_candidate_id": "idea_candidate_001",
        "conversion_intent_id": "conversion_intent_001",
        "intent_type": "REVIEW_FOR_REBALANCE",
        "source_refs": [
            {
                "source_system": "lotus-idea",
                "source_type": "IdeaCandidate",
                "source_id": "idea_candidate_001",
                "content_hash": "sha256:abc123",
            }
        ],
    }


def _headers(
    *,
    correlation_id: str | None = "corr-idea-action-001",
    idempotency_key: str = "idea-action-intake-idem-001",
    capabilities: str = "manage.idea_action_intake.accept",
    role: str = "SERVICE",
) -> dict[str, str]:
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": "svc-lotus-idea",
        "X-Role": role,
        "X-Tenant-Id": "tenant-private-bank-sg",
        "X-Legal-Entity-Code": "SGPB",
        "X-Service-Identity": "lotus-idea",
        "X-Capabilities": capabilities,
    }
    if correlation_id is not None:
        headers["X-Correlation-Id"] = correlation_id
    return headers


def setup_function() -> None:
    reset_idea_action_intake_idempotency_for_tests()


def test_idea_action_intake_route_returns_source_safe_non_execution_posture() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )

    assert response.status_code == 202
    body = response.json()
    assert body["intake_id"].startswith("iai_")
    assert body["intake_status"] == "ACCEPTED"
    assert body["supportability_status"] == "not_certified"
    assert body["source_authority"] == "lotus-idea"
    assert body["action_authority"] == "lotus-manage"
    assert body["target_product"] == "lotus-manage:PortfolioActionRegister:v1"
    assert body["route_existence_proven"] is True
    assert body["action_receipt_accepted"] is True
    assert body["idempotency_replay"] is False
    assert body["idempotency_key_hash"].startswith("sha256:")
    assert body["request_fingerprint"].startswith("sha256:")
    assert body["trusted_scope"] == {
        "subject": "svc-lotus-idea",
        "role": "SERVICE",
        "tenant_id": "tenant-private-bank-sg",
        "legal_entity_code": "SGPB",
        "correlation_id": "corr-idea-action-001",
        "service_identity": "lotus-idea",
        "capability": "manage.idea_action_intake.accept",
    }
    assert body["outcome_reason_codes"] == ["idea_action_intake_receipt_accepted"]
    assert body["action_register_created"] is False
    assert body["rebalance_execution_authority_granted"] is False
    assert body["order_created"] is False
    assert body["client_publication_authorized"] is False
    assert body["certification_blockers"] == IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS
    assert body["correlation_id"] == "corr-idea-action-001"


def test_idea_action_intake_rejects_query_parameters() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake?dry_run=true",
            json=_payload(),
            headers=_headers(),
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
    )


def test_idea_action_intake_route_replays_same_idempotency_key_and_payload() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(correlation_id="corr-first"),
        )
        second = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(correlation_id="corr-second"),
        )

    assert first.status_code == 202
    assert second.status_code == 202
    first_body = first.json()
    second_body = second.json()
    assert second_body["intake_id"] == first_body["intake_id"]
    assert second_body["intake_status"] == "ACCEPTED_REPLAYED"
    assert second_body["idempotency_replay"] is True
    assert second_body["outcome_reason_codes"] == ["idea_action_intake_receipt_replayed"]
    assert second_body["correlation_id"] == "corr-second"


def test_idea_action_intake_route_rejects_conflicting_idempotency_replay() -> None:
    changed_payload = _payload()
    changed_payload["conversion_intent_id"] = "conversion_intent_changed"

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )
        second = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=changed_payload,
            headers=_headers(),
        )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["detail"] == "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"


def test_idea_action_intake_route_returns_bounded_rejection_without_action_register() -> None:
    payload = _payload()
    payload["intent_type"] = "CREATE_MANAGEMENT_ACTION_DRAFT"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=payload,
            headers=_headers(idempotency_key="idea-action-intake-idem-rejected"),
        )

    assert response.status_code == 202
    body = response.json()
    assert body["intake_status"] == "REJECTED"
    assert body["action_receipt_accepted"] is False
    assert body["action_register_created"] is False
    assert body["rebalance_execution_authority_granted"] is False
    assert body["outcome_reason_codes"] == [
        "action_register_persistence_not_certified",
        "idea_action_intake_receipt_rejected_no_action_created",
    ]


def test_idea_action_intake_route_requires_trusted_local_dev_principal() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers={"Idempotency-Key": "idea-action-intake-idem-missing-principal"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED"


def test_idea_action_intake_route_rejects_unauthorized_role() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(role="CLIENT"),
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED"


def test_idea_action_intake_route_rejects_missing_capability() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(capabilities="manage.rebalance.read"),
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED"


def test_idea_action_intake_domain_acknowledgement_is_deterministic() -> None:
    request = IdeaActionIntakeRequest.model_validate(_payload())

    first = acknowledge_idea_action_intake(request, correlation_id="corr-a")
    second = acknowledge_idea_action_intake(request, correlation_id="corr-b")

    assert first.intake_id == second.intake_id
    assert first.action_receipt_accepted is True
    assert first.action_register_created is False
    assert first.rebalance_execution_authority_granted is False
    assert first.order_created is False
    assert first.client_publication_authorized is False


def test_idea_action_intake_route_is_documented_in_openapi() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    operation = openapi["paths"]["/api/v1/rebalance/idea-action-intake"]["post"]
    assert operation["summary"] == "Accept lotus-idea Action Intake Receipt"
    assert "does not grant rebalance authority" in operation["description"]
    assert "202" in operation["responses"]
    assert "401" in operation["responses"]
    assert "403" in operation["responses"]
    assert "409" in operation["responses"]
