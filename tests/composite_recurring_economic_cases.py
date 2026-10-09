"""Independent selected-profile expectations; no production evaluator is used for oracles."""

from copy import deepcopy
from datetime import date, timedelta

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.policy import month_window
from tests.unit.dpm.infrastructure.test_composite_monthly_source_assembly import assembly_material


def economic_cases():
    _, base = assembly_material()
    flows = base["observations"]["portfolios"][0]["flows"]
    original = deepcopy(flows[0])
    reversal = {
        **original,
        "event_id": "synthetic-reversal",
        "classification": "REVERSAL",
        "amount": "-150",
        "reverses_event_id": original["event_id"],
    }
    cases = [
        ("net_and_cash_equality", {}, "INCLUDED", ("PASS", "PASS", "PASS"), "0.05"),
        ("withdrawal_equality", {"flows": [flows[1]]}, "EXCLUDED", ("FAIL", "PASS", "PASS"), "0.1"),
        (
            "cash_above",
            {"settled_unencumbered_cash": "51"},
            "EXCLUDED",
            ("PASS", "FAIL", "PASS"),
            "0.05",
        ),
        (
            "prior_missing",
            {"prior_month_end_assets": None},
            "PENDING_REVIEW",
            ("UNKNOWN", "PASS", "PASS"),
            None,
        ),
        (
            "prior_zero",
            {"prior_month_end_assets": "0"},
            "PENDING_REVIEW",
            ("UNKNOWN", "PASS", "PASS"),
            None,
        ),
        (
            "prior_negative",
            {"prior_month_end_assets": "-1"},
            "PENDING_REVIEW",
            ("UNKNOWN", "PASS", "PASS"),
            None,
        ),
        (
            "cash_denominator_zero",
            {"month_end_assets": "0"},
            "PENDING_REVIEW",
            ("PASS", "UNKNOWN", "PASS"),
            "0.05",
        ),
        (
            "cash_missing",
            {"settled_unencumbered_cash": None},
            "PENDING_REVIEW",
            ("PASS", "UNKNOWN", "PASS"),
            "0.05",
        ),
        ("funded_unknown", {"funded": None}, "PENDING_REVIEW", ("PASS", "PASS", "UNKNOWN"), "0.05"),
        (
            "fail_over_unknown",
            {"settled_unencumbered_cash": "51", "funded": None},
            "EXCLUDED",
            ("PASS", "FAIL", "UNKNOWN"),
            "0.05",
        ),
        (
            "multiple_failures",
            {
                "flows": [flows[1]],
                "settled_unencumbered_cash": "51",
                "funded": False,
                "invested": None,
            },
            "EXCLUDED",
            ("FAIL", "FAIL", "FAIL"),
            "0.1",
        ),
        (
            "duplicate_exact",
            {"flows": [*flows, flows[0]]},
            "INCLUDED",
            ("PASS", "PASS", "PASS"),
            "0.05",
        ),
        (
            "duplicate_conflict",
            {"flows": [*flows, {**flows[0], "amount": "151"}]},
            "PENDING_REVIEW",
            ("UNKNOWN", "PASS", "PASS"),
            None,
        ),
        (
            "linked_reversal",
            {"flows": [original, reversal]},
            "INCLUDED",
            ("PASS", "PASS", "PASS"),
            "0",
        ),
        (
            "late_after_cut",
            {"flows": [{**flows[0], "received_at": "2026-10-02T00:00:00.000000Z"}]},
            "PENDING_REVIEW",
            ("UNKNOWN", "PASS", "PASS"),
            None,
        ),
        (
            "cash_cleared_funding_failed",
            {"funded": False},
            "EXCLUDED",
            ("PASS", "PASS", "FAIL"),
            "0.05",
        ),
        (
            "expected_member_missing",
            None,
            "PENDING_REVIEW",
            ("UNKNOWN", "UNKNOWN", "UNKNOWN"),
            None,
        ),
    ]
    for name, changes, status, outcomes, flow_ratio in cases:
        assembly = deepcopy(base)
        snapshot = assembly["observations"]
        snapshot["source_cut_id"] = f"economic.{name}.cut"
        snapshot["source_revision"] = f"economic.{name}.r1"
        if changes is None:
            snapshot["portfolios"] = []
        else:
            snapshot["portfolios"][0].update(deepcopy(changes))
        for item in assembly["inputs"]:
            item["source_cut_id"] = f"economic.{name}.{item['kind']}.cut"
            item["evidence"]["revision"] = f"economic.{name}.r1"
            item["evidence"]["digest"] = hash_canonical_payload(
                {"kind": item["kind"], "synthetic_observations": snapshot}
            )
        assembly["compatibility_binding"]["revision"] = f"economic.{name}.r1"
        assembly["compatibility_binding"]["digest"] = hash_canonical_payload(
            {"observations": snapshot, "inputs": assembly["inputs"]}
        )
        yield name, assembly, status, outcomes, flow_ratio


def transition_cases():
    """Three separately approved months; clearing cash alone cannot establish re-entry."""
    for month, cash, funded, status, outcomes in (
        ("2026-07", "51", False, "EXCLUDED", ("PASS", "FAIL", "FAIL")),
        ("2026-08", "50", False, "EXCLUDED", ("PASS", "PASS", "FAIL")),
        ("2026-09", "50", True, "INCLUDED", ("PASS", "PASS", "PASS")),
    ):
        _, assembly, *_ = next(economic_cases())
        first, last = month_window(month)
        generated = (date.fromisoformat(last) + timedelta(days=1)).isoformat() + "T00:00:00.000000Z"
        snapshot = assembly["observations"]
        snapshot.update(
            month=month,
            source_cut_id=f"transition.{month}.cut",
            source_revision=f"transition.{month}.r1",
            source_generated_at=generated,
        )
        portfolio = snapshot["portfolios"][0]
        portfolio.update(
            prior_assets_as_of=(date.fromisoformat(first) - timedelta(days=1)).isoformat(),
            cash_as_of=last,
            readiness_as_of=last,
            flow_coverage_from=first,
            flow_coverage_to=last,
            settled_unencumbered_cash=cash,
            funded=funded,
        )
        for flow in portfolio["flows"]:
            flow.update(business_date=month + "-15", received_at=generated)
        for item in assembly["inputs"]:
            item["source_cut_id"] = f"transition.{month}.{item['kind']}.cut"
            item["evidence"].update(
                revision=f"transition.{month}.r1",
                digest=hash_canonical_payload(
                    {"kind": item["kind"], "synthetic_observations": snapshot}
                ),
            )
        assembly["compatibility_binding"].update(
            revision=f"transition.{month}.r1",
            digest=hash_canonical_payload({"observations": snapshot, "inputs": assembly["inputs"]}),
        )
        yield month, assembly, status, outcomes
