"""Independent monthly policy oracles; synthetic choices are not bank approval."""

from decimal import Decimal, DefaultContext, Inexact, Rounded, ROUND_DOWN, ROUND_UP, Subnormal
from decimal import localcontext

import pytest

from src.core.composite_eligibility.policy import (
    MonthlyPolicyLayer,
    MonthlyPolicyScope,
    resolve_monthly_policy as _resolve_monthly_policy,
)
from src.core.composite_eligibility.observations import MonthlyPortfolioObservations
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.rules import evaluate_monthly_rules
from src.core.composite_eligibility.evaluation import (
    MonthlyEligibilityEvaluation,
    evaluate_monthly_eligibility as _evaluate_monthly_eligibility,
)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("expected_count", 2, "COUNTS_MISMATCH"),
        ("observed_count", 0, "COUNTS_MISMATCH"),
        ("included_count", 0, "COUNTS_MISMATCH"),
        ("declared_universe_coverage", "INCOMPLETE", "COVERAGE_MISMATCH"),
        ("month", "2026-10", "EVALUATION_SCOPE_MISMATCH"),
        ("tenant_id", "foreign-tenant", "EVALUATION_SCOPE_MISMATCH"),
        ("content_hash", "sha256:" + "0" * 64, "EVALUATION_CONTENT_MISMATCH"),
    ],
)
def test_evaluation_artifact_refuses_tampered_counts_scope_and_digest(field, value, code):
    result = evaluate_monthly_eligibility(
        resolve_monthly_policy([layer()], month="2026-09"), scenario(observations())
    )
    assert MonthlyEligibilityEvaluation.model_validate(result.model_dump(mode="json")) == result
    raw = result.model_dump(mode="json")
    raw[field] = value
    with pytest.raises(ValueError, match=code):
        MonthlyEligibilityEvaluation.model_validate(raw)


@pytest.mark.parametrize(
    "change,code",
    [
        ("status", "STATUS_MISMATCH"),
        ("rules", "RULE_SET_INVALID"),
        ("universe", "UNIVERSE_NONCANONICAL"),
    ],
)
def test_evaluation_artifact_refuses_partial_or_inconsistent_member_results(change, code):
    result = evaluate_monthly_eligibility(
        resolve_monthly_policy([layer()], month="2026-09"), scenario(observations())
    )
    raw = result.model_dump(mode="json")
    if change == "status":
        raw["portfolios"][0]["status"] = "EXCLUDED"
    elif change == "rules":
        raw["portfolios"][0]["assessments"][1]["rule"] = "SIGNIFICANT_FLOW"
    else:
        raw["portfolios"].append(raw["portfolios"][0])
    with pytest.raises(ValueError, match=code):
        MonthlyEligibilityEvaluation.model_validate(raw)


def layer(**changes: object) -> MonthlyPolicyLayer:
    raw = {
        "level": "PLATFORM",
        "policy_id": "synthetic-monthly",
        "revision": "r1",
        "effective_from": "2026-09-01",
        "effective_to": "2026-12-31",
        "flow_threshold": "0.10",
        "cash_threshold": "0.05",
        "permitted_overrides": ["CASH_THRESHOLD", "FLOW_THRESHOLD"],
    }
    raw.update(changes)
    if raw["level"] != "PLATFORM":
        raw.setdefault("tenant_id", "synthetic-tenant")
    return MonthlyPolicyLayer.model_validate(raw)


def resolve_monthly_policy(layers: list[MonthlyPolicyLayer], *, month: str):
    return _resolve_monthly_policy(
        layers,
        month=month,
        scope=MonthlyPolicyScope(
            tenant_id="synthetic-tenant",
            composite_id="synthetic-composite",
            definition_version="synthetic-definition-r1",
            strategy_code="synthetic-strategy",
        ),
    )


def evaluate_monthly_eligibility(
    policy,
    observations,
    *,
    evaluated_at="2026-10-01T01:00:00.000000Z",
):
    return _evaluate_monthly_eligibility(
        policy,
        observations,
        evaluated_at=evaluated_at,
        universe_content_hash="sha256:" + "a" * 64,
    )


