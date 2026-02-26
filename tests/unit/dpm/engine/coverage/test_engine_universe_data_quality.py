from src.core.dpm_engine import run_simulation
from src.core.models import (
    EngineOptions,
)
from src.core.valuation import build_simulated_state
from tests.shared.assertions import assert_dq_contains, assert_status, find_excluded
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    position,
    price,
    shelf_entry,
    target,
)
from tests.unit.dpm.engine.coverage.helpers import usd_cash_portfolio


class TestUniverseAndDataQuality:
    def test_engine_restricted_logic(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        result = run_simulation(pf, mkt, model, shelf, EngineOptions(allow_restricted=False))
        excl = find_excluded(result, "LOCKED_ASSET")
        assert excl is not None
        assert "LOCKED_DUE_TO_RESTRICTED" in excl.reason_code

    def test_universe_suspended_exclusion(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        model = model_portfolio(targets=[target("SUSPENDED_ASSET", "0.1")])
        shelf.append(shelf_entry("SUSPENDED_ASSET", status="SUSPENDED"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        excl = find_excluded(result, "SUSPENDED_ASSET")
        assert excl is not None
        assert "SHELF_STATUS_SUSPENDED" in excl.reason_code

    def test_universe_missing_shelf_locked(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions.append(position("GHOST_ASSET", "10"))
        mkt.prices.append(price("GHOST_ASSET", "100", "USD"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        excl = find_excluded(result, "GHOST_ASSET")
        assert excl is not None
        assert "LOCKED_DUE_TO_MISSING_SHELF" in excl.reason_code

    def test_universe_missing_shelf_locked_for_negative_quantity_position(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions.append(position("SHORT_GHOST", "-5"))
        mkt.prices.append(price("SHORT_GHOST", "100", "USD"))

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        excl = find_excluded(result, "SHORT_GHOST")
        assert excl is not None
        assert "LOCKED_DUE_TO_MISSING_SHELF" in excl.reason_code

    def test_blocked_when_model_target_missing_from_shelf(self):
        pf = usd_cash_portfolio("pf_missing_shelf")
        mkt = market_data_snapshot(prices=[price("MODEL_ONLY", "10", "USD")], fx_rates=[])
        model = model_portfolio(targets=[target("MODEL_ONLY", "1.0")])

        result = run_simulation(pf, mkt, model, shelf=[], options=EngineOptions())

        assert_status(result, "BLOCKED")
        assert_dq_contains(result, "shelf_missing", "MODEL_ONLY")

    def test_valuation_missing_fx_log(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        pf.positions.append(position("NO_FX_ASSET", "10"))
        mkt.prices.append(price("NO_FX_ASSET", "100", "KRW"))
        pf.cash_balances.append(cash("KRW", "500"))
        dq = {}
        warns = []

        build_simulated_state(pf, mkt, shelf, dq, warns)

        assert "KRW/USD" in dq.get("fx_missing", [])
