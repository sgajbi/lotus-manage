"""Explicit source-cut assembly evidence; matching business dates is not compatibility."""

from typing import Literal

from pydantic import Field, model_validator

from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.verification import VerificationRequest, VerificationReceipt

InputKind = Literal["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"]


class MonthlyInputBinding(StrictAuthorityModel):
    kind: InputKind
    owner_service: Identity
    source_cut_id: Identity
    evidence: EvidenceBinding


class MonthlySourceAssembly(StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityAssembly"]
    product_version: Literal["v1"]
    observations: MonthlyEligibilityObservations
    inputs: list[MonthlyInputBinding] = Field(min_length=5, max_length=5)
    compatibility_binding: EvidenceBinding
    compatibility_posture: Literal["SYNTHETIC_UNQUALIFIED", "SOURCE_UNVERIFIED", "UNAVAILABLE"]

    @model_validator(mode="after")
    def require_all_input_authorities(self) -> "MonthlySourceAssembly":
        if {item.kind for item in self.inputs} != {
            "PRIOR_ASSETS",
            "MONTH_END_ASSETS",
            "CASH",
            "READINESS",
            "FLOWS",
        }:
            raise ValueError("COMPOSITE_SOURCE_ASSEMBLY_INPUTS_INCOMPLETE")
        if self.compatibility_binding.product_name != "CompositeSourceCutCompatibility":
            raise ValueError("COMPOSITE_SOURCE_COMPATIBILITY_BINDING_INVALID")
        if [item.kind for item in self.inputs] != sorted(item.kind for item in self.inputs):
            raise ValueError("COMPOSITE_SOURCE_ASSEMBLY_INPUTS_NONCANONICAL")
        material = {
            "observations": self.observations.model_dump(mode="json"),
            "inputs": [item.model_dump(mode="json") for item in self.inputs],
        }
        if self.compatibility_binding.digest != hash_canonical_payload(material):
            raise ValueError("COMPOSITE_SOURCE_COMPATIBILITY_CONTENT_MISMATCH")
        return self


def assembly_verification_request(assembly: MonthlySourceAssembly) -> VerificationRequest:
    """Bind every constituent and normalized fact to one exact whole-month verification."""
    snapshot = assembly.observations
    first, last = month_window(snapshot.month)
    return VerificationRequest(
        purpose="COMPOSITE_MONTHLY_SOURCE_CUT",
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
        subject_content_hash=hash_canonical_payload(snapshot.model_dump(mode="json")),
        claims_digest=hash_canonical_payload(assembly.model_dump(mode="json")),
        effective_from=first,
        effective_to=last,
        binding=assembly.compatibility_binding,
        source_product=assembly.product_name,
    )


class VerifiedMonthlySourceAssembly(StrictAuthorityModel):
    """Retained non-certifying manifest and independently admitted verification receipt."""

    assembly: MonthlySourceAssembly
    verification: VerificationReceipt

    @model_validator(mode="after")
    def require_complete_verification(self) -> "VerifiedMonthlySourceAssembly":
        self.assembly = MonthlySourceAssembly.model_validate(self.assembly.model_dump(mode="json"))
        self.verification = VerificationReceipt.model_validate(
            self.verification.model_dump(mode="json")
        )
        if (
            self.assembly.compatibility_posture != "SYNTHETIC_UNQUALIFIED"
            or self.assembly.observations.evidence_class != "SYNTHETIC_UNQUALIFIED"
            or self.verification.posture != "SYNTHETIC_NON_CERTIFYING"
            or self.verification.request != assembly_verification_request(self.assembly)
        ):
            raise ValueError("COMPOSITE_SOURCE_ASSEMBLY_VERIFICATION_MISMATCH")
        return self
