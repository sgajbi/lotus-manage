"""Strict, bounded economic-authority payloads; no trust is inferred from these DTOs."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_policy import require_authority_coverage

Identity = Annotated[
    str, StringConstraints(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
]
Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
BusinessDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
SourceKind = Literal["LOTUS_CORE", "LOTUS_PERFORMANCE", "EXTERNAL_PROVIDER"]


class StrictAuthorityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceBinding(StrictAuthorityModel):
    product_name: Identity
    product_version: Literal["v1"]
    revision: Identity
    digest: Digest


class ProviderRegistrationBinding(StrictAuthorityModel):
    provider_id: Identity
    source_kind: SourceKind
    registry_revision: Identity
    registry_digest: Digest
    trust_registration_ref: Identity


class CompositeMemberIdentity(StrictAuthorityModel):
    member_id: Identity
    identity_kind: Literal["CORE_PORTFOLIO", "EXTERNAL_MEMBER"]
    namespace: Identity
    provider_id: Identity
    source_member_id: Identity


class CompositeFactSelection(StrictAuthorityModel):
    selection_id: Identity
    fact: Literal["BEGINNING_ASSETS", "ENDING_ASSETS", "MEMBER_RETURN", "BENCHMARK_RETURN"]
    member_ids: list[Identity] = Field(min_length=1, max_length=1000)
    effective_from: BusinessDate
    effective_to: BusinessDate
    provider_id: Identity
    economic_authority: Identity
    publisher_service: Identity
    source_product: Identity
    source_contract_version: Identity
    source_revision: Identity
    source_watermark: Identity
    source_cut_id: Identity
    source_digest: Digest
    method_profile_binding: EvidenceBinding | None


class CompositeEconomicAuthorityPayload(StrictAuthorityModel):
    product_name: Literal["CompositeSourceAuthority"]
    product_version: Literal["v2"]
    profile_id: Identity
    profile_revision: Identity
    tenant_id: Identity
    composite_id: Identity
    effective_from: BusinessDate
    effective_to: BusinessDate
    mode: Literal["INTERNAL", "EXTERNAL", "HYBRID"]
    definition_owner: Literal["lotus-manage"]
    membership_owner: Literal["lotus-manage"]
    publisher: Literal["lotus-manage"]
    materialization_owner: Literal["lotus-performance"]
    calculation_owner: Literal["lotus-performance"]
    member_identities: list[CompositeMemberIdentity] = Field(min_length=1, max_length=1000)
    providers: list[ProviderRegistrationBinding] = Field(min_length=1, max_length=16)
    selections: list[CompositeFactSelection] = Field(min_length=2, max_length=256)
    eligibility_evaluation_binding: EvidenceBinding
    return_method_binding: EvidenceBinding

    @model_validator(mode="after")
    def require_unambiguous_authority(self) -> CompositeEconomicAuthorityPayload:
        date.fromisoformat(self.effective_from)
        date.fromisoformat(self.effective_to)
        require_authority_coverage(self)
        return self


class CompositeSourceAuthorityV2(StrictAuthorityModel):
    payload: CompositeEconomicAuthorityPayload
    profile_digest: Digest

    @model_validator(mode="after")
    def require_profile_digest(self) -> CompositeSourceAuthorityV2:
        if hash_canonical_payload(self.payload.model_dump(mode="json")) != self.profile_digest:
            raise ValueError("COMPOSITE_PROFILE_DIGEST_MISMATCH")
        return self
