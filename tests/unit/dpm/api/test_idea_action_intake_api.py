from fastapi.testclient import TestClient
import pytest

import src.api.routers.rebalance_runs_idea_action_intake_routes as idea_action_routes
from src.api.dependencies import reset_idea_management_action_repository_for_tests
from src.api.main import app
from src.core.rebalance_runs import IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS
from src.core.rebalance_runs.idea_management_action_repository import (
    IdeaManagementActionRepositoryUnavailableError,
)


PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


def _payload() -> dict[str, object]:
    return {
        "source_system": "lotus-idea",
        "source_product": "lotus-idea:IdeaCandidate:v1",
        "portfolio_id": PORTFOLIO_ID,
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
    tenant_id: str = "tenant-private-bank-sg",
    legal_entity_code: str = "SGPB",
    actor_id: str = "svc-lotus-idea",
    service_identity: str = "lotus-idea",
    portfolio_ids: str = PORTFOLIO_ID,
) -> dict[str, str]:
    headers = {
        "Idempotency-Key": idempotency_key,
        "X-Actor-Id": actor_id,
        "X-Role": role,
        "X-Tenant-Id": tenant_id,
        "X-Legal-Entity-Code": legal_entity_code,
        "X-Service-Identity": service_identity,
        "X-Capabilities": capabilities,
        "X-Portfolio-Ids": portfolio_ids,
    }
    if correlation_id is not None:
        headers["X-Correlation-Id"] = correlation_id
    return headers


def setup_function() -> None:
    reset_idea_management_action_repository_for_tests()


def test_intake_creates_scoped_manage_review_work_without_execution_claims() -> None:
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
    assert body["action_receipt_accepted"] is True
    assert body["action_register_created"] is True
    assert body["management_action_id"].startswith("ima_")
    assert body["management_action_status"] == "PENDING_REVIEW"
    assert body["source_event_version"] == 1
    assert body["outcome_history_route"].endswith(f"/{body['intake_id']}/outcomes")
    assert body["idempotency_replay"] is False
    assert body["trusted_scope"]["portfolio_ids"] == [PORTFOLIO_ID]
    assert body["outcome_reason_codes"] == ["idea_action_created_for_management_review"]
    assert body["rebalance_execution_authority_granted"] is False
    assert body["order_created"] is False
    assert body["client_publication_authorized"] is False
    assert body["certification_blockers"] == IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS


def test_intake_replay_returns_exact_durable_work_identity() -> None:
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
    assert second.json()["intake_status"] == "ACCEPTED_REPLAYED"
    assert second.json()["idempotency_replay"] is True
    assert second.json()["intake_id"] == first.json()["intake_id"]
    assert second.json()["management_action_id"] == first.json()["management_action_id"]
    assert second.json()["source_event_version"] == 1
    assert second.json()["correlation_id"] == "corr-second"


def test_intake_rejects_changed_payload_for_same_scoped_idempotency_key() -> None:
    changed = _payload()
    changed["conversion_intent_id"] = "conversion_intent_changed"

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )
        conflict = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=changed,
            headers=_headers(),
        )

    assert first.status_code == 202
    assert conflict.status_code == 409
    assert conflict.headers["content-type"].startswith("application/problem+json")
    assert conflict.json()["reasonCode"] == "IDEA_ACTION_INTAKE_IDEMPOTENCY_CONFLICT"


def test_intake_fails_scope_before_persistence() -> None:
    with TestClient(app) as client:
        forbidden = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(portfolio_ids="PB_SG_OTHER_001"),
        )

    assert forbidden.status_code == 403
    assert forbidden.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN"


def test_unsupported_intent_returns_terminal_rejection_without_work() -> None:
    payload = _payload()
    payload["intent_type"] = "CREATE_MANAGEMENT_ACTION_DRAFT"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=payload,
            headers=_headers(idempotency_key="idea-action-rejected"),
        )

    assert response.status_code == 202
    body = response.json()
    assert body["intake_status"] == "REJECTED"
    assert body["action_register_created"] is False
    assert body["management_action_id"] is None
    assert body["source_event_version"] is None
    assert body["rebalance_execution_authority_granted"] is False


