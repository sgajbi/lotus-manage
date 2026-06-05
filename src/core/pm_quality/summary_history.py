from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from src.core.outcomes import DpmOutcomeSourceRef
from src.core.pm_quality.models import (
    DpmPmOperatingQualityScoreRun,
    DpmPmQualityReviewAction,
    DpmPmQualitySummaryInvocation,
    PmQualitySummaryInvocationState,
    build_pm_quality_summary_text_boundary,
)


def build_pm_quality_summary_invocation(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    review_action: DpmPmQualityReviewAction,
    invocation_state: PmQualitySummaryInvocationState,
    summary_ref: str,
    requested_by: str,
    source_refs: list[DpmOutcomeSourceRef],
    workflow_pack_name: str = "pm_quality_summary.pack",
    workflow_pack_version: str = "v1",
    workflow_run_id: str | None = None,
    summary_artifact_ref: str | None = None,
    summary_content_hash: str | None = None,
    correlation_id: str,
    generated_at: datetime | None = None,
) -> DpmPmQualitySummaryInvocation:
    """Build append-only support-summary invocation history from governed evidence."""

    _validate_summary_invocation_inputs(
        score_run=score_run,
        review_action=review_action,
        workflow_pack_name=workflow_pack_name,
        summary_content_hash=summary_content_hash,
    )
    generated_at = generated_at or datetime.now(timezone.utc)
    invocation_source_refs = _summary_invocation_source_refs(
        score_run=score_run,
        review_action=review_action,
        workflow_pack_version=workflow_pack_version,
        workflow_run_id=workflow_run_id,
        summary_artifact_ref=summary_artifact_ref,
        summary_content_hash=summary_content_hash,
        source_refs=source_refs,
    )

    payload: dict[str, Any] = {
        "product_name": "PmOperatingQualitySummaryInvocation",
        "product_version": "v1",
        "score_run_id": score_run.score_run_id,
        "score_run_content_hash": score_run.content_hash,
        "review_action_id": review_action.review_action_id,
        "review_action_content_hash": review_action.content_hash,
        "policy_id": score_run.policy_id,
        "policy_version": score_run.policy_version,
        "as_of_date": score_run.as_of_date,
        "invocation_state": invocation_state,
        "summary_ref": summary_ref.strip(),
        "workflow_pack_name": workflow_pack_name.strip(),
        "workflow_pack_version": workflow_pack_version.strip(),
        "workflow_run_id": workflow_run_id.strip() if workflow_run_id else None,
        "summary_artifact_ref": summary_artifact_ref.strip() if summary_artifact_ref else None,
        "summary_content_hash": summary_content_hash,
        "requested_by": requested_by.strip(),
        "reason_codes": _reason_codes(invocation_state=invocation_state),
        "source_refs": [ref.model_dump(mode="json") for ref in invocation_source_refs],
        "forbidden_uses": [
            "summary_text_storage",
            "score_recalculation",
            "fairness_recomputation",
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
            "APPEND_ONLY_SUMMARY_INVOCATION_HISTORY",
            "NO_SUMMARY_TEXT_STORAGE",
            "NO_SUMMARY_TEXT_EXPOSURE",
            "NO_DOWNSTREAM_SUMMARY_UX_CLAIM",
            "NO_SCORE_RECALCULATION",
            "NO_FAIRNESS_RECOMPUTATION",
            "NO_PM_RANKING",
            "NO_HR_COMPENSATION_OR_CONDUCT_DECISION",
            "NO_CLIENT_CONTACT",
            "NO_TRADE_APPROVAL",
            "NO_ORDER_OR_OMS_EXECUTION",
        ],
        "summary_text_boundary": build_pm_quality_summary_text_boundary().model_dump(mode="json"),
        "generated_at": generated_at,
        "correlation_id": correlation_id.strip(),
    }
    content_hash = _content_hash(payload)
    payload["summary_invocation_id"] = f"pmq_summary_{uuid5(NAMESPACE_URL, content_hash).hex[:16]}"
    payload["content_hash"] = content_hash
    return DpmPmQualitySummaryInvocation.model_validate(payload)


