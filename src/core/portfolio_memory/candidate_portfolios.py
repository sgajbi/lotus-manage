"""Candidate portfolio discovery for portfolio-memory search."""

from src.core.mandate_repository import DpmMandateRepository
from src.core.outcomes.repository import DpmOutcomeReviewRepository
from src.core.pm_quality.repository import DpmPmQualityScoreRunRepository
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.waves.campaign_repository import DpmBulkReviewCampaignDefinitionRepository
from src.core.waves.repository import DpmWaveRepository


def candidate_portfolio_ids(
    *,
    proof_pack_repository: DpmProofPackRepository,
    wave_repository: DpmWaveRepository,
    outcome_review_repository: DpmOutcomeReviewRepository,
    mandate_repository: DpmMandateRepository | None,
    campaign_definition_repository: DpmBulkReviewCampaignDefinitionRepository | None,
    pm_quality_score_run_repository: DpmPmQualityScoreRunRepository | None,
    portfolio_ids: list[str] | None,
    source_scan_limit: int,
) -> list[str]:
    candidates: set[str] = {
        portfolio_id.strip() for portfolio_id in (portfolio_ids or []) if portfolio_id.strip()
    }
    candidates.update(
        proof_pack.portfolio_id
        for proof_pack in proof_pack_repository.list_proof_packs(limit=source_scan_limit)
    )
    candidates.update(
        item.portfolio_id
        for wave in wave_repository.list_waves(limit=source_scan_limit)
        for item in wave.items
    )
    candidates.update(
        review.portfolio_id
        for review in outcome_review_repository.list_outcome_reviews(limit=source_scan_limit)
    )
    if mandate_repository is not None:
        exceptions, _cursor = mandate_repository.list_monitoring_exceptions(
            monitoring_run_id=None,
            mandate_id=None,
            portfolio_id=None,
            state=None,
            limit=source_scan_limit,
            cursor=None,
        )
        candidates.update(exception.portfolio_id for exception in exceptions)
    if campaign_definition_repository is not None:
        candidates.update(
            candidate.portfolio_id
            for definition in campaign_definition_repository.list_definitions(
                limit=source_scan_limit
            )
            for candidate in definition.candidates
        )
    if pm_quality_score_run_repository is not None:
        candidates.update(
            portfolio_id
            for score_run in pm_quality_score_run_repository.list_score_runs(
                limit=source_scan_limit
            )
            if score_run.book_scope_evidence is not None
            for portfolio_id in score_run.book_scope_evidence.member_portfolio_ids
        )
    return sorted(candidates)
