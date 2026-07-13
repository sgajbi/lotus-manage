from datetime import timedelta
from decimal import Decimal

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityReviewActionConflictError,
    DpmPmQualityReviewActionIntegrityError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualitySummaryInvocationConflictError,
    DpmPmQualitySummaryInvocationIntegrityError,
    DpmPmQualityWeight,
    DpmPmQualityFairnessSegmentInput,
    build_pm_operating_quality_fairness_analysis,
    build_pm_operating_quality_score_run,
    build_pm_quality_review_action,
    build_pm_quality_summary_invocation,
)
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityReviewActionRepository,
    InMemoryDpmPmQualityScoreRunRepository,
    InMemoryDpmPmQualitySummaryInvocationRepository,
)
from src.infrastructure.pm_quality.in_memory import (
    _FairnessAnalysisFilters,
    _PolicyFilters,
    _ReviewActionFilters,
    _ScoreRunFilters,
    _SummaryInvocationFilters,
    _fairness_analysis_matches_filters,
    _list_fairness_analyses,
    _list_policies,
    _list_review_actions,
    _list_score_runs,
    _list_summary_invocations,
    _optional_bool_matches,
    _policy_matches_filters,
    _review_action_matches_filters,
    _score_run_matches_filters,
    _sort_fairness_analyses,
    _sort_policies,
    _sort_review_actions,
    _sort_score_runs,
    _sort_summary_invocations,
    _summary_invocation_matches_filters,
)
from src.infrastructure.pm_quality import postgres as postgres_module
from src.infrastructure.pm_quality.postgres import (
    PostgresDpmPmQualityFairnessAnalysisRepository,
    PostgresDpmPmQualityPolicyRepository,
    PostgresDpmPmQualityReviewActionRepository,
    PostgresDpmPmQualityScoreRunRepository,
    PostgresDpmPmQualitySummaryInvocationRepository,
)


ROOT = Path(__file__).resolve().parents[4]
TENANT_ID = "tenant-sg"
TENANT_OTHER = "tenant-hk"


def _governance_approval() -> DpmPmQualityGovernanceApproval:
    return DpmPmQualityGovernanceApproval(
        approval_ref="PMQ-APPROVAL-2026-05",
        approved_by="pm_quality_committee",
        approved_at="2026-05-10T09:00:00Z",
        fairness_review_ref="FAIRNESS-PMQ-2026-05",
        fairness_reviewed_by="model_risk_governance",
        fairness_reviewed_at="2026-05-10T10:00:00Z",
        expires_on="2026-06-30",
        entitled_actor_ids=["ops"],
    )


def _score_run(*, pm_id: str = "pm_001", policy_id: str = "pmq_sg_dpm"):
    policy = DpmPmOperatingQualityPolicy(
        tenant_id=TENANT_ID,
        policy_id=policy_id,
        policy_version="2026.05",
        enabled=True,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="OUTCOME_DISCIPLINE",
                weight=Decimal("100"),
                minimum_evidence_count=1,
            )
        ],
        governance_approval=_governance_approval(),
    )
    return build_pm_operating_quality_score_run(
        tenant_id=TENANT_ID,
        pm_id=pm_id,
        book_id="sg_dpm_book",
        as_of_date="2026-05-12",
        policy=policy,
        evidence_items=[],
        outcome_reviews=[],
        generated_by="ops",
        correlation_id=f"corr-{pm_id}",
    )


def _policy(*, policy_id: str = "pmq_sg_dpm", enabled: bool = True):
    return DpmPmOperatingQualityPolicy(
        tenant_id=TENANT_ID,
        policy_id=policy_id,
        policy_version="2026.05",
        enabled=enabled,
        as_of_date="2026-05-12",
        access_purpose="SUPERVISORY_CONTROL_REVIEW",
        weights=[
            DpmPmQualityWeight(
                indicator="OUTCOME_DISCIPLINE",
                weight=Decimal("100"),
                minimum_evidence_count=1,
            )
        ]
        if enabled
        else [],
        governance_approval=_governance_approval() if enabled else None,
    )


def _fairness_analysis():
    first = _score_run(pm_id="pm_001")
    second = _score_run(pm_id="pm_002")
    return build_pm_operating_quality_fairness_analysis(
        tenant_id=TENANT_ID,
        policy_id="pmq_sg_dpm",
        policy_version="2026.05",
        as_of_date="2026-05-12",
        segments=[
            DpmPmQualityFairnessSegmentInput(
                segment_id="region_sg",
                segment_type="REGION",
                display_name="Singapore",
                score_runs=[first],
                source_refs=[],
            ),
            DpmPmQualityFairnessSegmentInput(
                segment_id="region_hk",
                segment_type="REGION",
                display_name="Hong Kong",
                score_runs=[second],
                source_refs=[],
            ),
        ],
        minimum_segment_score_run_count=1,
        maximum_average_score_spread=Decimal("15"),
        generated_by="ops",
        correlation_id="corr-fairness",
    )


def _review_action():
    score_run = _score_run()
    return build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )


def _summary_invocation():
    score_run = _score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )
    return build_pm_quality_summary_invocation(
        score_run=score_run,
        review_action=review_action,
        invocation_state="REQUESTED",
        summary_ref="PMQ-SUMMARY-2026-05-001",
        requested_by="ops",
        source_refs=[],
        correlation_id="corr-summary",
    )


def _summary_invocation_with_parents():
    score_run = _score_run()
    review_action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-001",
        review_reason="Reviewed and acknowledged for supervisory evidence.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-review-action",
    )
    invocation = build_pm_quality_summary_invocation(
        score_run=score_run,
        review_action=review_action,
        invocation_state="REQUESTED",
        summary_ref="PMQ-SUMMARY-2026-05-001",
        requested_by="ops",
        source_refs=[],
        correlation_id="corr-summary",
    )
    return score_run, review_action, invocation


