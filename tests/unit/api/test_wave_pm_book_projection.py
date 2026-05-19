from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.api.routers.wave_pm_book_projection import build_pm_book_resolved_portfolios


@dataclass(frozen=True)
class Supportability:
    state: str = "READY"


@dataclass(frozen=True)
class Member:
    portfolio_id: str
    source_record_id: str | None


@dataclass(frozen=True)
class Membership:
    snapshot_id: str | None = "pm-book-snapshot-20260519"
    source_batch_fingerprint: str | None = "sha256:pm-book"
    portfolio_manager_id: str = "PM_SG_DPM_001"
    as_of_date: date = date(2026, 5, 19)
    product_version: str = "PortfolioManagerBookMembership:v1"
    supportability: Supportability = Supportability()
    members: list[Member] | None = None

    def __post_init__(self) -> None:
        if self.members is None:
            object.__setattr__(
                self,
                "members",
                [Member("PB_SG_GLOBAL_BAL_001", "pm-book-member-001")],
            )


def test_build_pm_book_resolved_portfolios_preserves_snapshot_lineage() -> None:
    assert build_pm_book_resolved_portfolios(Membership()) == [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "source_refs": [
                {
                    "source_system": "lotus-core",
                    "source_type": "PortfolioManagerBookMembership",
                    "source_id": "pm-book-snapshot-20260519",
                    "source_version": "PortfolioManagerBookMembership:v1",
                    "supportability_state": "READY",
                    "content_hash": "sha256:pm-book",
                },
                {
                    "source_system": "lotus-core",
                    "source_type": "PORTFOLIO_MANAGER_BOOK_MEMBER",
                    "source_id": "pm-book-member-001",
                    "source_version": "2026-05-19",
                    "supportability_state": "READY",
                },
            ],
        }
    ]


def test_build_pm_book_resolved_portfolios_falls_back_to_batch_fingerprint() -> None:
    portfolios = build_pm_book_resolved_portfolios(Membership(snapshot_id=None))

    assert portfolios[0]["source_refs"][0]["source_id"] == "sha256:pm-book"


def test_build_pm_book_resolved_portfolios_falls_back_to_deterministic_book_id() -> None:
    portfolios = build_pm_book_resolved_portfolios(
        Membership(snapshot_id=None, source_batch_fingerprint=None)
    )

    assert portfolios[0]["source_refs"][0]["source_id"] == "pm_book:PM_SG_DPM_001:2026-05-19"
    assert portfolios[0]["source_refs"][0]["content_hash"] is None


def test_build_pm_book_resolved_portfolios_falls_back_member_ref_to_portfolio_id() -> None:
    portfolios = build_pm_book_resolved_portfolios(
        Membership(members=[Member("PB_SG_GLOBAL_BAL_002", None)])
    )

    assert portfolios[0]["source_refs"][1]["source_id"] == "PB_SG_GLOBAL_BAL_002"
