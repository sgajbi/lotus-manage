"""Source-only controlled history; empty business repository and current runtime admission."""

from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.core.composite_eligibility.source import MonthlyEligibilitySourceResolution
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import ControlledHistoricalPolicyPort
from tests.composite_staged_eligibility_helpers import SyntheticEvidenceVerifier, lifecycle_material


def empty_historical_subject_service():
    _, subject, policy, approved_policy, evaluation, *_ = lifecycle_material()
    historical = ControlledHistoricalPolicyPort(approved_policy.approval)
    repository = InMemoryDpmCompositeRepository()

    class Candidates:
        def resolve(self, request):
            assert request.registry_binding == subject.universe.registry_binding
            return subject.universe

    class Observations:
        def resolve(self, request):
            return MonthlyEligibilitySourceResolution(
                evaluation.observations,
                owner_service=subject.universe.observation_owner,
            )

    service = CompositeSubjectApplicationService(
        repository=repository,
        candidates=Candidates(),
        observations=Observations(),
        verifier=SyntheticEvidenceVerifier(),
        historical_admission=historical,
    )
    return service, repository, historical, subject, policy, evaluation
