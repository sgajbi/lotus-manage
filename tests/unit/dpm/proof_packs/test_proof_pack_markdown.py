from datetime import datetime, timezone

from src.core.models import EngineOptions, RebalanceResult
from src.core.proof_packs import build_proof_pack_from_run, render_proof_pack_markdown
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
            portfolio_id="pf_markdown_1",
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
        request_hash="sha256:proof-pack-markdown",
        correlation_id="corr-proof-pack-markdown",
    )


def _proof_pack():
    result = _ready_rebalance_result()
    run = DpmRunRecord(
        rebalance_run_id=result.rebalance_run_id,
        correlation_id=result.correlation_id,
        request_hash="sha256:proof-pack-markdown",
        idempotency_key="idem-proof-pack-markdown",
        portfolio_id="pf_markdown_1",
        created_at=CREATED_AT,
        result_json=result.model_dump(mode="json"),
    )
    return build_proof_pack_from_run(
        run=run,
        created_by="pm_markdown",
        reason="Rebalance back to target.",
        created_at=CREATED_AT,
        mandate_id="mandate_markdown_1",
    )


def test_markdown_summary_is_deterministic_and_exposes_evidence_gaps() -> None:
    proof_pack = _proof_pack()
    first = render_proof_pack_markdown(proof_pack)
    second = render_proof_pack_markdown(proof_pack)

    assert first == second
    assert first.startswith("# Pre-Trade Proof Pack ")
    assert "| `selected_alternative` | `DEGRADED` |" in first
    assert "`DPM_DIRECT_RUN_NO_SELECTED_ALTERNATIVE`" in first
    assert "| `reporting_refs` | `READY` |" in first
    assert "| `ai_refs` | `READY` |" in first
    assert "## Integrity" in first
    assert "Content hash: `sha256:" in first


def test_markdown_summary_has_stable_section_order() -> None:
    markdown = render_proof_pack_markdown(_proof_pack())

    decision_index = markdown.index("| `decision_summary` |")
    mandate_index = markdown.index("| `mandate_context` |")
    ai_index = markdown.index("| `ai_refs` |")

    assert decision_index < mandate_index < ai_index
