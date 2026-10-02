"""Durable, tenant-scoped publication evidence for composite membership revisions.

A publication announces an immutable source revision; it does not assert that
the decision universe, member returns, assets, or downstream calculations are complete.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.composite_membership import DpmCompositeMembershipRevision


class DpmCompositeMembershipPublication(BaseModel):
    product_name: Literal["CompositeMembershipPublication"] = "CompositeMembershipPublication"
    product_version: Literal["v1"] = "v1"
    sequence: int = Field(gt=0, description="Monotonic tenant-visible publication cursor.")
    tenant_id: str
    composite_id: str
    definition_version: str
    membership_revision: str
    membership_content_hash: str
    policy_version: str
    source_cut_id: str
    decision_count: int = Field(ge=1)
    supersedes_membership_revision: str | None = None
    affected_from: str | None = None
    affected_to: str | None = None
    decided_at: datetime
    published_at: datetime
    completeness: Literal["UNVERIFIED"] = "UNVERIFIED"

    @field_validator(
        "tenant_id",
        "composite_id",
        "definition_version",
        "membership_revision",
        "membership_content_hash",
        "policy_version",
        "source_cut_id",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("COMPOSITE_PUBLICATION_REQUIRED_TEXT")
        return value

    @model_validator(mode="after")
    def chronological_publication(self) -> "DpmCompositeMembershipPublication":
        if self.decided_at.tzinfo is None or self.published_at.tzinfo is None:
            raise ValueError("COMPOSITE_PUBLICATION_TIMEZONE_REQUIRED")
        return self


class DpmCompositePublicationReceipt(BaseModel):
    product_name: Literal["CompositePublicationReceipt"] = "CompositePublicationReceipt"
    product_version: Literal["v1"] = "v1"
    tenant_id: str
    publication_sequence: int = Field(gt=0)
    membership_content_hash: str
    consumer_id: str
    receipt_evidence_hash: str
    disposition: Literal["RECEIVED", "REJECTED"]
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    received_at: datetime
    correlation_id: str

    @field_validator(
        "tenant_id",
        "membership_content_hash",
        "consumer_id",
        "receipt_evidence_hash",
        "correlation_id",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("COMPOSITE_PUBLICATION_RECEIPT_REQUIRED_TEXT")
        return value

    @model_validator(mode="after")
    def valid_disposition(self) -> "DpmCompositePublicationReceipt":
        if self.received_at.tzinfo is None:
            raise ValueError("COMPOSITE_RECEIPT_TIMEZONE_REQUIRED")
        if self.disposition == "REJECTED" and self.reason_code is None:
            raise ValueError("COMPOSITE_RECEIPT_REJECTION_REASON_REQUIRED")
        if self.disposition == "RECEIVED" and self.reason_code is not None:
            raise ValueError("COMPOSITE_RECEIPT_SUCCESS_REASON_FORBIDDEN")
        return self


class DpmCompositePublicationPage(BaseModel):
    items: list[DpmCompositeMembershipPublication]
    high_watermark: int = Field(ge=0)
    next_sequence: int = Field(ge=0)
    has_more: bool


class DpmCompositePublicationReconciliation(BaseModel):
    publication: DpmCompositeMembershipPublication
    receipts: list[DpmCompositePublicationReceipt]
    consumer_posture: Literal["UNACKNOWLEDGED", "RECEIVED", "REJECTED"]


def publication_from_revision(
    *,
    revision: DpmCompositeMembershipRevision,
    sequence: int,
    published_at: datetime,
) -> DpmCompositeMembershipPublication:
    return DpmCompositeMembershipPublication(
        sequence=sequence,
        tenant_id=revision.tenant_id,
        composite_id=revision.composite_id,
        definition_version=revision.definition_version,
        membership_revision=revision.membership_revision,
        membership_content_hash=revision.content_hash,
        policy_version=revision.policy_version,
        source_cut_id=revision.source_cut_id,
        decision_count=len(revision.decisions),
        supersedes_membership_revision=revision.supersedes_membership_revision,
        affected_from=revision.affected_from,
        affected_to=revision.affected_to,
        decided_at=revision.decided_at,
        published_at=published_at,
    )


__all__ = [
    "DpmCompositeMembershipPublication",
    "DpmCompositePublicationReceipt",
    "DpmCompositePublicationPage",
    "DpmCompositePublicationReconciliation",
    "publication_from_revision",
]
