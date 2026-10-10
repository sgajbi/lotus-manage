"""Deployment-owned transport for the frozen normalized historical verifier port."""

from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.core.composite_eligibility.historical_policy import HistoricalPolicyTrust


class HistoricalPolicyConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    endpoint: str = Field(min_length=1, max_length=2048)
    credential_env: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    trust: HistoricalPolicyTrust
    timeout_seconds: float = Field(default=2, ge=0.1, le=30)
    attempts: int = Field(default=1, ge=1, le=3)
    # A 2MB original expands to 2.67MB base64, before policy and attachments.
    maximum_response_bytes: int = Field(default=8_000_000, ge=1024, le=8_000_000)

    @model_validator(mode="after")
    def require_pinned_independent_provider(self) -> "HistoricalPolicyConfiguration":
        url = urlsplit(self.endpoint)
        if (
            url.scheme != "https"
            or not url.hostname
            or any((url.username, url.password, url.query, url.fragment))
            or "?" in self.endpoint
            or "#" in self.endpoint
            or url.port == 0
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_ENDPOINT_INVALID")
        if (
            self.trust.signer_principal_id == self.trust.verifier_principal_id
            or self.trust.signer_key_digest == self.trust.verifier_key_digest
        ):
            raise ValueError("COMPOSITE_HISTORICAL_POLICY_INDEPENDENCE_REQUIRED")
        return self
