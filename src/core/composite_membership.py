"""Manage-owned composite definitions and effective-dated membership evidence.

This module deliberately owns composite eligibility decisions, not portfolio returns,
assets, benchmarks, or composite calculation. Those remain source-owned by the
declared Performance and Core boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.common.canonical import hash_canonical_payload, strip_keys

CompositeMembershipStatus = Literal["INCLUDED", "EXCLUDED", "PENDING_REVIEW"]


def _require_nonblank(value: str, *, reason_code: str) -> str:
    if not value.strip():
        raise ValueError(reason_code)
    return value


def _parse_business_date(value: str, *, reason_code: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(reason_code) from exc


class DpmCompositeSourceAuthority(BaseModel):
    """Versioned ownership declaration compatible with Performance RFC-049."""

    definition_owner: Literal["lotus-manage"] = "lotus-manage"
    membership_owner: Literal["lotus-manage"] = "lotus-manage"
    member_return_owner: Literal["lotus-performance"] = "lotus-performance"
    asset_owner: Literal["lotus-core"] = "lotus-core"
    benchmark_owner: Literal["lotus-core"] | None = "lotus-core"
    policy_version: str = Field(examples=["composite-source-authority.v1"])

    @field_validator("policy_version")
    @classmethod
    def validate_policy_version(cls, value: str) -> str:
        return _require_nonblank(
            value, reason_code="COMPOSITE_SOURCE_AUTHORITY_POLICY_VERSION_REQUIRED"
        )


class DpmCompositeDefinition(BaseModel):
    """Immutable, tenant-owned composite definition revision."""

    product_name: Literal["CompositeDefinition"] = "CompositeDefinition"
    product_version: Literal["v1"] = "v1"
    tenant_id: str
    composite_id: str
    definition_version: str
    display_name: str
    strategy_code: str
    reporting_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    inception_date: str
    termination_date: str | None = None
    calculation_method: Literal["ASSET_WEIGHTED"] = "ASSET_WEIGHTED"
    eligibility_policy_version: str
    source_authority: DpmCompositeSourceAuthority
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    correlation_id: str
    content_hash: str = ""

    @field_validator(
        "tenant_id",
        "composite_id",
        "definition_version",
        "display_name",
        "strategy_code",
        "eligibility_policy_version",
        "created_by",
        "correlation_id",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_nonblank(value, reason_code="COMPOSITE_DEFINITION_REQUIRED_TEXT")

    @field_validator("reporting_currency", mode="before")
    @classmethod
    def normalize_reporting_currency(cls, value: object) -> object:
        if not isinstance(value, str) or value != value.strip() or not value.isascii():
            raise ValueError("COMPOSITE_DEFINITION_REPORTING_CURRENCY_INVALID")
        return value.upper()

    @model_validator(mode="after")
    def validate_dates_and_hash(self) -> "DpmCompositeDefinition":
        inception = _parse_business_date(
            self.inception_date, reason_code="COMPOSITE_DEFINITION_INCEPTION_DATE_INVALID"
        )
        if (
            self.termination_date is not None
            and _parse_business_date(
                self.termination_date, reason_code="COMPOSITE_DEFINITION_TERMINATION_DATE_INVALID"
            )
            < inception
        ):
            raise ValueError("COMPOSITE_DEFINITION_TERMINATION_BEFORE_INCEPTION")
        expected_hash = composite_definition_hash(self)
        if self.content_hash and self.content_hash != expected_hash:
            raise ValueError("COMPOSITE_DEFINITION_HASH_MISMATCH")
        self.content_hash = expected_hash
        return self


class DpmCompositeMembershipDecision(BaseModel):
    """One effective-dated inclusion, exclusion, or pending-review decision."""

    portfolio_id: str
    effective_from: str
    effective_to: str | None = None
    status: CompositeMembershipStatus = "INCLUDED"
    reason_code: str | None = None
    discretionary: bool = True
    approval_ref: str | None = None
    source_snapshot_id: str

    @field_validator("portfolio_id", "source_snapshot_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_nonblank(value, reason_code="COMPOSITE_MEMBERSHIP_REQUIRED_TEXT")

    @model_validator(mode="after")
    def validate_window_and_reason(self) -> "DpmCompositeMembershipDecision":
        effective_from = _parse_business_date(
            self.effective_from, reason_code="COMPOSITE_MEMBERSHIP_EFFECTIVE_FROM_INVALID"
        )
        if (
            self.effective_to is not None
            and _parse_business_date(
                self.effective_to, reason_code="COMPOSITE_MEMBERSHIP_EFFECTIVE_TO_INVALID"
            )
            < effective_from
        ):
            raise ValueError("COMPOSITE_MEMBERSHIP_EFFECTIVE_WINDOW_INVALID")
        if self.status != "INCLUDED" and not (self.reason_code and self.reason_code.strip()):
            raise ValueError("COMPOSITE_MEMBERSHIP_REASON_REQUIRED")
        if self.status == "INCLUDED" and self.reason_code is not None:
            raise ValueError("COMPOSITE_MEMBERSHIP_INCLUDED_REASON_FORBIDDEN")
        return self


class DpmCompositeMembershipRevision(BaseModel):
    """Immutable snapshot of eligibility decisions for one definition revision."""

    product_name: Literal["CompositeMembership"] = "CompositeMembership"
    product_version: Literal["v1"] = "v1"
    tenant_id: str
    composite_id: str
    definition_version: str
    membership_revision: str
    policy_version: str
    source_cut_id: str
    decisions: list[DpmCompositeMembershipDecision] = Field(min_length=1)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str
    correlation_id: str
    supersedes_membership_revision: str | None = None
    affected_from: str | None = None
    affected_to: str | None = None
    content_hash: str = ""

    @field_validator(
        "tenant_id",
        "composite_id",
        "definition_version",
        "membership_revision",
        "policy_version",
        "source_cut_id",
        "decided_by",
        "correlation_id",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _require_nonblank(value, reason_code="COMPOSITE_MEMBERSHIP_REVISION_REQUIRED_TEXT")

    @model_validator(mode="after")
    def validate_revision_windows_and_hash(self) -> "DpmCompositeMembershipRevision":
        _validate_decision_windows(self.decisions)
        if (self.affected_from is None) != (self.affected_to is None):
            raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_INCOMPLETE")
        if self.affected_from is not None and _parse_business_date(
            self.affected_to or "", reason_code="COMPOSITE_MEMBERSHIP_AFFECTED_TO_INVALID"
        ) < _parse_business_date(
            self.affected_from, reason_code="COMPOSITE_MEMBERSHIP_AFFECTED_FROM_INVALID"
        ):
            raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_INVALID")
        if self.supersedes_membership_revision is None and self.affected_from is not None:
            raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_SUPERSEDES_REQUIRED")
        if self.supersedes_membership_revision is not None and self.affected_from is None:
            raise ValueError("COMPOSITE_MEMBERSHIP_CORRECTION_WINDOW_REQUIRED")
        expected_hash = composite_membership_revision_hash(self)
        if self.content_hash and self.content_hash != expected_hash:
            raise ValueError("COMPOSITE_MEMBERSHIP_REVISION_HASH_MISMATCH")
        self.content_hash = expected_hash
        return self


def _validate_decision_windows(decisions: list[DpmCompositeMembershipDecision]) -> None:
    by_portfolio: dict[str, list[DpmCompositeMembershipDecision]] = {}
    for decision in decisions:
        by_portfolio.setdefault(decision.portfolio_id, []).append(decision)
    for portfolio_decisions in by_portfolio.values():
        ordered = sorted(portfolio_decisions, key=lambda decision: decision.effective_from)
        for previous, current in zip(ordered, ordered[1:]):
            if previous.effective_to is None or _parse_business_date(
                current.effective_from, reason_code="COMPOSITE_MEMBERSHIP_EFFECTIVE_FROM_INVALID"
            ) <= _parse_business_date(
                previous.effective_to, reason_code="COMPOSITE_MEMBERSHIP_EFFECTIVE_TO_INVALID"
            ):
                raise ValueError("COMPOSITE_MEMBERSHIP_DECISION_WINDOW_OVERLAP")


def composite_definition_hash(definition: DpmCompositeDefinition) -> str:
    return hash_canonical_payload(
        strip_keys(definition.model_dump(mode="json"), exclude={"content_hash"})
    )


def composite_membership_revision_hash(revision: DpmCompositeMembershipRevision) -> str:
    return hash_canonical_payload(
        strip_keys(revision.model_dump(mode="json"), exclude={"content_hash"})
    )


__all__ = [
    "CompositeMembershipStatus",
    "DpmCompositeDefinition",
    "DpmCompositeMembershipDecision",
    "DpmCompositeMembershipRevision",
    "DpmCompositeSourceAuthority",
    "composite_definition_hash",
    "composite_membership_revision_hash",
]
