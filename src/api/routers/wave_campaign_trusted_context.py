from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from src.api.routers.wave_campaign_definition_errors import (
    campaign_definition_trusted_tenant_http_exception,
)


@dataclass(frozen=True)
class CampaignTrustedContext:
    tenant_id: str


def campaign_trusted_context_required(request: Request) -> CampaignTrustedContext:
    tenant_id = request.headers.get("X-Tenant-Id", "").strip()
    if not tenant_id:
        raise campaign_definition_trusted_tenant_http_exception()
    return CampaignTrustedContext(tenant_id=tenant_id)
