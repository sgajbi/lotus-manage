"""Separate configured synthetic sources and institutional verification; default unavailable."""

import os
from dataclasses import dataclass

import httpx

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyAdmissionPort,
    UnavailableHistoricalPolicyAdmission,
)
from src.core.composite_eligibility.institutional_verification import (
    InstitutionalEvidenceVerifier,
    UnavailableInstitutionalEvidenceVerifier,
)
from src.core.composite_eligibility.staged_ports import StagedCompositeRepository
from src.core.composite_repository import DpmCompositeRepository
from src.core.composite_eligibility.verification import UnavailableCompositeEvidenceVerifier
from src.core.common.canonical import hash_canonical_payload
from src.infrastructure.composites.controlled_assembly_verifier import ControlledAssemblyVerifier
from src.infrastructure.composites.core_financial_sources import (
    CoreCandidateUniverseSource,
    CoreMonthlyEligibilitySource,
)
from src.infrastructure.composites.core_financial_configuration import CoreReaderConfiguration
from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
from src.infrastructure.composites.core_source_authentication import (
    CoreRetainedReadAuth,
    CoreSourceAuthenticationPolicy,
)
from src.infrastructure.composites.native_assembly_configuration import (
    NativeAssemblyConfiguration,
    native_monthly_signer,
)
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCandidateUniverseSource,
    ConfiguredCompositeEvidenceVerifier,
    ConfiguredMonthlyEligibilitySource,
)
from src.infrastructure.composites.controlled_source_verifier import (
    NativeControlledHistoricalVerifier,
)
from src.infrastructure.composites.historical_configuration import HistoricalPolicyConfiguration
from src.infrastructure.composites.historical_verifier import ConfiguredHistoricalPolicyVerifier
from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from src.infrastructure.composites.institutional_verifier import (
    ConfiguredInstitutionalEvidenceVerifier,
)
from src.infrastructure.composites.native_source_configuration import (
    NativeHistoricalConfiguration,
    strict_controlled_json,
)
from src.infrastructure.composites.source_configuration import CompositeSourceConfiguration
from src.infrastructure.source_http_clients import (
    build_source_http_client_policy,
    get_shared_source_http_client,
    get_partitioned_source_http_client,
)


@dataclass(frozen=True)
class _NativeSources:
    candidates: CoreCandidateUniverseSource
    observations: CoreMonthlyEligibilitySource
    policy_transport: CompositeSourceTransport | None


def build_composite_subject_service(
    repository: StagedCompositeRepository,
) -> CompositeSubjectApplicationService:
    """Requests cannot choose endpoints, source identities, credentials or trust posture."""
    configured = _configured_sources()
    if isinstance(configured, _NativeSources):
        return CompositeSubjectApplicationService(
            repository=repository,
            candidates=configured.candidates,
            observations=configured.observations,
            attestations=_configured_attestations(),
            historical_admission=_configured_historical_admission(),
            verifier=ConfiguredCompositeEvidenceVerifier(configured.policy_transport)
            if configured.policy_transport is not None
            else UnavailableCompositeEvidenceVerifier(),
        )
    transport = configured
    if transport is None:
        return CompositeSubjectApplicationService(
            repository=repository,
            attestations=_configured_attestations(),
            historical_admission=_configured_historical_admission(),
        )
    return CompositeSubjectApplicationService(
        repository=repository,
        candidates=ConfiguredCandidateUniverseSource(transport),
        verifier=ConfiguredCompositeEvidenceVerifier(transport),
        attestations=_configured_attestations(),
        historical_admission=_configured_historical_admission(),
        observations=ConfiguredMonthlyEligibilitySource(
            transport, ConfiguredCompositeEvidenceVerifier(transport)
        ),
    )


def build_composite_monthly_service(
    repository: DpmCompositeRepository,
) -> CompositeMonthlyEligibilityApplicationService:
    """Recurring months use the same deployed source and independent verifier admission."""
    historical = _configured_historical_admission()
    configured = _configured_sources()
    if isinstance(configured, _NativeSources):
        return CompositeMonthlyEligibilityApplicationService(
            repository=repository,
            source=configured.observations,
            historical_admission=historical,
        )
    transport = configured
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
    document = strict_controlled_json(raw)
    if "adapter" in document:
        return NativeControlledHistoricalVerifier(
            NativeHistoricalConfiguration.model_validate(document)
        )
    configuration = HistoricalPolicyConfiguration.model_validate_json(raw)
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    return ConfiguredHistoricalPolicyVerifier(configuration, client)


def _configured_sources() -> CompositeSourceTransport | _NativeSources | None:
    raw = os.getenv("DPM_COMPOSITE_SOURCES_JSON")
    if not raw or not raw.strip():
        return None
    document = strict_controlled_json(raw)
    if "adapter" in document:
        configuration = NativeAssemblyConfiguration.model_validate_json(raw)
        return _native_sources(configuration)
    return _transport(CompositeSourceConfiguration.model_validate_json(raw))


def _transport(configuration: CompositeSourceConfiguration) -> CompositeSourceTransport:
    if any(item.evidence_posture != "SYNTHETIC_NON_CERTIFYING" for item in configuration.bindings):
        raise ValueError("COMPOSITE_SOURCE_INSTITUTIONAL_CHANNEL_REQUIRED")
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    return CompositeSourceTransport(configuration=configuration, client=client)


def _native_client(
    role: str,
    reader: CoreReaderConfiguration,
    authorization: CoreSourceAuthenticationPolicy,
    timeout: float,
) -> httpx.Client:
    partition = hash_canonical_payload(
        {
            "role": role,
            "reader": reader.model_dump(mode="json"),
            "authorization": authorization.model_dump(mode="json"),
        }
    )
    return get_partitioned_source_http_client(
        "composite",
        partition=partition,
        policy=build_source_http_client_policy("composite", request_timeout_seconds=timeout),
        auth=CoreRetainedReadAuth(authorization),
    )


def _native_sources(configuration: NativeAssemblyConfiguration) -> _NativeSources | None:
    for authorization in (
        configuration.assembly_authorization,
        configuration.verification_authorization,
    ):
        secret = os.getenv(authorization.credential_env)
        if not secret or secret != secret.strip():
            return None
    signer = native_monthly_signer(configuration)
    if signer is None:
        return None
    client_a = _native_client(
        "assembly",
        configuration.reader,
        configuration.assembly_authorization,
        configuration.timeout_seconds,
    )
    client_c = _native_client(
        "verification",
        configuration.verification.reader,
        configuration.verification_authorization,
        configuration.timeout_seconds,
    )
    reader = CoreHttpRetainedReader(
        configuration.reader, client_a, members=configuration.financial.members
    )
    verifier = ControlledAssemblyVerifier(configuration.verification, client_c, signer=signer)
    return _NativeSources(
        CoreCandidateUniverseSource(configuration.financial, reader),
        CoreMonthlyEligibilitySource(
            configuration.financial, reader, verifier=verifier, controlled_synthetic=True
        ),
        _transport(configuration.policy_verification)
        if configuration.policy_verification is not None
        else None,
    )


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
