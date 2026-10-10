"""Transport normalized signed proofs; original-format verification stays with the provider."""

import os
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyTrust,
    HistoricalPolicyVerification,
    HistoricalPolicyVerificationRequest,
)
from src.infrastructure.authority_http import AuthorityHttpError, post_json_with_retries
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration


@dataclass(frozen=True)
class ConfiguredHistoricalPolicyVerifier:
    configuration: HistoricalPolicyConfiguration
    client: httpx.Client

    @property
    def trust(self) -> HistoricalPolicyTrust:
        return self.configuration.trust

    def verify(
        self, request: HistoricalPolicyVerificationRequest
    ) -> HistoricalPolicyVerification | None:
        if request.scope.tenant_id != self.trust.tenant_id or (
            request.reference.signing_contract != self.trust.signing_contract
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_TRUST_MISMATCH")
        credential = os.getenv(self.configuration.credential_env, "")
        if not credential.strip():
            return None
        try:
            body = post_json_with_retries(
                client=self.client,
                url=self.configuration.endpoint,
                payload=request.model_dump(mode="json"),
                headers={"Authorization": f"Bearer {credential}", "Accept-Encoding": "identity"},
                attempts=self.configuration.attempts,
                unavailable_error="COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE",
                rejected_error="COMPOSITE_HISTORICAL_POLICY_PROVIDER_REJECTED",
                invalid_response_error="COMPOSITE_HISTORICAL_POLICY_RESPONSE_INVALID",
                source_service="composite-historical-policy",
                maximum_response_bytes=self.configuration.maximum_response_bytes,
                reject_duplicate_members=True,
            )
        except AuthorityHttpError as exc:
            raise ValueError(exc.code) from exc
        # The owning application calls admitted_historical_policy for exact request/trust admission.
        try:
            return HistoricalPolicyVerification.model_validate(body)
        except ValidationError as exc:
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_RESPONSE_INVALID") from exc
