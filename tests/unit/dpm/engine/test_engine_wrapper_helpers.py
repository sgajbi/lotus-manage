from decimal import Decimal

import src.core.rebalance.engine as dpm_engine


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


def test_compare_target_methods_if_requested_skips_disabled_comparison(monkeypatch):
    def _unexpected(**kwargs):
        raise AssertionError("comparison should not be called")

    monkeypatch.setattr(dpm_engine, "_compare_target_generation_methods", _unexpected)
    diagnostics = dpm_engine.make_diagnostics_data()

    result = dpm_engine._compare_target_methods_if_requested(
        model="model",
        eligible_targets={},
        buy_list=[],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=dpm_engine.EngineOptions(compare_target_methods=False),
        total_val=Decimal("1"),
        base_ccy="USD",
        primary_trace=[],
        primary_status="READY",
        diagnostics=diagnostics,
    )

    assert result is None
    assert diagnostics.warnings == []


def test_compare_target_methods_if_requested_records_divergence_warnings(monkeypatch):
    captured = {}

    def _stub(**kwargs):
        captured.update(kwargs)
        return {
            "primary_status": "READY",
            "alternate_status": "PENDING_REVIEW",
            "differing_instruments": ["EQ_1"],
        }

    monkeypatch.setattr(dpm_engine, "_compare_target_generation_methods", _stub)
    diagnostics = dpm_engine.make_diagnostics_data()

    result = dpm_engine._compare_target_methods_if_requested(
        model="model",
        eligible_targets={"EQ_1": Decimal("0.5")},
        buy_list=["EQ_1"],
        sell_only_excess=Decimal("0"),
        shelf=[],
        options=dpm_engine.EngineOptions(compare_target_methods=True),
        total_val=Decimal("1"),
        base_ccy="USD",
        primary_trace=[],
        primary_status="READY",
        diagnostics=diagnostics,
    )

    assert result == {
        "primary_status": "READY",
        "alternate_status": "PENDING_REVIEW",
        "differing_instruments": ["EQ_1"],
    }
    assert captured["eligible_targets"] == {"EQ_1": Decimal("0.5")}
    assert diagnostics.warnings == [
        "TARGET_METHOD_STATUS_DIVERGENCE",
        "TARGET_METHOD_WEIGHT_DIVERGENCE",
    ]


def test_resolve_final_gate_status_preserves_target_review_requirement():
    assert (
        dpm_engine._resolve_final_gate_status(
            target_status="PENDING_REVIEW",
            execution_status="READY",
        )
        == "PENDING_REVIEW"
    )
    assert (
        dpm_engine._resolve_final_gate_status(
            target_status="PENDING_REVIEW",
            execution_status="BLOCKED",
        )
        == "BLOCKED"
    )
    assert (
        dpm_engine._resolve_final_gate_status(
            target_status="READY",
            execution_status="READY",
        )
        == "READY"
    )


def test_build_settlement_ladder_wrapper_delegates(monkeypatch):
    monkeypatch.setattr(
        dpm_engine,
        "build_settlement_ladder_impl",
        lambda *args: {"ok": args},
    )
    result = dpm_engine._build_settlement_ladder("pf", "shelf", "intents", "options", "diag")
    assert result["ok"][0] == "pf"
