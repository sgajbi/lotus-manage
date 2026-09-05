from __future__ import annotations

import json
from pathlib import Path

from src.core.rebalance_runs import IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS


ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = (
    ROOT / "contracts" / "idea-action-intake" / ("lotus-manage-idea-action-intake.v1.json")
)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_idea_action_intake_contract_preserves_manage_authority_boundary() -> None:
    contract = _contract()

    assert contract["schema_version"] == "lotus-manage.idea-action-intake.v1"
    assert contract["repository"] == "lotus-manage"
    assert contract["approved_producer_repository"] == "lotus-idea"
    assert contract["approved_producer_product"] == "lotus-idea:IdeaCandidate:v1"
    assert contract["owned_product"] == "lotus-manage:PortfolioActionRegister:v1"
    assert contract["source_authority"] == "lotus-manage"
    assert contract["target_route"] == "POST /api/v1/rebalance/idea-action-intake"
    assert contract["lifecycle_status"] == "implemented"
    assert contract["supportability_status"] == "not_certified"
    assert contract["route_existence_proven"] is True
    assert contract["runtime_action_receipt_proven"] is True
    assert contract["durable_management_action_proven"] is True
    assert contract["management_review_outcome_history_proven"] is True
    assert contract["conversion_intent_owner_recovery_proven"] is True
    assert contract["conversion_intent_outcome_history_route"] == (
        "GET /api/v1/rebalance/idea-action-intakes/by-conversion-intent/"
        "{conversion_intent_id}/outcomes?portfolio_id={portfolio_id}"
    )
    assert contract["downstream_execution_proven"] is False
    assert contract["supported_feature_promoted"] is False


def test_idea_action_intake_contract_keeps_non_proof_boundaries_and_blockers() -> None:
    contract = _contract()
    boundaries = " ".join(contract["non_proof_boundaries"])

    assert "one durable, portfolio-scoped PENDING_REVIEW management action" in boundaries
    assert "Does not grant suitability" in boundaries
    assert "does not prove rebalance execution" in boundaries
    assert "never creates or repeats management work" in boundaries
    assert "Does not promote a supported feature" in boundaries
    assert contract["certification_blockers"] == IDEA_ACTION_INTAKE_CERTIFICATION_BLOCKERS
    assert "manage_live_contract_proof_missing" not in contract["certification_blockers"]
    assert {
        "src/api/routers/rebalance_runs_idea_action_intake_routes.py",
        "src/api/routers/rebalance_runs_idea_action_intake_principal.py",
        "src/core/rebalance_runs/idea_action_intake_authority.py",
        "src/core/rebalance_runs/idea_action_intake.py",
        "src/core/rebalance_runs/idea_management_action.py",
        "src/infrastructure/postgres_migrations/dpm/0021_idea_management_actions.sql",
        "src/infrastructure/rebalance_runs/idea_management_actions_postgres.py",
        "tests/unit/dpm/api/test_idea_action_intake_api.py",
        "tests/integration/dpm/supportability/test_idea_management_action_postgres_integration.py",
    }.issubset(set(contract["evidence_refs"]))