def _validate_summary_invocation_inputs(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    review_action: DpmPmQualityReviewAction,
    workflow_pack_name: str,
    summary_content_hash: str | None,
) -> None:
    if (
        review_action.target_type != "SCORE_RUN"
        or review_action.target_id != score_run.score_run_id
    ):
        raise ValueError("PM_QUALITY_SUMMARY_REVIEW_ACTION_TARGET_MISMATCH")
    if review_action.target_content_hash != score_run.content_hash:
        raise ValueError("PM_QUALITY_SUMMARY_REVIEW_ACTION_HASH_MISMATCH")
    if workflow_pack_name != "pm_quality_summary.pack":
        raise ValueError("PM_QUALITY_SUMMARY_WORKFLOW_PACK_UNSUPPORTED")
    if summary_content_hash is not None and not summary_content_hash.startswith("sha256:"):
        raise ValueError("PM_QUALITY_SUMMARY_CONTENT_HASH_INVALID")


def _summary_invocation_source_refs(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    review_action: DpmPmQualityReviewAction,
    workflow_pack_version: str,
    workflow_run_id: str | None,
    summary_artifact_ref: str | None,
    summary_content_hash: str | None,
    source_refs: list[DpmOutcomeSourceRef],
) -> list[DpmOutcomeSourceRef]:
    return _dedupe_refs(
        [
            *_managed_summary_source_refs(score_run=score_run, review_action=review_action),
            *_ai_summary_source_refs(
                workflow_pack_version=workflow_pack_version,
                workflow_run_id=workflow_run_id,
                summary_artifact_ref=summary_artifact_ref,
                summary_content_hash=summary_content_hash,
            ),
            *source_refs,
        ]
    )


def _managed_summary_source_refs(
    *,
    score_run: DpmPmOperatingQualityScoreRun,
    review_action: DpmPmQualityReviewAction,
) -> list[DpmOutcomeSourceRef]:
    return [
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityScoreRun",
            source_id=score_run.score_run_id,
            source_version=score_run.product_version,
            content_hash=score_run.content_hash,
        ),
        DpmOutcomeSourceRef(
            source_system="lotus-manage",
            source_type="PmOperatingQualityReviewAction",
            source_id=review_action.review_action_id,
            source_version=review_action.product_version,
            content_hash=review_action.content_hash,
        ),
    ]


def _ai_summary_source_refs(
    *,
    workflow_pack_version: str,
    workflow_run_id: str | None,
    summary_artifact_ref: str | None,
    summary_content_hash: str | None,
) -> list[DpmOutcomeSourceRef]:
    refs: list[DpmOutcomeSourceRef] = []
    if workflow_run_id:
        refs.append(
            DpmOutcomeSourceRef(
                source_system="lotus-ai",
                source_type="pm_quality_summary.pack",
                source_id=workflow_run_id.strip(),
                source_version=workflow_pack_version.strip(),
                content_hash=summary_content_hash,
            )
        )
    if summary_artifact_ref:
        refs.append(
            DpmOutcomeSourceRef(
                source_system="lotus-ai",
                source_type="PM_QUALITY_SUMMARY_ARTIFACT",
                source_id=summary_artifact_ref.strip(),
                source_version=workflow_pack_version.strip(),
                content_hash=summary_content_hash,
            )
        )
    return refs


def _reason_codes(*, invocation_state: PmQualitySummaryInvocationState) -> list[str]:
    return [
        f"PM_QUALITY_SUMMARY_INVOCATION_{invocation_state}",
        "PM_QUALITY_SUMMARY_REVIEW_GATED",
        "PM_QUALITY_SUMMARY_HISTORY_NO_TEXT_STORED",
    ]


def _dedupe_refs(refs: list[DpmOutcomeSourceRef]) -> list[DpmOutcomeSourceRef]:
    by_key: dict[tuple[str, str, str], DpmOutcomeSourceRef] = {}
    for ref in refs:
        by_key[(ref.source_system, ref.source_type, ref.source_id)] = ref
    return [by_key[key] for key in sorted(by_key)]


def _content_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
