from __future__ import annotations

from datetime import date
import hashlib
import json

from src.api.services import wave_service
from src.api.services.wave_campaign_governance import (
    campaign_actor_entitlement_state,
    campaign_approval_status,
    campaign_expiry_state,
)
from src.core.waves import (
    DpmBulkReviewCampaignDefinition,
    DpmBulkReviewCampaignDefinitionCandidate,
    DpmWaveSourceRef,
)
from src.core.waves.campaign_candidate_source_contracts import (
    DpmBulkReviewCampaignSourceContractError,
    validate_bulk_review_campaign_candidate_source_refs,
)


def build_campaign_definition_launch_portfolios(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    actor_id: str,
    requested_as_of_date: str,
) -> list[dict[str, object]]:
    campaign_as_of_date = _parse_campaign_as_of_date(requested_as_of_date)
    eligible_portfolio_types = {
        _normalize_campaign_portfolio_type(portfolio_type)
        for portfolio_type in definition.eligible_portfolio_types
    }
    if not eligible_portfolio_types:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPES_REQUIRED",
            "BULK_REVIEW_CAMPAIGN requires at least one eligible portfolio type.",
        )
    included_candidates: list[DpmBulkReviewCampaignDefinitionCandidate] = []
    excluded_candidate_count = 0
    for candidate in definition.candidates:
        if (
            _normalize_campaign_portfolio_type(candidate.portfolio_type)
            not in eligible_portfolio_types
        ):
            excluded_candidate_count += 1
            continue
        included_candidates.append(candidate)
    if not included_candidates:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_MEMBERSHIP_EMPTY",
            "Bulk-review campaign membership returned no eligible DPM portfolios.",
        )

    candidate_payloads = [
        _campaign_definition_candidate_payload(definition=definition, candidate=candidate)
        for candidate in included_candidates
    ]
    for candidate_payload in candidate_payloads:
        _validate_candidate_source_contracts(candidate_payload)

    membership_hash = _campaign_membership_hash(
        trigger_id=definition.campaign_id,
        as_of_date=campaign_as_of_date,
        portfolio_types=sorted(eligible_portfolio_types),
        portfolios=candidate_payloads,
    )
    membership_ref = _source_ref_payload(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignMembership",
        source_id=f"campaign:{definition.campaign_id}:{campaign_as_of_date.isoformat()}",
        source_version="v1",
        supportability_state="READY",
        content_hash=membership_hash,
    )
    governance_diagnostics, governance_refs = _campaign_governance_diagnostics_and_refs(
        definition=definition,
        actor_id=actor_id,
        campaign_as_of_date=campaign_as_of_date,
    )
    return [
        _campaign_portfolio_payload(
            payload=payload,
            definition=definition,
            campaign_as_of_date=campaign_as_of_date,
            membership_hash=membership_hash,
            membership_ref=membership_ref,
            governance_refs=governance_refs,
            governance_diagnostics=governance_diagnostics,
            eligible_portfolio_types=eligible_portfolio_types,
            excluded_candidate_count=excluded_candidate_count,
        )
        for payload in candidate_payloads
    ]


def _parse_campaign_as_of_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise wave_service.DpmWaveValidationError(
            "WAVE_AS_OF_DATE_INVALID",
            "as_of_date must be an ISO date.",
        ) from exc


