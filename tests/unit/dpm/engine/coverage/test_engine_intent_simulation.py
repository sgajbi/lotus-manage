from decimal import Decimal

from src.core.rebalance.execution import (
    _after_simulation_options,
    _apply_execution_intents,
    _append_projected_cash_fx_intents,
    _fx_intent_for_projected_cash_balance,
    _link_execution_dependencies,
    _project_cash_after_security_trades,
    _settlement_blocked_simulation_result,
    build_settlement_ladder,
)
from src.core.rebalance.engine import _generate_fx_and_simulate, run_simulation
from src.core.models import (
    CashLadderBreach,
    EngineOptions,
    FxSpotIntent,
    IntentRationale,
    SecurityTradeIntent,
    ValuationMode,
)
from tests.shared.assertions import security_intents
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)
from tests.unit.dpm.engine.coverage.helpers import empty_diagnostics, usd_cash_portfolio


class TestIntentDependenciesAndSimulation:
    def test_fx_intent_for_projected_cash_balance_builds_funding_intent(self):
        intent = _fx_intent_for_projected_cash_balance(
            currency="EUR",
            balance=Decimal("-100"),
            base_currency="USD",
            rate_to_base=Decimal("1.2"),
            intent_id="oi_fx_1",
            fx_buffer_pct=Decimal("0.05"),
        )

        assert intent is not None
        assert intent.intent_id == "oi_fx_1"
        assert intent.pair == "EUR/USD"
        assert intent.buy_currency == "EUR"
        assert intent.buy_amount == Decimal("105.00")
        assert intent.sell_currency == "USD"
        assert intent.sell_amount_estimated == Decimal("126.000")
        assert intent.rationale.code == "FUNDING"

    def test_fx_intent_for_projected_cash_balance_builds_sweep_intent(self):
        intent = _fx_intent_for_projected_cash_balance(
            currency="EUR",
            balance=Decimal("100"),
            base_currency="USD",
            rate_to_base=Decimal("1.2"),
            intent_id="oi_fx_2",
            fx_buffer_pct=Decimal("0.05"),
        )

        assert intent is not None
        assert intent.intent_id == "oi_fx_2"
        assert intent.pair == "EUR/USD"
        assert intent.buy_currency == "USD"
        assert intent.buy_amount == Decimal("120.0")
        assert intent.sell_currency == "EUR"
        assert intent.sell_amount_estimated == Decimal("100")
        assert intent.rationale.code == "SWEEP"

    def test_fx_intent_for_projected_cash_balance_skips_zero_balance(self):
        assert (
            _fx_intent_for_projected_cash_balance(
                currency="EUR",
                balance=Decimal("0"),
                base_currency="USD",
                rate_to_base=Decimal("1.2"),
                intent_id="oi_fx_3",
                fx_buffer_pct=Decimal("0.05"),
            )
            is None
        )

    def test_link_execution_dependencies_defaults_to_same_currency_sell_dependency(self):
        sell = SecurityTradeIntent(
            intent_id="oi_sell_eur",
            instrument_id="EQ_EU_SELL",
            side="SELL",
            quantity=Decimal("1"),
            notional={"amount": Decimal("100"), "currency": "EUR"},
            notional_base={"amount": Decimal("120"), "currency": "USD"},
        )
        buy = SecurityTradeIntent(
            intent_id="oi_buy_eur",
            instrument_id="EQ_EU_BUY",
            side="BUY",
            quantity=Decimal("1"),
            notional={"amount": Decimal("100"), "currency": "EUR"},
            notional_base={"amount": Decimal("120"), "currency": "USD"},
        )

        _link_execution_dependencies(
            intents=[sell, buy],
            fx_intent_id_by_currency={"EUR": "oi_fx_eur"},
            include_same_currency_sell_dependency=None,
        )

        assert buy.dependencies == ["oi_fx_eur", "oi_sell_eur"]

    def test_link_execution_dependencies_respects_same_currency_sell_opt_out(self):
        sell = SecurityTradeIntent(
            intent_id="oi_sell_eur",
            instrument_id="EQ_EU_SELL",
            side="SELL",
            quantity=Decimal("1"),
            notional={"amount": Decimal("100"), "currency": "EUR"},
            notional_base={"amount": Decimal("120"), "currency": "USD"},
        )
        buy = SecurityTradeIntent(
            intent_id="oi_buy_eur",
            instrument_id="EQ_EU_BUY",
            side="BUY",
            quantity=Decimal("1"),
            notional={"amount": Decimal("100"), "currency": "EUR"},
            notional_base={"amount": Decimal("120"), "currency": "USD"},
        )

        _link_execution_dependencies(
            intents=[sell, buy],
            fx_intent_id_by_currency={"EUR": "oi_fx_eur"},
            include_same_currency_sell_dependency=False,
        )

        assert buy.dependencies == ["oi_fx_eur"]

    def test_project_cash_after_security_trades_applies_buy_sell_and_skips_missing_notional(self):
        portfolio = portfolio_snapshot(
            portfolio_id="pf_project_cash",
            base_currency="USD",
            cash_balances=[cash("USD", "1000"), cash("EUR", "50")],
        )
        intents = [
            SecurityTradeIntent(
                intent_id="oi_buy",
                instrument_id="EQ_US",
                side="BUY",
                quantity=Decimal("1"),
                notional={"amount": Decimal("100"), "currency": "USD"},
                notional_base={"amount": Decimal("100"), "currency": "USD"},
            ),
            SecurityTradeIntent(
                intent_id="oi_sell",
                instrument_id="EQ_EU",
                side="SELL",
                quantity=Decimal("1"),
                notional={"amount": Decimal("25"), "currency": "EUR"},
                notional_base={"amount": Decimal("30"), "currency": "USD"},
            ),
            SecurityTradeIntent(
                intent_id="oi_missing_notional",
                instrument_id="EQ_SKIP",
                side="BUY",
                quantity=Decimal("1"),
                notional=None,
                notional_base=None,
            ),
        ]

        projected = _project_cash_after_security_trades(
            portfolio=portfolio,
            intents=intents,
        )

        assert projected == {"USD": Decimal("900"), "EUR": Decimal("75")}

    def test_append_projected_cash_fx_intents_adds_funding_and_sweep_intents(self):
        portfolio = portfolio_snapshot(portfolio_id="pf_fx_append", base_currency="USD")
        diagnostics = empty_diagnostics()
        intents = []

        blocked, fx_map = _append_projected_cash_fx_intents(
            projected_cash={"USD": Decimal("1000"), "EUR": Decimal("-100"), "GBP": Decimal("50")},
            portfolio=portfolio,
            market_data=market_data_snapshot(
                fx_rates=[
                    fx("EUR/USD", "1.2"),
                    fx("GBP/USD", "1.3"),
                ]
            ),
            intents=intents,
            options=EngineOptions(fx_buffer_pct=Decimal("0.05")),
            diagnostics=diagnostics,
        )

        assert blocked is False
        assert fx_map == {"EUR": "oi_fx_1"}
        assert [intent.intent_id for intent in intents] == ["oi_fx_1", "oi_fx_2"]
        assert intents[0].buy_currency == "EUR"
        assert intents[0].sell_currency == "USD"
        assert intents[1].buy_currency == "USD"
        assert intents[1].sell_currency == "GBP"
        assert diagnostics.data_quality == {}

    def test_append_projected_cash_fx_intents_blocks_on_missing_fx(self):
        portfolio = portfolio_snapshot(portfolio_id="pf_fx_missing_append", base_currency="USD")
        diagnostics = empty_diagnostics()
        intents = []

        blocked, fx_map = _append_projected_cash_fx_intents(
            projected_cash={"EUR": Decimal("-100")},
            portfolio=portfolio,
            market_data=market_data_snapshot(),
            intents=intents,
            options=EngineOptions(block_on_missing_fx=True),
            diagnostics=diagnostics,
        )

        assert blocked is True
        assert fx_map == {}
        assert intents == []
        assert diagnostics.data_quality == {"fx_missing": ["EUR/USD"]}

    def test_settlement_blocked_simulation_result_builds_rule_and_warning(self):
        portfolio = portfolio_snapshot(
            portfolio_id="pf_settlement_block_helper",
            base_currency="USD",
            cash_balances=[cash("USD", "100")],
        )
        diagnostics = empty_diagnostics()
        diagnostics.cash_ladder_breaches.append(
            CashLadderBreach(
                date_offset=1,
                currency="USD",
                projected_balance=Decimal("-25"),
                allowed_floor=Decimal("0"),
                reason_code="OVERDRAFT_ON_T_PLUS_1",
            )
        )

        _, blocked_state, rules, status, recon = _settlement_blocked_simulation_result(
            portfolio=portfolio,
            market_data=market_data_snapshot(),
            shelf=[],
            intents=[],
            options=EngineOptions(),
            diagnostics=diagnostics,
        )

        assert blocked_state.cash_balances[0].currency == "USD"
        assert blocked_state.cash_balances[0].amount == Decimal("100")
        assert status == "BLOCKED"
        assert recon is None
        assert diagnostics.warnings == ["OVERDRAFT_ON_T_PLUS_1"]
        assert rules[0].rule_id == "SETTLEMENT_CASH_LADDER"
        assert rules[0].measured == Decimal("25")

    def test_apply_execution_intents_returns_mutated_copy_for_fx_intent(self):
        portfolio = portfolio_snapshot(
            portfolio_id="pf_apply_execution_intents",
            base_currency="USD",
            cash_balances=[cash("USD", "100"), cash("EUR", "0")],
        )

        after = _apply_execution_intents(
            portfolio=portfolio,
            intents=[
                FxSpotIntent(
                    intent_id="oi_fx_eur",
                    pair="EUR/USD",
                    buy_currency="EUR",
                    buy_amount=Decimal("10"),
                    sell_currency="USD",
                    sell_amount_estimated=Decimal("12"),
                    rationale=IntentRationale(code="FUNDING", message="Fund EUR"),
                )
            ],
        )

        assert portfolio.cash_balances[0].amount == Decimal("100")
        assert {cash_balance.currency: cash_balance.amount for cash_balance in after.cash_balances}[
            "USD"
        ] == Decimal("88")
        assert {cash_balance.currency: cash_balance.amount for cash_balance in after.cash_balances}[
            "EUR"
        ] == Decimal("10")

    def test_after_simulation_options_preserves_trust_snapshot_or_calculates_result(self):
        trust_options = EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT)
        calculated_options = EngineOptions(valuation_mode=ValuationMode.CALCULATED)

        assert (
            _after_simulation_options(trust_options).valuation_mode == ValuationMode.TRUST_SNAPSHOT
        )
        assert (
            _after_simulation_options(calculated_options).valuation_mode == ValuationMode.CALCULATED
        )

    def test_dependency_linking_explicit(self):
        pf = usd_cash_portfolio("dep_test")
        mkt = market_data_snapshot(
            prices=[price("GBP_STK", "100", "GBP")],
            fx_rates=[fx("GBP/USD", "1.2")],
        )
        shelf = [shelf_entry("GBP_STK", status="APPROVED")]
        model = model_portfolio(targets=[target("GBP_STK", "1.0")])

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(i for i in security_intents(result) if i.side == "BUY")
        assert len(buy.dependencies) > 0

    def test_dependency_sell_linking(self):
        pf = portfolio_snapshot(
            portfolio_id="p_chain",
            base_currency="USD",
            positions=[position("GBP_STK", "10")],
        )
        mkt = market_data_snapshot(
            prices=[
                price("GBP_STK", "100", "GBP"),
                price("GBP_STK_B", "100", "GBP"),
            ],
            fx_rates=[fx("GBP/USD", "1.2")],
        )
        shelf = [
            shelf_entry("GBP_STK", status="APPROVED"),
            shelf_entry("GBP_STK_B", status="APPROVED"),
        ]
        model = model_portfolio(targets=[target("GBP_STK_B", "1.0"), target("GBP_STK", "0.0")])

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        buy = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK_B")
        sell = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK")
        assert sell.intent_id in buy.dependencies

    def test_dependency_sell_linking_can_be_disabled(self):
        pf = portfolio_snapshot(
            portfolio_id="p_chain_opt_out",
            base_currency="USD",
            positions=[position("GBP_STK", "10")],
        )
        mkt = market_data_snapshot(
            prices=[
                price("GBP_STK", "100", "GBP"),
                price("GBP_STK_B", "100", "GBP"),
            ],
            fx_rates=[fx("GBP/USD", "1.2")],
        )
        shelf = [
            shelf_entry("GBP_STK", status="APPROVED"),
            shelf_entry("GBP_STK_B", status="APPROVED"),
        ]
        model = model_portfolio(targets=[target("GBP_STK_B", "1.0"), target("GBP_STK", "0.0")])

        result = run_simulation(
            pf,
            mkt,
            model,
            shelf,
            EngineOptions(link_buy_to_same_currency_sell_dependency=False),
        )

        buy = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK_B")
        sell = next(i for i in security_intents(result) if i.instrument_id == "GBP_STK")
        assert sell.intent_id not in buy.dependencies

    def test_generate_fx_and_simulate_blocks_on_missing_fx_when_enabled(self):
        pf = portfolio_snapshot(
            portfolio_id="pf_fx_block",
            base_currency="USD",
            cash_balances=[cash("EUR", "100")],
        )
        diagnostics = empty_diagnostics()

        intents, after, rules, status, recon = _generate_fx_and_simulate(
            portfolio=pf,
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=[],
            options=EngineOptions(block_on_missing_fx=True),
            total_val_before=Decimal("0"),
            diagnostics=diagnostics,
        )

        assert status == "BLOCKED"
        assert rules == []
        assert recon is None
        assert intents == []
        assert after.portfolio_id == pf.portfolio_id
        assert diagnostics.data_quality["fx_missing"] == ["EUR/USD"]

    def test_generate_fx_and_simulate_continues_on_missing_fx_when_disabled(self):
        diagnostics = empty_diagnostics()

        _, _, _, status, _ = _generate_fx_and_simulate(
            portfolio=portfolio_snapshot(
                portfolio_id="pf_fx_continue",
                base_currency="USD",
                cash_balances=[cash("EUR", "100")],
            ),
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=[],
            options=EngineOptions(block_on_missing_fx=False),
            total_val_before=Decimal("0"),
            diagnostics=diagnostics,
        )

        assert status in {"READY", "PENDING_REVIEW"}
        assert diagnostics.data_quality["fx_missing"].count("EUR/USD") >= 1

    def test_generate_fx_and_simulate_skips_security_intent_without_notional(self):
        diagnostics = empty_diagnostics()
        intents = [
            SecurityTradeIntent(
                intent_id="oi_incomplete",
                instrument_id="EQ_1",
                side="BUY",
                quantity=Decimal("1"),
                notional=None,
                notional_base=None,
            )
        ]

        _, _, _, status, _ = _generate_fx_and_simulate(
            portfolio=portfolio_snapshot(
                portfolio_id="pf_skip_missing_notional",
                base_currency="USD",
                cash_balances=[cash("USD", "1000")],
            ),
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
            shelf=[],
            intents=intents,
            options=EngineOptions(),
            total_val_before=Decimal("1000"),
            diagnostics=diagnostics,
        )

        assert status in {"READY", "PENDING_REVIEW"}

    def test_build_settlement_ladder_skips_security_intent_without_notional(self):
        diagnostics = empty_diagnostics()
        portfolio = portfolio_snapshot(
            portfolio_id="pf_ladder_missing_notional",
            base_currency="USD",
            cash_balances=[cash("USD", "1000")],
        )
        intents = [
            SecurityTradeIntent(
                intent_id="oi_incomplete_ladder",
                instrument_id="EQ_1",
                side="BUY",
                quantity=Decimal("1"),
                notional=None,
                notional_base=None,
            )
        ]

        build_settlement_ladder(
            portfolio=portfolio,
            shelf=[],
            intents=intents,
            options=EngineOptions(enable_settlement_awareness=True),
            diagnostics=diagnostics,
        )

        assert diagnostics.cash_ladder_breaches == []
