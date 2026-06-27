from fastapi.testclient import TestClient

from src.api.main import app
from src.core.rebalance_runs import (
    IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS,
    IdeaActionIntakeRequest,
    acknowledge_idea_action_intake,
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


def test_idea_action_intake_route_returns_source_safe_non_execution_posture() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers={"X-Correlation-Id": "corr-idea-action-001"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["intake_id"].startswith("iai_")
    assert body["intake_status"] == "ROUTE_FOUNDATION_ACCEPTED_NOT_CERTIFIED"
    assert body["supportability_status"] == "not_certified"
    assert body["source_authority"] == "lotus-idea"
    assert body["action_authority"] == "lotus-manage"
    assert body["target_product"] == "lotus-manage:PortfolioActionRegister:v1"
    assert body["route_existence_proven"] is True
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
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "UNSUPPORTED_QUERY_PARAMETER: dry_run not supported for this endpoint"
    )


def test_idea_action_intake_domain_acknowledgement_is_deterministic() -> None:
    request = IdeaActionIntakeRequest.model_validate(_payload())

    first = acknowledge_idea_action_intake(request, correlation_id="corr-a")
    second = acknowledge_idea_action_intake(request, correlation_id="corr-b")

    assert first.intake_id == second.intake_id
    assert first.action_register_created is False
    assert first.rebalance_execution_authority_granted is False
    assert first.order_created is False
    assert first.client_publication_authorized is False


def test_idea_action_intake_route_is_documented_in_openapi() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    operation = openapi["paths"]["/api/v1/rebalance/idea-action-intake"]["post"]
    assert operation["summary"] == "Accept lotus-idea Action Intake Foundation"
    assert "does not grant rebalance authority" in operation["description"]
    assert "202" in operation["responses"]