def _normalize_campaign_portfolio_type(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise wave_service.DpmWaveValidationError(
            "BULK_REVIEW_CAMPAIGN_PORTFOLIO_TYPE_REQUIRED",
            "BULK_REVIEW_CAMPAIGN candidate portfolios require source-owned portfolio_type.",
        )
    return normalized


def _validate_candidate_source_contracts(candidate_payload: dict[str, object]) -> None:
    try:
        validate_bulk_review_campaign_candidate_source_refs(
            portfolio_id=str(candidate_payload["portfolio_id"]),
            source_refs=[
                DpmWaveSourceRef.model_validate(ref)
                for ref in _source_refs_payload(candidate_payload["source_refs"])
            ],
        )
    except DpmBulkReviewCampaignSourceContractError as exc:
        raise wave_service.DpmWaveValidationError(exc.code, exc.message) from exc


def _campaign_definition_candidate_payload(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    candidate: DpmBulkReviewCampaignDefinitionCandidate,
) -> dict[str, object]:
    definition_ref = _campaign_definition_source_ref(definition)
    return {
        "portfolio_id": candidate.portfolio_id,
        "mandate_id": candidate.mandate_id,
        "portfolio_manager_id": candidate.portfolio_manager_id,
        "portfolio_type": candidate.portfolio_type,
        "source_refs": [definition_ref, *_source_refs_payload(candidate.source_refs)],
    }


def _campaign_definition_source_ref(
    definition: DpmBulkReviewCampaignDefinition,
) -> dict[str, object]:
    return _source_ref_payload(
        source_system="lotus-manage",
        source_type="BulkReviewCampaignDefinition",
        source_id=f"campaign-definition:{definition.campaign_id}:{definition.campaign_version}",
        source_version=definition.product_version,
        supportability_state="READY",
        content_hash=definition.content_hash,
    )


def _campaign_portfolio_payload(
    *,
    payload: dict[str, object],
    definition: DpmBulkReviewCampaignDefinition,
    campaign_as_of_date: date,
    membership_hash: str,
    membership_ref: dict[str, object],
    governance_refs: list[dict[str, object]],
    governance_diagnostics: dict[str, object],
    eligible_portfolio_types: set[str],
    excluded_candidate_count: int,
) -> dict[str, object]:
    portfolio_id = str(payload["portfolio_id"])
    portfolio_type = payload.get("portfolio_type")
    return {
        "portfolio_id": portfolio_id,
        "mandate_id": payload.get("mandate_id"),
        "source_refs": [
            membership_ref,
            *governance_refs,
            _source_ref_payload(
                source_system="lotus-manage",
                source_type="BULK_REVIEW_CAMPAIGN_MEMBER",
                source_id=f"{definition.campaign_id}:{portfolio_id}",
                source_version=campaign_as_of_date.isoformat(),
                supportability_state="READY",
                content_hash=membership_hash,
            ),
            *_source_refs_payload(payload["source_refs"]),
        ],
        "diagnostics": {
            "source_owner": "lotus-manage",
            "source_product": "BulkReviewCampaignMembership:v1",
            "campaign_id": definition.campaign_id,
            "campaign_as_of_date": campaign_as_of_date.isoformat(),
            "portfolio_type": str(portfolio_type).strip().upper() if portfolio_type else None,
            "eligible_portfolio_types": sorted(eligible_portfolio_types),
            "excluded_candidate_count": excluded_candidate_count,
            "membership_supportability_state": "READY",
            **governance_diagnostics,
        },
    }


def _campaign_governance_diagnostics_and_refs(
    *,
    definition: DpmBulkReviewCampaignDefinition,
    actor_id: str,
    campaign_as_of_date: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    governance = definition.governance
    if governance is None:
        return (
            {
                "campaign_governance_status": "NOT_SUPPLIED",
                "campaign_access_purpose": None,
                "campaign_expiry_state": "NOT_SUPPLIED",
                "campaign_actor_entitlement_state": "NOT_SUPPLIED",
            },
            [],
        )
    approval_status = campaign_approval_status(
        approval_ref=governance.approval_ref,
        approved_by=governance.approved_by,
        approved_at=governance.approved_at,
    )
    expiry_state = campaign_expiry_state(
        expires_on=governance.expires_on,
        campaign_as_of_date=campaign_as_of_date,
    )
    actor_entitlement_state = campaign_actor_entitlement_state(
        entitled_actor_ids=governance.entitled_actor_ids,
        actor_id=actor_id,
    )
    governance_hash = _canonical_sha256(
        {
            "product_name": "BulkReviewCampaignGovernance",
            "product_version": "v1",
            "trigger_id": definition.campaign_id,
            "actor_id": actor_id,
            "governance": governance.model_dump(mode="json"),
        }
    )
    governance_refs: list[dict[str, object]] = [
        _source_ref_payload(
            source_system="lotus-manage",
            source_type="BulkReviewCampaignGovernance",
            source_id=f"campaign-governance:{definition.campaign_id}",
            source_version=governance.approved_at or campaign_as_of_date.isoformat(),
            supportability_state="READY",
            content_hash=governance_hash,
        ),
        *_source_refs_payload(governance.source_refs),
    ]
    return (
        {
            "campaign_governance_status": approval_status,
            "campaign_approval_ref": governance.approval_ref,
            "campaign_approved_by": governance.approved_by,
            "campaign_approved_at": governance.approved_at,
            "campaign_access_purpose": governance.access_purpose,
            "campaign_expiry_state": expiry_state,
            "campaign_expires_on": governance.expires_on,
            "campaign_actor_entitlement_state": actor_entitlement_state,
        },
        governance_refs,
    )


def _campaign_membership_hash(
    *,
    trigger_id: str,
    as_of_date: date,
    portfolio_types: list[str],
    portfolios: list[dict[str, object]],
) -> str:
    return _canonical_sha256(
        {
            "product_name": "BulkReviewCampaignMembership",
            "product_version": "v1",
            "trigger_id": trigger_id,
            "as_of_date": as_of_date.isoformat(),
            "portfolio_types": portfolio_types,
            "portfolios": portfolios,
        }
    )


def _source_refs_payload(refs: object) -> list[dict[str, object]]:
    if not isinstance(refs, list):
        raise TypeError("DpmWaveSourceRef payload must be a list.")
    return [
        ref.model_dump(mode="json", exclude_none=True) if hasattr(ref, "model_dump") else dict(ref)
        for ref in refs
    ]


def _source_ref_payload(
    *,
    source_system: str,
    source_type: str,
    source_id: str | None,
    source_version: str | None,
    supportability_state: str,
    content_hash: str | None,
) -> dict[str, object]:
    return {
        "source_system": source_system,
        "source_type": source_type,
        "source_id": source_id,
        "source_version": source_version,
        "supportability_state": supportability_state,
        "content_hash": content_hash,
    }


def _canonical_sha256(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"
