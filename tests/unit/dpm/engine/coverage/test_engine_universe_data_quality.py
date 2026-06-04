from decimal import Decimal

from src.core.rebalance.universe import (
    _add_model_target_to_universe,
    _add_portfolio_position_to_universe,
)
from src.core.rebalance.engine import run_simulation
from src.core.models import (
    EngineOptions,
)
from src.core.valuation import build_simulated_state
from tests.shared.assertions import assert_dq_contains, assert_status, find_excluded
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
from tests.unit.dpm.engine.coverage.helpers import usd_cash_portfolio


class TestUniverseAndDataQuality:
    def test_add_model_target_to_universe_tracks_sell_only_target(self):
        eligible_targets = {}
        excluded = []
        buy_list = []
        sell_list = []
        dq_log = {"shelf_missing": []}

        sell_only_excess = _add_model_target_to_universe(
            target=target("SELL_ONLY_ASSET", "0.25"),
            shelf_by_id={"SELL_ONLY_ASSET": shelf_entry("SELL_ONLY_ASSET", status="SELL_ONLY")},
            options=EngineOptions(),
            dq_log=dq_log,
            eligible_targets=eligible_targets,
            excluded=excluded,
            buy_list=buy_list,
            sell_list=sell_list,
        )

        assert sell_only_excess == Decimal("0.25")
        assert eligible_targets == {"SELL_ONLY_ASSET": Decimal("0.0")}
        assert buy_list == []
        assert sell_list == ["SELL_ONLY_ASSET"]
        assert excluded[0].reason_code == "SHELF_STATUS_SELL_ONLY"

    def test_add_portfolio_position_to_universe_locks_current_weight(self):
        portfolio = portfolio_snapshot(
            portfolio_id="pf_locked_position",
            positions=[position("SUSPENDED_ASSET", "2")],
            cash_balances=[cash("USD", "0")],
        )
        market_data = market_data_snapshot(prices=[price("SUSPENDED_ASSET", "50", "USD")])
        shelf = [shelf_entry("SUSPENDED_ASSET", status="SUSPENDED")]
        current_val = build_simulated_state(portfolio, market_data, shelf, {}, [])
        eligible_targets = {}
        excluded = []
        sell_list = []

        _add_portfolio_position_to_universe(
            position=portfolio.positions[0],
            shelf_by_id={"SUSPENDED_ASSET": shelf[0]},
            current_val=current_val,
            eligible_targets=eligible_targets,
            excluded=excluded,
            sell_list=sell_list,
        )

        assert eligible_targets == {"SUSPENDED_ASSET": current_val.positions[0].weight}
        assert excluded[0].reason_code == "LOCKED_DUE_TO_SUSPENDED"
        assert sell_list == []

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
