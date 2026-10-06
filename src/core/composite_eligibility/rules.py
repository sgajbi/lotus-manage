"""Decimal monthly synthetic rules: every applicable rule retains its evidence."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext
from typing import Literal

from pydantic import Field, TypeAdapter

from src.core.composite_authority_models import StrictAuthorityModel
from src.core.composite_eligibility.flows import admitted_monthly_flows
from src.core.composite_eligibility.observations import MonthlyPortfolioObservations, UtcInstant
from src.core.composite_eligibility.policy import ResolvedMonthlyPolicy, month_window

RuleOutcome = Literal["PASS", "FAIL", "UNKNOWN"]
RuleName = Literal["SIGNIFICANT_FLOW", "CASH", "READINESS"]


class MonthlyRuleAssessment(StrictAuthorityModel):
    rule: RuleName
    outcome: RuleOutcome
    failure_reasons: list[str]
    unknown_reasons: list[str]
    numerator: str | None = Field(default=None, max_length=160)
    denominator: str | None = Field(default=None, max_length=160)
    ratio: str | None = Field(default=None, max_length=160)
    gross_inflow: str | None = None
    gross_outflow: str | None = None
    admitted_flow_count: int | None = Field(default=None, ge=0, le=250)


def evaluate_monthly_rules(
    policy: ResolvedMonthlyPolicy,
    observation: MonthlyPortfolioObservations,
    *,
    evaluated_at: str,
    source_generated_at: str,
) -> list[MonthlyRuleAssessment]:
    # Revalidate mutable nested models before using their pinned material.
    policy = ResolvedMonthlyPolicy.model_validate(policy.model_dump(mode="json"))
    observation = MonthlyPortfolioObservations.model_validate(observation.model_dump(mode="json"))
    evaluated = datetime.fromisoformat(TypeAdapter(UtcInstant).validate_python(evaluated_at))
    generated = datetime.fromisoformat(TypeAdapter(UtcInstant).validate_python(source_generated_at))
    if generated > evaluated:
        raise ValueError("COMPOSITE_ELIGIBILITY_FUTURE_SOURCE_GENERATION")
    start, end = month_window(policy.month)
    if evaluated.date().isoformat() <= end:
        return _not_finalized_rules("MONTH_NOT_FINALIZED")
    if generated.date().isoformat() <= end:
        return _not_finalized_rules("SOURCE_CUT_NOT_FINALIZED")
    # Bound money has at most 36 digits, 250 flows add at most 3, and thresholds
    # have at most 12. Precision 80 keeps the breach cross-products exact and
    # isolates arithmetic from process-global Decimal context changes.
    with localcontext() as context:
        context.prec = 80
        return [
            _flow_rule(policy, observation, start, end, evaluated, generated),
            _cash_rule(policy, observation, end),
            _readiness_rule(observation, end),
        ]


def _not_finalized_rules(reason: str) -> list[MonthlyRuleAssessment]:
    rule_names: tuple[RuleName, ...] = ("SIGNIFICANT_FLOW", "CASH", "READINESS")
    return [
        MonthlyRuleAssessment(
            rule=rule, outcome="UNKNOWN", failure_reasons=[], unknown_reasons=[reason]
        )
        for rule in rule_names
    ]


def _flow_rule(
    policy: ResolvedMonthlyPolicy,
    observation: MonthlyPortfolioObservations,
    start: str,
    end: str,
    evaluated_at: datetime,
    source_generated_at: datetime,
) -> MonthlyRuleAssessment:
    admitted, reasons = admitted_monthly_flows(
        observation.flows,
        start=start,
        end=end,
        currency=observation.currency,
        evaluated_at=evaluated_at,
        source_generated_at=source_generated_at,
    )
    denominator, input_reasons = _flow_denominator_and_window(observation, start, end)
    reasons.extend(input_reasons)
    if reasons or denominator is None:
        return MonthlyRuleAssessment(
            rule="SIGNIFICANT_FLOW",
            outcome="UNKNOWN",
            failure_reasons=[],
            unknown_reasons=sorted(set(reasons)),
        )
    amounts = [Decimal(flow.amount) for flow in admitted]
    net = sum(amounts, Decimal(0))
    breach = abs(net) >= Decimal(policy.flow_threshold) * denominator
    return MonthlyRuleAssessment(
        rule="SIGNIFICANT_FLOW",
        outcome="FAIL" if breach else "PASS",
        failure_reasons=["SIGNIFICANT_FLOW_THRESHOLD_BREACH"] if breach else [],
        unknown_reasons=[],
        numerator=format(net, "f"),
        denominator=format(denominator, "f"),
        ratio=format(abs(net) / denominator, "f"),
        gross_inflow=format(sum((value for value in amounts if value > 0), Decimal(0)), "f"),
        gross_outflow=format(-sum((value for value in amounts if value < 0), Decimal(0)), "f"),
        admitted_flow_count=len(admitted),
    )


def _positive_denominator(value: str | None) -> Decimal | None:
    if value is None:
        return None
    amount = Decimal(value)
    return amount if amount > 0 else None


def _flow_denominator_and_window(
    observation: MonthlyPortfolioObservations,
    start: str,
    end: str,
) -> tuple[Decimal | None, list[str]]:
    reasons: list[str] = []
    if (observation.flow_coverage_from, observation.flow_coverage_to) != (start, end):
        reasons.append("FLOW_OBSERVATION_WINDOW_INCOMPLETE")
    prior_end = (date.fromisoformat(start) - timedelta(days=1)).isoformat()
    if observation.prior_assets_as_of != prior_end:
        reasons.append("FLOW_DENOMINATOR_DATE_MISMATCH")
    denominator = _positive_denominator(observation.prior_month_end_assets)
    if denominator is None:
        reasons.append("FLOW_DENOMINATOR_MISSING_OR_NONPOSITIVE")
    return denominator, reasons


def _cash_rule(
    policy: ResolvedMonthlyPolicy, observation: MonthlyPortfolioObservations, end: str
) -> MonthlyRuleAssessment:
    numerator, denominator, reasons = _cash_inputs(observation, end)
    if reasons or denominator is None or numerator is None:
        return MonthlyRuleAssessment(
            rule="CASH",
            outcome="UNKNOWN",
            failure_reasons=[],
            unknown_reasons=reasons,
        )
    breach = numerator > Decimal(policy.cash_threshold) * denominator
    return MonthlyRuleAssessment(
        rule="CASH",
        outcome="FAIL" if breach else "PASS",
        failure_reasons=["CASH_THRESHOLD_BREACH"] if breach else [],
        unknown_reasons=[],
        numerator=format(numerator, "f"),
        denominator=format(denominator, "f"),
        ratio=format(numerator / denominator, "f"),
    )


def _cash_inputs(
    observation: MonthlyPortfolioObservations,
    end: str,
) -> tuple[Decimal | None, Decimal | None, list[str]]:
    reasons: list[str] = []
    denominator = _positive_denominator(observation.month_end_assets)
    numerator = (
        None
        if observation.settled_unencumbered_cash is None
        else Decimal(observation.settled_unencumbered_cash)
    )
    if observation.cash_as_of != end:
        reasons.append("CASH_OBSERVATION_DATE_MISMATCH")
    if denominator is None:
        reasons.append("CASH_DENOMINATOR_MISSING_OR_NONPOSITIVE")
    if numerator is None or numerator < 0:
        reasons.append("CASH_NUMERATOR_MISSING_OR_NEGATIVE")
    return numerator, denominator, reasons


def _readiness_rule(observation: MonthlyPortfolioObservations, end: str) -> MonthlyRuleAssessment:
    if observation.readiness_as_of != end:
        return MonthlyRuleAssessment(
            rule="READINESS",
            outcome="UNKNOWN",
            failure_reasons=[],
            unknown_reasons=["READINESS_OBSERVATION_DATE_MISMATCH"],
        )
    failures: list[str] = []
    unknowns: list[str] = []
    for name, value in (
        ("DISCRETIONARY", observation.discretionary),
        ("FUNDED", observation.funded),
        ("INVESTED", observation.invested),
    ):
        if value is False:
            failures.append("READINESS_" + name + "_FAILED")
        elif value is None:
            unknowns.append("READINESS_" + name + "_UNKNOWN")
    outcome: RuleOutcome = "FAIL" if failures else "UNKNOWN" if unknowns else "PASS"
    return MonthlyRuleAssessment(
        rule="READINESS",
        outcome=outcome,
        failure_reasons=failures,
        unknown_reasons=unknowns,
    )
