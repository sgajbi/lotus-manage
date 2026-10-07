"""Closed commands: scope/actor/time are admitted by routes and server clock."""

from pydantic import Field
from src.api.composite_definition_requests import CompositeDefinitionV2Request
from src.core.composite_authority_models import (
    BusinessDate,
    Digest,
    EvidenceBinding,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.observations import Currency
from src.core.composite_eligibility.policy import MonthlyPolicyLayer


class SubjectRequest(StrictAuthorityModel):
    display_name: str = Field(min_length=1, max_length=256)
    strategy_code: Identity
    reporting_currency: Currency
    inception_date: BusinessDate
    termination_date: BusinessDate | None
    eligibility_policy_version: Identity
    month: str
    registry_binding: EvidenceBinding
    correlation_id: Identity


class SubjectPolicyRequest(StrictAuthorityModel):
    expected_subject_content_hash: Digest
    layers: list[MonthlyPolicyLayer] = Field(min_length=1, max_length=5)
    attachments: list[EvidenceBinding] = Field(min_length=1, max_length=20)


class SubjectApprovalRequest(StrictAuthorityModel):
    expected_proposal_content_hash: Digest


class SubjectEvaluationRequest(StrictAuthorityModel):
    policy_proposal_revision: Identity
    policy_approval_content_hash: Digest
    target_membership_revision: Identity
    source_cut_id: Identity
    source_revision: Identity
    source_content_hash: Digest


class SubjectFinalizationRequest(StrictAuthorityModel):
    evaluation_revision: Identity
    expected_approval_content_hash: Digest
    definition: CompositeDefinitionV2Request
