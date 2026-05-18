from __future__ import annotations

from datetime import date

from src.api.routers.wave_campaign_hashing import (
    campaign_governance_hash,
    campaign_membership_hash,
)


def test_campaign_governance_hash_is_stable_for_reordered_governance_fields() -> None:
    first = campaign_governance_hash(
        trigger_id="campaign-q2-review",
        actor_id="pm_001",
        governance={
            "approved_by": "cio_001",
            "approval_ref": "approval-001",
            "approved_at": "2026-05-18T09:00:00Z",
        },
    )
    second = campaign_governance_hash(
        trigger_id="campaign-q2-review",
        actor_id="pm_001",
        governance={
            "approved_at": "2026-05-18T09:00:00Z",
            "approval_ref": "approval-001",
            "approved_by": "cio_001",
        },
    )

    assert first == second
    assert first.startswith("sha256:")


def test_campaign_governance_hash_changes_when_actor_changes() -> None:
    governance = {
        "approval_ref": "approval-001",
        "approved_by": "cio_001",
        "approved_at": "2026-05-18T09:00:00Z",
    }

    assert campaign_governance_hash(
        trigger_id="campaign-q2-review",
        actor_id="pm_001",
        governance=governance,
    ) != campaign_governance_hash(
        trigger_id="campaign-q2-review",
        actor_id="pm_002",
        governance=governance,
    )


def test_campaign_membership_hash_is_stable_for_same_payload() -> None:
    portfolios = [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "portfolio_type": "DISCRETIONARY",
        }
    ]

    assert campaign_membership_hash(
        trigger_id="campaign-q2-review",
        as_of_date=date(2026, 5, 18),
        portfolio_types=["DISCRETIONARY"],
        portfolios=portfolios,
    ) == campaign_membership_hash(
        trigger_id="campaign-q2-review",
        as_of_date=date(2026, 5, 18),
        portfolio_types=["DISCRETIONARY"],
        portfolios=portfolios,
    )


def test_campaign_membership_hash_changes_when_membership_changes() -> None:
    base_portfolios = [
        {
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "portfolio_type": "DISCRETIONARY",
        }
    ]
    expanded_portfolios = [
        *base_portfolios,
        {
            "portfolio_id": "PB_SG_INCOME_002",
            "portfolio_type": "DISCRETIONARY",
        },
    ]

    assert campaign_membership_hash(
        trigger_id="campaign-q2-review",
        as_of_date=date(2026, 5, 18),
        portfolio_types=["DISCRETIONARY"],
        portfolios=base_portfolios,
    ) != campaign_membership_hash(
        trigger_id="campaign-q2-review",
        as_of_date=date(2026, 5, 18),
        portfolio_types=["DISCRETIONARY"],
        portfolios=expanded_portfolios,
    )
