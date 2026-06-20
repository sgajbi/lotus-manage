from datetime import date

from src.core.dpm_source_context import (
    DpmCorePortfolioManagerBookMember,
    DpmCorePortfolioManagerBookMembershipResponse,
    DpmCorePortfolioManagerBookSupportability,
)
from src.core.pm_quality.book_scope_refs import pm_book_member_source_refs


def _membership_response(member_count: int) -> DpmCorePortfolioManagerBookMembershipResponse:
    return DpmCorePortfolioManagerBookMembershipResponse(
        product_name="PortfolioManagerBookMembership",
        product_version="v1",
        as_of_date=date.fromisoformat("2026-05-12"),
        portfolio_manager_id="pm_001",
        members=[
            DpmCorePortfolioManagerBookMember(
                portfolio_id=f"PF_{index:03d}",
                client_id=f"client-{index:03d}",
                booking_center_code="Singapore",
                portfolio_type="DPM",
                status="ACTIVE",
                source_record_id=f"core-book-member-{index:03d}" if index == 1 else None,
            )
            for index in range(1, member_count + 1)
        ],
        supportability=DpmCorePortfolioManagerBookSupportability(
            state="READY",
            reason="PM_BOOK_SCOPE_MATERIALIZED",
            returned_portfolio_count=member_count,
            filters_applied={"portfolio_types": ["DPM"]},
        ),
        snapshot_id="pm-book-snapshot-20260512",
        source_batch_fingerprint="sha256:pm-book",
    )


def test_pm_book_member_source_refs_are_capped_and_use_source_record_fallback() -> None:
    refs = pm_book_member_source_refs(_membership_response(101))

    assert len(refs) == 100
    assert refs[0].source_id == "core-book-member-001"
    assert refs[1].source_id == "PF_002"
    assert refs[-1].source_id == "PF_100"
    assert {ref.source_system for ref in refs} == {"lotus-core"}
    assert {ref.source_type for ref in refs} == {"PORTFOLIO_MANAGER_BOOK_MEMBER"}
    assert {ref.source_version for ref in refs} == {"2026-05-12"}
