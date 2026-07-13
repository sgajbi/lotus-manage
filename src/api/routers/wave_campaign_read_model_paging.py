from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.api.observability import record_campaign_read_model_scan

CampaignReadModelScanMode = Literal["bounded_prefix", "full_scan"]
CampaignReadModelScanReason = Literal[
    "repository_filters",
    "workflow_projection_filters",
    "derived_filters",
]


@dataclass(frozen=True)
class CampaignReadModelRepositoryPaging:
    page_limit: int | None
    page_offset: int
    scan_mode: CampaignReadModelScanMode
    reason: CampaignReadModelScanReason


def campaign_read_model_repository_paging(
    *,
    repository_safe: bool,
    limit: int,
    offset: int,
    bounded_reason: CampaignReadModelScanReason,
) -> CampaignReadModelRepositoryPaging:
    if repository_safe:
        return CampaignReadModelRepositoryPaging(
            page_limit=limit,
            page_offset=offset,
            scan_mode="bounded_prefix",
            reason=bounded_reason,
        )
    return CampaignReadModelRepositoryPaging(
        page_limit=None,
        page_offset=0,
        scan_mode="full_scan",
        reason="derived_filters",
    )


def record_campaign_read_model_paging(
    *,
    surface: str,
    paging: CampaignReadModelRepositoryPaging,
) -> None:
    record_campaign_read_model_scan(
        surface=surface,
        scan_mode=paging.scan_mode,
        reason=paging.reason,
    )
