from decimal import Decimal

from src.core.dpm_engine import run_simulation
from src.core.models import EngineOptions, Money, ValuationMode
from tests.shared.assertions import assert_status
from tests.shared.factories import position, price, shelf_entry


class TestFinalStatusAndBlocking:
    def test_reconciliation_failure_block(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions[0].market_value = Money(amount=Decimal("9999999"), currency="USD")

        result = run_simulation(
            pf,
            mkt,
            model,
            shelf,
            EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT),
        )

        assert_status(result, "BLOCKED")
        blocker = next(r for r in result.rule_results if r.rule_id == "RECONCILIATION")
        assert blocker.status == "FAIL"

    def test_hard_fail_shorting(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions.append(position("SHORT_POS", "-10"))
        mkt.prices.append(price("SHORT_POS", "100", "USD"))
        shelf.append(shelf_entry("SHORT_POS", status="APPROVED"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        assert_status(result, "BLOCKED")
        assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    def test_soft_fail_status(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        result = run_simulation(
            pf, mkt, model, shelf, EngineOptions(cash_band_min_weight=Decimal("0.05"))
        )

        assert_status(result, "PENDING_REVIEW")