def test_resolution_binds_actual_layers_and_decimal_profile_values() -> None:
    base = layer()
    tenant = layer(
        level="TENANT", policy_id="synthetic-tenant", flow_threshold="0.12", cash_threshold=None
    )
    resolved = resolve_monthly_policy([base, tenant], month="2026-09")
    assert Decimal(resolved.flow_threshold) == Decimal("0.12")
    assert Decimal(resolved.cash_threshold) == Decimal("0.05")
    assert resolved.layers == [base, tenant]
    assert resolved.official_activation == "UNAVAILABLE"
    assert resolved.content_hash != resolve_monthly_policy([base], month="2026-09").content_hash


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e-1", "-0.1", "1.01", 0.1])
def test_policy_thresholds_refuse_nonfinite_implicit_or_out_of_range_values(value: object) -> None:
    with pytest.raises(ValueError):
        layer(flow_threshold=value)


def test_unpermitted_override_and_stale_month_refuse_instead_of_falling_back() -> None:
    base = layer(permitted_overrides=[])
    tenant = layer(level="TENANT", policy_id="synthetic-tenant", flow_threshold="0.12")
    with pytest.raises(ValueError, match="OVERRIDE_FORBIDDEN"):
        resolve_monthly_policy([base, tenant], month="2026-09")
    with pytest.raises(ValueError, match="POLICY_NOT_EFFECTIVE"):
        resolve_monthly_policy([base], month="2027-01")


def test_inheritance_order_and_missing_root_threshold_refuse() -> None:
    tenant = layer(level="TENANT", policy_id="synthetic-tenant")
    with pytest.raises(ValueError, match="INHERITANCE_ORDER_INVALID"):
        resolve_monthly_policy([tenant, layer()], month="2026-09")
    with pytest.raises(ValueError, match="THRESHOLD_REQUIRED"):
        resolve_monthly_policy([layer(flow_threshold=None)], month="2026-09")


def test_locked_threshold_accepts_equal_decimal_material_but_keeps_exact_content_identity() -> None:
    base = layer(permitted_overrides=[])
    tenant = layer(
        level="TENANT", policy_id="synthetic-tenant", flow_threshold="0.100", cash_threshold="0.050"
    )
    resolved = resolve_monthly_policy([base, tenant], month="2026-09")
    assert Decimal(resolved.flow_threshold) == Decimal("0.10")
    assert resolved.layers[1].flow_threshold == "0.100"
    assert resolved.content_hash != resolve_monthly_policy([base], month="2026-09").content_hash


@pytest.mark.parametrize(
    "foreign_layer",
    [
        {"level": "TENANT", "tenant_id": "foreign-tenant"},
        {"level": "STRATEGY", "strategy_code": "foreign-strategy"},
        {"level": "COMPOSITE", "composite_id": "foreign-composite"},
        {"level": "RUN", "composite_id": "synthetic-composite", "run_id": "unbound-run"},
    ],
)
def test_ordered_layers_cannot_substitute_foreign_or_unbound_scope(foreign_layer: dict) -> None:
    with pytest.raises(ValueError, match="LAYER_SCOPE_MISMATCH"):
        resolve_monthly_policy([layer(), layer(**foreign_layer)], month="2026-09")


def observations(*amounts: str, **changes: object) -> MonthlyPortfolioObservations:
    raw = {
        "portfolio_id": "synthetic-member-a",
        "currency": "USD",
        "prior_month_end_assets": "1000",
        "prior_assets_as_of": "2026-08-31",
        "month_end_assets": "1000",
        "settled_unencumbered_cash": "50",
        "cash_as_of": "2026-09-30",
        "discretionary": True,
        "funded": True,
        "invested": True,
        "readiness_as_of": "2026-09-30",
        "flow_coverage_from": "2026-09-01",
        "flow_coverage_to": "2026-09-30",
        "flows": [
            {
                "event_id": f"synthetic-flow-{index}",
                "business_date": "2026-09-15",
                "received_at": "2026-10-01T00:00:00.000000Z",
                "currency": "USD",
                "amount": amount,
                "classification": "EXTERNAL_CASH",
                "status": "POSTED",
                "reverses_event_id": None,
            }
            for index, amount in enumerate(amounts)
        ],
    }
    return MonthlyPortfolioObservations.model_validate(raw | changes)


