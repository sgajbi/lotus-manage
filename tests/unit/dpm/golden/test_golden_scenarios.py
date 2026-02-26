"""
FILE: tests/golden/test_golden_scenarios.py
"""

import glob
import json
import os
from decimal import Decimal
from typing import Any, Dict

import pytest

from src.core.dpm_engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)


def load_golden_file(filename: str) -> Dict[str, Any]:
    path = os.path.join(os.path.dirname(__file__), "../golden_data", filename)
    with open(path, "r") as f:
        return json.loads(f.read(), parse_float=Decimal)


GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "../golden_data")


def _is_rebalance_golden_fixture(path: str) -> bool:
    with open(path, "r") as file:
        data = json.loads(file.read())
    return "inputs" in data


SCENARIOS = sorted(
    os.path.basename(path)
    for path in glob.glob(os.path.join(GOLDEN_DIR, "*.json"))
    if _is_rebalance_golden_fixture(path)
)


@pytest.mark.parametrize("filename", SCENARIOS)
def test_golden_scenario(filename):
    data = load_golden_file(filename)
    inputs = data["inputs"]
    expected = data.get("expected_output") or data.get("expected_outputs")
    assert expected is not None, f"Missing expected output block in {filename}"

    # 1. Deserialize Inputs
    portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**inputs["market_data_snapshot"])
    model = ModelPortfolio(**inputs["model_portfolio"])
    shelf = [ShelfEntry(**entry) for entry in inputs["shelf_entries"]]
    options = EngineOptions(**inputs.get("options", {}))

    # 2. Run Engine
    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=options,
        request_hash="golden_test",
    )

    # 3. Assertions
    # Status
    assert result.status == expected["status"]

    # Target Weights
    if "target" in expected:
        for exp_t in expected["target"]["targets"]:
            actual_t = next(
                (t for t in result.target.targets if t.instrument_id == exp_t["instrument_id"]),
                None,
            )
            assert actual_t is not None, f"Missing target {exp_t['instrument_id']}"
            # Exact decimal match expected for golden
            assert actual_t.final_weight == Decimal(str(exp_t["final_weight"]))

            if "tags" in exp_t:
                assert set(actual_t.tags) == set(exp_t["tags"])

    # Intents
    if "intents" in expected:
        assert len(result.intents) == len(expected["intents"])
        for i, exp_intent in enumerate(expected["intents"]):
            act_intent = result.intents[i]
            assert act_intent.intent_type == exp_intent["intent_type"]
            if "instrument_id" in exp_intent:
                assert act_intent.instrument_id == exp_intent["instrument_id"]
            if "side" in exp_intent:
                assert act_intent.side == exp_intent["side"]
            if "quantity" in exp_intent:
                assert act_intent.quantity == Decimal(str(exp_intent["quantity"]))
            if "notional" in exp_intent:
                assert act_intent.notional.amount == Decimal(str(exp_intent["notional"]["amount"]))

    # Diagnostics
    if "diagnostics" in expected:
        if "warnings" in expected["diagnostics"]:
            assert set(result.diagnostics.warnings) == set(expected["diagnostics"]["warnings"])
        if "dropped_intents" in expected["diagnostics"]:
            assert len(result.diagnostics.dropped_intents) == len(
                expected["diagnostics"]["dropped_intents"]
            )
            for i, exp_drop in enumerate(expected["diagnostics"]["dropped_intents"]):
                act_drop = result.diagnostics.dropped_intents[i]
                assert act_drop.instrument_id == exp_drop["instrument_id"]
                assert act_drop.reason == exp_drop["reason"]
                assert act_drop.potential_notional.amount == Decimal(
                    str(exp_drop["potential_notional"]["amount"])
                )
                assert (
                    act_drop.potential_notional.currency
                    == exp_drop["potential_notional"]["currency"]
                )
                assert act_drop.score == Decimal(str(exp_drop["score"]))

    # After Simulated Attributes (RFC-0008 check)
    if "after_simulated" in expected and "allocation_by_attribute" in expected["after_simulated"]:
        exp_attrs = expected["after_simulated"]["allocation_by_attribute"]
        act_attrs = result.after_simulated.allocation_by_attribute

        for attr_key, exp_list in exp_attrs.items():
            assert attr_key in act_attrs
            for exp_item in exp_list:
                act_item = next((a for a in act_attrs[attr_key] if a.key == exp_item["key"]), None)
                assert act_item is not None
                assert act_item.weight == Decimal(str(exp_item["weight"]))
