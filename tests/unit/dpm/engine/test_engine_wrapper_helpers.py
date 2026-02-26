from decimal import Decimal

import src.core.dpm.engine as dpm_engine


def test_to_weight_map_helper_returns_expected_mapping():
    trace = [
        type("Row", (), {"instrument_id": "EQ_1", "final_weight": Decimal("0.60")})(),
        type("Row", (), {"instrument_id": "EQ_2", "final_weight": Decimal("0.40")})(),
    ]
    assert dpm_engine._to_weight_map(trace) == {"EQ_1": Decimal("0.60"), "EQ_2": Decimal("0.40")}


def test_generate_targets_heuristic_wrapper_delegates(monkeypatch):
    captured = {}

    def _stub(**kwargs):
        captured.update(kwargs)
        return ["trace"], "READY"

    monkeypatch.setattr(dpm_engine, "generate_targets_heuristic_impl", _stub)
    result = dpm_engine._generate_targets_heuristic(
        model="model",
        eligible_targets={},
        buy_list=[],
        sell_only_excess={},
        shelf=[],
        options="options",
        total_val=Decimal("1"),
        base_ccy="USD",
        diagnostics="diag",
    )
    assert result == (["trace"], "READY")
    assert captured["model"] == "model"


def test_build_settlement_ladder_wrapper_delegates(monkeypatch):
    monkeypatch.setattr(
        dpm_engine,
        "build_settlement_ladder_impl",
        lambda *args: {"ok": args},
    )
    result = dpm_engine._build_settlement_ladder("pf", "shelf", "intents", "options", "diag")
    assert result["ok"][0] == "pf"
