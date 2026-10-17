"""Explicit source-cut assembly evidence; matching business dates is not compatibility."""

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import EvidenceBinding, Identity, StrictAuthorityModel
from src.core.composite_eligibility.native_source_custody import (
    MonthlyNativeCustody,
    native_role_set_digest,
    require_native_observation_scope,
)
from src.core.composite_eligibility.native_source_verification import MonthlySourceAdmissionProof
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest

InputKind = Literal["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"]


class MonthlyInputBinding(StrictAuthorityModel):
    kind: InputKind
    owner_service: Identity
    source_cut_id: Identity
    evidence: EvidenceBinding


class _MonthlySourceAssembly[AssemblyVersion: str](StrictAuthorityModel):
    product_name: Literal["CompositeMonthlyEligibilityAssembly"]
    product_version: AssemblyVersion
    observations: MonthlyEligibilityObservations
    inputs: list[MonthlyInputBinding] = Field(min_length=5, max_length=5)
    compatibility_binding: EvidenceBinding
    compatibility_posture: Literal["SYNTHETIC_UNQUALIFIED", "SOURCE_UNVERIFIED", "UNAVAILABLE"]

    @model_validator(mode="after")
    def require_all_input_authorities(self) -> "_MonthlySourceAssembly[AssemblyVersion]":
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


class MonthlySourceAssembly(_MonthlySourceAssembly[Literal["v1"]]):
    # Keep the original v1 schema as well as its wire field order.
    pass


class NativeMonthlySourceAssembly(_MonthlySourceAssembly[Literal["v2"]]):
    native_custody: MonthlyNativeCustody

    @model_validator(mode="after")
    def require_native_role_sets(self) -> "NativeMonthlySourceAssembly":
        custody = MonthlyNativeCustody.model_validate(self.native_custody.model_dump(mode="json"))
        require_native_observation_scope(custody, self.observations)
        for binding in self.inputs:
            if (
                binding.owner_service != "lotus-manage"
                or binding.source_cut_id != self.observations.source_cut_id
                or binding.evidence.product_name != "CompositeMonthlyRoleSet"
                or binding.evidence.revision != self.observations.source_revision
                or binding.evidence.digest != native_role_set_digest(custody, binding.kind)
            ):
                raise ValueError("COMPOSITE_NATIVE_ROLE_SET_MISMATCH")
        return self


MonthlyAssemblyVariant = Annotated[
    MonthlySourceAssembly | NativeMonthlySourceAssembly, Field(discriminator="product_version")
]


def assembly_verification_request(assembly: MonthlyAssemblyVariant) -> VerificationRequest:
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

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "assembly": {
                                "properties": {"product_version": {"const": "v1"}},
                                "required": ["product_version"],
                            }
                        },
                        "required": ["assembly"],
                    },
                    "then": {"not": {"required": ["native_proof"]}},
                    "else": {
                        "required": ["native_proof"],
                        "properties": {"native_proof": {"not": {"type": "null"}}},
                    },
                }
            ]
        },
    )
    assembly: MonthlyAssemblyVariant
    verification: VerificationReceipt
    native_proof: MonthlySourceAdmissionProof | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="before")
    @classmethod
    def require_versioned_proof_presence(cls, value: Any) -> Any:
        if isinstance(value, dict):
            assembly = value.get("assembly")
            version = (
                assembly.get("product_version")
                if isinstance(assembly, dict)
                else getattr(assembly, "product_version", None)
            )
            if version == "v1" and "native_proof" in value:
                raise ValueError("COMPOSITE_NATIVE_PROOF_FORBIDDEN_V1")
            if version == "v2" and value.get("native_proof") is None:
                raise ValueError("COMPOSITE_NATIVE_PROOF_REQUIRED_V2")
        return value

    @model_validator(mode="after")
    def require_complete_verification(self) -> "VerifiedMonthlySourceAssembly":
        assembly_type = (
            NativeMonthlySourceAssembly
            if self.assembly.product_version == "v2"
            else MonthlySourceAssembly
        )
        self.assembly = assembly_type.model_validate(self.assembly.model_dump(mode="json"))
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
        if isinstance(self.assembly, NativeMonthlySourceAssembly):
            self._require_native_proof(self.assembly)
        elif self.native_proof is not None:
            raise ValueError("COMPOSITE_NATIVE_PROOF_FORBIDDEN_V1")
        return self

    def _require_native_proof(self, assembly: NativeMonthlySourceAssembly) -> None:
        if self.native_proof is None:
            raise ValueError("COMPOSITE_NATIVE_PROOF_REQUIRED_V2")
        proof = MonthlySourceAdmissionProof.model_validate(
            self.native_proof.model_dump(mode="json")
        )
        if (
            proof.result.receipt != self.verification
            or proof.result.native_custody_digest != assembly.native_custody.content_hash
            or self.verification.artifact_revision != assembly.observations.source_revision
        ):
            raise ValueError("COMPOSITE_NATIVE_PROOF_ASSEMBLY_MISMATCH")


def retained_source_assembly(
    evidence: VerifiedMonthlySourceAssembly | None,
    observations: MonthlyEligibilityObservations,
) -> VerifiedMonthlySourceAssembly | None:
    """Revalidate complete custody without certifying legacy history lacking a manifest."""
    if evidence is None:
        return None
    verified = VerifiedMonthlySourceAssembly.model_validate(evidence.model_dump(mode="json"))
    if verified.assembly.observations != observations:
        raise ValueError("COMPOSITE_SOURCE_ASSEMBLY_OBSERVATIONS_MISMATCH")
    return verified