@pytest.mark.parametrize(
    "amounts,flow_outcome,net,ratio",
    [
        (("150", "-100"), "PASS", "50", "0.05"),
        (("-100",), "FAIL", "-100", "0.1"),
        (("100",), "FAIL", "100", "0.1"),
        ((), "PASS", "0", "0"),
    ],
)
def test_independent_absolute_net_and_cash_equality_oracles(
    amounts: tuple[str, ...], flow_outcome: str, net: str, ratio: str
) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    results = evaluate_monthly_rules(
        policy,
        observations(*amounts),
        evaluated_at="2026-10-01T01:00:00.000000Z",
        source_generated_at="2026-10-01T00:00:00.000000Z",
    )
    flow, cash, readiness = results
    assert flow.outcome == flow_outcome
    assert Decimal(flow.numerator) == Decimal(net)
    assert Decimal(flow.ratio) == Decimal(ratio)
    assert cash.outcome == "PASS"
    assert Decimal(cash.ratio) == Decimal("0.05")
    assert readiness.outcome == "PASS"


@pytest.mark.parametrize("field", ["tenant_id", "composite_id", "definition_version"])
def test_source_scope_substitution_refuses_before_calculation(field: str) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    with pytest.raises(ValueError, match="SOURCE_SCOPE_MISMATCH"):
        evaluate_monthly_eligibility(policy, scenario(observations(), **{field: "foreign-scope"}))


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"prior_assets_as_of": "2026-08-30"}, "FLOW_DENOMINATOR_DATE_MISMATCH"),
        ({"flow_coverage_to": "2026-09-29"}, "FLOW_OBSERVATION_WINDOW_INCOMPLETE"),
        ({"cash_as_of": "2026-09-29"}, "CASH_OBSERVATION_DATE_MISMATCH"),
        ({"settled_unencumbered_cash": None}, "CASH_NUMERATOR_MISSING_OR_NEGATIVE"),
        ({"settled_unencumbered_cash": "-1"}, "CASH_NUMERATOR_MISSING_OR_NEGATIVE"),
        ({"readiness_as_of": None}, "READINESS_OBSERVATION_DATE_MISMATCH"),
        ({"currency": "EUR"}, "PORTFOLIO_CURRENCY_SCOPE_MISMATCH"),
    ],
)
def test_invalid_observation_dates_or_cash_do_not_synthesize_valid_data(
    changes: dict, reason: str
) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    result = evaluate_monthly_eligibility(policy, scenario(observations(**changes)))
    assert result.portfolios[0].status == "PENDING_REVIEW"
    assert any(reason in item.unknown_reasons for item in result.portfolios[0].assessments)


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"flow_threshold": "0"}, "THRESHOLD_NONPOSITIVE"),
        ({"effective_to": "2026-08-31"}, "POLICY_WINDOW_INVALID"),
        ({"permitted_overrides": ["FLOW_THRESHOLD", "FLOW_THRESHOLD"]}, "PERMISSIONS_NONCANONICAL"),
    ],
)
def test_policy_semantic_validation_refuses_invalid_economic_material(
    changes: dict, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        layer(**changes)


def test_policy_reconstruction_refuses_resolved_value_or_digest_tampering() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    raw = policy.model_dump(mode="json")
    raw["flow_threshold"] = "0.20"
    with pytest.raises(ValueError, match="RESOLUTION_MISMATCH"):
        type(policy).model_validate(raw)
    raw = policy.model_dump(mode="json")
    raw["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="POLICY_DIGEST_MISMATCH"):
        type(policy).model_validate(raw)


def test_invalid_month_and_unbounded_inheritance_refuse() -> None:
    with pytest.raises(ValueError, match="MONTH_INVALID"):
        resolve_monthly_policy([layer()], month="2026-13")
    with pytest.raises(ValueError, match="LAYER_BOUND_EXCEEDED"):
        resolve_monthly_policy([layer()] * 6, month="2026-09")


def test_future_generation_or_noncanonical_population_cannot_enter_the_source_cut() -> None:
    with pytest.raises(ValueError, match="FUTURE_SOURCE_GENERATION"):
        evaluate_monthly_eligibility(
            resolve_monthly_policy([layer()], month="2026-09"),
            scenario(observations(), source_generated_at="2026-10-02T00:00:00.000000Z"),
        )
    with pytest.raises(ValueError, match="UNIVERSE_NONCANONICAL"):
        scenario(observations(), expected_portfolio_ids=["synthetic-member-a"] * 2)
    with pytest.raises(ValueError, match="UNEXPECTED_PORTFOLIO"):
        scenario(observations(portfolio_id="unlisted-member"))


def test_missing_and_repeated_reversal_links_refuse_without_guessing_original_flows() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("150", "-150", "-150")
    for flow in member.flows[1:]:
        flow.classification = "REVERSAL"
        flow.reverses_event_id = member.flows[0].event_id
    assessment = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert assessment.unknown_reasons == ["FLOW_MULTIPLE_REVERSALS"]
    member.flows = member.flows[1:2]
    assessment = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert assessment.unknown_reasons == ["FLOW_REVERSAL_BINDING_INVALID"]
    raw = member.model_dump(mode="json")
    raw["flows"][0]["reverses_event_id"] = None
    with pytest.raises(ValueError, match="REVERSAL_REFERENCE_INVALID"):
        MonthlyPortfolioObservations.model_validate(raw)
    raw["flows"][0]["reverses_event_id"] = raw["flows"][0]["event_id"]
    with pytest.raises(ValueError, match="REVERSAL_SELF_REFERENCE"):
        MonthlyPortfolioObservations.model_validate(raw)


def test_cancelled_and_internal_transfers_are_not_external_economic_flows() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("1000", "1000")
    member.flows[0].status = "CANCELLED"
    member.flows[1].classification = "INTERNAL_TRANSFER"
    assessment = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert (assessment.outcome, assessment.numerator, assessment.admitted_flow_count) == (
        "PASS",
        "0",
        0,
    )


def scenario(
    *members: MonthlyPortfolioObservations, **changes: object
) -> MonthlyEligibilityObservations:
    raw = {
        "product_name": "CompositeMonthlyEligibilityObservations",
        "product_version": "v1",
        "evidence_class": "SYNTHETIC_UNQUALIFIED",
        "tenant_id": "synthetic-tenant",
        "composite_id": "synthetic-composite",
        "definition_version": "synthetic-definition-r1",
        "month": "2026-09",
        "source_cut_id": "synthetic-cut-r1",
        "source_revision": "synthetic-source-r1",
        "reporting_currency": "USD",
        "source_generated_at": "2026-10-01T00:00:00.000000Z",
        "expected_portfolio_ids": ["synthetic-member-a"],
        "portfolios": [item.model_dump(mode="json") for item in members],
    }
    return MonthlyEligibilityObservations.model_validate(raw | changes)


def test_every_failure_and_unknown_survives_fail_over_unknown_precedence() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    result = evaluate_monthly_eligibility(
        policy,
        scenario(
            observations(
                "100",
                prior_month_end_assets=None,
                settled_unencumbered_cash="51",
                discretionary=False,
                funded=None,
            )
        ),
    )
    member = result.portfolios[0]
    assert member.status == "EXCLUDED"
    assert [item.outcome for item in member.assessments] == ["UNKNOWN", "FAIL", "FAIL"]
    assert member.assessments[0].unknown_reasons == ["FLOW_DENOMINATOR_MISSING_OR_NONPOSITIVE"]
    assert member.assessments[1].failure_reasons == ["CASH_THRESHOLD_BREACH"]
    assert member.assessments[2].failure_reasons == ["READINESS_DISCRETIONARY_FAILED"]
    assert member.assessments[2].unknown_reasons == ["READINESS_FUNDED_UNKNOWN"]
    assert result.excluded_count == 1
    assert result.population_verification == "UNVERIFIED"
    assert result.official_activation == "UNAVAILABLE"


@pytest.mark.parametrize("denominator", [None, "0", "-1"])
def test_missing_or_nonpositive_denominator_never_becomes_zero_ratio(
    denominator: str | None,
) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    result = evaluate_monthly_eligibility(
        policy,
        scenario(observations(prior_month_end_assets=denominator, month_end_assets=denominator)),
    )
    assert result.portfolios[0].status == "PENDING_REVIEW"
    for assessment in result.portfolios[0].assessments[:2]:
        assert assessment.outcome == "UNKNOWN"
        assert assessment.ratio is None


def test_missing_expected_member_is_incomplete_not_an_ordinary_exclusion() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    result = evaluate_monthly_eligibility(
        policy,
        scenario(
            observations(), expected_portfolio_ids=["synthetic-member-a", "synthetic-member-b"]
        ),
    )
    assert (result.expected_count, result.observed_count) == (2, 1)
    assert (result.included_count, result.excluded_count, result.pending_review_count) == (1, 0, 1)
    assert result.declared_universe_coverage == "INCOMPLETE"
    assert not result.portfolios[1].observations_present
    assert all(
        item.unknown_reasons == ["MISSING_EXPECTED_PORTFOLIO_OBSERVATIONS"]
        for item in result.portfolios[1].assessments
    )


def test_exact_portfolio_and_flow_replays_deduplicate_but_conflicts_refuse() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("60")
    member.flows.append(member.flows[0].model_copy(deep=True))
    result = evaluate_monthly_eligibility(policy, scenario(member, member))
    assert result.observed_count == 1
    flow = result.portfolios[0].assessments[0]
    assert flow.admitted_flow_count == 1
    assert flow.numerator == "60"
    assert flow.outcome == "PASS"
    conflict = member.model_copy(deep=True)
    conflict.flows[1].amount = "61"
    bad_flow = evaluate_monthly_eligibility(policy, scenario(conflict)).portfolios[0].assessments[0]
    assert bad_flow.outcome == "UNKNOWN"
    assert "FLOW_DUPLICATE_CONTENT_CONFLICT" in bad_flow.unknown_reasons
    with pytest.raises(ValueError, match="DUPLICATE_PORTFOLIO_CONFLICT"):
        evaluate_monthly_eligibility(policy, scenario(member, conflict))


def test_linked_same_currency_reversal_nets_once_and_retains_gross_diagnostics() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("150", "-150")
    member.flows[1].classification = "REVERSAL"
    member.flows[1].reverses_event_id = member.flows[0].event_id
    flow = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert flow.outcome == "PASS"
    assert (flow.numerator, flow.gross_inflow, flow.gross_outflow) == ("0", "150", "150")
    member.flows[1].amount = "-149"
    invalid = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert invalid.outcome == "UNKNOWN"
    assert invalid.unknown_reasons == ["FLOW_REVERSAL_BINDING_INVALID"]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("received_at", "2026-10-02T00:00:00.000000Z", "FLOW_RECEIVED_AFTER_EVALUATION"),
        ("received_at", "2026-10-01T00:00:00.000001Z", "FLOW_RECEIVED_AFTER_SOURCE_CUT"),
        ("currency", "EUR", "FLOW_CURRENCY_NOT_NORMALIZED"),
        ("business_date", "2026-08-31", "FLOW_BUSINESS_DATE_OUTSIDE_MONTH"),
        ("classification", "IN_KIND", "FLOW_IN_KIND_POLICY_UNAVAILABLE"),
    ],
)
def test_late_mixed_currency_out_of_period_and_unapproved_flow_types_remain_unknown(
    field: str, value: str, reason: str
) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("100")
    raw = member.model_dump(mode="json")
    raw["flows"][0][field] = value
    member = MonthlyPortfolioObservations.model_validate(raw)
    assessment = evaluate_monthly_eligibility(policy, scenario(member)).portfolios[0].assessments[0]
    assert assessment.outcome == "UNKNOWN"
    expected = [reason]
    if reason == "FLOW_RECEIVED_AFTER_EVALUATION":
        expected.append("FLOW_RECEIVED_AFTER_SOURCE_CUT")
    assert assessment.unknown_reasons == sorted(expected)


