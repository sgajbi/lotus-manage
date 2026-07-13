from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.core.waves.models import DpmWaveSourceRef


@dataclass(frozen=True)
class DpmBulkReviewCampaignSourceContractError(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


_APPROVED_HASH_REQUIRED_SOURCE_CONTRACTS = frozenset(
    {
        ("lotus-core", "DpmPortfolioUniverseCandidate"),
        ("lotus-manage", "BulkReviewCampaignDefinition"),
        ("lotus-manage", "AFFECTED_PORTFOLIO_MANIFEST"),
    }
)
_APPROVED_BATCH_COVERED_SOURCE_CONTRACTS = frozenset(
    {
        ("lotus-core", "DPM_PORTFOLIO_UNIVERSE_CANDIDATE"),
    }
)
_APPROVED_SOURCE_CONTRACTS = (
    _APPROVED_HASH_REQUIRED_SOURCE_CONTRACTS | _APPROVED_BATCH_COVERED_SOURCE_CONTRACTS
)
_BATCH_HASH_SOURCE_CONTRACTS = frozenset(
    {
        ("lotus-core", "DpmPortfolioUniverseCandidate"),
    }
)


def validate_bulk_review_campaign_candidate_source_refs(
    *,
    portfolio_id: str,
    source_refs: Sequence[DpmWaveSourceRef],
) -> None:
    batch_hash_available = any(
        _source_contract_key(ref) in _BATCH_HASH_SOURCE_CONTRACTS
        and _non_blank(ref.content_hash)
        for ref in source_refs
    )
    for ref in source_refs:
        _validate_candidate_source_ref(
            portfolio_id=portfolio_id,
            ref=ref,
            batch_hash_available=batch_hash_available,
        )


def _validate_candidate_source_ref(
    *,
    portfolio_id: str,
    ref: DpmWaveSourceRef,
    batch_hash_available: bool,
) -> None:
    source_contract = _source_contract_key(ref)
    if source_contract not in _APPROVED_SOURCE_CONTRACTS:
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_CONTRACT_UNSUPPORTED",
            message=(
                "Bulk-review campaign candidate source refs must use an approved source "
                f"contract before membership can be published as READY; portfolio {portfolio_id} "
                f"provided {ref.source_system}:{ref.source_type}."
            ),
        )
    if not _non_blank(ref.source_id):
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_ID_REQUIRED",
            message=(
                "Bulk-review campaign candidate source refs require a source_id before "
                f"membership can be published as READY; portfolio {portfolio_id} is incomplete."
            ),
        )
    if not _non_blank(ref.source_version):
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_VERSION_REQUIRED",
            message=(
                "Bulk-review campaign candidate source refs require a source_version before "
                f"membership can be published as READY; portfolio {portfolio_id} is incomplete."
            ),
        )
    if not _non_blank(ref.supportability_state):
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_SUPPORTABILITY_REQUIRED",
            message=(
                "Bulk-review campaign candidate source refs require supportability_state before "
                f"membership can be published as READY; portfolio {portfolio_id} is incomplete."
            ),
        )
    if ref.supportability_state is None or ref.supportability_state.strip().upper() != "READY":
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_NOT_READY",
            message=(
                "Bulk-review campaign candidate source refs must be READY before membership can "
                f"be published as READY; portfolio {portfolio_id} is "
                f"{ref.supportability_state}."
            ),
        )
    if source_contract in _APPROVED_HASH_REQUIRED_SOURCE_CONTRACTS and not _non_blank(
        ref.content_hash
    ):
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_HASH_REQUIRED",
            message=(
                "Bulk-review campaign candidate source refs require a content_hash before "
                f"membership can be published as READY; portfolio {portfolio_id} is incomplete."
            ),
        )
    if source_contract in _APPROVED_BATCH_COVERED_SOURCE_CONTRACTS and not (
        _non_blank(ref.content_hash) or batch_hash_available
    ):
        raise DpmBulkReviewCampaignSourceContractError(
            code="BULK_REVIEW_CAMPAIGN_SOURCE_HASH_REQUIRED",
            message=(
                "Bulk-review campaign candidate record refs require a content_hash or an "
                "approved batch-level source fingerprint before membership can be published as "
                f"READY; portfolio {portfolio_id} is incomplete."
            ),
        )


def _source_contract_key(ref: DpmWaveSourceRef) -> tuple[str, str]:
    return (ref.source_system.strip(), ref.source_type.strip())


def _non_blank(value: str | None) -> bool:
    return value is not None and bool(value.strip())
