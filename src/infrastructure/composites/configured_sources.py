"""Configured HTTP adapters for existing source and independent verification ports."""

import os
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import TypeAdapter

from src.core.composite_eligibility.staged_ports import CandidateUniverseRequest
from src.core.composite_eligibility.staged_subject import CandidateUniverse
from src.core.composite_eligibility.verification import VerificationReceipt, VerificationRequest
from src.core.composite_eligibility.source import (
    MonthlyEligibilitySourceRequest,
    MonthlyEligibilitySourceResolution,
    admitted_source_snapshot,
)
from src.core.composite_eligibility.source_assembly import (
    MonthlySourceAssembly,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
)
from src.infrastructure.authority_http import post_json_with_retries, AuthorityHttpError
from src.infrastructure.composites.source_configuration import (
    CompositeSourceConfiguration,
    SourceOperation,
)
from src.infrastructure.composites.source_credentials import verified_artifact


@dataclass(frozen=True)
class CompositeSourceTransport:
    configuration: CompositeSourceConfiguration
    client: httpx.Client

    def resolve(
        self, *, tenant_id: str, operation: SourceOperation, request: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Resolve only a deployment-pinned endpoint and a signed bound response."""
        binding = self.configuration.binding(tenant_id, operation)
        if binding is None:
            return None
        credential = os.getenv(binding.credential_env)
        if not credential or not credential.strip():
            return None
        try:
            body = post_json_with_retries(
                client=self.client,
                url=binding.endpoint,
                payload=request,
                headers={"Authorization": f"Bearer {credential}", "Accept-Encoding": "identity"},
                attempts=self.configuration.attempts,
                unavailable_error="COMPOSITE_SOURCE_TRANSPORT_UNAVAILABLE",
                rejected_error="COMPOSITE_SOURCE_TRANSPORT_REJECTED",
                invalid_response_error="COMPOSITE_SOURCE_RESPONSE_INVALID",
                source_service=binding.owner_service,
                maximum_response_bytes=self.configuration.maximum_response_bytes,
            )
        except AuthorityHttpError as exc:
            raise ValueError(exc.code) from exc
        if set(body) != {"owner_service", "payload", "credential"} or (
            body["owner_service"] != binding.owner_service
            or not isinstance(body["payload"], dict)
            or not isinstance(body["credential"], str)
        ):
            raise ValueError("COMPOSITE_SOURCE_RESPONSE_INVALID")
        verified_artifact(
            body["credential"], binding=binding, request=request, payload=body["payload"]
        )
        return body["payload"]


@dataclass(frozen=True)
class ConfiguredCandidateUniverseSource:
    transport: CompositeSourceTransport

    def resolve(self, request: CandidateUniverseRequest) -> CandidateUniverse | None:
        """Admit the strict existing universe contract with exact requested scope."""
        payload = self.transport.resolve(
            tenant_id=request.tenant_id,
            operation="candidates",
            request=TypeAdapter(CandidateUniverseRequest).dump_python(request, mode="json"),
        )
        if payload is None:
            return None
        result = CandidateUniverse.model_validate(payload)
        if (
            result.tenant_id,
            result.composite_id,
            result.definition_version,
            result.month,
            result.reporting_currency,
            result.registry_binding,
        ) != (
            request.tenant_id,
            request.composite_id,
            request.definition_version,
            request.month,
            request.reporting_currency,
            request.registry_binding,
        ):
            raise ValueError("COMPOSITE_SUBJECT_UNIVERSE_SCOPE_MISMATCH")
        return result


@dataclass(frozen=True)
class ConfiguredCompositeEvidenceVerifier:
    transport: CompositeSourceTransport

    def verify(self, request: VerificationRequest) -> VerificationReceipt | None:
        """A signed response never promotes synthetic evidence to qualified receipt."""
        configured = self.transport.configuration.binding(request.tenant_id, "verification")
        if configured is None or request.purpose not in configured.verification_purposes:
            return None
        payload = self.transport.resolve(
            tenant_id=request.tenant_id,
            operation="verification",
            request=request.model_dump(mode="json"),
        )
        if payload is None:
            return None
        result = VerificationReceipt.model_validate(payload)
        binding = self.transport.configuration.binding(request.tenant_id, "verification")
        if binding is None or (
            result.request,
            result.verifier_id,
            result.issuer_id,
            result.posture,
        ) != (
            request,
            binding.principal_id,
            binding.receipt_issuer_id,
            binding.evidence_posture,
        ):
            raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH")
        return result


@dataclass(frozen=True)
class ConfiguredMonthlyEligibilitySource:
    transport: CompositeSourceTransport
    verifier: ConfiguredCompositeEvidenceVerifier

    def resolve(
        self, request: MonthlyEligibilitySourceRequest
    ) -> MonthlyEligibilitySourceResolution:
        """Require a complete source manifest and independent full-assembly verification."""
        unavailable = MonthlyEligibilitySourceResolution(observations=None)
        binding = self.transport.configuration.binding(request.scope.tenant_id, "observations")
        if binding is None:
            return unavailable
        if binding.owner_service != request.owner_service:
            raise ValueError("COMPOSITE_ELIGIBILITY_SOURCE_OWNER_MISMATCH")
        payload = self.transport.resolve(
            tenant_id=request.scope.tenant_id,
            operation="observations",
            request=TypeAdapter(MonthlyEligibilitySourceRequest).dump_python(request, mode="json"),
        )
        if payload is None:
            return unavailable
        assembly = MonthlySourceAssembly.model_validate(payload)
        if assembly.compatibility_posture != "SYNTHETIC_UNQUALIFIED" or (
            assembly.observations.evidence_class != "SYNTHETIC_UNQUALIFIED"
        ):
            return unavailable
        result = MonthlyEligibilitySourceResolution(assembly.observations, binding.owner_service)
        admitted_source_snapshot(request, result)
        verification = self.verifier.verify(assembly_verification_request(assembly))
        if verification is None:
            return unavailable
        evidence = VerifiedMonthlySourceAssembly(assembly=assembly, verification=verification)
        return MonthlyEligibilitySourceResolution(
            assembly.observations, binding.owner_service, evidence
        )
