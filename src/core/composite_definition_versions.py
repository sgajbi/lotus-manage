"""Versioned definition decoding and acyclic profile/business/approval wire hashes."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import (
    BusinessDate,
    CompositeSourceAuthorityV2,
    Digest,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_membership import DpmCompositeDefinition


class CompositeAuthorityClaims(StrictAuthorityModel):
    purpose: Literal["COMPOSITE_ECONOMIC_AUTHORITY_PROFILE"]
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    profile_id: Identity
    profile_revision: Identity
    profile_digest: Digest
    definition_payload_digest: Digest
    effective_from: BusinessDate
    effective_to: BusinessDate
    approving_identity: Identity
    approved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
    eligibility_evidence_digest: Digest
    method_evidence_digest: Digest


class CompositeAuthorityApprovalClaims(CompositeAuthorityClaims):
    schema_version: Literal["synthetic-approval-claims.v1"]


class CompositeInstitutionalAuthorityClaims(CompositeAuthorityClaims):
    schema_version: Literal["composite-authority-approval-claims.v1"]


class CompositeSyntheticAuthorityApproval(StrictAuthorityModel):
    """Recognized only as synthetic evidence; never an affirmative bank approval."""

    evidence_kind: Literal["SYNTHETIC_UNSIGNED"]
    claims: CompositeAuthorityApprovalClaims
    official_activation: Literal["UNAVAILABLE"]


class CompositeAuthorityAttestationReference(StrictAuthorityModel):
    contract_version: Literal["composite-authority-attestation.v1"]
    issuer_id: Identity
    attestation_id: Identity
    revision: Identity
    digest: Digest


class CompositeInstitutionalAuthorityReference(StrictAuthorityModel):
    """Schema representation, not verification of the external signed artifact."""

    evidence_kind: Literal["INSTITUTIONAL_ATTESTATION_REFERENCE"]
    claims: CompositeInstitutionalAuthorityClaims
    attestation: CompositeAuthorityAttestationReference
    official_activation: Literal["UNAVAILABLE"]


CompositeAuthorityApproval = Annotated[
    CompositeSyntheticAuthorityApproval | CompositeInstitutionalAuthorityReference,
    Field(discriminator="evidence_kind"),
]


class DpmCompositeDefinitionV2(StrictAuthorityModel):
    product_name: Literal["CompositeDefinition"]
    product_version: Literal["v2"]
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    display_name: str = Field(min_length=1, max_length=256)
    strategy_code: Identity
    reporting_currency: str = Field(pattern=r"^[A-Z]{3}$")
    inception_date: BusinessDate
    termination_date: BusinessDate | None
    calculation_method: Literal["ASSET_WEIGHTED"]
    eligibility_policy_version: Identity
    source_authority: CompositeSourceAuthorityV2
    created_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
    created_by: Identity
    correlation_id: Identity
    definition_payload_digest: Digest
    authority_approval: CompositeAuthorityApproval
    content_hash: Digest

    @model_validator(mode="after")
    def require_bound_immutable_content(self) -> DpmCompositeDefinitionV2:
        p, c = self.source_authority.payload, self.authority_approval.claims
        if (p.tenant_id, p.composite_id) != (self.tenant_id, self.composite_id):
            raise ValueError("COMPOSITE_AUTHORITY_SCOPE_MISMATCH")
        if self.inception_date > p.effective_from or (
            self.termination_date is not None and self.termination_date < p.effective_to
        ):
            raise ValueError("COMPOSITE_AUTHORITY_DEFINITION_WINDOW_MISMATCH")
        # Parse all lexical dates/instants rather than accepting regex-shaped invalid dates.
        date.fromisoformat(self.inception_date)
        if self.termination_date is not None:
            date.fromisoformat(self.termination_date)
        created_at = datetime.fromisoformat(self.created_at)
        approved_at = datetime.fromisoformat(c.approved_at)
        if approved_at < created_at:
            raise ValueError("COMPOSITE_AUTHORITY_APPROVAL_BEFORE_CREATION")
        if c.approving_identity == self.created_by:
            raise ValueError("COMPOSITE_AUTHORITY_SELF_APPROVAL_FORBIDDEN")
        business = self.model_dump(
            mode="json", exclude={"content_hash", "definition_payload_digest", "authority_approval"}
        )
        if hash_canonical_payload(business) != self.definition_payload_digest:
            raise ValueError("COMPOSITE_DEFINITION_PAYLOAD_DIGEST_MISMATCH")
        if (
            c.tenant_id,
            c.composite_id,
            c.definition_version,
            c.profile_id,
            c.profile_revision,
            c.profile_digest,
            c.definition_payload_digest,
            c.effective_from,
            c.effective_to,
            c.eligibility_evidence_digest,
            c.method_evidence_digest,
        ) != (
            self.tenant_id,
            self.composite_id,
            self.definition_version,
            p.profile_id,
            p.profile_revision,
            self.source_authority.profile_digest,
            self.definition_payload_digest,
            p.effective_from,
            p.effective_to,
            p.eligibility_evaluation_binding.digest,
            p.return_method_binding.digest,
        ):
            raise ValueError("COMPOSITE_AUTHORITY_APPROVAL_BINDING_MISMATCH")
        if (
            hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
            != self.content_hash
        ):
            raise ValueError("COMPOSITE_DEFINITION_WIRE_DIGEST_MISMATCH")
        return self


CompositeDefinition = Annotated[
    DpmCompositeDefinition | DpmCompositeDefinitionV2, Field(discriminator="product_version")
]


def validated_definition_snapshot(definition: CompositeDefinition) -> CompositeDefinition:
    """Revalidate v2 mutable nested data before admission/storage; leave v1 unchanged."""
    if isinstance(definition, DpmCompositeDefinitionV2):
        return DpmCompositeDefinitionV2.model_validate(definition.model_dump(mode="json"))
    return definition


def parse_composite_definition_json(payload: str) -> dict[str, Any]:
    """Reject ambiguous v2 raw input without changing legacy v1 JSON semantics."""
    duplicate_keys = False
    contains_v2 = False

    def inspect_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        nonlocal duplicate_keys, contains_v2
        keys = [key for key, _ in pairs]
        duplicate_keys |= len(keys) != len(set(keys))
        contains_v2 |= any(key == "product_version" and value == "v2" for key, value in pairs)
        return dict(pairs)

    def refuse_nonfinite(value: str) -> None:
        raise ValueError("COMPOSITE_DEFINITION_NONFINITE_JSON_FORBIDDEN")

    try:
        raw = json.loads(payload, object_pairs_hook=inspect_pairs)
        if not isinstance(raw, dict):
            raise ValueError("COMPOSITE_DEFINITION_JSON_OBJECT_REQUIRED")
        if contains_v2:
            if duplicate_keys:
                raise ValueError("COMPOSITE_DEFINITION_DUPLICATE_JSON_KEY")
            raw = json.loads(payload, parse_constant=refuse_nonfinite)
        if not isinstance(raw, dict):
            raise ValueError("COMPOSITE_DEFINITION_JSON_OBJECT_REQUIRED")
        return raw
    except json.JSONDecodeError as exc:
        raise ValueError("COMPOSITE_DEFINITION_RAW_JSON_INVALID") from exc


def decode_composite_definition(payload: str | dict[str, Any]) -> CompositeDefinition:
    raw = parse_composite_definition_json(payload) if isinstance(payload, str) else payload
    version = raw.get("product_version", "v1")
    if version == "v1":
        return DpmCompositeDefinition.model_validate(raw)
    if version == "v2":
        return DpmCompositeDefinitionV2.model_validate(raw)
    raise ValueError("COMPOSITE_DEFINITION_PRODUCT_VERSION_UNSUPPORTED")
