"""Canonical complete-universe evaluation, separate from approved membership publication."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from pydantic import Field, TypeAdapter, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.observations import (
    MonthlyPortfolioObservations,
    MonthlyEligibilityObservations,
    UtcInstant,
)
from src.core.composite_eligibility.policy import ResolvedMonthlyPolicy
from src.core.composite_eligibility.rules import (
    MonthlyRuleAssessment,
    RuleName,
    evaluate_monthly_rules,
)
from src.core.composite_membership import CompositeMembershipStatus


class MonthlyPortfolioEvaluation(StrictAuthorityModel):
    portfolio_id: Identity
    observations_present: bool
    status: CompositeMembershipStatus
    assessments: list[MonthlyRuleAssessment] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def require_all_rules_and_status(self) -> MonthlyPortfolioEvaluation:
        if [item.rule for item in self.assessments] != ["SIGNIFICANT_FLOW", "CASH", "READINESS"]:
            raise ValueError("COMPOSITE_ELIGIBILITY_RULE_SET_INVALID")
        if self.status != _membership_status(self.assessments):
            raise ValueError("COMPOSITE_ELIGIBILITY_STATUS_MISMATCH")
        return self


class PortfolioCounts(TypedDict):
    expected_count: int
    observed_count: int
    included_count: int
    excluded_count: int
    pending_review_count: int


class MonthlyEligibilityEvaluation(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityEvaluation"] = (
        "CompositeMonthlyEligibilityEvaluation"
    )
    product_version: Literal["v1"] = "v1"
    evidence_class: Literal["SYNTHETIC_UNQUALIFIED", "SOURCE_UNVERIFIED"]
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    population_verification: Literal["UNVERIFIED"] = "UNVERIFIED"
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    month: str
    source_cut_id: Identity
    source_revision: Identity
    evaluated_at: UtcInstant
    input_content_hash: Digest
    universe_content_hash: Digest
    resolved_policy: ResolvedMonthlyPolicy
    declared_universe_coverage: Literal["COMPLETE", "INCOMPLETE"]
    expected_count: int = Field(ge=1, le=1000)
    observed_count: int = Field(ge=0, le=1000)
    included_count: int = Field(ge=0, le=1000)
    excluded_count: int = Field(ge=0, le=1000)
    pending_review_count: int = Field(ge=0, le=1000)
    portfolios: list[MonthlyPortfolioEvaluation] = Field(min_length=1, max_length=1000)
    content_hash: str = ""

    @model_validator(mode="after")
    def require_pinned_scope_counts_and_content(self) -> MonthlyEligibilityEvaluation:
        datetime.fromisoformat(self.evaluated_at)
        _require_evaluation_scope(self)
        members = [item.portfolio_id for item in self.portfolios]
        if members != sorted(set(members)):
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_UNIVERSE_NONCANONICAL")
        counts = _portfolio_counts(self.portfolios)
        if any(getattr(self, key) != value for key, value in counts.items()):
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_COUNTS_MISMATCH")
        coverage = "COMPLETE" if self.expected_count == self.observed_count else "INCOMPLETE"
        if self.declared_universe_coverage != coverage:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_COVERAGE_MISMATCH")
        expected_hash = hash_canonical_payload(
            self.model_dump(mode="json", exclude={"content_hash"})
        )
        if self.content_hash and self.content_hash != expected_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_CONTENT_MISMATCH")
        self.content_hash = expected_hash
        return self


def evaluate_monthly_eligibility(
    policy: ResolvedMonthlyPolicy,
    scenario: MonthlyEligibilityObservations,
    *,
    evaluated_at: str,
    universe_content_hash: str,
) -> MonthlyEligibilityEvaluation:
    policy = ResolvedMonthlyPolicy.model_validate(policy.model_dump(mode="json"))
    scenario = MonthlyEligibilityObservations.model_validate(scenario.model_dump(mode="json"))
    evaluated_at = TypeAdapter(UtcInstant).validate_python(evaluated_at)
    if datetime.fromisoformat(scenario.source_generated_at) > datetime.fromisoformat(evaluated_at):
        raise ValueError("COMPOSITE_ELIGIBILITY_FUTURE_SOURCE_GENERATION")
    if scenario.month != policy.month:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_MONTH_MISMATCH")
    if (scenario.tenant_id, scenario.composite_id, scenario.definition_version) != (
        policy.scope.tenant_id,
        policy.scope.composite_id,
        policy.scope.definition_version,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_SCOPE_MISMATCH")
    observations = _distinct_portfolios(scenario.portfolios)
    portfolios = [
        _evaluate_portfolio(member, observations.get(member), policy, scenario, evaluated_at)
        for member in scenario.expected_portfolio_ids
    ]
    result = MonthlyEligibilityEvaluation(
        evidence_class=scenario.evidence_class,
        tenant_id=scenario.tenant_id,
        composite_id=scenario.composite_id,
        definition_version=scenario.definition_version,
        month=policy.month,
        source_cut_id=scenario.source_cut_id,
        source_revision=scenario.source_revision,
        evaluated_at=evaluated_at,
        universe_content_hash=universe_content_hash,
        input_content_hash=hash_canonical_payload(scenario.model_dump(mode="json")),
        resolved_policy=policy,
        declared_universe_coverage=(
            "COMPLETE" if len(observations) == len(portfolios) else "INCOMPLETE"
        ),
        **_portfolio_counts(portfolios),
        portfolios=portfolios,
    )
    return result


def _require_evaluation_scope(evaluation: MonthlyEligibilityEvaluation) -> None:
    scope = evaluation.resolved_policy.scope
    if (
        evaluation.tenant_id,
        evaluation.composite_id,
        evaluation.definition_version,
        evaluation.month,
    ) != (
        scope.tenant_id,
        scope.composite_id,
        scope.definition_version,
        evaluation.resolved_policy.month,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_SCOPE_MISMATCH")


def _portfolio_counts(portfolios: list[MonthlyPortfolioEvaluation]) -> PortfolioCounts:
    return {
        "expected_count": len(portfolios),
        "observed_count": sum(item.observations_present for item in portfolios),
        "included_count": sum(item.status == "INCLUDED" for item in portfolios),
        "excluded_count": sum(item.status == "EXCLUDED" for item in portfolios),
        "pending_review_count": sum(item.status == "PENDING_REVIEW" for item in portfolios),
    }


def _distinct_portfolios(
    portfolios: list[MonthlyPortfolioObservations],
) -> dict[str, MonthlyPortfolioObservations]:
    distinct: dict[str, MonthlyPortfolioObservations] = {}
    for portfolio in portfolios:
        prior = distinct.get(portfolio.portfolio_id)
        if prior is not None and prior != portfolio:
            raise ValueError("COMPOSITE_ELIGIBILITY_DUPLICATE_PORTFOLIO_CONFLICT")
        distinct[portfolio.portfolio_id] = portfolio
    return distinct


def _evaluate_portfolio(
    portfolio_id: str,
    observation: MonthlyPortfolioObservations | None,
    policy: ResolvedMonthlyPolicy,
    scenario: MonthlyEligibilityObservations,
    evaluated_at: str,
) -> MonthlyPortfolioEvaluation:
    assessments = _portfolio_assessments(observation, policy, scenario, evaluated_at)
    return MonthlyPortfolioEvaluation(
        portfolio_id=portfolio_id,
        observations_present=observation is not None,
        status=_membership_status(assessments),
        assessments=assessments,
    )


def _portfolio_assessments(
    observation: MonthlyPortfolioObservations | None,
    policy: ResolvedMonthlyPolicy,
    scenario: MonthlyEligibilityObservations,
    evaluated_at: str,
) -> list[MonthlyRuleAssessment]:
    if observation is None:
        return _unknown_assessments("MISSING_EXPECTED_PORTFOLIO_OBSERVATIONS")
    if observation.currency != scenario.reporting_currency:
        return _unknown_assessments("PORTFOLIO_CURRENCY_SCOPE_MISMATCH")
    return evaluate_monthly_rules(
        policy,
        observation,
        evaluated_at=evaluated_at,
        source_generated_at=scenario.source_generated_at,
    )


def _unknown_assessments(reason: str) -> list[MonthlyRuleAssessment]:
    names: tuple[RuleName, ...] = ("SIGNIFICANT_FLOW", "CASH", "READINESS")
    return [
        MonthlyRuleAssessment(
            rule=rule, outcome="UNKNOWN", failure_reasons=[], unknown_reasons=[reason]
        )
        for rule in names
    ]


def _membership_status(assessments: list[MonthlyRuleAssessment]) -> CompositeMembershipStatus:
    if any(item.outcome == "FAIL" for item in assessments):
        return "EXCLUDED"
    if any(item.outcome == "UNKNOWN" for item in assessments):
        return "PENDING_REVIEW"
    return "INCLUDED"
