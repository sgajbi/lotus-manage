from datetime import datetime, timezone

import pytest

from src.core.construction import (
    ConstructionAlternativeSelection,
    build_alternative_set,
    build_rebalance_result_alternative,
)
from src.core.models import EngineOptions, RebalanceResult
from src.core.proof_packs import (
    ProofPackSourceValidationError,
    build_proof_pack_from_run,
    build_proof_pack_from_selected_alternative,
)
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import DpmRunRecord, DpmRunWorkflowDecisionRecord
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
    portfolio = portfolio_snapshot(
        portfolio_id="pf_proof_pack_1",
        base_currency="USD",
        positions=[position("EQ_A", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "100", "USD"),
            price("EQ_B", "100", "USD"),
        ]
    )
    model = model_portfolio(
        targets=[
            target("EQ_A", "0.50"),
            target("EQ_B", "0.50"),
        ]
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
    ]
    return run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(),
        request_hash="sha256:proof-pack-test",
        correlation_id="corr-proof-pack-test",
    )


def _run_record(*, result: RebalanceResult | None = None) -> DpmRunRecord:
    resolved_result = result or _ready_rebalance_result()
    return DpmRunRecord(
        rebalance_run_id=resolved_result.rebalance_run_id,
        correlation_id=resolved_result.correlation_id,
        request_hash="sha256:proof-pack-test",
        idempotency_key="idem-proof-pack-test",
        portfolio_id="pf_proof_pack_1",
        created_at=CREATED_AT,
        result_json=resolved_result.model_dump(mode="json"),
    )


def _section(pack, section_type: str):
    return next(section for section in pack.sections if section.section_type == section_type)


def test_direct_run_proof_pack_generates_every_section_with_truthful_states() -> None:
    run = _run_record()
    decision = DpmRunWorkflowDecisionRecord(
        decision_id="dwd_proof_pack_1",
        run_id=run.rebalance_run_id,
        action="APPROVE",
        reason_code="REVIEW_APPROVED",
        comment="Evidence reviewed.",
        actor_id="reviewer_001",
        decided_at=CREATED_AT,
        correlation_id="corr-workflow-proof-pack",
    )
    pack = build_proof_pack_from_run(
        run=run,
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
        workflow_decisions=[decision],
    )

    assert pack.source_type == "REBALANCE_RUN"
    assert len(pack.sections) == 27
    assert pack.content_hash.startswith("sha256:")
    assert pack.source_hashes["rebalance_run"].startswith("sha256:")
    assert _section(pack, "before_state").state == "READY"
    assert _section(pack, "trade_intents").metrics["trade_count"] == 2
    assert _section(pack, "approval_requirements").metrics["workflow_decision_count"] == 1
    assert any(event.event_type == "WORKFLOW_DECISION" for event in pack.decision_timeline.events)
    assert _section(pack, "selected_alternative").state == "DEGRADED"
    assert "DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE" in pack.supportability.reason_codes
    assert _section(pack, "reporting_refs").state == "DEGRADED"
    assert _section(pack, "ai_refs").state == "DEGRADED"
    assert pack.status == "DEGRADED"


def test_missing_mandate_identity_blocks_promotion_without_hiding_other_evidence() -> None:
    pack = build_proof_pack_from_run(
        run=_run_record(),
        created_by="pm_001",
        reason="Rebalance back to model after drift review.",
        created_at=CREATED_AT,
    )

    mandate = _section(pack, "mandate_context")
    assert mandate.state == "BLOCKED"
    assert "DPM_PROOF_PACK_MANDATE_ID_MISSING" in mandate.reason_codes
    assert pack.status == "BLOCKED"
    assert _section(pack, "before_state").state == "READY"


def test_proof_pack_hash_is_deterministic_for_equivalent_inputs() -> None:
    kwargs = {
        "run": _run_record(),
        "created_by": "pm_001",
        "reason": "Rebalance back to model after drift review.",
        "created_at": CREATED_AT,
        "mandate_id": "mandate_001",
    }

    first = build_proof_pack_from_run(**kwargs)
    second = build_proof_pack_from_run(**kwargs)

    assert first.content_hash == second.content_hash
    assert first.supportability.section_hashes == second.supportability.section_hashes


def test_selected_alternative_proof_pack_captures_method_trace_and_selection_event() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})
    selection = ConstructionAlternativeSelection(
        selection_id="sel_proof_pack_1",
        alternative_set_id="cas_proof_pack_1",
        alternative_id=alternative.alternative_id,
        selected_at=CREATED_AT,
        actor_id="pm_001",
        reason_code="MODEL_DRIFT_REVIEW",
        comment="Use explainable heuristic.",
        correlation_id="corr-selection-proof-pack",
    )

    pack = build_proof_pack_from_selected_alternative(
        alternative_set=alternative_set,
        selected_alternative_id=alternative.alternative_id,
        run=_run_record(result=result),
        selection=selection,
        created_by="pm_001",
        reason="Use selected alternative after drift review.",
        created_at=CREATED_AT,
        mandate_id="mandate_001",
    )

    selected = _section(pack, "selected_alternative")
    assert pack.source_type == "SELECTED_ALTERNATIVE"
    assert pack.alternative_set_id == "cas_proof_pack_1"
    assert pack.selected_alternative_id == alternative.alternative_id
    assert pack.correlation_id == "corr-selection-proof-pack"
    assert selected.state == "READY"
    assert selected.facts["method"] == "HEURISTIC_EXPLAINABLE"
    assert selected.facts["objective_trace"]
    assert selected.facts["constraint_trace"]
    assert pack.source_hashes["selected_alternative"].startswith("sha256:")
    assert [event.event_type for event in pack.decision_timeline.events] == [
        "REBALANCE_RUN_CREATED",
        "ALTERNATIVE_SET_GENERATED",
        "SELECTED_ALTERNATIVE",
        "PROOF_PACK_GENERATED",
    ]


def test_selected_alternative_builder_rejects_unknown_selection() -> None:
    result = _ready_rebalance_result()
    alternative = build_rebalance_result_alternative(result=result)
    alternative_set = build_alternative_set(
        alternative_set_id="cas_proof_pack_1",
        portfolio_id="pf_proof_pack_1",
        as_of="2026-05-03",
        alternatives=[alternative],
    ).model_copy(update={"generated_at": CREATED_AT})

    with pytest.raises(ProofPackSourceValidationError, match="DPM_SELECTED_ALTERNATIVE_NOT_FOUND"):
        build_proof_pack_from_selected_alternative(
            alternative_set=alternative_set,
            selected_alternative_id="missing",
            run=_run_record(result=result),
            created_by="pm_001",
            reason="Use selected alternative after drift review.",
            created_at=CREATED_AT,
            mandate_id="mandate_001",
        )
