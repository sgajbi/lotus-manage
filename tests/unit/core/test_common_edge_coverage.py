from decimal import Decimal

from src.core.common.intent_dependencies import link_buy_intent_dependencies
from src.core.common.simulation_shared import (
    apply_fx_spot_to_portfolio,
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    ensure_cash_balance,
    ensure_position,
    quantize_amount_for_currency,
    sort_execution_intents,
)
from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.compliance import RuleEngine
from src.core.models import (
    AllocationMetric,
    DiagnosticsData,
    EngineOptions,
    FxSpotIntent,
    Money,
    PortfolioSnapshot,
    PositionSummary,
    RuleResult,
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SecurityTradeIntent,
    SimulatedState,
    SuitabilityIssue,
    SuitabilityResult,
    SuitabilitySummary,
)


def test_simulation_shared_portfolio_mutation_and_status_edges() -> None:
    portfolio = PortfolioSnapshot(
        portfolio_id="PF", base_currency="JPY", positions=[], cash_balances=[]
    )
    buy = SecurityTradeIntent(
        intent_id="buy_jpy",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("2"),
        notional=Money(amount=Decimal("200"), currency="JPY"),
        notional_base=Money(amount=Decimal("200"), currency="JPY"),
    )
    sell_without_notional = SecurityTradeIntent(
        intent_id="sell_missing_notional",
        instrument_id="EQ_2",
        side="SELL",
    )
    add_to_existing = SecurityTradeIntent(
        intent_id="buy_more_jpy",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency="JPY"),
        notional_base=Money(amount=Decimal("100"), currency="JPY"),
    )

    apply_security_trade_to_portfolio(portfolio, sell_without_notional)
    apply_security_trade_to_portfolio(portfolio, buy)
    apply_security_trade_to_portfolio(portfolio, add_to_existing)
    apply_fx_spot_to_portfolio(
        portfolio,
        FxSpotIntent(
            intent_id="fx_jpy_usd",
            pair="JPY/USD",
            sell_currency="JPY",
            buy_currency="USD",
            sell_amount_estimated=Decimal("100"),
            buy_amount=Decimal("1"),
            fx_rate=Decimal("0.01"),
        ),
    )

    assert ensure_position(portfolio, "EQ_1").market_value.amount == Decimal("300")
    assert ensure_cash_balance(portfolio, "JPY").amount == Decimal("-400")
    assert quantize_amount_for_currency(Decimal("123.45"), "JPY") == Decimal("123")
    assert [intent.side for intent in sort_execution_intents([buy, sell_without_notional])] == [
        "SELL",
        "BUY",
    ]
    assert (
        derive_status_from_rules(
            [
                RuleResult(
                    rule_id="soft",
                    severity="SOFT",
                    status="FAIL",
                    measured=Decimal("1"),
                    threshold={"max": Decimal("0")},
                    reason_code="X",
                )
            ]
        )
        == "PENDING_REVIEW"
    )
    assert (
        derive_status_from_rules(
            [
                RuleResult(
                    rule_id="hard",
                    severity="HARD",
                    status="FAIL",
                    measured=Decimal("1"),
                    threshold={"max": Decimal("0")},
                    reason_code="X",
                )
            ]
        )
        == "BLOCKED"
    )
    assert (
        build_reconciliation(
            Decimal("0"),
            Decimal("-100"),
            Decimal("-100"),
            "JPY",
            use_absolute_scale=True,
        )[0].status
        == "OK"
    )


