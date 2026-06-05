from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from src.api.routers.wave_campaign_source_resolution import (
    _bulk_review_campaign_membership_diagnostics,
    _bulk_review_campaign_portfolio_payload,
    _candidate_payload,
    _candidate_payloads,
)


@dataclass(frozen=True)
class CandidateModel:
    portfolio_id: str
    mandate_id: str | None
    portfolio_type: str
    source_refs: list[dict[str, object]]

    def model_dump(self, *, mode: str) -> dict[str, object]:
        assert mode == "json"
        return {
            "portfolio_id": self.portfolio_id,
            "mandate_id": self.mandate_id,
            "portfolio_type": self.portfolio_type,
            "source_refs": self.source_refs,
        }


class InvalidCandidateModel:
    def model_dump(self, *, mode: str) -> list[str]:
        assert mode == "json"
        return ["not-a-dict"]


def test_candidate_payloads_accept_mapping_and_model_dump() -> None:
    mapping_candidate = {
        "portfolio_id": "PB_SG_GLOBAL_BAL_001",
        "mandate_id": "MANDATE_001",
        "portfolio_type": "DISCRETIONARY",
        "source_refs": [{"source_id": "mapping-source"}],
    }
    model_candidate = CandidateModel(
        portfolio_id="PB_SG_ADVISORY_001",
        mandate_id=None,
        portfolio_type="ADVISORY",
        source_refs=[{"source_id": "model-source"}],
    )

    payloads = _candidate_payloads([mapping_candidate, model_candidate])

    assert payloads[0]["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert payloads[1]["portfolio_id"] == "PB_SG_ADVISORY_001"
    assert payloads[1]["source_refs"] == [{"source_id": "model-source"}]


def test_candidate_payload_rejects_unsupported_candidates() -> None:
    with pytest.raises(TypeError, match="model_dump"):
        _candidate_payload(InvalidCandidateModel())

    with pytest.raises(TypeError, match="mapping semantics"):
        _candidate_payload(object())


def test_bulk_review_campaign_membership_diagnostics_normalizes_portfolio_type() -> None:
    diagnostics = _bulk_review_campaign_membership_diagnostics(
        trigger_id="campaign-q2-review",
        campaign_as_of_date=date(2026, 5, 18),
        portfolio_type=" discretionary ",
        eligible_portfolio_types={"ADVISORY", "DISCRETIONARY"},
        excluded_candidate_count=2,
        governance_diagnostics={"governance_state": "READY"},
    )

    assert diagnostics["campaign_as_of_date"] == "2026-05-18"
    assert diagnostics["portfolio_type"] == "DISCRETIONARY"
    assert diagnostics["eligible_portfolio_types"] == ["ADVISORY", "DISCRETIONARY"]
    assert diagnostics["excluded_candidate_count"] == 2
    assert diagnostics["membership_supportability_state"] == "READY"
    assert diagnostics["governance_state"] == "READY"


def test_bulk_review_campaign_portfolio_payload_projects_lineage_and_diagnostics() -> None:
    membership_ref = {"source_type": "BulkReviewCampaignMembership", "source_id": "membership"}
    governance_ref = {"source_type": "CAMPAIGN_GOVERNANCE", "source_id": "governance"}
    candidate_source_ref = {
        "source_system": "lotus-core",
        "source_type": "DPM_PORTFOLIO_UNIVERSE_CANDIDATE",
        "source_id": "candidate-source",
        "source_version": "v1",
        "supportability_state": "READY",
    }

    payload = _bulk_review_campaign_portfolio_payload(
        payload={
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "mandate_id": "MANDATE_001",
            "portfolio_type": " discretionary ",
            "source_refs": [candidate_source_ref],
        },
        trigger_id="campaign-q2-review",
        campaign_as_of_date=date(2026, 5, 18),
        membership_hash="sha256:membership",
        membership_ref=membership_ref,
        governance_refs=[governance_ref],
        governance_diagnostics={"governance_state": "READY"},
        eligible_portfolio_types={"DISCRETIONARY"},
        excluded_candidate_count=1,
    )

    assert payload["portfolio_id"] == "PB_SG_GLOBAL_BAL_001"
    assert payload["mandate_id"] == "MANDATE_001"
    source_refs = payload["source_refs"]
    assert isinstance(source_refs, list)
    assert source_refs[0] == membership_ref
    assert source_refs[1] == governance_ref
    assert source_refs[2]["source_type"] == "BULK_REVIEW_CAMPAIGN_MEMBER"
    assert source_refs[3] == candidate_source_ref
    assert payload["diagnostics"]["portfolio_type"] == "DISCRETIONARY"
    assert payload["diagnostics"]["governance_state"] == "READY"
