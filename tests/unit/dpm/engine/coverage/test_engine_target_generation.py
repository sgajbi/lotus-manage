from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.dpm_engine import _apply_group_constraints, _generate_targets, run_simulation
from src.core.models import DiagnosticsData, EngineOptions, GroupConstraint, ShelfEntry
from tests.shared.assertions import assert_status
from tests.shared.factories import model_portfolio, position, target


class TestTargetGeneration:
    def test_target_locked_over_100(self, base_inputs):
        pf, mkt, model, shelf = base_inputs
        pf.positions = [position("LOCKED_ASSET", "1000")]
        mkt.prices[0].price = Decimal("1000")

        result = run_simulation(pf, mkt, model, shelf, EngineOptions())

        assert_status(result, "PENDING_REVIEW")

    def test_min_cash_buffer_scaling(self, base_inputs):
        pf, mkt, _, shelf = base_inputs
        model = model_portfolio(targets=[target("TARGET_ASSET", "1.0")])

        result = run_simulation(
            pf, mkt, model, shelf, EngineOptions(min_cash_buffer_pct=Decimal("0.10"))
        )

        tgt = next(t for t in result.target.targets if t.instrument_id == "TARGET_ASSET")
        assert tgt.final_weight <= Decimal("0.91")
        assert_status(result, "PENDING_REVIEW")

    def test_generate_targets_marks_pending_when_redistribution_remainder_stays(self):
        model = model_portfolio(targets=[target("B1", "0.2313"), target("B2", "0.4895")])
        eligible_targets = {
            "B1": Decimal("0.2313"),
            "B2": Decimal("0.4895"),
            "L1": Decimal("0.5266"),
            "L2": Decimal("0.0933"),
        }

        _, status = _generate_targets(
            model=model,
            eligible_targets=eligible_targets,
            buy_list=["B1", "B2"],
            sell_only_excess=Decimal("0.0"),
            options=EngineOptions(single_position_max_weight=Decimal("0.5")),
            total_val=Decimal("100"),
            base_ccy="USD",
        )

        assert status == "PENDING_REVIEW"

    def test_group_constraint_key_validation_rejects_invalid_key(self):
        with pytest.raises(ValidationError):
            EngineOptions(
                group_constraints={"bad_key": GroupConstraint(max_weight=Decimal("0.10"))}
            )

    def test_apply_group_constraints_warns_when_attribute_key_unknown(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )
        eligible_targets = {"A": Decimal("0.60")}
        shelf = [ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"})]
        options = EngineOptions(
            group_constraints={"region:EMEA": GroupConstraint(max_weight=Decimal("0.10"))}
        )

        status = _apply_group_constraints(eligible_targets, ["A"], shelf, options, diagnostics)

        assert status == "READY"
        assert "UNKNOWN_CONSTRAINT_ATTRIBUTE_region" in diagnostics.warnings

    def test_apply_group_constraints_tracks_structured_cap_event(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )
        eligible_targets = {"A": Decimal("0.60"), "B": Decimal("0.40")}
        shelf = [
            ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
            ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FI"}),
        ]
        options = EngineOptions(
            group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.20"))}
        )

        status = _apply_group_constraints(eligible_targets, ["A", "B"], shelf, options, diagnostics)

        assert status == "READY"
        assert len(diagnostics.group_constraint_events) == 1
        event = diagnostics.group_constraint_events[0]
        assert event.constraint_key == "sector:TECH"
        assert event.status == "CAPPED"
        assert event.released_weight == Decimal("0.40")
        assert event.recipients["B"] == Decimal("0.40")

    def test_apply_group_constraints_noop_when_within_tolerance(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )
        eligible_targets = {"A": Decimal("0.5000"), "B": Decimal("0.5000")}
        shelf = [
            ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"}),
            ShelfEntry(instrument_id="B", status="APPROVED", attributes={"sector": "FIN"}),
        ]
        options = EngineOptions(
            group_constraints={"sector:TECH": GroupConstraint(max_weight=Decimal("0.5000"))}
        )

        status = _apply_group_constraints(eligible_targets, ["A", "B"], shelf, options, diagnostics)

        assert status == "READY"
        assert eligible_targets["A"] == Decimal("0.5000")
        assert diagnostics.warnings == []

    def test_apply_group_constraints_handles_invalid_key_defensively(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )
        eligible_targets = {"A": Decimal("0.60")}
        shelf = [ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"})]
        options = type(
            "InvalidOpts",
            (),
            {"group_constraints": {"bad_key": GroupConstraint(max_weight=Decimal("0.10"))}},
        )()

        status = _apply_group_constraints(eligible_targets, ["A"], shelf, options, diagnostics)

        assert status == "READY"
        assert "INVALID_CONSTRAINT_KEY_bad_key" in diagnostics.warnings

    def test_apply_group_constraints_skips_when_group_has_no_matching_value(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )
        eligible_targets = {"A": Decimal("0.60")}
        shelf = [ShelfEntry(instrument_id="A", status="APPROVED", attributes={"sector": "TECH"})]
        options = EngineOptions(
            group_constraints={"sector:HEALTH": GroupConstraint(max_weight=Decimal("0.10"))}
        )

        status = _apply_group_constraints(eligible_targets, ["A"], shelf, options, diagnostics)

        assert status == "READY"
        assert diagnostics.warnings == []

    def test_generate_targets_uses_default_options_when_not_provided(self):
        model = model_portfolio(targets=[target("A", "0.40")])
        eligible_targets = {"A": Decimal("0.40")}

        trace, status = _generate_targets(
            model=model,
            eligible_targets=eligible_targets,
            buy_list=["A"],
            sell_only_excess=Decimal("0.0"),
            total_val=Decimal("100"),
            base_ccy="USD",
        )

        assert status == "READY"
        assert trace[0].instrument_id == "A"
