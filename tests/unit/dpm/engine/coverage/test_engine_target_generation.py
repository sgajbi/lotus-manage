from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.common.target_redistribution import redistribute_sell_only_excess
from src.core.rebalance.targets import (
    _apply_min_cash_buffer,
    _apply_single_position_max_weight,
    _cap_single_position_targets,
    _cap_tradeable_targets_to_available_weight,
    _constraint_key_parts,
    _group_constraint_members,
    _redistribute_group_constraint_excess,
    _redistribute_single_position_excess,
)
from src.core.rebalance.engine import _apply_group_constraints, _generate_targets, run_simulation
from src.core.models import DiagnosticsData, EngineOptions, GroupConstraint, ShelfEntry
from tests.shared.assertions import assert_status
from tests.shared.factories import model_portfolio, position, target


class TestTargetGeneration:
    def test_redistribute_sell_only_excess_allocates_to_buy_targets_proportionally(self):
        eligible_targets = {
            "BUY_A": Decimal("0.30"),
            "BUY_B": Decimal("0.10"),
            "LOCKED": Decimal("0.20"),
        }

        status = redistribute_sell_only_excess(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
            sell_only_excess=Decimal("0.20"),
        )

        assert status == "READY"
        assert eligible_targets == {
            "BUY_A": Decimal("0.45"),
            "BUY_B": Decimal("0.15"),
            "LOCKED": Decimal("0.20"),
        }

    def test_redistribute_sell_only_excess_skips_when_no_excess(self):
        eligible_targets = {"BUY_A": Decimal("0.30")}

        status = redistribute_sell_only_excess(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A"},
            sell_only_excess=Decimal("0.0"),
        )

        assert status == "READY"
        assert eligible_targets == {"BUY_A": Decimal("0.30")}

    def test_redistribute_sell_only_excess_marks_pending_without_recipient_weight(self):
        eligible_targets = {"BUY_A": Decimal("0.0"), "LOCKED": Decimal("0.20")}

        status = redistribute_sell_only_excess(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A"},
            sell_only_excess=Decimal("0.20"),
        )

        assert status == "PENDING_REVIEW"
        assert eligible_targets == {"BUY_A": Decimal("0.0"), "LOCKED": Decimal("0.20")}

    def test_cap_tradeable_targets_to_available_weight_skips_balanced_targets(self):
        eligible_targets = {"BUY_A": Decimal("0.40"), "LOCKED": Decimal("0.30")}

        status = _cap_tradeable_targets_to_available_weight(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A"},
        )

        assert status == "READY"
        assert eligible_targets == {"BUY_A": Decimal("0.40"), "LOCKED": Decimal("0.30")}

    def test_cap_tradeable_targets_to_available_weight_scales_buy_targets(self):
        eligible_targets = {
            "BUY_A": Decimal("0.60"),
            "BUY_B": Decimal("0.30"),
            "LOCKED": Decimal("0.30"),
        }

        status = _cap_tradeable_targets_to_available_weight(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
        )

        assert status == "PENDING_REVIEW"
        assert eligible_targets == {
            "BUY_A": Decimal("0.4666666666666666666666666667"),
            "BUY_B": Decimal("0.2333333333333333333333333333"),
            "LOCKED": Decimal("0.30"),
        }

    def test_cap_tradeable_targets_to_available_weight_marks_locked_overage_pending(self):
        eligible_targets = {"BUY_A": Decimal("0.20"), "LOCKED": Decimal("1.10")}

        status = _cap_tradeable_targets_to_available_weight(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A"},
        )

        assert status == "PENDING_REVIEW"
        assert eligible_targets == {"BUY_A": Decimal("0.00"), "LOCKED": Decimal("1.10")}

    def test_constraint_key_parts_validates_key_and_known_attribute(self):
        diagnostics = DiagnosticsData(
            warnings=[],
            suppressed_intents=[],
            data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
        )

        assert _constraint_key_parts(
            "sector:TECH",
            known_attr_keys={"sector"},
            diagnostics=diagnostics,
        ) == ("sector", "TECH")
        assert (
            _constraint_key_parts(
                "bad_key",
                known_attr_keys={"sector"},
                diagnostics=diagnostics,
            )
            is None
        )
        assert (
            _constraint_key_parts(
                "region:EMEA",
                known_attr_keys={"sector"},
                diagnostics=diagnostics,
            )
            is None
        )
        assert diagnostics.warnings == [
            "INVALID_CONSTRAINT_KEY_bad_key",
            "UNKNOWN_CONSTRAINT_ATTRIBUTE_region",
        ]

    def test_group_constraint_members_match_shelf_attribute_value(self):
        eligible_targets = {
            "TECH_A": Decimal("0.40"),
            "FI_A": Decimal("0.30"),
            "TECH_B": Decimal("0.20"),
        }
        shelf_attrs_by_id = {
            "TECH_A": {"sector": "TECH"},
            "FI_A": {"sector": "FI"},
            "TECH_B": {"sector": "TECH"},
        }

        assert _group_constraint_members(
            eligible_targets=eligible_targets,
            shelf_attrs_by_id=shelf_attrs_by_id,
            attr_key="sector",
            attr_val="TECH",
        ) == ["TECH_A", "TECH_B"]

    def test_redistribute_group_constraint_excess_allocates_to_buyable_non_members(self):
        eligible_targets = {
            "TECH_A": Decimal("0.20"),
            "FI_A": Decimal("0.30"),
            "FI_B": Decimal("0.10"),
            "LOCKED": Decimal("0.10"),
        }

        recipients = _redistribute_group_constraint_excess(
            eligible_targets=eligible_targets,
            buy_set={"TECH_A", "FI_A", "FI_B"},
            group_members=["TECH_A"],
            released_weight=Decimal("0.20"),
        )

        assert recipients == {
            "FI_A": Decimal("0.150"),
            "FI_B": Decimal("0.050"),
        }
        assert eligible_targets["FI_A"] == Decimal("0.450")
        assert eligible_targets["FI_B"] == Decimal("0.150")

    def test_cap_single_position_targets_returns_released_weight(self):
        eligible_targets = {
            "BUY_A": Decimal("0.80"),
            "BUY_B": Decimal("0.20"),
            "LOCKED": Decimal("0.60"),
        }

        excess = _cap_single_position_targets(
            eligible_targets=eligible_targets,
            max_weight=Decimal("0.50"),
        )

        assert excess == Decimal("0.40")
        assert eligible_targets == {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.20"),
            "LOCKED": Decimal("0.50"),
        }

    def test_redistribute_single_position_excess_returns_unplaced_remainder(self):
        eligible_targets = {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.40"),
            "LOCKED": Decimal("0.50"),
        }

        remainder = _redistribute_single_position_excess(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
            max_weight=Decimal("0.50"),
            excess=Decimal("0.30"),
        )

        assert remainder == Decimal("0.20")
        assert eligible_targets == {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.50"),
            "LOCKED": Decimal("0.50"),
        }

    def test_apply_single_position_max_weight_caps_and_redistributes_excess(self):
        eligible_targets = {
            "BUY_A": Decimal("0.80"),
            "BUY_B": Decimal("0.20"),
            "LOCKED": Decimal("0.10"),
        }

        status = _apply_single_position_max_weight(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
            max_weight=Decimal("0.50"),
        )

        assert status == "READY"
        assert eligible_targets == {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.50"),
            "LOCKED": Decimal("0.10"),
        }

    def test_apply_single_position_max_weight_marks_pending_when_excess_remains(self):
        eligible_targets = {
            "BUY_A": Decimal("0.90"),
            "BUY_B": Decimal("0.10"),
            "LOCKED": Decimal("0.80"),
        }

        status = _apply_single_position_max_weight(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
            max_weight=Decimal("0.50"),
        )

        assert status == "PENDING_REVIEW"
        assert eligible_targets == {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.50"),
            "LOCKED": Decimal("0.50"),
        }

    def test_apply_min_cash_buffer_scales_tradeable_weight_after_locked_weight(self):
        eligible_targets = {
            "BUY_A": Decimal("0.50"),
            "BUY_B": Decimal("0.30"),
            "LOCKED": Decimal("0.10"),
        }

        status = _apply_min_cash_buffer(
            eligible_targets=eligible_targets,
            buy_set={"BUY_A", "BUY_B"},
            min_cash_buffer_pct=Decimal("0.20"),
        )

        assert status == "PENDING_REVIEW"
        assert eligible_targets == {
            "BUY_A": Decimal("0.43750"),
            "BUY_B": Decimal("0.26250"),
            "LOCKED": Decimal("0.10"),
        }

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
