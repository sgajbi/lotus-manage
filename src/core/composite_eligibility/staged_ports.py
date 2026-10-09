"""Source and custody contracts for staged eligibility; no transport dependencies."""

from dataclasses import dataclass
from typing import Literal, Protocol

from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_eligibility.monthly_evidence import MonthlyEligibilityPublicationReceipt
from src.core.composite_eligibility.staged_subject import CandidateUniverse, EligibilitySubject
from src.core.composite_eligibility.staged_controls import StagedControl
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalization,
    SubjectFinalizationReceipt,
)

SubjectKey = tuple[str, str, str, str]
ControlKind = Literal[
    "CompositeSubjectPolicyProposal",
    "CompositeSubjectPolicyApproval",
    "CompositeSubjectEvaluationProposal",
    "CompositeSubjectEvaluationApproval",
]


@dataclass(frozen=True)
class CandidateUniverseRequest:
    tenant_id: str
    composite_id: str
    definition_version: str
    month: str
    reporting_currency: str
    registry_binding: EvidenceBinding


class CandidateUniverseSource(Protocol):
    def resolve(self, request: CandidateUniverseRequest) -> CandidateUniverse | None:
        """Resolve source-owned population; caller facts cannot grant authority."""


class UnavailableCandidateUniverseSource:
    def resolve(self, request: CandidateUniverseRequest) -> CandidateUniverse | None:
        return None


class StagedCompositeRepository(Protocol):
    def resolve_monthly_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> MonthlyEligibilityPublicationReceipt | None:
        """Join exact monthly approval and canonical publication in one read snapshot."""

    def save_eligibility_subject(self, *, subject: EligibilitySubject) -> None: ...
    def get_eligibility_subject(self, *, key: SubjectKey) -> EligibilitySubject | None: ...
    def save_subject_control(self, *, control: StagedControl) -> None: ...
    def get_subject_control(
        self, *, key: SubjectKey, kind: ControlKind, revision: str
    ) -> StagedControl | None: ...
    def finalize_eligibility_subject(
        self, *, finalization: SubjectFinalization
    ) -> SubjectFinalizationReceipt: ...
    def get_eligibility_finalization(
        self, *, key: SubjectKey
    ) -> SubjectFinalizationReceipt | None: ...
    def resolve_eligibility_evidence(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        approval_content_hash: str,
    ) -> SubjectFinalizationReceipt | None: ...
