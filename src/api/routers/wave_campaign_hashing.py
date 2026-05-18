from __future__ import annotations

import hashlib
import json
from datetime import date


def campaign_governance_hash(
    *,
    trigger_id: str,
    actor_id: str,
    governance: dict[str, object],
) -> str:
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignGovernance",
        "product_version": "v1",
        "trigger_id": trigger_id,
        "actor_id": actor_id,
        "governance": governance,
    }
    return _canonical_sha256(payload)


def campaign_membership_hash(
    *,
    trigger_id: str,
    as_of_date: date,
    portfolio_types: list[str],
    portfolios: list[dict[str, object]],
) -> str:
    payload: dict[str, object] = {
        "product_name": "BulkReviewCampaignMembership",
        "product_version": "v1",
        "trigger_id": trigger_id,
        "as_of_date": as_of_date.isoformat(),
        "portfolio_types": portfolio_types,
        "portfolios": portfolios,
    }
    return _canonical_sha256(payload)


def _canonical_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
