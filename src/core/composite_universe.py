"""Immutable completeness evidence for a pinned composite membership revision.

The attestation proves coverage only for its declared tenant, composite, business-date
range, policy version, and source cut.  It never treats a repository page count or a
current mandate cohort as the authoritative composite universe.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.core.common.canonical import hash_canonical_payload, strip_keys

CompositeUniversePosture = Literal["COMPLETE", "INCOMPLETE", "UNAVAILABLE"]


def _required(value: str, *, code: str) -> str:
    if not value.strip():
        raise ValueError(code)
    return value


def _business_date(value: str, *, code: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(code) from exc


class DpmCompositeUniverseSourceProduct(BaseModel):
    """One versioned input used to establish the declared universe."""

    model_config = ConfigDict(extra="forbid")

    owner_service: str
    product_name: str
    contract_version: str
    authority_scope: Literal["AUTHORITATIVE_UNIVERSE", "POLICY_INPUT", "REFERENCE_INPUT"]
    source_cut_id: str
    source_watermark: str
    content_hash: str

    @field_validator(
        "owner_service",
        "product_name",
        "contract_version",
        "source_cut_id",
        "source_watermark",
        "content_hash",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        return _required(value, code="COMPOSITE_UNIVERSE_SOURCE_PRODUCT_REQUIRED_TEXT")


class DpmCompositeUniverseAttestation(BaseModel):
    """Approved, immutable reconciliation of one membership revision to its universe."""

    model_config = ConfigDict(extra="forbid")

    product_name: Literal["CompositeUniverseAttestation"] = "CompositeUniverseAttestation"
    product_version: Literal["v1"] = "v1"
    tenant_id: str
    composite_id: str
    definition_version: str
    membership_revision: str
    membership_content_hash: str
    attestation_version: str
    coverage_from: str
    coverage_to: str
    policy_version: str
    source_cut_id: str
    source_products: list[DpmCompositeUniverseSourceProduct] = Field(min_length=1)
    posture: CompositeUniversePosture
    expected_portfolio_ids: list[str] = Field(default_factory=list)
    expected_portfolio_count: int = Field(ge=0)
    observed_portfolio_count: int = Field(ge=0)
    missing_portfolio_ids: list[str] = Field(default_factory=list)
    unexpected_portfolio_ids: list[str] = Field(default_factory=list)
    coverage_gap_portfolio_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    attested_at: datetime
    attested_by: str
    correlation_id: str
    content_hash: str = ""

    @field_validator(
        "tenant_id",
        "composite_id",
        "definition_version",
        "membership_revision",
        "membership_content_hash",
        "attestation_version",
        "policy_version",
        "source_cut_id",
        "attested_by",
        "correlation_id",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        return _required(value, code="COMPOSITE_UNIVERSE_ATTESTATION_REQUIRED_TEXT")

    @field_validator(
        "expected_portfolio_ids",
        "missing_portfolio_ids",
        "unexpected_portfolio_ids",
        "coverage_gap_portfolio_ids",
    )
    @classmethod
    def canonical_portfolio_ids(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("COMPOSITE_UNIVERSE_PORTFOLIO_ID_REQUIRED")
        if len(set(values)) != len(values):
            raise ValueError("COMPOSITE_UNIVERSE_PORTFOLIO_ID_DUPLICATE")
        return sorted(values)

    @model_validator(mode="after")
    def validate_attestation(self) -> "DpmCompositeUniverseAttestation":
        self.source_products = _canonical_source_products(self.source_products)
        _validate_authoritative_source(self)
        _validate_coverage(self)
        _validate_posture(self)
        expected_hash = composite_universe_attestation_hash(self)
        if self.content_hash and self.content_hash != expected_hash:
            raise ValueError("COMPOSITE_UNIVERSE_ATTESTATION_HASH_MISMATCH")
        self.content_hash = expected_hash
        return self


def _canonical_source_products(
    products: list[DpmCompositeUniverseSourceProduct],
) -> list[DpmCompositeUniverseSourceProduct]:
    def key(item: DpmCompositeUniverseSourceProduct) -> tuple[str, str, str, str]:
        return (
            item.owner_service,
            item.product_name,
            item.contract_version,
            item.source_cut_id,
        )

    keys = [key(item) for item in products]
    if len(set(keys)) != len(keys):
        raise ValueError("COMPOSITE_UNIVERSE_SOURCE_PRODUCT_DUPLICATE")
    return sorted(products, key=key)


def _validate_authoritative_source(attestation: DpmCompositeUniverseAttestation) -> None:
    authoritative = [
        item
        for item in attestation.source_products
        if item.authority_scope == "AUTHORITATIVE_UNIVERSE"
    ]
    if len(authoritative) != 1:
        raise ValueError("COMPOSITE_UNIVERSE_AUTHORITATIVE_SOURCE_REQUIRED")
    if authoritative[0].source_cut_id != attestation.source_cut_id:
        raise ValueError("COMPOSITE_UNIVERSE_AUTHORITATIVE_SOURCE_CUT_MISMATCH")


def _validate_coverage(attestation: DpmCompositeUniverseAttestation) -> None:
    if _business_date(
        attestation.coverage_to, code="COMPOSITE_UNIVERSE_COVERAGE_TO_INVALID"
    ) < _business_date(attestation.coverage_from, code="COMPOSITE_UNIVERSE_COVERAGE_FROM_INVALID"):
        raise ValueError("COMPOSITE_UNIVERSE_COVERAGE_WINDOW_INVALID")
    if attestation.attested_at.tzinfo is None:
        raise ValueError("COMPOSITE_UNIVERSE_ATTESTED_AT_TIMEZONE_REQUIRED")
    if attestation.expected_portfolio_count != len(attestation.expected_portfolio_ids):
        raise ValueError("COMPOSITE_UNIVERSE_EXPECTED_COUNT_MISMATCH")


def _validate_posture(attestation: DpmCompositeUniverseAttestation) -> None:
    discrepancies = any(
        (
            attestation.missing_portfolio_ids,
            attestation.unexpected_portfolio_ids,
            attestation.coverage_gap_portfolio_ids,
        )
    )
    if attestation.posture == "COMPLETE":
        _validate_complete(attestation, discrepancies=discrepancies)
        return
    if attestation.posture == "INCOMPLETE":
        _validate_incomplete(attestation, discrepancies=discrepancies)
        return
    _validate_unavailable(attestation, discrepancies=discrepancies)


def _validate_complete(
    attestation: DpmCompositeUniverseAttestation, *, discrepancies: bool
) -> None:
    if not attestation.expected_portfolio_ids:
        raise ValueError("COMPOSITE_UNIVERSE_COMPLETE_SET_REQUIRED")
    if discrepancies or attestation.reason_code is not None:
        raise ValueError("COMPOSITE_UNIVERSE_COMPLETE_CONTRADICTED")


def _validate_incomplete(
    attestation: DpmCompositeUniverseAttestation, *, discrepancies: bool
) -> None:
    if not attestation.expected_portfolio_ids:
        raise ValueError("COMPOSITE_UNIVERSE_INCOMPLETE_EVIDENCE_REQUIRED")
    if not discrepancies or attestation.reason_code is None:
        raise ValueError("COMPOSITE_UNIVERSE_INCOMPLETE_EVIDENCE_REQUIRED")


def _validate_unavailable(
    attestation: DpmCompositeUniverseAttestation, *, discrepancies: bool
) -> None:
    if attestation.expected_portfolio_ids or discrepancies:
        raise ValueError("COMPOSITE_UNIVERSE_UNAVAILABLE_EVIDENCE_INVALID")
    if attestation.reason_code is None:
        raise ValueError("COMPOSITE_UNIVERSE_UNAVAILABLE_EVIDENCE_INVALID")


def composite_universe_attestation_hash(attestation: DpmCompositeUniverseAttestation) -> str:
    return hash_canonical_payload(
        strip_keys(attestation.model_dump(mode="json"), exclude={"content_hash"})
    )


__all__ = [
    "CompositeUniversePosture",
    "DpmCompositeUniverseAttestation",
    "DpmCompositeUniverseSourceProduct",
    "composite_universe_attestation_hash",
]
