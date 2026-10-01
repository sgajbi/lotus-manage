"""Immutable approved-instruction package contracts.

Manage releases a package for an execution adapter to retrieve.  It does not
submit an order, receive a fill, settle cash, or book a transaction.  Those
facts remain with the bank execution and core-booking owners.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.core.common.canonical import hash_canonical_payload, strip_keys


InstructionOrderType = Literal["MARKET", "LIMIT"]
InstructionTimeInForce = Literal["DAY", "GTC"]
FundingDisposition = Literal["CERTIFIED", "DELEGATED_TO_EXECUTION_OWNER"]


class DpmInstructionPackageSourceRevision(BaseModel):
    """One immutable source revision that qualified a release."""

    source_type: str = Field(description="Bounded source product or evidence type.")
    source_id: str = Field(description="Source-owned revision or artifact identifier.")
    source_version: str = Field(description="Version supplied by the source owner.")
    content_hash: str = Field(description="Canonical source content hash.")
    material: bool = Field(
        default=True,
        description="Whether a change to this source invalidates the reviewed material.",
    )


class DpmInstructionApprovalEvidence(BaseModel):
    """Evidence from the approval system, not an execution acknowledgement."""

    approval_id: str = Field(description="Stable approval evidence identifier.")
    approved_by: str = Field(description="Approver identity recorded by the approval process.")
    approved_at: datetime = Field(description="UTC approval timestamp.")
    approved_material_hash: str = Field(
        description="Canonical hash of the exact mapped instructions and release qualifications."
    )
    approval_policy_version: str = Field(description="Applied approval-policy revision.")


class DpmInstructionFundingEvidence(BaseModel):
    """Pinned funding posture; historical observed cost is never a commission quote."""

    disposition: FundingDisposition
    policy_id: str = Field(description="Funding or fee policy identifier.")
    policy_version: str = Field(description="Funding or fee policy version.")
    evidence_hash: str = Field(description="Canonical funding evidence hash.")
    settlement_awareness_enabled: bool = Field(
        description="Whether the reviewed source used settlement-aware funding controls."
    )
    fee_reserve_currency: str | None = Field(
        default=None, description="Currency of an explicit execution-cost reserve when applicable."
    )
    fee_reserve_amount: Decimal | None = Field(
        default=None, ge=0, description="Explicit reserve required by the pinned policy."
    )
    delegated_source_product: str | None = Field(
        default=None,
        description="Required downstream source product when final funding is delegated.",
    )

    @model_validator(mode="after")
    def _validate_disposition(self) -> "DpmInstructionFundingEvidence":
        has_reserve = self.fee_reserve_currency is not None or self.fee_reserve_amount is not None
        if has_reserve and (not self.fee_reserve_currency or self.fee_reserve_amount is None):
            raise ValueError("INSTRUCTION_PACKAGE_FEE_RESERVE_INCOMPLETE")
        if self.disposition == "DELEGATED_TO_EXECUTION_OWNER" and not self.delegated_source_product:
            raise ValueError("INSTRUCTION_PACKAGE_FUNDING_DELEGATION_EVIDENCE_REQUIRED")
        if self.disposition == "CERTIFIED" and self.delegated_source_product is not None:
            raise ValueError("INSTRUCTION_PACKAGE_FUNDING_DELEGATION_NOT_ALLOWED")
        return self


class DpmInstructionMappingEvidence(BaseModel):
    """Approved account/instrument mapping and explicit adapter constraints."""

    original_intent_id: str = Field(description="Run-local source intent identifier.")
    canonical_instrument_key: str = Field(description="Execution-adapter canonical instrument key.")
    account_key: str = Field(description="Execution-adapter account key in the approved scope.")
    mapping_revision: str = Field(description="Pinned account/instrument mapping revision.")
    mapping_content_hash: str = Field(description="Canonical mapping evidence hash.")
    order_type: InstructionOrderType = Field(description="Explicit supported order type.")
    time_in_force: InstructionTimeInForce = Field(description="Explicit supported time in force.")
    settlement_date: str = Field(description="Approved ISO-8601 business settlement date.")
    limit_price: Decimal | None = Field(
        default=None, gt=0, description="Required only for an approved LIMIT instruction."
    )

    @model_validator(mode="after")
    def _validate_order_terms(self) -> "DpmInstructionMappingEvidence":
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("INSTRUCTION_PACKAGE_LIMIT_PRICE_REQUIRED")
        if self.order_type == "MARKET" and self.limit_price is not None:
            raise ValueError("INSTRUCTION_PACKAGE_LIMIT_PRICE_NOT_ALLOWED")
        return self


class DpmApprovedInstruction(BaseModel):
    """Exact economic instruction visible to the execution adapter."""

    instruction_id: str = Field(description="Stable identity within an immutable package version.")
    original_intent_id: str = Field(description="Run-local intent identity retained for lineage.")
    canonical_instrument_key: str = Field(description="Execution-adapter instrument key.")
    account_key: str = Field(description="Execution-adapter account key.")
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(
        gt=0, description="Exact security quantity; no rounded reconstruction."
    )
    unit: Literal["UNITS"] = "UNITS"
    currency: str = Field(description="Trade notional currency from the approved run.")
    order_type: InstructionOrderType
    time_in_force: InstructionTimeInForce
    settlement_date: str
    limit_price: Decimal | None = None
    dependencies: list[str] = Field(
        default_factory=list,
        description="Instruction identities that must be respected by the downstream owner.",
    )
    mapping_revision: str
    mapping_content_hash: str


class DpmApprovedInstructionPackage(BaseModel):
    """A durable immutable package that is intentionally not an external order."""

    package_id: str
    package_version: str
    tenant_id: str
    portfolio_id: str
    account_key: str
    wave_id: str
    wave_item_id: str
    rebalance_run_id: str
    proof_pack_id: str
    mandate_id: str
    mandate_version: str
    model_portfolio_id: str
    model_portfolio_version: str | None
    policy_revision: str
    source_revisions: list[DpmInstructionPackageSourceRevision]
    approved_intent_hash: str
    approval_evidence: DpmInstructionApprovalEvidence
    funding_evidence: DpmInstructionFundingEvidence
    instructions: list[DpmApprovedInstruction] = Field(min_length=1)
    supersedes_package_id: str | None = None
    supersedes_package_version: str | None = None
    release_eligibility: Literal["ELIGIBLE"] = "ELIGIBLE"
    external_execution_claimed: Literal[False] = False
    external_execution_boundary: Literal["MANAGE_PACKAGE_IS_NOT_ORDER_OR_BOOKING"] = (
        "MANAGE_PACKAGE_IS_NOT_ORDER_OR_BOOKING"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    released_by: str
    correlation_id: str
    content_hash: str = ""

    @model_validator(mode="after")
    def _validate_supersession(self) -> "DpmApprovedInstructionPackage":
        left = self.supersedes_package_id is None
        right = self.supersedes_package_version is None
        if left != right:
            raise ValueError("INSTRUCTION_PACKAGE_SUPERSESSION_INCOMPLETE")
        if len({instruction.instruction_id for instruction in self.instructions}) != len(
            self.instructions
        ):
            raise ValueError("INSTRUCTION_PACKAGE_DUPLICATE_INSTRUCTION_ID")
        return self

    @classmethod
    def from_material(cls, **values: Any) -> "DpmApprovedInstructionPackage":
        payload: dict[str, Any] = cls(**values).model_dump(mode="json")
        payload["content_hash"] = hash_canonical_payload(
            strip_keys(payload, exclude={"content_hash"})
        )
        return cls.model_validate(payload)


class DpmInstructionPackageApprovalMaterial(BaseModel):
    """Canonical material returned before a separate approval is bound.

    This deliberately is not a package: it has neither release eligibility nor
    an approval record and cannot be retrieved by an execution adapter.
    """

    package_id: str
    package_version: str
    tenant_id: str
    portfolio_id: str
    account_key: str
    wave_id: str
    wave_item_id: str
    rebalance_run_id: str
    proof_pack_id: str
    mandate_id: str
    mandate_version: str
    model_portfolio_id: str
    model_portfolio_version: str | None
    policy_revision: str
    source_revisions: list[DpmInstructionPackageSourceRevision]
    approved_intent_hash: str
    instructions: list[DpmApprovedInstruction]
    funding_evidence: DpmInstructionFundingEvidence
    approval_status: Literal["PENDING_EXTERNAL_APPROVAL"] = "PENDING_EXTERNAL_APPROVAL"
    external_execution_claimed: Literal[False] = False
    external_execution_boundary: Literal["MANAGE_PACKAGE_IS_NOT_ORDER_OR_BOOKING"] = (
        "MANAGE_PACKAGE_IS_NOT_ORDER_OR_BOOKING"
    )


class DpmInstructionPackageReceipt(BaseModel):
    """Durable adapter receipt only; deliberately not a fill, settle, or booking event."""

    receipt_id: str
    tenant_id: str
    package_id: str
    package_version: str
    consumer_id: str
    receipt_evidence_hash: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    external_execution_claimed: Literal[False] = False
    receipt_scope: Literal["RETRIEVAL_ONLY"] = "RETRIEVAL_ONLY"


class DpmInstructionPackagePage(BaseModel):
    items: list[DpmApprovedInstructionPackage]
    count: int
    total_count: int
    limit: int
    snapshot_at: datetime
    next_page_token: str | None
    completeness: Literal["SNAPSHOT_COMPLETE_WHEN_ALL_PAGES_RETRIEVED"] = (
        "SNAPSHOT_COMPLETE_WHEN_ALL_PAGES_RETRIEVED"
    )


__all__ = [
    "DpmApprovedInstruction",
    "DpmApprovedInstructionPackage",
    "DpmInstructionApprovalEvidence",
    "DpmInstructionFundingEvidence",
    "DpmInstructionMappingEvidence",
    "DpmInstructionPackageApprovalMaterial",
    "DpmInstructionPackagePage",
    "DpmInstructionPackageReceipt",
    "DpmInstructionPackageSourceRevision",
]
