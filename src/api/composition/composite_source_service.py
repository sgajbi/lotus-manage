"""Separate configured synthetic sources and institutional verification; default unavailable."""

import os

from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.core.composite_repository import DpmCompositeRepository
from src.core.composite_eligibility.staged_ports import StagedCompositeRepository
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCandidateUniverseSource,
    ConfiguredCompositeEvidenceVerifier,
    ConfiguredMonthlyEligibilitySource,
)
from src.infrastructure.composites.source_configuration import CompositeSourceConfiguration
from src.core.composite_eligibility.institutional_verification import (
    InstitutionalEvidenceVerifier,
    UnavailableInstitutionalEvidenceVerifier,
)
from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from src.infrastructure.composites.institutional_verifier import (
    ConfiguredInstitutionalEvidenceVerifier,
)
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from src.infrastructure.composites.historical_verifier import ConfiguredHistoricalPolicyVerifier
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyAdmissionPort,
    UnavailableHistoricalPolicyAdmission,
)
from src.infrastructure.source_http_clients import (
    build_source_http_client_policy,
    get_shared_source_http_client,
)


def build_composite_subject_service(
    repository: StagedCompositeRepository,
) -> CompositeSubjectApplicationService:
    """Requests cannot choose endpoints, source identities, credentials or trust posture."""
    transport = _configured_transport()
    if transport is None:
        return CompositeSubjectApplicationService(
            repository=repository, attestations=_configured_attestations()
        )
    return CompositeSubjectApplicationService(
        repository=repository,
        candidates=ConfiguredCandidateUniverseSource(transport),
        verifier=ConfiguredCompositeEvidenceVerifier(transport),
        attestations=_configured_attestations(),
        observations=ConfiguredMonthlyEligibilitySource(
            transport, ConfiguredCompositeEvidenceVerifier(transport)
        ),
    )


def build_composite_monthly_service(
    repository: DpmCompositeRepository,
) -> CompositeMonthlyEligibilityApplicationService:
    """Recurring months use the same deployed source and independent verifier admission."""
    historical = _configured_historical_admission()
    transport = _configured_transport()
    if transport is None:
        return CompositeMonthlyEligibilityApplicationService(
            repository=repository, historical_admission=historical
        )
    verifier = ConfiguredCompositeEvidenceVerifier(transport)
    return CompositeMonthlyEligibilityApplicationService(
        repository=repository,
        source=ConfiguredMonthlyEligibilitySource(transport, verifier),
        historical_admission=historical,
    )


def _configured_historical_admission() -> HistoricalPolicyAdmissionPort:
    raw = os.getenv("DPM_COMPOSITE_HISTORICAL_POLICY_ADMISSION_JSON", "")
    if not raw.strip():
        return UnavailableHistoricalPolicyAdmission()
    configuration = HistoricalPolicyConfiguration.model_validate_json(raw)
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    return ConfiguredHistoricalPolicyVerifier(configuration, client)


def _configured_transport() -> CompositeSourceTransport | None:
    raw = os.getenv("DPM_COMPOSITE_SOURCES_JSON")
    if not raw or not raw.strip():
        return None
    configuration = CompositeSourceConfiguration.model_validate_json(raw)
    if any(item.evidence_posture != "SYNTHETIC_NON_CERTIFYING" for item in configuration.bindings):
        raise ValueError("COMPOSITE_SOURCE_INSTITUTIONAL_CHANNEL_REQUIRED")
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    return CompositeSourceTransport(configuration=configuration, client=client)


def _configured_attestations() -> InstitutionalEvidenceVerifier:
    raw = os.getenv("DPM_COMPOSITE_ATTESTATION_VERIFICATION_JSON")
    if not raw or not raw.strip():
        return UnavailableInstitutionalEvidenceVerifier()
    configuration = InstitutionalVerificationConfiguration.model_validate_json(raw)
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    return ConfiguredInstitutionalEvidenceVerifier(configuration, client)
