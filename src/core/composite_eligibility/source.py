"""Authority-scoped source port: caller data cannot substitute for registered observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.policy import MonthlyPolicyScope


class MonthlyEligibilitySourceUnavailable(ValueError):
    """No source adapter supplies the requested immutable monthly population."""


@dataclass(frozen=True)
class MonthlyEligibilitySourceRequest:
    scope: MonthlyPolicyScope
    month: str
    source_cut_id: str
    owner_service: str
    expected_source_revision: str
    expected_content_hash: str
    expected_portfolio_ids: tuple[str, ...]
    reporting_currency: str


@dataclass(frozen=True)
class MonthlyEligibilitySourceResolution:
    observations: MonthlyEligibilityObservations | None
    owner_service: str | None = None


class MonthlyEligibilitySourcePort(Protocol):
    def resolve(
        self, request: MonthlyEligibilitySourceRequest
    ) -> MonthlyEligibilitySourceResolution:
        """Resolve source-owned facts; never accept a client-supplied population as authority."""


class UnavailableMonthlyEligibilitySource:
    def resolve(
        self, request: MonthlyEligibilitySourceRequest
    ) -> MonthlyEligibilitySourceResolution:
        return MonthlyEligibilitySourceResolution(observations=None)


def admitted_source_snapshot(
    request: MonthlyEligibilitySourceRequest, resolution: MonthlyEligibilitySourceResolution
) -> MonthlyEligibilityObservations:
    if resolution.observations is None:
        raise MonthlyEligibilitySourceUnavailable("COMPOSITE_ELIGIBILITY_SOURCE_UNAVAILABLE")
    if resolution.owner_service != request.owner_service:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_OWNER_MISMATCH")
    snapshot = MonthlyEligibilityObservations.model_validate(
        resolution.observations.model_dump(mode="json")
    )
    if (snapshot.tenant_id, snapshot.composite_id, snapshot.definition_version) != (
        request.scope.tenant_id,
        request.scope.composite_id,
        request.scope.definition_version,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_SCOPE_MISMATCH")
    if snapshot.source_cut_id != request.source_cut_id:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_CUT_MISMATCH")
    if snapshot.source_revision != request.expected_source_revision:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_REVISION_MISMATCH")
    if snapshot.month != request.month:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_MONTH_MISMATCH")
    if snapshot.reporting_currency != request.reporting_currency:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_CURRENCY_MISMATCH")
    if tuple(snapshot.expected_portfolio_ids) != request.expected_portfolio_ids:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_UNIVERSE_MISMATCH")
    if hash_canonical_payload(snapshot.model_dump(mode="json")) != request.expected_content_hash:
        raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_CONTENT_MISMATCH")
    return snapshot