def test_provisional_month_does_not_exclude_from_a_temporary_net_flow_breach() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    result = evaluate_monthly_eligibility(
        policy,
        scenario(
            observations("150"),
            source_generated_at="2026-09-30T23:59:59.000000Z",
        ),
        evaluated_at="2026-09-30T23:59:59.000000Z",
    )
    assert result.portfolios[0].status == "PENDING_REVIEW"
    assert all(
        item.unknown_reasons == ["MONTH_NOT_FINALIZED"] for item in result.portfolios[0].assessments
    )


def test_delayed_evaluation_cannot_finalize_a_pre_month_close_source_cut() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    incomplete = evaluate_monthly_eligibility(
        policy, scenario(observations(), source_generated_at="2026-09-30T23:59:59.999999Z")
    )
    assert incomplete.portfolios[0].status == "PENDING_REVIEW"
    assert all(
        item.unknown_reasons == ["SOURCE_CUT_NOT_FINALIZED"]
        for item in incomplete.portfolios[0].assessments
    )
    complete = evaluate_monthly_eligibility(
        policy, scenario(observations(), source_generated_at="2026-10-01T00:00:00.000000Z")
    )
    assert complete.portfolios[0].status == "INCLUDED"


def test_threshold_comparison_is_exact_and_independent_of_global_decimal_context() -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    member = observations("99.999999999999", settled_unencumbered_cash="50.000000000001")
    with localcontext() as context:
        context.prec = 6
        low_precision = evaluate_monthly_eligibility(policy, scenario(member))
    with localcontext() as context:
        context.prec = 40
        high_precision = evaluate_monthly_eligibility(policy, scenario(member))
    assert low_precision == high_precision
    assert [item.outcome for item in low_precision.portfolios[0].assessments] == [
        "PASS",
        "FAIL",
        "PASS",
    ]