def test_owner_history_and_review_transition_are_source_owned_and_versioned() -> None:
    with TestClient(app) as client:
        intake = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        ).json()
        read_headers = _headers(
            capabilities="manage.idea_action_intake.read",
            idempotency_key="unused-read",
        )
        history = client.get(intake["outcome_history_route"], headers=read_headers)
        review_headers = _headers(
            capabilities="manage.idea_action_intake.review",
            role="PORTFOLIO_MANAGER",
            actor_id="pm-001",
            service_identity="lotus-workbench",
            idempotency_key="unused-review",
            correlation_id="corr-review-001",
        )
        approved = client.post(
            intake["outcome_history_route"],
            json={
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "management_review_approved",
            },
            headers=review_headers,
        )

    assert history.status_code == 200
    assert history.json()["status"] == "PENDING_REVIEW"
    assert history.json()["source_event_version"] == 1
    assert history.json()["events"][0]["event_type"] == "INTAKE_ACCEPTED"
    assert approved.status_code == 200
    assert approved.json()["source_authority"] == "lotus-manage"
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["source_event_version"] == 2
    assert approved.json()["events"][-1]["event_type"] == "APPROVE"
    assert approved.json()["rebalance_execution_proven"] is False
    assert approved.json()["order_execution_proven"] is False


def test_conversion_intent_lookup_recovers_current_owner_history_without_mutation() -> None:
    read_headers = _headers(
        capabilities="manage.idea_action_intake.read",
        idempotency_key="unused-read",
    )
    review_headers = _headers(
        capabilities="manage.idea_action_intake.review",
        role="PORTFOLIO_MANAGER",
        actor_id="pm-001",
        service_identity="lotus-workbench",
        idempotency_key="unused-review",
    )
    recovery_route = "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent"

    with TestClient(app) as client:
        intake = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        ).json()
        approved = client.post(
            intake["outcome_history_route"],
            json={
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "management_review_approved",
            },
            headers=review_headers,
        )
        recovered = client.get(
            recovery_route,
            params={
                "conversion_intent_id": "conversion_intent_001",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=read_headers,
        )
        replayed = client.get(
            recovery_route,
            params={
                "conversion_intent_id": "conversion_intent_001",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=read_headers,
        )

    assert approved.status_code == 200
    assert recovered.status_code == 200
    assert recovered.json() == approved.json()
    assert replayed.json() == recovered.json()
    assert recovered.json()["request_fingerprint"] == intake["request_fingerprint"]
    assert recovered.json()["source_event_version"] == 2
    assert [event["event_type"] for event in recovered.json()["events"]] == [
        "INTAKE_ACCEPTED",
        "APPROVE",
    ]


def test_conversion_intent_lookup_denies_scope_and_masks_absence() -> None:
    recovery_route = "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent"
    with TestClient(app) as client:
        client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )
        forbidden = client.get(
            recovery_route,
            params={
                "conversion_intent_id": "conversion_intent_001",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.read",
                portfolio_ids="PB_SG_OTHER_001",
                idempotency_key="unused-read",
            ),
        )
        missing = client.get(
            recovery_route,
            params={
                "conversion_intent_id": "conversion_intent_missing",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.read",
                idempotency_key="unused-read",
            ),
        )

    assert forbidden.status_code == 403
    assert forbidden.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN"
    assert missing.status_code == 404
    assert missing.json()["reasonCode"] == "IDEA_MANAGEMENT_ACTION_NOT_FOUND"


def test_conversion_intent_lookup_recovers_normalized_opaque_intake_identifiers() -> None:
    padded = _payload()
    padded["portfolio_id"] = f"  {PORTFOLIO_ID}  "
    padded["conversion_intent_id"] = "  vendor/123  "

    with TestClient(app) as client:
        accepted = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=padded,
            headers=_headers(),
        )
        recovered = client.get(
            "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent",
            params={
                "conversion_intent_id": "  vendor/123  ",
                "portfolio_id": f"  {PORTFOLIO_ID}  ",
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.read",
                idempotency_key="unused-read",
            ),
        )

    assert accepted.status_code == 202
    assert recovered.status_code == 200
    assert recovered.json()["conversion_intent_id"] == "vendor/123"
    assert recovered.json()["portfolio_id"] == PORTFOLIO_ID
    assert recovered.json()["request_fingerprint"] == accepted.json()["request_fingerprint"]


def test_conversion_intent_lookup_denies_scope_before_repository_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_repository_is_resolved():
        raise AssertionError("out-of-scope recovery must not initialize persistence")

    monkeypatch.setattr(
        idea_action_routes,
        "get_idea_management_action_repository",
        fail_if_repository_is_resolved,
    )

    with TestClient(app) as client:
        forbidden = client.get(
            "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent",
            params={
                "conversion_intent_id": "conversion_intent_001",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.read",
                portfolio_ids="PB_SG_OTHER_001",
                idempotency_key="unused-read",
            ),
        )

    assert forbidden.status_code == 403
    assert forbidden.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_FORBIDDEN"


