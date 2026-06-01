from datetime import date
from types import SimpleNamespace

import pytest

from src.api.services import mandate_pm_book, mandate_service
from src.api.services.mandate_errors import DpmMandateSourceIncompleteError
from src.api.services.mandate_pm_book import mandate_ids_from_pm_book_membership
from src.core.dpm_source_context import DpmCorePortfolioManagerBookMembershipResponse


class _Repository:
    def __init__(self, portfolio_to_mandate: dict[str, str]) -> None:
        self.portfolio_to_mandate = portfolio_to_mandate

    def get_latest_mandate_by_portfolio(self, *, portfolio_id: str) -> object | None:
        mandate_id = self.portfolio_to_mandate.get(portfolio_id)
        if mandate_id is None:
            return None
        return SimpleNamespace(mandate_id=mandate_id)


def _membership(
    *,
    portfolio_ids: list[str],
) -> DpmCorePortfolioManagerBookMembershipResponse:
    return DpmCorePortfolioManagerBookMembershipResponse.model_validate(
        {
            "product_name": "PortfolioManagerBookMembership",
            "product_version": "v1",
            "as_of_date": date(2026, 5, 3),
            "tenant_id": "default",
            "portfolio_manager_id": "PM_SG_DPM_001",
            "members": [
                {
                    "portfolio_id": portfolio_id,
                    "client_id": f"CLIENT_{index}",
                    "booking_center_code": "Singapore",
                    "portfolio_type": "DISCRETIONARY",
                    "status": "ACTIVE",
                    "base_currency": "SGD",
                }
                for index, portfolio_id in enumerate(portfolio_ids, start=1)
            ],
            "supportability": {
                "state": "READY",
                "reason": "PM_BOOK_MEMBERSHIP_READY",
                "returned_portfolio_count": len(portfolio_ids),
                "filters_applied": {"portfolio_types": ["DISCRETIONARY"]},
            },
        }
    )


def test_mandate_ids_from_pm_book_membership_resolves_portfolio_members() -> None:
    mandate_ids = mandate_ids_from_pm_book_membership(
        repository=_Repository(
            {
                "PB_SG_GLOBAL_BAL_001": "MANDATE_PB_SG_GLOBAL_BAL_001",
                "PB_SG_INCOME_002": "MANDATE_PB_SG_INCOME_002",
            }
        ),
        membership=_membership(
            portfolio_ids=["PB_SG_GLOBAL_BAL_001", "PB_SG_INCOME_002"],
        ),
    )

    assert mandate_ids == [
        "MANDATE_PB_SG_GLOBAL_BAL_001",
        "MANDATE_PB_SG_INCOME_002",
    ]


def test_mandate_ids_from_pm_book_membership_rejects_missing_snapshot() -> None:
    with pytest.raises(DpmMandateSourceIncompleteError) as exc_info:
        mandate_ids_from_pm_book_membership(
            repository=_Repository({"PB_SG_GLOBAL_BAL_001": "MANDATE_PB_SG_GLOBAL_BAL_001"}),
            membership=_membership(
                portfolio_ids=["PB_SG_GLOBAL_BAL_001", "PB_SG_MISSING_002"],
            ),
        )

    assert str(exc_info.value) == "DPM_PM_BOOK_MANDATE_SNAPSHOT_MISSING"


def test_mandate_ids_from_pm_book_membership_rejects_empty_membership() -> None:
    with pytest.raises(DpmMandateSourceIncompleteError) as exc_info:
        mandate_ids_from_pm_book_membership(
            repository=_Repository({}),
            membership=_membership(portfolio_ids=[]),
        )

    assert str(exc_info.value) == "DPM_PM_BOOK_MANDATE_SNAPSHOT_EMPTY"


def test_service_preserves_pm_book_helper_import_surface() -> None:
    assert (
        mandate_service.mandate_ids_from_pm_book_membership is mandate_ids_from_pm_book_membership
    )


def test_pm_book_helper_exports_public_surface() -> None:
    assert mandate_pm_book.__all__ == ["mandate_ids_from_pm_book_membership"]