@pytest.mark.parametrize("fault", ["rounding", "traps", "exponents", "combined"])
def test_recurring_ratio_wire_and_hash_ignore_caller_decimal_configuration(fault) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    material = scenario(
        observations(
            "1",
            prior_month_end_assets="300",
            month_end_assets="300",
            settled_unencumbered_cash="1",
        )
    )
    expected = evaluate_monthly_eligibility(policy, material)
    assert expected.content_hash == (
        "sha256:b3cc1167a2b17826f8fe9e954e3e190d868246dc6b33eb483976338e9bc68bd5"
    )
    assert expected.portfolios[0].assessments[0].ratio == "0.00" + "3" * 80
    with localcontext() as caller:
        caller.prec = 6
        if fault in ("rounding", "combined"):
            caller.rounding = ROUND_UP
        if fault in ("traps", "combined"):
            caller.traps[Inexact] = caller.traps[Rounded] = True
        if fault in ("exponents", "combined"):
            caller.Emin, caller.Emax, caller.clamp = -2, 2, 1
            caller.traps[Subnormal] = True
        caller.flags[Inexact] = True
        retained = _decimal_context_state(caller)
        actual = evaluate_monthly_eligibility(policy, material)
        assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
        assert _decimal_context_state(caller) == retained


def test_monthly_context_does_not_inherit_mutable_decimal_defaults(monkeypatch) -> None:
    policy = resolve_monthly_policy([layer()], month="2026-09")
    material = scenario(observations("1", prior_month_end_assets="300"))
    expected = evaluate_monthly_eligibility(policy, material)
    monkeypatch.setattr(DefaultContext, "rounding", ROUND_UP)
    monkeypatch.setitem(DefaultContext.traps, Inexact, True)
    with localcontext() as caller:
        caller.rounding = ROUND_DOWN
        caller.traps[Inexact] = True
        retained = _decimal_context_state(caller)
        assert evaluate_monthly_eligibility(policy, material) == expected
        assert _decimal_context_state(caller) == retained


def _decimal_context_state(context):
    return (
        context.prec,
        context.rounding,
        context.Emin,
        context.Emax,
        context.capitals,
        context.clamp,
        dict(context.traps),
        dict(context.flags),
    )