def test_concurrent_review_decision_rejects_stale_source_event_version() -> None:
    with TestClient(app) as client:
        intake = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        ).json()
        review_headers = _headers(
            capabilities="manage.idea_action_intake.review",
            role="DPM_MANAGER",
            actor_id="dpm-manager-001",
            service_identity="lotus-workbench",
            idempotency_key="unused-review",
        )
        first = client.post(
            intake["outcome_history_route"],
            json={
                "workflow_action": "REJECT",
                "expected_source_event_version": 1,
                "reason_code": "mandate_constraint_conflict",
            },
            headers=review_headers,
        )
        stale = client.post(
            intake["outcome_history_route"],
            json={
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "management_review_approved",
            },
            headers=review_headers,
        )

    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["reasonCode"] == ("IDEA_MANAGEMENT_ACTION_SOURCE_EVENT_VERSION_CONFLICT")


def test_cross_tenant_history_lookup_is_product_safe_not_found() -> None:
    with TestClient(app) as client:
        intake = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        ).json()
        response = client.get(
            intake["outcome_history_route"],
            headers=_headers(
                capabilities="manage.idea_action_intake.read",
                tenant_id="tenant-private-bank-hk",
                legal_entity_code="HKPB",
                actor_id="svc-lotus-idea-hk",
                idempotency_key="unused-read",
            ),
        )

    assert response.status_code == 404
    assert response.json()["reasonCode"] == "IDEA_MANAGEMENT_ACTION_NOT_FOUND"


def test_intake_requires_lotus_idea_service_identity() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(service_identity="untrusted-service"),
        )

    assert response.status_code == 403
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_SERVICE_IDENTITY_REQUIRED"


def test_intake_fails_closed_when_management_action_persistence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable_repository():
        # The repository protocol's own error: a fake raising a Postgres type
        # would diverge from the real adapter, which translates at its
        # connection funnel and never lets one cross the boundary.
        raise IdeaManagementActionRepositoryUnavailableError(
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
        )

    monkeypatch.setattr(
        idea_action_routes,
        "get_idea_management_action_repository",
        _unavailable_repository,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["reasonCode"] == "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
    assert response.json()["instance"] == "/api/v1/rebalance/idea-action-intake"


def test_intake_openapi_documents_scope_and_owner_history_contracts() -> None:
    with TestClient(app) as client:
        openapi = client.get("/openapi.json").json()

    intake = openapi["paths"]["/api/v1/rebalance/idea-action-intake"]["post"]
    history_path = openapi["paths"]["/api/v1/rebalance/idea-action-intakes/{intake_id}/outcomes"]
    recovery_path = openapi["paths"][
        "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent"
    ]
    assert intake["summary"] == ("Realize lotus-idea Conversion Intent as Management Review Work")
    assert "not rebalance approval or execution" in intake["description"]
    assert "get" in history_path
    assert "post" in history_path
    assert recovery_path["get"]["summary"] == (
        "Get Manage-owned Outcome History by Idea Conversion Intent"
    )
    assert "read-only recovery route" in recovery_path["get"]["description"]
    required_headers = {
        parameter["name"]
        for parameter in intake["parameters"]
        if parameter.get("in") == "header" and parameter.get("required") is True
    }
    assert {
        "idempotency-key",
        "x-actor-id",
        "x-role",
        "x-tenant-id",
        "x-legal-entity-code",
        "x-service-identity",
        "x-capabilities",
        "x-portfolio-ids",
    }.issubset(required_headers)
    assert "application/problem+json" in intake["responses"]["409"]["content"]


def test_intake_rejects_blank_idempotency_key_as_unprocessable() -> None:
    """A whitespace key is neither an idempotency scope nor an omission; the
    intake refuses it before any scope or persistence work."""

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(idempotency_key="   "),
        )

    assert response.status_code == 422
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_IDEMPOTENCY_KEY_REQUIRED"


def test_inactive_principal_is_unauthenticated() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers={**_headers(), "X-Principal-Status": "SUSPENDED"},
        )

    assert response.status_code == 401
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PRINCIPAL_INVALID"


def test_principal_without_portfolio_scope_is_unauthenticated() -> None:
    """A trusted principal that names no portfolios has no scope to validate
    against - authentication-shaped, because the scope claim itself is
    missing, not merely insufficient."""

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(portfolio_ids="  "),
        )

    assert response.status_code == 401
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PORTFOLIO_SCOPE_REQUIRED"


