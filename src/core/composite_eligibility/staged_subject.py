"""Immutable pre-definition subject and source-owned candidate population."""

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import (
    BusinessDate,
    CompositeMemberIdentity,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.observations import Currency, UtcInstant
from src.core.composite_eligibility.policy import month_window
from src.core.composite_universe import DpmCompositeUniverseSourceProduct


class CandidateUniverse(StrictAuthorityModel):
    product_name: Literal["CompositeEligibilityCandidateUniverse"] = (
        "CompositeEligibilityCandidateUniverse"
    )
    product_version: Literal["v1"] = "v1"
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    month: str
    registry_binding: EvidenceBinding
    reporting_currency: Currency
    members: list[CompositeMemberIdentity] = Field(min_length=1, max_length=1000)
    source_products: list[DpmCompositeUniverseSourceProduct] = Field(min_length=1, max_length=19)
    observation_owner: Identity
    coverage_from: BusinessDate
    coverage_to: BusinessDate
    posture: Literal["COMPLETE", "INCOMPLETE", "UNAVAILABLE"]
    population_verification: Literal["UNVERIFIED"] = "UNVERIFIED"
    source_cut_id: Identity
    generated_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_bound_population(self) -> "CandidateUniverse":
        first, last = month_window(self.month)
        try:
            date.fromisoformat(self.coverage_from)
            date.fromisoformat(self.coverage_to)
            datetime.fromisoformat(self.generated_at)
        except ValueError as exc:
            raise ValueError("COMPOSITE_SUBJECT_UNIVERSE_DATE_INVALID") from exc
        if not self.coverage_from <= first <= last <= self.coverage_to:
            raise ValueError("COMPOSITE_SUBJECT_UNIVERSE_WINDOW_MISMATCH")
        ids = [member.member_id for member in self.members]
        if ids != sorted(set(ids)):
            raise ValueError("COMPOSITE_SUBJECT_MEMBERS_NONCANONICAL")
        _require_registry_source(self.source_products, self.registry_binding, self.source_cut_id)
        bind_content(self)
        return self


def _require_registry_source(
    products: list[DpmCompositeUniverseSourceProduct], binding: EvidenceBinding, cut: str
) -> None:
    authorities = [
        product for product in products if product.authority_scope == "AUTHORITATIVE_UNIVERSE"
    ]
    if len(authorities) != 1 or any(
        product.authority_scope == "POLICY_INPUT" for product in products
    ):
        raise ValueError("COMPOSITE_SUBJECT_SOURCE_REFERENCE_INVALID")
    authority = authorities[0]
    if (
        authority.product_name,
        authority.contract_version,
        authority.source_watermark,
        authority.content_hash,
        authority.source_cut_id,
    ) != (binding.product_name, binding.product_version, binding.revision, binding.digest, cut):
        raise ValueError("COMPOSITE_SUBJECT_REGISTRY_BINDING_MISMATCH")


class EligibilitySubject(StrictAuthorityModel):
    product_name: Literal["CompositeEligibilitySubject"] = "CompositeEligibilitySubject"
    product_version: Literal["v1"] = "v1"
    tenant_id: Identity
    composite_id: Identity
    definition_version: Identity
    subject_revision: Identity
    display_name: str = Field(min_length=1, max_length=256)
    strategy_code: Identity
    reporting_currency: Currency
    inception_date: BusinessDate
    termination_date: BusinessDate | None
    eligibility_policy_version: Identity
    month: str
    universe: CandidateUniverse
    created_by: Identity
    created_at: UtcInstant
    correlation_id: Identity
    content_hash: str = ""

    @model_validator(mode="after")
    def require_exact_subject(self) -> "EligibilitySubject":
        self.universe = CandidateUniverse.model_validate(self.universe.model_dump(mode="json"))
        if (
            self.tenant_id,
            self.composite_id,
            self.definition_version,
            self.month,
            self.reporting_currency,
        ) != (
            self.universe.tenant_id,
            self.universe.composite_id,
            self.universe.definition_version,
            self.universe.month,
            self.universe.reporting_currency,
        ):
            raise ValueError("COMPOSITE_SUBJECT_UNIVERSE_SCOPE_MISMATCH")
        first, last = month_window(self.month)
        date.fromisoformat(self.inception_date)
        datetime.fromisoformat(self.created_at)
        if self.universe.generated_at > self.created_at:
            raise ValueError("COMPOSITE_SUBJECT_FUTURE_UNIVERSE_GENERATION")
        if self.termination_date is not None:
            date.fromisoformat(self.termination_date)
        if self.inception_date > first or (
            self.termination_date is not None and self.termination_date < last
        ):
            raise ValueError("COMPOSITE_SUBJECT_DEFINITION_WINDOW_MISMATCH")
        bind_content(self)
        return self


def subject_key(subject: EligibilitySubject) -> tuple[str, str, str, str]:
    return (
        subject.tenant_id,
        subject.composite_id,
        subject.definition_version,
        subject.subject_revision,
    )


def bind_content(model: StrictAuthorityModel) -> None:
    expected = hash_canonical_payload(model.model_dump(mode="json", exclude={"content_hash"}))
    supplied = getattr(model, "content_hash")
    if supplied and supplied != expected:
        raise ValueError("COMPOSITE_SUBJECT_CONTENT_MISMATCH")
    setattr(model, "content_hash", expected)
