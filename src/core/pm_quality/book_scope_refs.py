"""Shared source-reference projection for PM-quality book-scope evidence."""

from __future__ import annotations

from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.outcomes import DpmOutcomeSourceRef


def pm_book_member_source_refs(
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> list[DpmOutcomeSourceRef]:
    return [
        DpmOutcomeSourceRef(
            source_system="lotus-core",
            source_type="PORTFOLIO_MANAGER_BOOK_MEMBER",
            source_id=member.source_record_id or member.portfolio_id,
            source_version=membership.as_of_date.isoformat(),
        )
        for member in membership.members[:100]
    ]