def test_wrong_role_is_forbidden_before_capability() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(role="VIEWER"),
        )

    assert response.status_code == 403
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_ROLE_NOT_AUTHORIZED"


def test_whitespace_actor_header_is_unauthenticated_not_a_validation_error() -> None:
    """FastAPI enforces header PRESENCE (min_length on the raw value), so the
    principal's own required-header branch guards the case FastAPI cannot: a
    header that is present but whitespace. That is an authentication fact -
    no actor was identified - not a 422 shape problem. Correlation is omitted
    here too: it is genuinely optional and must default, not fail."""

    headers = _headers(correlation_id=None)
    headers["X-Actor-Id"] = " "

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=headers,
        )

    assert response.status_code == 401
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_PRINCIPAL_REQUIRED"


class _UnavailableAfterConstructionRepository:
    """Constructs fine, then persistence vanishes - the mid-operation case,
    distinct from the construction failure the factory catches."""

    def create_or_replay(self, *, action):
        raise IdeaManagementActionRepositoryUnavailableError(
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
        )

    def get_by_intake_id(self, *, tenant_id, legal_entity_code, intake_id):
        raise IdeaManagementActionRepositoryUnavailableError(
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
        )

    def get_by_conversion_intent(
        self,
        *,
        tenant_id,
        legal_entity_code,
        portfolio_id,
        conversion_intent_id,
    ):
        raise IdeaManagementActionRepositoryUnavailableError(
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
        )

    def update(self, *, action, expected_source_event_version):
        raise IdeaManagementActionRepositoryUnavailableError(
            "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"
        )


@pytest.fixture
def _mid_operation_unavailable(monkeypatch):
    monkeypatch.setattr(
        idea_action_routes,
        "get_idea_management_action_repository",
        lambda: _UnavailableAfterConstructionRepository(),
    )


def test_each_endpoint_fails_closed_when_persistence_vanishes_mid_operation(
    _mid_operation_unavailable,
) -> None:
    """The repository can become unavailable AFTER construction - a dropped
    connection during the call - and every endpoint must map that to the same
    503 posture it gives a construction failure. Asserted per endpoint,
    because each carries its own catch."""

    with TestClient(app) as client:
        intake = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(),
        )
        history = client.get(
            "/api/v1/rebalance/idea-action-intakes/idea-intake-x/outcomes",
            headers=_headers(capabilities="manage.idea_action_intake.read"),
        )
        recovery = client.get(
            "/api/v1/rebalance/idea-action-intakes/outcomes/by-conversion-intent",
            params={
                "conversion_intent_id": "conversion-intent-x",
                "portfolio_id": PORTFOLIO_ID,
            },
            headers=_headers(capabilities="manage.idea_action_intake.read"),
        )
        decision = client.post(
            "/api/v1/rebalance/idea-action-intakes/idea-intake-x/outcomes",
            json={
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "REVIEWED_OK",
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.review", role="PORTFOLIO_MANAGER"
            ),
        )

    for response in (intake, history, recovery, decision):
        assert response.status_code == 503
        assert response.json()["reasonCode"] == "IDEA_MANAGEMENT_ACTION_PERSISTENCE_UNAVAILABLE"


def test_review_decision_for_unknown_intake_is_scoped_not_found() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intakes/idea-intake-missing/outcomes",
            json={
                "workflow_action": "APPROVE",
                "expected_source_event_version": 1,
                "reason_code": "REVIEWED_OK",
            },
            headers=_headers(
                capabilities="manage.idea_action_intake.review", role="PORTFOLIO_MANAGER"
            ),
        )

    assert response.status_code == 404


def test_right_role_without_capability_is_forbidden() -> None:
    """Role and capability are separate authorization facts; a SERVICE
    principal without the accept capability fails on the capability, proving
    the check is not role-only."""

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(capabilities="manage.something_else"),
        )

    assert response.status_code == 403
    assert response.json()["reasonCode"] == "IDEA_ACTION_INTAKE_CAPABILITY_REQUIRED"


def test_whitespace_correlation_header_defaults_instead_of_failing() -> None:
    """Correlation is genuinely optional: a present-but-blank header is the
    same fact as an absent one and must default, not 4xx an otherwise valid
    intake."""

    with TestClient(app) as client:
        blank = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers={**_headers(correlation_id=None), "X-Correlation-Id": "  "},
        )
        absent = client.post(
            "/api/v1/rebalance/idea-action-intake",
            json=_payload(),
            headers=_headers(correlation_id=None, idempotency_key="idea-action-intake-idem-noc"),
        )

    assert blank.status_code == 202
    assert absent.status_code == 202
