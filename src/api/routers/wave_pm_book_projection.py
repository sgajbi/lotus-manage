from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from src.api.routers.wave_source_refs import pm_book_member_ref, pm_book_membership_ref


class PmBookSupportability(Protocol):
    @property
    def state(self) -> str: ...


class PmBookMember(Protocol):
    @property
    def portfolio_id(self) -> str: ...

    @property
    def source_record_id(self) -> str | None: ...


class PmBookMembership(Protocol):
    @property
    def snapshot_id(self) -> str | None: ...

    @property
    def source_batch_fingerprint(self) -> str | None: ...

    @property
    def portfolio_manager_id(self) -> str: ...

    @property
    def as_of_date(self) -> date: ...

    @property
    def product_version(self) -> str: ...

    @property
    def supportability(self) -> PmBookSupportability: ...

    @property
    def members(self) -> Sequence[PmBookMember]: ...


def build_pm_book_resolved_portfolios(
    membership: PmBookMembership,
) -> list[dict[str, object]]:
    source_id = (
        membership.snapshot_id
        or membership.source_batch_fingerprint
        or f"pm_book:{membership.portfolio_manager_id}:{membership.as_of_date.isoformat()}"
    )
    book_ref = pm_book_membership_ref(
        source_id=source_id,
        product_version=membership.product_version,
        supportability_state=membership.supportability.state,
        content_hash=membership.source_batch_fingerprint,
    )
    return [
        {
            "portfolio_id": member.portfolio_id,
            "source_refs": [
                book_ref,
                pm_book_member_ref(
                    source_record_id=member.source_record_id,
                    portfolio_id=member.portfolio_id,
                    as_of_date=membership.as_of_date,
                ),
            ],
        }
        for member in membership.members
    ]
