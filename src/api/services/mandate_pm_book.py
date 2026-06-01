from __future__ import annotations

from src.api.services.mandate_errors import DpmMandateSourceIncompleteError
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse
from src.core.mandate_repository import DpmMandateRepository


def mandate_ids_from_pm_book_membership(
    *,
    repository: DpmMandateRepository,
    membership: DpmCorePortfolioManagerBookMembershipResponse,
) -> list[str]:
    mandate_ids: list[str] = []
    missing_portfolio_ids: list[str] = []
    for member in membership.members:
        twin = repository.get_latest_mandate_by_portfolio(portfolio_id=member.portfolio_id)
        if twin is None:
            missing_portfolio_ids.append(member.portfolio_id)
            continue
        mandate_ids.append(twin.mandate_id)

    if missing_portfolio_ids:
        raise DpmMandateSourceIncompleteError("DPM_PM_BOOK_MANDATE_SNAPSHOT_MISSING")
    if not mandate_ids:
        raise DpmMandateSourceIncompleteError("DPM_PM_BOOK_MANDATE_SNAPSHOT_EMPTY")
    return mandate_ids


__all__ = ["mandate_ids_from_pm_book_membership"]