def test_workflow_gate_decision_covers_suitability_and_mandate_paths() -> None:
    diagnostics = DiagnosticsData(
        data_quality={"price_missing": ["EQ_1"], "fx_missing": ["USD/SGD"]},
        suppressed_intents=[],
        warnings=[],
    )
    suitability = SuitabilityResult(
        summary=SuitabilitySummary(
            new_count=1,
            resolved_count=0,
            persistent_count=0,
            highest_severity_new="HIGH",
        ),
        recommended_gate="COMPLIANCE_REVIEW",
        issues=[
            SuitabilityIssue(
                issue_id="issue-high",
                issue_key="concentration",
                dimension="CONCENTRATION",
                severity="HIGH",
                status_change="NEW",
                summary="Concentration issue.",
                evidence=SuitabilityEvidence(
                    as_of="2026-04-10",
                    snapshot_ids=SuitabilityEvidenceSnapshotIds(
                        portfolio_snapshot_id="pf",
                        market_data_snapshot_id="md",
                    ),
                ),
            ),
            SuitabilityIssue(
                issue_id="issue-old",
                issue_key="known",
                dimension="LIQUIDITY",
                severity="MEDIUM",
                status_change="PERSISTENT",
                summary="Existing issue.",
                evidence=SuitabilityEvidence(
                    as_of="2026-04-10",
                    snapshot_ids=SuitabilityEvidenceSnapshotIds(
                        portfolio_snapshot_id="pf",
                        market_data_snapshot_id="md",
                    ),
                ),
            ),
        ],
    )

    decision = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=suitability,
        diagnostics=diagnostics,
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )

    assert decision.gate == "COMPLIANCE_REVIEW_REQUIRED"
    assert decision.summary.new_high_suitability_count == 1
    assert {reason.reason_code for reason in decision.reasons} >= {
        "DATA_QUALITY_MISSING_PRICE",
        "DATA_QUALITY_MISSING_FX",
        "NEW_HIGH_SUITABILITY_ISSUE",
    }

    mandate_decision = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=None,
        options=EngineOptions(workflow_requires_mandate_approval=True),
        default_requires_mandate_approval=False,
    )
    assert mandate_decision.gate == "MANDATE_APPROVAL_REQUIRED"

    medium_suitability = SuitabilityResult(
        summary=SuitabilitySummary(
            new_count=1,
            resolved_count=0,
            persistent_count=0,
            highest_severity_new="MEDIUM",
        ),
        recommended_gate="RISK_REVIEW",
        issues=[
            SuitabilityIssue(
                issue_id="issue-medium",
                issue_key="liquidity",
                dimension="LIQUIDITY",
                severity="MEDIUM",
                status_change="NEW",
                summary="Liquidity issue.",
                evidence=SuitabilityEvidence(
                    as_of="2026-04-10",
                    snapshot_ids=SuitabilityEvidenceSnapshotIds(
                        portfolio_snapshot_id="pf",
                        market_data_snapshot_id="md",
                    ),
                ),
            )
        ],
    )
    medium_decision = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=medium_suitability,
        diagnostics=None,
        options=EngineOptions(),
        default_requires_mandate_approval=False,
    )
    assert medium_decision.gate == "RISK_REVIEW_REQUIRED"
    assert medium_decision.summary.new_medium_suitability_count == 1


def test_intent_dependency_linking_and_simulated_state_edges() -> None:
    sell = SecurityTradeIntent(
        intent_id="sell_1",
        instrument_id="EQ_SELL",
        side="SELL",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("10"), currency="USD"),
    )
    buy = SecurityTradeIntent(
        intent_id="buy_1",
        instrument_id="EQ_BUY",
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("10"), currency="USD"),
    )

    link_buy_intent_dependencies(
        [sell, buy],
        fx_intent_id_by_currency={"USD": "fx_1"},
        include_same_currency_sell_dependency=True,
    )

    assert buy.dependencies == ["fx_1", "sell_1"]

    state = SimulatedState(
        total_value=Money(amount=Decimal("100"), currency="USD"),
        positions=[
            PositionSummary(
                instrument_id="EQ_1",
                quantity=Decimal("-1"),
                instrument_currency="USD",
                value_in_instrument_ccy=Money(amount=Decimal("-10"), currency="USD"),
                value_in_base_ccy=Money(amount=Decimal("-10"), currency="USD"),
                weight=Decimal("-0.1"),
            )
        ],
        cash_balances=[],
        allocation_by_asset_class=[
            AllocationMetric(
                key="CASH",
                weight=Decimal("0.1"),
                value=Money(amount=Decimal("10"), currency="USD"),
            )
        ],
        allocation_by_instrument=[
            AllocationMetric(
                key="EQ_1",
                weight=Decimal("0.2"),
                value=Money(amount=Decimal("20"), currency="USD"),
            )
        ],
    )
    assert state.positions[0].quantity < 0


def test_rule_engine_flags_single_position_limit_breaches() -> None:
    state = SimulatedState(
        total_value=Money(amount=Decimal("100"), currency="USD"),
        positions=[],
        cash_balances=[],
        allocation_by_asset_class=[
            AllocationMetric(
                key="CASH",
                weight=Decimal("0.05"),
                value=Money(amount=Decimal("5"), currency="USD"),
            )
        ],
        allocation_by_instrument=[
            AllocationMetric(
                key="EQ_CONCENTRATED",
                weight=Decimal("0.75"),
                value=Money(amount=Decimal("75"), currency="USD"),
            )
        ],
    )

    results = RuleEngine.evaluate(
        state=state,
        options=EngineOptions(single_position_max_weight=Decimal("0.50")),
        diagnostics=DiagnosticsData(data_quality={}, suppressed_intents=[], warnings=[]),
    )

    assert any(
        result.rule_id == "SINGLE_POSITION_MAX"
        and result.status == "FAIL"
        and result.reason_code == "LIMIT_BREACH"
        for result in results
    )
