"""Compare complete evaluations over one pinned input and evaluation instant."""

from pydantic import Field

from src.core.composite_authority_models import Identity, StrictAuthorityModel
from src.core.composite_eligibility.evaluation import MonthlyEligibilityEvaluation
from src.core.composite_eligibility.rules import RuleName
from src.core.composite_membership import CompositeMembershipStatus


class MonthlyMemberDifference(StrictAuthorityModel):
    portfolio_id: Identity
    baseline_status: CompositeMembershipStatus
    candidate_status: CompositeMembershipStatus
    changed_rules: list[RuleName] = Field(max_length=3)


class MonthlyEligibilityDiff(StrictAuthorityModel):
    baseline: MonthlyEligibilityEvaluation
    candidate: MonthlyEligibilityEvaluation
    policy_content_changed: bool
    changed_portfolio_count: int = Field(ge=0, le=1000)
    differences: list[MonthlyMemberDifference] = Field(max_length=1000)


def compare_monthly_evaluations(
    baseline: MonthlyEligibilityEvaluation,
    candidate: MonthlyEligibilityEvaluation,
) -> MonthlyEligibilityDiff:
    baseline = MonthlyEligibilityEvaluation.model_validate(baseline.model_dump(mode="json"))
    candidate = MonthlyEligibilityEvaluation.model_validate(candidate.model_dump(mode="json"))
    bindings = (
        "tenant_id",
        "composite_id",
        "definition_version",
        "month",
        "source_cut_id",
        "source_revision",
        "input_content_hash",
        "universe_content_hash",
        "evaluated_at",
    )
    if any(getattr(baseline, key) != getattr(candidate, key) for key in bindings):
        raise ValueError("COMPOSITE_ELIGIBILITY_DIFF_BINDING_MISMATCH")
    if [item.portfolio_id for item in baseline.portfolios] != [
        item.portfolio_id for item in candidate.portfolios
    ]:
        raise ValueError("COMPOSITE_ELIGIBILITY_DIFF_UNIVERSE_MISMATCH")
    differences = []
    for before, after in zip(baseline.portfolios, candidate.portfolios, strict=True):
        changed = [
            old.rule
            for old, new in zip(before.assessments, after.assessments, strict=True)
            if old != new
        ]
        if changed:
            differences.append(
                MonthlyMemberDifference(
                    portfolio_id=before.portfolio_id,
                    baseline_status=before.status,
                    candidate_status=after.status,
                    changed_rules=changed,
                )
            )
    return MonthlyEligibilityDiff(
        baseline=baseline,
        candidate=candidate,
        policy_content_changed=baseline.resolved_policy.content_hash
        != candidate.resolved_policy.content_hash,
        changed_portfolio_count=len(differences),
        differences=differences,
    )
