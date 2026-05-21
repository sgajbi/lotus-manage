from datetime import datetime, timezone

import pytest

from src.core.models import EngineOptions, RebalanceResult
from src.core.portfolio_memory.handoffs import DpmPortfolioMemoryReportContext
from src.core.proof_packs import (
    assert_no_ai_forbidden_fields,
    build_ai_evidence_input,
    build_proof_pack_from_run,
    build_report_input,
)
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import DpmRunRecord
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)


def _ready_rebalance_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_handoff_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash="sha256:proof-pack-handoff",
        correlation_id="corr-proof-pack-handoff",
    )


def _proof_pack():
    result = _ready_rebalance_result()
    run = DpmRunRecord(
        rebalance_run_id=result.rebalance_run_id,
        correlation_id=result.correlation_id,
        request_hash="sha256:proof-pack-handoff",
        idempotency_key="idem-proof-pack-handoff",
        portfolio_id="pf_handoff_1",
        created_at=CREATED_AT,
        result_json=result.model_dump(mode="json"),
    )
    return build_proof_pack_from_run(
        run=run,
        created_by="pm_handoff",
        reason="Rebalance back to target.",
        created_at=CREATED_AT,
        mandate_id="mandate_handoff_1",
    )


def test_report_input_is_deterministic_and_contains_render_ready_context() -> None:
    proof_pack = _proof_pack()

    first = build_report_input(proof_pack)
    second = build_report_input(proof_pack)

    assert first == second
    assert first.proof_pack_id == proof_pack.proof_pack_id
    assert first.proof_pack_content_hash == proof_pack.content_hash
    assert first.evidence_ref.ref_type == "DPM_PROOF_PACK_REPORT_INPUT"
    assert first.evidence_ref.content_hash == first.content_hash
    assert first.markdown_summary.startswith("# Pre-Trade Proof Pack")
    assert len(first.sections) == len(proof_pack.sections)
    assert first.redaction_policy == "NO_RAW_PAYLOADS"
    assert (
        first.client_communication_boundary.boundary_id
        == "DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY"
    )
    assert first.client_communication_boundary.supportability_state == "BLOCKED"
    assert first.client_communication_boundary.client_communication_projected is False
    assert first.client_communication_boundary.client_approval_projected is False
    assert first.client_communication_boundary.required_source_product == (
        "ClientCommunicationRecord:v1"
    )
    assert "client_contact" in first.client_communication_boundary.blocked_capabilities
    assert "certified_client_communication_source_owner" in (
        first.client_communication_boundary.promotion_requirements
    )
    assert "client_communication_consent_and_evidence_controls" in (
        first.client_communication_boundary.promotion_requirements
    )
    assert first.client_communication_boundary.content_hash.startswith("sha256:")


def test_report_input_carries_portfolio_memory_without_changing_evidence_hash() -> None:
    proof_pack = _proof_pack()
    without_context = build_report_input(proof_pack)
    memory_context = DpmPortfolioMemoryReportContext.model_validate(
        {
            "portfolio_id": proof_pack.portfolio_id,
            "supportability_state": "READY",
            "event_count": 1,
            "source_systems": ["lotus-manage"],
            "reason_codes": ["proof_pack_ready"],
            "content_hash": "sha256:portfolio-memory",
            "governance_policy": {
                "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
                "redaction_policy": "NO_RAW_PAYLOADS",
                "audit_policy": "AUDIT_READ_AND_EXPORT",
                "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
            },
            "event_refs": [
                {
                    "event_identity": "lotus-manage:DPM_PRE_TRADE_PROOF_PACK:dpp_001:sha256:proof-pack",
                    "event_type": "PROOF_PACK_CREATED",
                    "source_system": "lotus-manage",
                    "source_type": "DPM_PRE_TRADE_PROOF_PACK",
                    "source_id": proof_pack.proof_pack_id,
                    "content_hash": proof_pack.content_hash,
                    "retention_policy": "DPM_PORTFOLIO_MEMORY_SOURCE_LINEAGE_7Y",
                    "redaction_policy": "NO_RAW_PAYLOADS",
                    "audit_policy": "AUDIT_READ_AND_EXPORT",
                    "access_classification": "CLIENT_CONFIDENTIAL_INTERNAL",
                }
            ],
        }
    )

    with_context = build_report_input(proof_pack, portfolio_memory_context=memory_context)

    assert with_context.portfolio_memory_context == memory_context
    assert with_context.content_hash == without_context.content_hash
    assert with_context.evidence_ref.content_hash == without_context.evidence_ref.content_hash


def test_ai_evidence_input_is_bounded_and_removes_forbidden_fields() -> None:
    proof_pack = _proof_pack()
    section = proof_pack.sections[0]
    section.facts["client_name"] = "Sensitive Name"
    section.facts["nested"] = {"raw_payload": {"secret": "value"}, "allowed": "kept"}

    ai_input = build_ai_evidence_input(proof_pack)
    payload = ai_input.model_dump(mode="json")

    assert ai_input.proof_pack_id == proof_pack.proof_pack_id
    assert ai_input.evidence_ref.ref_type == "DPM_PROOF_PACK_AI_EVIDENCE_INPUT"
    assert ai_input.evidence_ref.content_hash == ai_input.content_hash
    assert "client_name" in ai_input.forbidden_fields_removed
    assert "raw_payload" in ai_input.forbidden_fields_removed
    assert "secret" not in str(payload)
    assert "place_orders" in ai_input.forbidden_actions
    assert "score_portfolio_manager" in ai_input.forbidden_actions
    assert "generate_client_message" in ai_input.forbidden_actions
    assert (
        ai_input.client_communication_boundary.boundary_id
        == "DPM_PROOF_PACK_CLIENT_COMMUNICATION_BOUNDARY"
    )
    assert ai_input.client_communication_boundary.supportability_state == "BLOCKED"
    assert ai_input.client_communication_boundary.client_communication_projected is False
    assert ai_input.client_communication_boundary.client_approval_projected is False
    assert "client_message_generation" in (
        ai_input.client_communication_boundary.blocked_capabilities
    )
    assert_no_ai_forbidden_fields(payload)


def test_ai_forbidden_field_guardrail_detects_nested_list_payloads() -> None:
    with pytest.raises(ValueError, match="DPM_PROOF_PACK_AI_FORBIDDEN_FIELDS"):
        assert_no_ai_forbidden_fields({"sections": [{"client_id": "forbidden"}]})