class _FakeCursor:
    def __init__(self, row: dict[str, Any] | None = None, rows: list[dict[str, Any]] | None = None):
        self._row = row
        self._rows = rows or ([] if row is None else [row])

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakePolicyConnection:
    def __init__(self) -> None:
        self.policies: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.score_runs: dict[tuple[str, str], dict[str, Any]] = {}
        self.fairness_analyses: dict[tuple[str, str], dict[str, Any]] = {}
        self.review_actions: dict[tuple[str, str], dict[str, Any]] = {}
        self.summary_invocations: dict[tuple[str, str], dict[str, Any]] = {}
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, query: str, params: Sequence[Any] = ()) -> _FakeCursor:
        normalized = " ".join(query.split())
        if normalized.startswith("INSERT INTO dpm_pm_quality_score_runs"):
            tenant_id = str(params[0])
            score_run_id = str(params[1])
            key = (tenant_id, score_run_id)
            if key not in self.score_runs:
                self.score_runs[key] = {
                    "tenant_id": tenant_id,
                    "score_run_id": score_run_id,
                    "pm_id": str(params[2]),
                    "book_id": str(params[3]),
                    "policy_id": str(params[4]),
                    "policy_version": str(params[5]),
                    "as_of_date": str(params[6]),
                    "state": str(params[7]),
                    "content_hash": str(params[9]),
                    "generated_at": str(params[10]),
                    "payload_json": json.loads(str(params[13])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_score_runs"):
            row = self.score_runs.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith(
            "SELECT content_hash, policy_id, policy_version, as_of_date, state "
            "FROM dpm_pm_quality_score_runs"
        ):
            row = self.score_runs.get((str(params[0]), str(params[1])))
            return _FakeCursor(row=_parent_evidence_row(row))
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_score_runs WHERE")
            and "score_run_id = %s" in normalized
        ):
            return _FakeCursor(self.score_runs.get((str(params[0]), str(params[1]))))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_score_runs"):
            rows = self._filter_score_runs(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_fairness_analyses"):
            tenant_id = str(params[0])
            fairness_analysis_id = str(params[1])
            key = (tenant_id, fairness_analysis_id)
            if key not in self.fairness_analyses:
                self.fairness_analyses[key] = {
                    "tenant_id": tenant_id,
                    "fairness_analysis_id": fairness_analysis_id,
                    "policy_id": str(params[2]),
                    "policy_version": str(params[3]),
                    "as_of_date": str(params[4]),
                    "state": str(params[5]),
                    "content_hash": str(params[7]),
                    "generated_at": str(params[8]),
                    "payload_json": json.loads(str(params[11])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_fairness_analyses"):
            row = self.fairness_analyses.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith(
            "SELECT content_hash, policy_id, policy_version, as_of_date, state "
            "FROM dpm_pm_quality_fairness_analyses"
        ):
            row = self.fairness_analyses.get((str(params[0]), str(params[1])))
            return _FakeCursor(row=_parent_evidence_row(row))
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_fairness_analyses WHERE")
            and "fairness_analysis_id = %s" in normalized
        ):
            return _FakeCursor(self.fairness_analyses.get((str(params[0]), str(params[1]))))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_fairness_analyses"):
            rows = self._filter_fairness_analyses(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_review_actions"):
            tenant_id = str(params[0])
            review_action_id = str(params[1])
            key = (tenant_id, review_action_id)
            if key not in self.review_actions:
                self.review_actions[key] = {
                    "tenant_id": tenant_id,
                    "review_action_id": review_action_id,
                    "review_action_ref": str(params[2]),
                    "target_type": str(params[3]),
                    "target_id": str(params[4]),
                    "policy_id": str(params[5]),
                    "policy_version": str(params[6]),
                    "as_of_date": str(params[7]),
                    "target_state": str(params[8]),
                    "action_type": str(params[9]),
                    "action_state": str(params[10]),
                    "content_hash": str(params[11]),
                    "generated_at": str(params[12]),
                    "actor_id": str(params[13]),
                    "payload_json": json.loads(str(params[15])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_review_actions"):
            row = self.review_actions.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith(
            "SELECT content_hash, target_type, target_id, policy_id, policy_version, as_of_date "
            "FROM dpm_pm_quality_review_actions"
        ):
            row = self.review_actions.get((str(params[0]), str(params[1])))
            return _FakeCursor(row=_review_action_parent_row(row))
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_review_actions WHERE")
            and "review_action_id = %s" in normalized
        ):
            return _FakeCursor(self.review_actions.get((str(params[0]), str(params[1]))))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_review_actions"):
            rows = self._filter_review_actions(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_summary_invocations"):
            tenant_id = str(params[0])
            summary_invocation_id = str(params[1])
            key = (tenant_id, summary_invocation_id)
            if key not in self.summary_invocations:
                self.summary_invocations[key] = {
                    "tenant_id": tenant_id,
                    "summary_invocation_id": summary_invocation_id,
                    "score_run_id": str(params[2]),
                    "review_action_id": str(params[3]),
                    "policy_id": str(params[4]),
                    "policy_version": str(params[5]),
                    "as_of_date": str(params[6]),
                    "invocation_state": str(params[7]),
                    "summary_ref": str(params[8]),
                    "workflow_pack_name": str(params[9]),
                    "workflow_pack_version": str(params[10]),
                    "workflow_run_id": params[11],
                    "summary_artifact_ref": params[12],
                    "summary_content_hash": params[13],
                    "content_hash": str(params[14]),
                    "generated_at": str(params[15]),
                    "requested_by": str(params[16]),
                    "payload_json": json.loads(str(params[18])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_summary_invocations"):
            row = self.summary_invocations.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if (
            normalized.startswith(
                "SELECT payload_json FROM dpm_pm_quality_summary_invocations WHERE"
            )
            and "summary_invocation_id = %s" in normalized
        ):
            return _FakeCursor(self.summary_invocations.get((str(params[0]), str(params[1]))))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_summary_invocations"):
            rows = self._filter_summary_invocations(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_policies"):
            key = (str(params[0]), str(params[1]), str(params[2]))
            if key not in self.policies:
                self.policies[key] = {
                    "tenant_id": str(params[0]),
                    "policy_id": str(params[1]),
                    "policy_version": str(params[2]),
                    "enabled": bool(params[3]),
                    "as_of_date": str(params[4]),
                    "access_purpose": str(params[5]),
                    "content_hash": str(params[6]),
                    "payload_json": json.loads(str(params[7])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_policies"):
            row = self.policies.get((str(params[0]), str(params[1]), str(params[2])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_policies WHERE"):
            if "policy_version = %s" in normalized:
                return _FakeCursor(
                    self.policies.get((str(params[0]), str(params[1]), str(params[2])))
                )
            rows = [row for row in self.policies.values() if row["tenant_id"] == str(params[0])]
            param_index = 1
            if "policy_id = %s" in normalized:
                rows = [row for row in rows if row["policy_id"] == params[param_index]]
                param_index += 1
            if "enabled = %s" in normalized:
                rows = [row for row in rows if row["enabled"] is params[param_index]]
                param_index += 1
            if "as_of_date = %s" in normalized:
                rows = [row for row in rows if row["as_of_date"] == params[param_index]]
            rows.sort(
                key=lambda row: (row["as_of_date"], row["policy_id"], row["policy_version"]),
                reverse=True,
            )
            limit = int(params[-2])
            offset = int(params[-1])
            return _FakeCursor(rows=rows[offset : offset + limit])
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_policies"):
            rows = sorted(
                [row for row in self.policies.values() if row["tenant_id"] == str(params[0])],
                key=lambda row: (row["as_of_date"], row["policy_id"], row["policy_version"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows[int(params[-1]) : int(params[-1]) + int(params[-2])])
        raise AssertionError(f"Unexpected query: {normalized}")

    def _filter_score_runs(
        self,
        *,
        normalized: str,
        params: Sequence[Any],
    ) -> list[dict[str, Any]]:
        rows = [row for row in self.score_runs.values() if row["tenant_id"] == str(params[0])]
        param_index = 1
        for column in ("pm_id", "book_id", "policy_id", "as_of_date", "state"):
            if f"{column} = %s" in normalized:
                rows = [row for row in rows if row[column] == str(params[param_index])]
                param_index += 1
        rows.sort(key=lambda row: (row["generated_at"], row["score_run_id"]), reverse=True)
        limit = int(params[-2])
        offset = int(params[-1])
        return rows[offset : offset + limit]

    def _filter_fairness_analyses(
        self,
        *,
        normalized: str,
        params: Sequence[Any],
    ) -> list[dict[str, Any]]:
        rows = [
            row for row in self.fairness_analyses.values() if row["tenant_id"] == str(params[0])
        ]
        param_index = 1
        for column in ("policy_id", "policy_version", "as_of_date", "state"):
            if f"{column} = %s" in normalized:
                rows = [row for row in rows if row[column] == str(params[param_index])]
                param_index += 1
        rows.sort(
            key=lambda row: (row["generated_at"], row["fairness_analysis_id"]),
            reverse=True,
        )
        limit = int(params[-2])
        offset = int(params[-1])
        return rows[offset : offset + limit]

    def _filter_review_actions(
        self,
        *,
        normalized: str,
        params: Sequence[Any],
    ) -> list[dict[str, Any]]:
        rows = [row for row in self.review_actions.values() if row["tenant_id"] == str(params[0])]
        param_index = 1
        for column in ("target_type", "target_id", "policy_id", "as_of_date", "action_state"):
            if f"{column} = %s" in normalized:
                rows = [row for row in rows if row[column] == str(params[param_index])]
                param_index += 1
        rows.sort(
            key=lambda row: (row["generated_at"], row["review_action_id"]),
            reverse=True,
        )
        limit = int(params[-2])
        offset = int(params[-1])
        return rows[offset : offset + limit]

    def _filter_summary_invocations(
        self,
        *,
        normalized: str,
        params: Sequence[Any],
    ) -> list[dict[str, Any]]:
        rows = [
            row for row in self.summary_invocations.values() if row["tenant_id"] == str(params[0])
        ]
        param_index = 1
        for column in (
            "score_run_id",
            "review_action_id",
            "policy_id",
            "as_of_date",
            "invocation_state",
        ):
            if f"{column} = %s" in normalized:
                rows = [row for row in rows if row[column] == str(params[param_index])]
                param_index += 1
        rows.sort(
            key=lambda row: (row["generated_at"], row["summary_invocation_id"]),
            reverse=True,
        )
        limit = int(params[-2])
        offset = int(params[-1])
        return rows[offset : offset + limit]

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def _parent_evidence_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "content_hash": row["content_hash"],
        "policy_id": row["policy_id"],
        "policy_version": row["policy_version"],
        "as_of_date": row["as_of_date"],
        "state": row["state"],
    }


def _review_action_parent_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "content_hash": row["content_hash"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "policy_id": row["policy_id"],
        "policy_version": row["policy_version"],
        "as_of_date": row["as_of_date"],
    }


def _seed_score_run_parent(
    connection: _FakePolicyConnection,
    score_run: Any,
) -> None:
    connection.score_runs[(score_run.tenant_id, score_run.score_run_id)] = {
        "tenant_id": score_run.tenant_id,
        "score_run_id": score_run.score_run_id,
        "pm_id": score_run.pm_id,
        "book_id": score_run.book_id,
        "policy_id": score_run.policy_id,
        "policy_version": score_run.policy_version,
        "as_of_date": score_run.as_of_date,
        "state": score_run.state,
        "content_hash": score_run.content_hash,
        "generated_at": score_run.generated_at.isoformat(),
        "payload_json": score_run.model_dump(mode="json"),
    }


def _seed_fairness_analysis_parent(
    connection: _FakePolicyConnection,
    analysis: Any,
) -> None:
    connection.fairness_analyses[(analysis.tenant_id, analysis.fairness_analysis_id)] = {
        "tenant_id": analysis.tenant_id,
        "fairness_analysis_id": analysis.fairness_analysis_id,
        "policy_id": analysis.policy_id,
        "policy_version": analysis.policy_version,
        "as_of_date": analysis.as_of_date,
        "state": analysis.state,
        "content_hash": analysis.content_hash,
        "generated_at": analysis.generated_at.isoformat(),
        "payload_json": analysis.model_dump(mode="json"),
    }


def _seed_review_action_parent(
    connection: _FakePolicyConnection,
    action: Any,
) -> None:
    connection.review_actions[(action.tenant_id, action.review_action_id)] = {
        "tenant_id": action.tenant_id,
        "review_action_id": action.review_action_id,
        "review_action_ref": action.review_action_ref,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "policy_id": action.policy_id,
        "policy_version": action.policy_version,
        "as_of_date": action.as_of_date,
        "target_state": action.target_state,
        "action_type": action.action_type,
        "action_state": action.action_state,
        "content_hash": action.content_hash,
        "generated_at": action.generated_at.isoformat(),
        "actor_id": action.actor_id,
        "payload_json": action.model_dump(mode="json"),
    }


@pytest.fixture
def fake_postgres_policy_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmPmQualityPolicyRepository, _FakePolicyConnection]:
    connection = _FakePolicyConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmPmQualityPolicyRepository(dsn="postgresql://unit-test"), connection


@pytest.fixture
def fake_postgres_score_run_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmPmQualityScoreRunRepository, _FakePolicyConnection]:
    connection = _FakePolicyConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmPmQualityScoreRunRepository(dsn="postgresql://unit-test"), connection


@pytest.fixture
def fake_postgres_fairness_analysis_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmPmQualityFairnessAnalysisRepository, _FakePolicyConnection]:
    connection = _FakePolicyConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmPmQualityFairnessAnalysisRepository(dsn="postgresql://unit-test"), connection


@pytest.fixture
def fake_postgres_review_action_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmPmQualityReviewActionRepository, _FakePolicyConnection]:
    connection = _FakePolicyConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmPmQualityReviewActionRepository(dsn="postgresql://unit-test"), connection


@pytest.fixture
def fake_postgres_summary_invocation_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[PostgresDpmPmQualitySummaryInvocationRepository, _FakePolicyConnection]:
    connection = _FakePolicyConnection()
    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: True)
    monkeypatch.setattr(postgres_module, "apply_postgres_migrations", lambda **_: None)
    monkeypatch.setattr(
        postgres_module,
        "_import_psycopg",
        lambda: (type("Psycopg", (), {"connect": lambda *_, **__: connection}), object()),
    )
    return PostgresDpmPmQualitySummaryInvocationRepository(dsn="postgresql://unit-test"), connection


def test_in_memory_pm_quality_repository_persists_immutable_policies() -> None:
    repository = InMemoryDpmPmQualityPolicyRepository()
    policy = _policy()

    repository.save_policy(tenant_id=TENANT_ID, policy=policy)
    repository.save_policy(tenant_id=TENANT_ID, policy=policy)

    stored = repository.get_policy(
        tenant_id=TENANT_ID,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
    )
    assert stored == policy

    changed = policy.model_copy(update={"ready_threshold": Decimal("90")})
    with pytest.raises(DpmPmQualityPolicyConflictError):
        repository.save_policy(tenant_id=TENANT_ID, policy=changed)


def test_in_memory_pm_quality_repository_lists_policy_versions() -> None:
    repository = InMemoryDpmPmQualityPolicyRepository()
    enabled = _policy(policy_id="pmq_enabled", enabled=True)
    disabled = _policy(policy_id="pmq_disabled", enabled=False)
    repository.save_policy(tenant_id=TENANT_ID, policy=enabled)
    repository.save_policy(tenant_id=TENANT_ID, policy=disabled)

    assert repository.list_policies(tenant_id=TENANT_ID, policy_id="pmq_enabled") == [enabled]
    assert repository.list_policies(tenant_id=TENANT_ID, enabled=False) == [disabled]
    assert repository.list_policies(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_policies(tenant_id=TENANT_ID, limit=1, offset=1) == [disabled]


def test_in_memory_pm_quality_repositories_scope_records_by_tenant() -> None:
    policy_repository = InMemoryDpmPmQualityPolicyRepository()
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    policy = _policy()
    other_policy = policy.model_copy(update={"tenant_id": TENANT_OTHER})
    score_run = _score_run()
    other_score_run = score_run.model_copy(
        update={
            "tenant_id": TENANT_OTHER,
            "content_hash": "sha256:tenant-other-score-run",
        }
    )

    policy_repository.save_policy(tenant_id=TENANT_ID, policy=policy)
    policy_repository.save_policy(tenant_id=TENANT_OTHER, policy=other_policy)
    score_run_repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)
    score_run_repository.save_score_run(tenant_id=TENANT_OTHER, score_run=other_score_run)

    assert (
        policy_repository.get_policy(
            tenant_id=TENANT_ID,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
        )
        == policy
    )
    assert (
        policy_repository.get_policy(
            tenant_id=TENANT_OTHER,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
        )
        == other_policy
    )
    assert (
        score_run_repository.get_score_run(
            tenant_id=TENANT_ID,
            score_run_id=score_run.score_run_id,
        )
        == score_run
    )
    assert (
        score_run_repository.get_score_run(
            tenant_id=TENANT_OTHER,
            score_run_id=score_run.score_run_id,
        )
        == other_score_run
    )
    assert policy_repository.list_policies(tenant_id=TENANT_ID) == [policy]
    assert policy_repository.list_policies(tenant_id=TENANT_OTHER) == [other_policy]
    assert score_run_repository.list_score_runs(tenant_id=TENANT_ID) == [score_run]
    assert score_run_repository.list_score_runs(tenant_id=TENANT_OTHER) == [other_score_run]


def test_in_memory_pm_quality_parent_validation_does_not_cross_tenants() -> None:
    score_run_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_action_repository = InMemoryDpmPmQualityReviewActionRepository(
        score_run_repository=score_run_repository,
    )
    score_run = _score_run()
    score_run_repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)
    action = build_pm_quality_review_action(
        target=score_run,
        target_type="SCORE_RUN",
        action_type="ACKNOWLEDGE",
        review_action_ref="PMQ-REVIEW-2026-05-XTENANT",
        review_reason="Cross-tenant parent validation must fail closed.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-cross-tenant-parent",
    ).model_copy(update={"tenant_id": TENANT_OTHER})

    with pytest.raises(DpmPmQualityReviewActionIntegrityError):
        review_action_repository.save_review_action(tenant_id=TENANT_OTHER, action=action)


def test_pm_quality_policy_list_helpers_filter_sort_and_page_results() -> None:
    enabled = _policy(policy_id="pmq_enabled", enabled=True)
    newer_enabled = enabled.model_copy(
        update={
            "policy_id": "pmq_enabled_newer",
            "as_of_date": "2026-05-13",
        }
    )
    disabled = _policy(policy_id="pmq_disabled", enabled=False)
    filters = _PolicyFilters(policy_id=None, enabled=True, as_of_date=None)

    assert _optional_bool_matches(enabled.enabled, True)
    assert _optional_bool_matches(disabled.enabled, None)
    assert not _optional_bool_matches(disabled.enabled, True)
    assert _policy_matches_filters(enabled, filters)
    assert not _policy_matches_filters(disabled, filters)
    assert _sort_policies([enabled, newer_enabled]) == [newer_enabled, enabled]
    assert _list_policies(
        policies=[enabled, newer_enabled, disabled],
        filters=filters,
        limit=1,
        offset=0,
    ) == [newer_enabled]
    assert _list_policies(
        policies=[enabled, newer_enabled, disabled],
        filters=filters,
        limit=1,
        offset=1,
    ) == [enabled]


def test_postgres_pm_quality_policy_repository_round_trips_policy_versions(
    fake_postgres_policy_repository: tuple[
        PostgresDpmPmQualityPolicyRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_policy_repository
    enabled = _policy(policy_id="pmq_enabled", enabled=True)
    disabled = _policy(policy_id="pmq_disabled", enabled=False)

    repository.save_policy(tenant_id=TENANT_ID, policy=enabled)
    repository.save_policy(tenant_id=TENANT_ID, policy=disabled)
    repository.save_policy(tenant_id=TENANT_ID, policy=enabled)

    assert (
        repository.get_policy(
            tenant_id=TENANT_ID,
            policy_id=enabled.policy_id,
            policy_version=enabled.policy_version,
        )
        == enabled
    )
    assert (
        repository.get_policy(tenant_id=TENANT_ID, policy_id="missing", policy_version="2026.05")
        is None
    )
    assert repository.list_policies(tenant_id=TENANT_ID, policy_id="pmq_enabled") == [enabled]
    assert repository.list_policies(tenant_id=TENANT_ID, enabled=False) == [disabled]
    assert repository.list_policies(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_policies(tenant_id=TENANT_ID, limit=1, offset=1) == [disabled]
    assert connection.commits == 3


def test_postgres_pm_quality_policy_repository_conflict_and_configuration_paths(
    fake_postgres_policy_repository: tuple[
        PostgresDpmPmQualityPolicyRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_policy_repository
    policy = _policy()
    repository.save_policy(tenant_id=TENANT_ID, policy=policy)

    changed = policy.model_copy(update={"ready_threshold": Decimal("90")})
    with pytest.raises(DpmPmQualityPolicyConflictError, match="IMMUTABLE"):
        repository.save_policy(tenant_id=TENANT_ID, policy=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityPolicyRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityPolicyRepository(dsn="postgresql://unit-test")


def test_postgres_pm_quality_score_run_repository_round_trips_score_runs(
    fake_postgres_score_run_repository: tuple[
        PostgresDpmPmQualityScoreRunRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_score_run_repository
    score_run = _score_run(pm_id="pm_001", policy_id="pmq_sg_dpm")
    other = _score_run(pm_id="pm_002", policy_id="pmq_other")

    repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)
    repository.save_score_run(tenant_id=TENANT_ID, score_run=other)
    repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)

    assert (
        repository.get_score_run(tenant_id=TENANT_ID, score_run_id=score_run.score_run_id)
        == score_run
    )
    assert repository.get_score_run(tenant_id=TENANT_ID, score_run_id="missing") is None
    assert repository.list_score_runs(tenant_id=TENANT_ID, pm_id="pm_001") == [score_run]
    assert repository.list_score_runs(tenant_id=TENANT_ID, book_id="missing") == []
    assert repository.list_score_runs(tenant_id=TENANT_ID, policy_id="pmq_other") == [other]
    assert repository.list_score_runs(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert (
        len(
            repository.list_score_runs(
                tenant_id=TENANT_ID, state=score_run.state, limit=1, offset=1
            )
        )
        == 1
    )
    assert connection.commits == 3


def test_postgres_pm_quality_score_run_repository_conflict_and_configuration_paths(
    fake_postgres_score_run_repository: tuple[
        PostgresDpmPmQualityScoreRunRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_score_run_repository
    score_run = _score_run()
    repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)

    changed = score_run.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityScoreRunConflictError, match="IMMUTABLE"):
        repository.save_score_run(tenant_id=TENANT_ID, score_run=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityScoreRunRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityScoreRunRepository(dsn="postgresql://unit-test")


def test_in_memory_pm_quality_repository_persists_immutable_fairness_analyses() -> None:
    repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    analysis = _fairness_analysis()

    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)
    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)

    stored = repository.get_fairness_analysis(
        tenant_id=TENANT_ID,
        fairness_analysis_id=analysis.fairness_analysis_id,
    )
    assert stored == analysis

    changed = analysis.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityFairnessAnalysisConflictError):
        repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=changed)


def test_in_memory_pm_quality_repository_lists_fairness_analyses() -> None:
    repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    analysis = _fairness_analysis()
    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)

    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [
        analysis
    ]
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, policy_version="2026.05") == [
        analysis
    ]
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, state=analysis.state) == [
        analysis
    ]
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, limit=1, offset=1) == []


def test_fairness_analysis_filter_helper_matches_all_optional_fields() -> None:
    analysis = _fairness_analysis()

    assert _fairness_analysis_matches_filters(
        analysis,
        _FairnessAnalysisFilters(
            policy_id=analysis.policy_id,
            policy_version=analysis.policy_version,
            as_of_date=analysis.as_of_date,
            state=analysis.state,
        ),
    )
    assert not _fairness_analysis_matches_filters(
        analysis,
        _FairnessAnalysisFilters(
            policy_id=None,
            policy_version="missing",
            as_of_date=None,
            state=None,
        ),
    )


def test_fairness_analysis_list_helper_filters_sorts_and_pages() -> None:
    older = _fairness_analysis()
    newer = older.model_copy(
        update={
            "fairness_analysis_id": "pmq_fairness_newer",
            "generated_at": older.generated_at + timedelta(minutes=1),
            "content_hash": "sha256:fairness-newer",
        }
    )
    unrelated = older.model_copy(
        update={
            "fairness_analysis_id": "pmq_fairness_unrelated",
            "policy_version": "2026.04",
            "generated_at": older.generated_at + timedelta(minutes=2),
            "content_hash": "sha256:fairness-unrelated",
        }
    )
    filters = _FairnessAnalysisFilters(
        policy_id=older.policy_id,
        policy_version=older.policy_version,
        as_of_date=older.as_of_date,
        state=older.state,
    )

    assert _sort_fairness_analyses([older, newer]) == [newer, older]
    assert _list_fairness_analyses(
        analyses=[older, newer, unrelated],
        filters=filters,
        limit=1,
        offset=0,
    ) == [newer]
    assert _list_fairness_analyses(
        analyses=[older, newer, unrelated],
        filters=filters,
        limit=1,
        offset=1,
    ) == [older]


def test_postgres_pm_quality_fairness_analysis_repository_round_trips_analyses(
    fake_postgres_fairness_analysis_repository: tuple[
        PostgresDpmPmQualityFairnessAnalysisRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_fairness_analysis_repository
    analysis = _fairness_analysis()

    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)
    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)

    assert (
        repository.get_fairness_analysis(
            tenant_id=TENANT_ID,
            fairness_analysis_id=analysis.fairness_analysis_id,
        )
        == analysis
    )
    assert (
        repository.get_fairness_analysis(tenant_id=TENANT_ID, fairness_analysis_id="missing")
        is None
    )
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [
        analysis
    ]
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, policy_version="2026.05") == [
        analysis
    ]
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_fairness_analyses(tenant_id=TENANT_ID, state=analysis.state) == [
        analysis
    ]
    assert connection.commits == 2


def test_postgres_pm_quality_fairness_analysis_repository_conflict_and_configuration_paths(
    fake_postgres_fairness_analysis_repository: tuple[
        PostgresDpmPmQualityFairnessAnalysisRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_fairness_analysis_repository
    analysis = _fairness_analysis()
    repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=analysis)

    changed = analysis.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityFairnessAnalysisConflictError, match="IMMUTABLE"):
        repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityFairnessAnalysisRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityFairnessAnalysisRepository(dsn="postgresql://unit-test")


def test_in_memory_pm_quality_repository_persists_immutable_review_actions() -> None:
    repository = InMemoryDpmPmQualityReviewActionRepository()
    action = _review_action()

    repository.save_review_action(tenant_id=TENANT_ID, action=action)
    repository.save_review_action(tenant_id=TENANT_ID, action=action)

    stored = repository.get_review_action(
        tenant_id=TENANT_ID, review_action_id=action.review_action_id
    )
    assert stored == action

    changed = action.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityReviewActionConflictError):
        repository.save_review_action(tenant_id=TENANT_ID, action=changed)


def test_in_memory_pm_quality_repository_validates_review_action_parents() -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    fairness_repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    repository = InMemoryDpmPmQualityReviewActionRepository(
        score_run_repository=score_repository,
        fairness_analysis_repository=fairness_repository,
    )
    score_action = _review_action()

    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_NOT_FOUND"):
        repository.save_review_action(tenant_id=TENANT_ID, action=score_action)

    score_repository.save_score_run(tenant_id=TENANT_ID, score_run=_score_run())
    changed_score_action = score_action.model_copy(update={"target_content_hash": "sha256:stale"})
    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_MISMATCH"):
        repository.save_review_action(tenant_id=TENANT_ID, action=changed_score_action)

    repository.save_review_action(tenant_id=TENANT_ID, action=score_action)
    repository.save_review_action(tenant_id=TENANT_ID, action=score_action)

    fairness_analysis = _fairness_analysis()
    fairness_action = build_pm_quality_review_action(
        target=fairness_analysis,
        target_type="FAIRNESS_ANALYSIS",
        action_type="ESCALATE_MODEL_RISK_REVIEW",
        review_action_ref="PMQ-FAIRNESS-REVIEW-2026-05-001",
        review_reason="Escalated for governed fairness review.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-fairness-review",
    )
    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_NOT_FOUND"):
        repository.save_review_action(tenant_id=TENANT_ID, action=fairness_action)

    fairness_repository.save_fairness_analysis(tenant_id=TENANT_ID, analysis=fairness_analysis)
    repository.save_review_action(tenant_id=TENANT_ID, action=fairness_action)


def test_in_memory_pm_quality_repository_lists_review_actions() -> None:
    repository = InMemoryDpmPmQualityReviewActionRepository()
    action = _review_action()
    repository.save_review_action(tenant_id=TENANT_ID, action=action)

    assert repository.list_review_actions(tenant_id=TENANT_ID, target_type="SCORE_RUN") == [action]
    assert repository.list_review_actions(tenant_id=TENANT_ID, target_id=action.target_id) == [
        action
    ]
    assert repository.list_review_actions(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [action]
    assert repository.list_review_actions(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_review_actions(
        tenant_id=TENANT_ID, action_state=action.action_state
    ) == [action]
    assert repository.list_review_actions(tenant_id=TENANT_ID, limit=1, offset=1) == []


def test_score_run_filter_helper_matches_all_optional_fields() -> None:
    score_run = _score_run()

    assert _score_run_matches_filters(
        score_run,
        _ScoreRunFilters(
            pm_id=score_run.pm_id,
            book_id=score_run.book_id,
            policy_id=score_run.policy_id,
            as_of_date=score_run.as_of_date,
            state=score_run.state,
        ),
    )
    assert not _score_run_matches_filters(
        score_run,
        _ScoreRunFilters(
            pm_id="missing",
            book_id=None,
            policy_id=None,
            as_of_date=None,
            state=None,
        ),
    )


def test_score_run_list_helper_filters_sorts_and_pages() -> None:
    older = _score_run(pm_id="pm_001", policy_id="pmq_sg_dpm")
    newer = older.model_copy(
        update={
            "score_run_id": "pmq_score_newer",
            "pm_id": "pm_002",
            "generated_at": older.generated_at + timedelta(minutes=1),
            "content_hash": "sha256:score-newer",
        }
    )
    filters = _ScoreRunFilters(
        pm_id=None,
        book_id=older.book_id,
        policy_id=older.policy_id,
        as_of_date=older.as_of_date,
        state=older.state,
    )

    assert _sort_score_runs([older, newer]) == [newer, older]
    assert _list_score_runs(
        score_runs=[older, newer],
        filters=filters,
        limit=1,
        offset=0,
    ) == [newer]
    assert _list_score_runs(
        score_runs=[older, newer],
        filters=filters,
        limit=1,
        offset=1,
    ) == [older]


def test_review_action_filter_helper_matches_all_optional_fields() -> None:
    action = _review_action()

    assert _review_action_matches_filters(
        action,
        _ReviewActionFilters(
            target_type=action.target_type,
            target_id=action.target_id,
            policy_id=action.policy_id,
            as_of_date=action.as_of_date,
            action_state=action.action_state,
        ),
    )
    assert not _review_action_matches_filters(
        action,
        _ReviewActionFilters(
            target_type="MISSING",
            target_id=None,
            policy_id=None,
            as_of_date=None,
            action_state=None,
        ),
    )


def test_review_action_list_helper_filters_sorts_and_pages() -> None:
    older = _review_action()
    newer = older.model_copy(
        update={
            "review_action_id": "pmq_review_action_newer",
            "target_id": "pmq_score_newer",
            "generated_at": older.generated_at + timedelta(minutes=1),
            "content_hash": "sha256:review-action-newer",
        }
    )
    filters = _ReviewActionFilters(
        target_type=older.target_type,
        target_id=None,
        policy_id=older.policy_id,
        as_of_date=older.as_of_date,
        action_state=older.action_state,
    )

    assert _sort_review_actions([older, newer]) == [newer, older]
    assert _list_review_actions(
        actions=[older, newer],
        filters=filters,
        limit=1,
        offset=0,
    ) == [newer]
    assert _list_review_actions(
        actions=[older, newer],
        filters=filters,
        limit=1,
        offset=1,
    ) == [older]


def test_in_memory_pm_quality_repository_persists_immutable_summary_invocations() -> None:
    repository = InMemoryDpmPmQualitySummaryInvocationRepository()
    invocation = _summary_invocation()

    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    stored = repository.get_summary_invocation(
        tenant_id=TENANT_ID, summary_invocation_id=invocation.summary_invocation_id
    )
    assert stored == invocation

    changed = invocation.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualitySummaryInvocationConflictError):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed)


def test_in_memory_pm_quality_repository_validates_summary_invocation_parents() -> None:
    score_repository = InMemoryDpmPmQualityScoreRunRepository()
    review_repository = InMemoryDpmPmQualityReviewActionRepository(
        score_run_repository=score_repository
    )
    repository = InMemoryDpmPmQualitySummaryInvocationRepository(
        score_run_repository=score_repository,
        review_action_repository=review_repository,
    )
    score_run, review_action, invocation = _summary_invocation_with_parents()

    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="SCORE_RUN_NOT_FOUND",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    score_repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="REVIEW_ACTION_NOT_FOUND",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    review_repository.save_review_action(tenant_id=TENANT_ID, action=review_action)
    changed_score_hash = invocation.model_copy(
        update={"score_run_content_hash": "sha256:stale-score"}
    )
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="SCORE_RUN_MISMATCH",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed_score_hash)

    changed_review_hash = invocation.model_copy(
        update={"review_action_content_hash": "sha256:stale-review"}
    )
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="REVIEW_ACTION_MISMATCH",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed_review_hash)

    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)


def test_in_memory_pm_quality_repository_lists_summary_invocations() -> None:
    repository = InMemoryDpmPmQualitySummaryInvocationRepository()
    invocation = _summary_invocation()
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        score_run_id=invocation.score_run_id,
    ) == [invocation]
    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        review_action_id=invocation.review_action_id,
    ) == [invocation]
    assert repository.list_summary_invocations(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [
        invocation
    ]
    assert repository.list_summary_invocations(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        invocation_state=invocation.invocation_state,
    ) == [invocation]
    assert repository.list_summary_invocations(tenant_id=TENANT_ID, limit=1, offset=1) == []


def test_summary_invocation_filter_helper_matches_all_optional_fields() -> None:
    invocation = _summary_invocation()

    assert _summary_invocation_matches_filters(
        invocation,
        _SummaryInvocationFilters(
            score_run_id=invocation.score_run_id,
            review_action_id=invocation.review_action_id,
            policy_id=invocation.policy_id,
            as_of_date=invocation.as_of_date,
            invocation_state=invocation.invocation_state,
        ),
    )
    assert not _summary_invocation_matches_filters(
        invocation,
        _SummaryInvocationFilters(
            score_run_id="missing",
            review_action_id=None,
            policy_id=None,
            as_of_date=None,
            invocation_state=None,
        ),
    )


def test_summary_invocation_list_helper_filters_sorts_and_pages() -> None:
    older = _summary_invocation()
    newer = older.model_copy(
        update={
            "summary_invocation_id": "pmq_summary_newer",
            "score_run_id": "score_run_other",
            "generated_at": older.generated_at + timedelta(minutes=1),
            "content_hash": "sha256:summary-newer",
        }
    )
    filters = _SummaryInvocationFilters(
        score_run_id=None,
        review_action_id=None,
        policy_id=older.policy_id,
        as_of_date=older.as_of_date,
        invocation_state=older.invocation_state,
    )

    assert _sort_summary_invocations([older, newer]) == [newer, older]
    assert _list_summary_invocations(
        invocations=[older, newer],
        filters=filters,
        limit=1,
        offset=0,
    ) == [newer]
    assert _list_summary_invocations(
        invocations=[older, newer],
        filters=filters,
        limit=1,
        offset=1,
    ) == [older]


def test_postgres_pm_quality_review_action_repository_round_trips_actions(
    fake_postgres_review_action_repository: tuple[
        PostgresDpmPmQualityReviewActionRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_review_action_repository
    action = _review_action()
    _seed_score_run_parent(connection, _score_run())

    repository.save_review_action(tenant_id=TENANT_ID, action=action)
    repository.save_review_action(tenant_id=TENANT_ID, action=action)

    assert (
        repository.get_review_action(tenant_id=TENANT_ID, review_action_id=action.review_action_id)
        == action
    )
    assert repository.get_review_action(tenant_id=TENANT_ID, review_action_id="missing") is None
    assert repository.list_review_actions(tenant_id=TENANT_ID, target_type="SCORE_RUN") == [action]
    assert repository.list_review_actions(tenant_id=TENANT_ID, target_id=action.target_id) == [
        action
    ]
    assert repository.list_review_actions(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [action]
    assert repository.list_review_actions(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_review_actions(
        tenant_id=TENANT_ID, action_state=action.action_state
    ) == [action]
    assert connection.commits == 2


def test_postgres_pm_quality_review_action_repository_validates_parent_lineage(
    fake_postgres_review_action_repository: tuple[
        PostgresDpmPmQualityReviewActionRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_review_action_repository
    score_action = _review_action()

    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_NOT_FOUND"):
        repository.save_review_action(tenant_id=TENANT_ID, action=score_action)

    _seed_score_run_parent(connection, _score_run())
    changed_score_action = score_action.model_copy(update={"target_content_hash": "sha256:stale"})
    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_MISMATCH"):
        repository.save_review_action(tenant_id=TENANT_ID, action=changed_score_action)

    repository.save_review_action(tenant_id=TENANT_ID, action=score_action)

    fairness_analysis = _fairness_analysis()
    fairness_action = build_pm_quality_review_action(
        target=fairness_analysis,
        target_type="FAIRNESS_ANALYSIS",
        action_type="ESCALATE_MODEL_RISK_REVIEW",
        review_action_ref="PMQ-FAIRNESS-REVIEW-2026-05-001",
        review_reason="Escalated for governed fairness review.",
        actor_id="ops",
        source_refs=[],
        remediation_due_date=None,
        correlation_id="corr-fairness-review",
    )
    with pytest.raises(DpmPmQualityReviewActionIntegrityError, match="TARGET_NOT_FOUND"):
        repository.save_review_action(tenant_id=TENANT_ID, action=fairness_action)

    _seed_fairness_analysis_parent(connection, fairness_analysis)
    repository.save_review_action(tenant_id=TENANT_ID, action=fairness_action)


def test_postgres_pm_quality_summary_invocation_repository_round_trips_invocations(
    fake_postgres_summary_invocation_repository: tuple[
        PostgresDpmPmQualitySummaryInvocationRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_summary_invocation_repository
    score_run, review_action, invocation = _summary_invocation_with_parents()
    _seed_score_run_parent(connection, score_run)
    _seed_review_action_parent(connection, review_action)

    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    assert (
        repository.get_summary_invocation(
            tenant_id=TENANT_ID,
            summary_invocation_id=invocation.summary_invocation_id,
        )
        == invocation
    )
    assert (
        repository.get_summary_invocation(tenant_id=TENANT_ID, summary_invocation_id="missing")
        is None
    )
    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        score_run_id=invocation.score_run_id,
    ) == [invocation]
    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        review_action_id=invocation.review_action_id,
    ) == [invocation]
    assert repository.list_summary_invocations(tenant_id=TENANT_ID, policy_id="pmq_sg_dpm") == [
        invocation
    ]
    assert repository.list_summary_invocations(tenant_id=TENANT_ID, as_of_date="missing") == []
    assert repository.list_summary_invocations(
        tenant_id=TENANT_ID,
        invocation_state=invocation.invocation_state,
    ) == [invocation]
    assert connection.commits == 2


def test_postgres_pm_quality_summary_invocation_repository_validates_parent_lineage(
    fake_postgres_summary_invocation_repository: tuple[
        PostgresDpmPmQualitySummaryInvocationRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_summary_invocation_repository
    score_run, review_action, invocation = _summary_invocation_with_parents()

    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="SCORE_RUN_NOT_FOUND",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    _seed_score_run_parent(connection, score_run)
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="REVIEW_ACTION_NOT_FOUND",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    _seed_review_action_parent(connection, review_action)
    changed_score_hash = invocation.model_copy(
        update={"score_run_content_hash": "sha256:stale-score"}
    )
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="SCORE_RUN_MISMATCH",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed_score_hash)

    changed_review_hash = invocation.model_copy(
        update={"review_action_content_hash": "sha256:stale-review"}
    )
    with pytest.raises(
        DpmPmQualitySummaryInvocationIntegrityError,
        match="REVIEW_ACTION_MISMATCH",
    ):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed_review_hash)

    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)


def test_postgres_pm_quality_review_action_repository_conflict_and_configuration_paths(
    fake_postgres_review_action_repository: tuple[
        PostgresDpmPmQualityReviewActionRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_review_action_repository
    action = _review_action()
    _seed_score_run_parent(connection, _score_run())
    repository.save_review_action(tenant_id=TENANT_ID, action=action)

    changed = action.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityReviewActionConflictError, match="IMMUTABLE"):
        repository.save_review_action(tenant_id=TENANT_ID, action=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityReviewActionRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityReviewActionRepository(dsn="postgresql://unit-test")


def test_postgres_pm_quality_summary_invocation_repository_conflict_and_configuration_paths(
    fake_postgres_summary_invocation_repository: tuple[
        PostgresDpmPmQualitySummaryInvocationRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_summary_invocation_repository
    score_run, review_action, invocation = _summary_invocation_with_parents()
    _seed_score_run_parent(connection, score_run)
    _seed_review_action_parent(connection, review_action)
    repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=invocation)

    changed = invocation.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualitySummaryInvocationConflictError, match="IMMUTABLE"):
        repository.save_summary_invocation(tenant_id=TENANT_ID, invocation=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualitySummaryInvocationRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualitySummaryInvocationRepository(dsn="postgresql://unit-test")


def test_pm_quality_postgres_helpers_normalize_payloads_and_import_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_psycopg = ModuleType("psycopg")
    fake_rows = ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)

    psycopg_module, dict_row = postgres_module._import_psycopg()

    assert psycopg_module is fake_psycopg
    assert dict_row is fake_rows.dict_row
    assert postgres_module._payload({"payload_json": {"a": 1}}) == {"a": 1}
    assert postgres_module._payload({"payload_json": 3}) == "3"
    assert postgres_module._payload({"payload_json": '{"a":1}'}) == '{"a":1}'


def test_pm_quality_lineage_integrity_migration_declares_restrictive_summary_parents() -> None:
    migration = (
        ROOT
        / "src"
        / "infrastructure"
        / "postgres_migrations"
        / "dpm"
        / "0016_pm_quality_lineage_integrity.sql"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "fk_pm_quality_summary_invocations_score_run",
        "REFERENCES dpm_pm_quality_score_runs(score_run_id)",
        "fk_pm_quality_summary_invocations_review_action",
        "REFERENCES dpm_pm_quality_review_actions(review_action_id)",
        "ON DELETE RESTRICT",
    ]
    assert [token for token in required_tokens if token not in migration] == []


def test_pm_quality_tenant_scope_migration_declares_composite_tenant_keys() -> None:
    migration = (
        ROOT
        / "src"
        / "infrastructure"
        / "postgres_migrations"
        / "dpm"
        / "0017_pm_quality_tenant_scope.sql"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "ADD COLUMN IF NOT EXISTS tenant_id TEXT",
        "PRIMARY KEY (tenant_id, score_run_id)",
        "PRIMARY KEY (tenant_id, policy_id, policy_version)",
        "PRIMARY KEY (tenant_id, fairness_analysis_id)",
        "PRIMARY KEY (tenant_id, review_action_id)",
        "PRIMARY KEY (tenant_id, summary_invocation_id)",
        "FOREIGN KEY (tenant_id, score_run_id)",
        "FOREIGN KEY (tenant_id, review_action_id)",
    ]
    assert [token for token in required_tokens if token not in migration] == []


def test_pm_quality_tenant_scope_migration_backfills_payload_tenant_ids() -> None:
    migration = (
        ROOT
        / "src"
        / "infrastructure"
        / "postgres_migrations"
        / "dpm"
        / "0017_pm_quality_tenant_scope.sql"
    ).read_text(encoding="utf-8")

    column_backfill = (
        "SET tenant_id = COALESCE(NULLIF(payload_json::jsonb ->> 'tenant_id', ''), "
        "'legacy-default')"
    )
    payload_backfill = (
        "SET payload_json = jsonb_set(payload_json::jsonb, '{tenant_id}', "
        "to_jsonb(tenant_id), true)::text"
    )

    assert migration.count(column_backfill) == 5
    assert migration.count(payload_backfill) == 5


def test_in_memory_pm_quality_repository_persists_immutable_score_runs() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run()

    repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)
    repository.save_score_run(tenant_id=TENANT_ID, score_run=score_run)

    stored = repository.get_score_run(tenant_id=TENANT_ID, score_run_id=score_run.score_run_id)
    assert stored == score_run

    changed = score_run.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityScoreRunConflictError):
        repository.save_score_run(tenant_id=TENANT_ID, score_run=changed)


def test_in_memory_pm_quality_repository_lists_with_bounded_filters() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    first = _score_run(pm_id="pm_001", policy_id="pmq_sg_dpm")
    second = _score_run(pm_id="pm_002", policy_id="pmq_hk_dpm")
    repository.save_score_run(tenant_id=TENANT_ID, score_run=first)
    repository.save_score_run(tenant_id=TENANT_ID, score_run=second)

    assert repository.list_score_runs(tenant_id=TENANT_ID, pm_id="pm_001") == [first]
    assert repository.list_score_runs(tenant_id=TENANT_ID, policy_id="pmq_hk_dpm") == [second]
    assert repository.list_score_runs(tenant_id=TENANT_ID, book_id="missing") == []
    assert repository.list_score_runs(tenant_id=TENANT_ID, limit=1, offset=1) == [first]
