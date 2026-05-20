from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityFairnessAnalysis,
    DpmPmQualityReviewAction,
    PmQualityReviewActionState,
    PmQualityReviewActionTargetType,
    PmQualityReviewActionType,
)


def build_pm_quality_review_action(
    *,
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis,
    target_type: PmQualityReviewActionTargetType,
    action_type: PmQualityReviewActionType,
    review_action_ref: str,
    review_reason: str,
    actor_id: str,
    source_refs: list[DpmOutcomeSourceRef],
    remediation_due_date: str | None,
    correlation_id: str,
    generated_at: datetime | None = None,
) -> DpmPmQualityReviewAction:
    """Build an immutable review-action ledger row from existing PM-quality evidence."""

    generated_at = generated_at or datetime.now(timezone.utc)
    action_state = _action_state(action_type=action_type)
    target_ref = _target_source_ref(target=target, target_type=target_type)
    deduped_source_refs = _dedupe_refs([target_ref, *source_refs])
    payload: dict[str, Any] = {
        "product_name": "PmOperatingQualityReviewAction",
        "product_version": "v1",
        "review_action_ref": review_action_ref.strip(),
        "target_type": target_type,
        "target_id": _target_id(target=target, target_type=target_type),
        "target_content_hash": target.content_hash,
        "policy_id": target.policy_id,
        "policy_version": target.policy_version,
        "as_of_date": target.as_of_date,
        "target_state": target.state,
        "action_type": action_type,
        "action_state": action_state,
        "review_reason": review_reason.strip(),
        "remediation_due_date": remediation_due_date,
        "actor_id": actor_id.strip(),
        "reason_codes": _reason_codes(action_type=action_type, action_state=action_state),
        "source_refs": [ref.model_dump(mode="json") for ref in deduped_source_refs],
        "forbidden_uses": [
            "compensation_decision",
            "hr_decision",
            "conduct_enforcement",
            "client_contact",
            "trade_approval",
            "order_routing",
            "oms_execution",
            "autonomous_pm_ranking",
        ],
        "operating_boundaries": [
            "IMMUTABLE_REVIEW_ACTION_LEDGER",
            "NO_SCORE_RECALCULATION",
            "NO_FAIRNESS_RECOMPUTATION",
            "NO_PM_RANKING",
            "NO_HR_COMPENSATION_OR_CONDUCT_DECISION",
            "NO_CLIENT_CONTACT",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_OR_OMS_EXECUTION",
        ],
        "generated_at": generated_at,
        "correlation_id": correlation_id.strip(),
    }
    content_hash = _content_hash(payload)
    payload["review_action_id"] = f"pmq_review_{uuid5(NAMESPACE_URL, content_hash).hex[:16]}"
    payload["content_hash"] = content_hash
    return DpmPmQualityReviewAction.model_validate(payload)


def _target_id(
    *,
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis,
    target_type: PmQualityReviewActionTargetType,
) -> str:
    if target_type == "SCORE_RUN":
        if not isinstance(target, DpmPmOperatingQualityScoreRun):
            raise ValueError("PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH")
        return target.score_run_id
    if not isinstance(target, DpmPmQualityFairnessAnalysis):
        raise ValueError("PM_QUALITY_REVIEW_ACTION_TARGET_TYPE_MISMATCH")
    return target.fairness_analysis_id


def _target_source_ref(
    *,
    target: DpmPmOperatingQualityScoreRun | DpmPmQualityFairnessAnalysis,
    target_type: PmQualityReviewActionTargetType,
) -> DpmOutcomeSourceRef:
    target_id = _target_id(target=target, target_type=target_type)
    source_type = (
        "PmOperatingQualityScoreRun"
        if target_type == "SCORE_RUN"
        else "PmOperatingQualityFairnessAnalysis"
    )
    return DpmOutcomeSourceRef(
        source_system="lotus-manage",
        source_type=source_type,
        source_id=target_id,
        source_version="v1",
        content_hash=target.content_hash,
    )


def _action_state(*, action_type: PmQualityReviewActionType) -> PmQualityReviewActionState:
    states: dict[PmQualityReviewActionType, PmQualityReviewActionState] = {
        "ACKNOWLEDGE": "RECORDED",
        "REQUEST_EVIDENCE_REMEDIATION": "REVIEW_REQUIRED",
        "ACCEPT_GOVERNANCE_EXCEPTION": "CLOSED",
        "ESCALATE_MODEL_RISK_REVIEW": "ESCALATED",
        "CLOSE_REVIEW": "CLOSED",
    }
    return states[action_type]


def _reason_codes(
    *,
    action_type: PmQualityReviewActionType,
    action_state: PmQualityReviewActionState,
) -> list[str]:
    return [
        f"PM_QUALITY_REVIEW_ACTION_{action_type}",
        f"PM_QUALITY_REVIEW_ACTION_STATE_{action_state}",
    ]


def _dedupe_refs(refs: list[DpmOutcomeSourceRef]) -> list[DpmOutcomeSourceRef]:
    by_key: dict[tuple[str, str, str], DpmOutcomeSourceRef] = {}
    for ref in refs:
        by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return [by_key[key] for key in sorted(by_key)]


def _content_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
