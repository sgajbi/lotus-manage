"""Deployment composition for synthetic source adapters; absent configuration fails closed."""

import os

from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.core.composite_eligibility.staged_ports import StagedCompositeRepository
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCandidateUniverseSource,
    ConfiguredCompositeEvidenceVerifier,
    ConfiguredMonthlyEligibilitySource,
)
from src.infrastructure.composites.source_configuration import CompositeSourceConfiguration
from src.infrastructure.source_http_clients import (
    build_source_http_client_policy,
    get_shared_source_http_client,
)


def build_composite_subject_service(
    repository: StagedCompositeRepository,
) -> CompositeSubjectApplicationService:
    """Requests cannot choose endpoints, source identities, credentials or trust posture."""
    raw = os.getenv("DPM_COMPOSITE_SOURCES_JSON")
    if not raw or not raw.strip():
        return CompositeSubjectApplicationService(repository=repository)
    configuration = CompositeSourceConfiguration.model_validate_json(raw)
    client = get_shared_source_http_client(
        "composite",
        policy=build_source_http_client_policy(
            "composite", request_timeout_seconds=configuration.timeout_seconds
        ),
    )
    transport = CompositeSourceTransport(configuration=configuration, client=client)
    return CompositeSubjectApplicationService(
        repository=repository,
        candidates=ConfiguredCandidateUniverseSource(transport),
        verifier=ConfiguredCompositeEvidenceVerifier(transport),
        observations=ConfiguredMonthlyEligibilitySource(
            transport, ConfiguredCompositeEvidenceVerifier(transport)
        ),
    )
