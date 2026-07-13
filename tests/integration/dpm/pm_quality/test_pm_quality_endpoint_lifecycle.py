from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

import src.api.dependencies as dependencies
from src.api.main import app
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.pm_quality import postgres as pm_quality_postgres


PM_QUALITY_POSTGRES_SINGLETONS = (
    "_POSTGRES_PM_QUALITY_POLICY_REPOSITORY",
    "_POSTGRES_PM_QUALITY_SCORE_RUN_REPOSITORY",
    "_POSTGRES_PM_QUALITY_FAIRNESS_ANALYSIS_REPOSITORY",
    "_POSTGRES_PM_QUALITY_REVIEW_ACTION_REPOSITORY",
    "_POSTGRES_PM_QUALITY_SUMMARY_INVOCATION_REPOSITORY",
    "_POSTGRES_OUTCOME_REVIEW_REPOSITORY",
)


class _FakeCursor:
    def __init__(
        self,
        row: dict[str, Any] | None = None,
        rows: list[dict[str, Any]] | None = None,
    ) -> None:
        self._row = row
        self._rows = rows or ([] if row is None else [row])

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _PmQualityPostgresConnection:
    def __init__(self) -> None:
        self.score_runs: dict[str, dict[str, Any]] = {}
        self.policies: dict[tuple[str, str], dict[str, Any]] = {}
        self.fairness_analyses: dict[str, dict[str, Any]] = {}
        self.review_actions: dict[str, dict[str, Any]] = {}
        self.summary_invocations: dict[str, dict[str, Any]] = {}
        self.commits = 0
        self.rollbacks = 0

    def execute(self, query: str, params: Sequence[Any] = ()) -> _FakeCursor:
        normalized = " ".join(query.split())
        if normalized.startswith("INSERT INTO dpm_pm_quality_policies"):
            key = (str(params[0]), str(params[1]))
            self.policies.setdefault(
                key,
                {
                    "policy_id": str(params[0]),
                    "policy_version": str(params[1]),
                    "enabled": bool(params[2]),
                    "as_of_date": str(params[3]),
                    "content_hash": str(params[5]),
                    "payload_json": json.loads(str(params[6])),
                },
            )
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_policies"):
            row = self.policies.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_policies WHERE"):
            if "policy_version = %s" in normalized and "LIMIT" not in normalized:
                return _FakeCursor(self.policies.get((str(params[0]), str(params[1]))))
            return _FakeCursor(
                rows=self._filtered_rows(
                    rows=list(self.policies.values()),
                    normalized=normalized,
                    params=params,
                    filter_columns=("policy_id", "enabled", "as_of_date"),
                    sort_columns=("as_of_date", "policy_id", "policy_version"),
                )
            )
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_policies"):
            return _FakeCursor(
                rows=self._page_rows(
                    rows=list(self.policies.values()),
                    params=params,
                    sort_columns=("as_of_date", "policy_id", "policy_version"),
                )
            )

        if normalized.startswith("INSERT INTO dpm_pm_quality_score_runs"):
            self.score_runs.setdefault(
                str(params[0]),
                {
                    "score_run_id": str(params[0]),
                    "pm_id": str(params[1]),
                    "book_id": str(params[2]),
                    "policy_id": str(params[3]),
                    "policy_version": str(params[4]),
                    "as_of_date": str(params[5]),
                    "state": str(params[6]),
                    "content_hash": str(params[8]),
                    "generated_at": str(params[9]),
                    "payload_json": json.loads(str(params[12])),
                },
            )
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_score_runs"):
            row = self.score_runs.get(str(params[0]))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_score_runs WHERE")
            and "score_run_id = %s" in normalized
        ):
            return _FakeCursor(self.score_runs.get(str(params[0])))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_score_runs"):
            return _FakeCursor(
                rows=self._filtered_rows(
                    rows=list(self.score_runs.values()),
                    normalized=normalized,
                    params=params,
                    filter_columns=("pm_id", "book_id", "policy_id", "as_of_date", "state"),
                    sort_columns=("generated_at", "score_run_id"),
                )
            )

        if normalized.startswith("INSERT INTO dpm_pm_quality_fairness_analyses"):
            self.fairness_analyses.setdefault(
                str(params[0]),
                {
                    "fairness_analysis_id": str(params[0]),
                    "policy_id": str(params[1]),
                    "policy_version": str(params[2]),
                    "as_of_date": str(params[3]),
                    "state": str(params[4]),
                    "content_hash": str(params[6]),
                    "generated_at": str(params[7]),
                    "payload_json": json.loads(str(params[10])),
                },
            )
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_fairness_analyses"):
            row = self.fairness_analyses.get(str(params[0]))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_fairness_analyses WHERE")
            and "fairness_analysis_id = %s" in normalized
        ):
            return _FakeCursor(self.fairness_analyses.get(str(params[0])))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_fairness_analyses"):
            return _FakeCursor(
                rows=self._filtered_rows(
                    rows=list(self.fairness_analyses.values()),
                    normalized=normalized,
                    params=params,
                    filter_columns=("policy_id", "policy_version", "as_of_date", "state"),
                    sort_columns=("generated_at", "fairness_analysis_id"),
                )
            )

        if normalized.startswith("INSERT INTO dpm_pm_quality_review_actions"):
            self.review_actions.setdefault(
                str(params[0]),
                {
                    "review_action_id": str(params[0]),
                    "target_type": str(params[2]),
                    "target_id": str(params[3]),
                    "policy_id": str(params[4]),
                    "policy_version": str(params[5]),
                    "as_of_date": str(params[6]),
                    "action_state": str(params[9]),
                    "content_hash": str(params[10]),
                    "generated_at": str(params[11]),
                    "payload_json": json.loads(str(params[14])),
                },
            )
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_review_actions"):
            row = self.review_actions.get(str(params[0]))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if (
            normalized.startswith("SELECT payload_json FROM dpm_pm_quality_review_actions WHERE")
            and "review_action_id = %s" in normalized
        ):
            return _FakeCursor(self.review_actions.get(str(params[0])))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_review_actions"):
            return _FakeCursor(
                rows=self._filtered_rows(
                    rows=list(self.review_actions.values()),
                    normalized=normalized,
                    params=params,
                    filter_columns=(
                        "target_type",
                        "target_id",
                        "policy_id",
                        "as_of_date",
                        "action_state",
                    ),
                    sort_columns=("generated_at", "review_action_id"),
                )
            )

        if normalized.startswith("INSERT INTO dpm_pm_quality_summary_invocations"):
            self.summary_invocations.setdefault(
                str(params[0]),
                {
                    "summary_invocation_id": str(params[0]),
                    "score_run_id": str(params[1]),
                    "review_action_id": str(params[2]),
                    "policy_id": str(params[3]),
                    "policy_version": str(params[4]),
                    "as_of_date": str(params[5]),
                    "invocation_state": str(params[6]),
                    "content_hash": str(params[13]),
                    "generated_at": str(params[14]),
                    "payload_json": json.loads(str(params[17])),
                },
            )
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_summary_invocations"):
            row = self.summary_invocations.get(str(params[0]))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if (
            normalized.startswith(
                "SELECT payload_json FROM dpm_pm_quality_summary_invocations WHERE"
            )
            and "summary_invocation_id = %s" in normalized
        ):
            return _FakeCursor(self.summary_invocations.get(str(params[0])))
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_summary_invocations"):
            return _FakeCursor(
                rows=self._filtered_rows(
                    rows=list(self.summary_invocations.values()),
                    normalized=normalized,
                    params=params,
                    filter_columns=(
                        "score_run_id",
                        "review_action_id",
                        "policy_id",
                        "as_of_date",
                        "invocation_state",
                    ),
                    sort_columns=("generated_at", "summary_invocation_id"),
                )
            )

        raise AssertionError(f"Unexpected PM-quality Postgres query: {normalized}")

    def _filtered_rows(
        self,
        *,
        rows: list[dict[str, Any]],
        normalized: str,
        params: Sequence[Any],
        filter_columns: tuple[str, ...],
        sort_columns: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        filtered = rows
        param_index = 0
        for column in filter_columns:
            if f"{column} = %s" in normalized:
                expected = params[param_index]
                filtered = [row for row in filtered if row[column] == expected]
                param_index += 1
        return self._page_rows(rows=filtered, params=params, sort_columns=sort_columns)

    def _page_rows(
        self,
        *,
        rows: list[dict[str, Any]],
        params: Sequence[Any],
        sort_columns: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        sorted_rows = sorted(
            rows,
            key=lambda row: tuple(row[column] for column in sort_columns),
            reverse=True,
        )
        limit = int(params[-2])
        offset = int(params[-1])
        return sorted_rows[offset : offset + limit]

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        return None


@pytest.fixture
def pm_quality_postgres_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[_PmQualityPostgresConnection]:
    connection = _PmQualityPostgresConnection()

    class _FakePsycopg:
        Error = Exception

        @staticmethod
        def connect(*_args: Any, **_kwargs: Any) -> _PmQualityPostgresConnection:
            return connection

    _reset_pm_quality_postgres_singletons()
    monkeypatch.setenv("DPM_PM_QUALITY_POSTGRES_DSN", "postgresql://pm-quality-integration")
    monkeypatch.setattr(pm_quality_postgres, "has_psycopg", lambda: True)
    monkeypatch.setattr(pm_quality_postgres, "_import_psycopg", lambda: (_FakePsycopg, object()))
    monkeypatch.setattr(
        pm_quality_postgres,
        "apply_postgres_migrations",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        dependencies,
        "PostgresDpmOutcomeReviewRepository",
        lambda **_kwargs: InMemoryDpmOutcomeReviewRepository(),
    )

    try:
        yield connection
    finally:
        _reset_pm_quality_postgres_singletons()


def test_pm_quality_endpoint_lifecycle_uses_canonical_app_and_postgres_adapter(
    pm_quality_postgres_connection: _PmQualityPostgresConnection,
) -> None:
    with TestClient(app) as client:
        policy = client.put(
            "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
            json=_policy(),
        )
        policy_get = client.get(
            "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05"
        )
        policy_list = client.get(
            "/api/v1/rebalance/pm-operating-quality/policies",
            params={"policy_id": "pmq_sg_dpm", "enabled": "true"},
        )
        changed_policy = _policy()
        changed_policy["ready_threshold"] = "95"
        policy_conflict = client.put(
            "/api/v1/rebalance/pm-operating-quality/policies/pmq_sg_dpm/versions/2026.05",
            json=changed_policy,
            headers={"X-Correlation-Id": "corr-pmq-policy-conflict"},
        )

        score_runs = [
            _create_score_run(client, pm_id="pm_bal_001", score="92"),
            _create_score_run(client, pm_id="pm_bal_002", score="88"),
            _create_score_run(client, pm_id="pm_inc_001", score="60"),
            _create_score_run(client, pm_id="pm_inc_002", score="58"),
        ]
        replay = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs",
            json=_score_run_request(pm_id="pm_bal_001", score="92"),
        )
        first_score_run_id = score_runs[0]["score_run_id"]
        score_get = client.get(
            f"/api/v1/rebalance/pm-operating-quality/score-runs/{first_score_run_id}"
        )
        score_list = client.get(
            "/api/v1/rebalance/pm-operating-quality/score-runs",
            params={"policy_id": "pmq_sg_dpm", "state": "READY", "limit": 2, "offset": 0},
        )
        score_missing = client.get(
            "/api/v1/rebalance/pm-operating-quality/score-runs/missing",
            headers={"X-Correlation-Id": "corr-pmq-score-missing"},
        )
        disabled_preview = client.post(
            "/api/v1/rebalance/pm-operating-quality/score-runs/preview",
            json=_score_run_request(pm_id="pm_disabled", score="80", policy=_policy(False)),
        )

        fairness_request = _fairness_request(
            balanced_ids=[score_runs[0]["score_run_id"], score_runs[1]["score_run_id"]],
            income_ids=[score_runs[2]["score_run_id"], score_runs[3]["score_run_id"]],
        )
        fairness_preview = client.post(
            "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
            json=fairness_request,
        )
        fairness_create = client.post(
            "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
            json=fairness_request,
            headers={"X-Correlation-Id": "corr-pmq-fairness-create"},
        )
        fairness_id = fairness_create.json()["fairness_analysis"]["fairness_analysis_id"]
        fairness_get = client.get(
            f"/api/v1/rebalance/pm-operating-quality/fairness-analyses/{fairness_id}"
        )
        fairness_list = client.get(
            "/api/v1/rebalance/pm-operating-quality/fairness-analyses",
            params={"state": "PENDING_REVIEW", "policy_id": "pmq_sg_dpm"},
        )
        fairness_blocked = client.post(
            "/api/v1/rebalance/pm-operating-quality/fairness-analyses/preview",
            json={**fairness_request, "minimum_segment_score_run_count": 3},
        )

        review_request = _review_action_request(target_id=first_score_run_id)
        review_preview = client.post(
            "/api/v1/rebalance/pm-operating-quality/review-actions/preview",
            json=review_request,
        )
        review_create = client.post(
            "/api/v1/rebalance/pm-operating-quality/review-actions",
            json=review_request,
            headers={"X-Correlation-Id": "corr-pmq-review-create"},
        )
        review_id = review_create.json()["review_action"]["review_action_id"]
        review_get = client.get(
            f"/api/v1/rebalance/pm-operating-quality/review-actions/{review_id}"
        )
        review_list = client.get(
            "/api/v1/rebalance/pm-operating-quality/review-actions",
            params={"target_type": "SCORE_RUN", "action_state": "REVIEW_REQUIRED"},
        )

        summary_completed_request = _summary_invocation_request(
            score_run_id=first_score_run_id,
            review_action_id=review_id,
            state="COMPLETED",
            summary_ref="PMQ-SUMMARY-2026-05-COMPLETED",
        )
        summary_create = client.post(
            "/api/v1/rebalance/pm-operating-quality/summary-invocations",
            json=summary_completed_request,
            headers={"X-Correlation-Id": "corr-pmq-summary-create"},
        )
        summary_id = summary_create.json()["summary_invocation"]["summary_invocation_id"]
        summary_get = client.get(
            f"/api/v1/rebalance/pm-operating-quality/summary-invocations/{summary_id}"
        )
        summary_list = client.get(
            "/api/v1/rebalance/pm-operating-quality/summary-invocations",
            params={"score_run_id": first_score_run_id, "invocation_state": "COMPLETED"},
        )
        summary_failed = client.post(
            "/api/v1/rebalance/pm-operating-quality/summary-invocations",
            json=_summary_invocation_request(
                score_run_id=first_score_run_id,
                review_action_id=review_id,
                state="FAILED",
                summary_ref="PMQ-SUMMARY-2026-05-FAILED",
            ),
        )

    assert policy.status_code == 200
    assert policy_get.json()["policy_id"] == "pmq_sg_dpm"
    assert policy_list.json()["count"] == 1
    _assert_problem(policy_conflict, 409, "PM_QUALITY_POLICY_IMMUTABLE_CONFLICT")

    assert replay.status_code == 201
    assert replay.json()["score_run"]["score_run_id"] == first_score_run_id
    assert score_get.json()["score_run"]["content_hash"] == score_runs[0]["content_hash"]
    assert score_list.json()["count"] == 2
    assert score_list.json()["score_runs"][0]["state"] == "READY"
    _assert_problem(score_missing, 404, "PM_QUALITY_SCORE_RUN_NOT_FOUND")
    assert disabled_preview.json()["score_run"]["state"] == "DISABLED"

    assert fairness_preview.status_code == 200
    assert fairness_preview.json()["fairness_analysis"]["state"] == "PENDING_REVIEW"
    assert fairness_create.status_code == 201
    assert fairness_get.json()["fairness_analysis"]["fairness_analysis_id"] == fairness_id
    assert fairness_list.json()["count"] == 1
    assert fairness_blocked.json()["fairness_analysis"]["state"] == "BLOCKED"
    assert any(
        ref["source_type"] == "PmOperatingQualityScoreRun"
        for ref in fairness_create.json()["fairness_analysis"]["source_refs"]
    )

    assert (
        review_preview.json()["review_action"]["target_content_hash"]
        == score_runs[0]["content_hash"]
    )
    assert review_create.status_code == 201
    assert review_get.json()["review_action"]["review_action_id"] == review_id
    assert review_list.json()["count"] == 1
    assert review_create.json()["review_action"]["action_state"] == "REVIEW_REQUIRED"

    assert summary_create.status_code == 201
    assert summary_get.json()["summary_invocation"]["summary_invocation_id"] == summary_id
    assert summary_list.json()["count"] == 1
    assert summary_create.json()["summary_invocation"]["invocation_state"] == "COMPLETED"
    assert summary_failed.json()["summary_invocation"]["invocation_state"] == "FAILED"
    assert (
        summary_create.json()["summary_invocation"]["score_run_content_hash"]
        == score_runs[0]["content_hash"]
    )
    assert (
        summary_create.json()["summary_invocation"]["review_action_content_hash"]
        == review_create.json()["review_action"]["content_hash"]
    )
    assert pm_quality_postgres_connection.commits >= 9
    assert pm_quality_postgres_connection.rollbacks == 1


def _create_score_run(client: TestClient, *, pm_id: str, score: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/rebalance/pm-operating-quality/score-runs",
        json=_score_run_request(pm_id=pm_id, score=score),
    )
    assert response.status_code == 201
    return dict(response.json()["score_run"])


def _policy(enabled: bool = True) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "policy_id": "pmq_sg_dpm",
        "policy_version": "2026.05",
        "enabled": enabled,
        "as_of_date": "2026-05-12",
        "access_purpose": "SUPERVISORY_CONTROL_REVIEW",
        "weights": [
            {
                "indicator": "SOURCE_QUALITY",
                "weight": "100",
                "minimum_evidence_count": 1,
            }
        ],
    }
    if enabled:
        policy["governance_approval"] = {
            "approval_ref": "PMQ-APPROVAL-2026-05",
            "approved_by": "pm_quality_committee",
            "approved_at": "2026-05-10T09:00:00Z",
            "fairness_review_ref": "FAIRNESS-PMQ-2026-05",
            "fairness_reviewed_by": "model_risk_governance",
            "fairness_reviewed_at": "2026-05-10T10:00:00Z",
            "expires_on": "2026-06-30",
            "entitled_actor_ids": ["ops"],
            "source_refs": [
                {
                    "source_system": "bank-governance",
                    "source_type": "PM_QUALITY_POLICY_APPROVAL",
                    "source_id": "PMQ-APPROVAL-2026-05",
                    "source_version": "2026.05",
                    "content_hash": "sha256:pmq-approval",
                }
            ],
        }
    return policy


def _score_run_request(
    *,
    pm_id: str,
    score: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "pm_id": pm_id,
        "book_id": "sg_dpm_book",
        "as_of_date": "2026-05-12",
        "evidence_items": [
            {
                "indicator": "SOURCE_QUALITY",
                "evidence_state": "READY",
                "score": score,
                "source_system": "lotus-risk",
                "source_type": "PM_SOURCE_QUALITY",
                "source_id": f"pm-source-quality-{pm_id}",
                "source_refs": [
                    {
                        "source_system": "lotus-risk",
                        "source_type": "PM_SOURCE_QUALITY",
                        "source_id": f"pm-source-quality-{pm_id}",
                        "source_version": "2026-05-12",
                        "content_hash": f"sha256:pm-source-quality-{pm_id}",
                    }
                ],
            }
        ],
        "outcome_review_ids": [],
        "actor_id": "ops",
    }
    if policy is None:
        request["policy_id"] = "pmq_sg_dpm"
        request["policy_version"] = "2026.05"
    else:
        request["policy"] = policy
    return request


def _fairness_request(
    *,
    balanced_ids: list[str],
    income_ids: list[str],
) -> dict[str, Any]:
    return {
        "policy_id": "pmq_sg_dpm",
        "policy_version": "2026.05",
        "as_of_date": "2026-05-12",
        "minimum_segment_score_run_count": 2,
        "maximum_average_score_spread": "15",
        "actor_id": "ops",
        "segments": [
            {
                "segment_id": "mandate_balanced",
                "segment_type": "MANDATE_TYPE",
                "display_name": "Balanced DPM mandates",
                "score_run_ids": balanced_ids,
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "MandateTypeSegment",
                        "source_id": "mandate_balanced",
                    }
                ],
            },
            {
                "segment_id": "mandate_income",
                "segment_type": "MANDATE_TYPE",
                "display_name": "Income DPM mandates",
                "score_run_ids": income_ids,
                "source_refs": [
                    {
                        "source_system": "lotus-core",
                        "source_type": "MandateTypeSegment",
                        "source_id": "mandate_income",
                    }
                ],
            },
        ],
    }


def _review_action_request(*, target_id: str) -> dict[str, Any]:
    return {
        "target_type": "SCORE_RUN",
        "target_id": target_id,
        "action_type": "REQUEST_EVIDENCE_REMEDIATION",
        "review_action_ref": "PMQ-REVIEW-2026-05-001",
        "review_reason": "Evidence remediation required before supervisory closure.",
        "remediation_due_date": "2026-06-15",
        "actor_id": "ops",
        "source_refs": [
            {
                "source_system": "bank-governance",
                "source_type": "PM_QUALITY_REVIEW_MINUTES",
                "source_id": "pmq-review-minutes-001",
            }
        ],
    }


def _summary_invocation_request(
    *,
    score_run_id: str,
    review_action_id: str,
    state: str,
    summary_ref: str,
) -> dict[str, Any]:
    return {
        "score_run_id": score_run_id,
        "review_action_id": review_action_id,
        "invocation_state": state,
        "summary_ref": summary_ref,
        "workflow_pack_name": "pm_quality_summary.pack",
        "workflow_pack_version": "v1",
        "workflow_run_id": f"{summary_ref.lower()}-workflow",
        "summary_artifact_ref": f"{summary_ref.lower()}-artifact",
        "summary_content_hash": f"sha256:{summary_ref.lower()}",
        "requested_by": "ops",
        "source_refs": [
            {
                "source_system": "lotus-ai",
                "source_type": "pm_quality_summary.pack",
                "source_id": f"{summary_ref.lower()}-workflow",
                "source_version": "v1",
                "content_hash": f"sha256:{summary_ref.lower()}",
            }
        ],
    }


def _assert_problem(response: Any, status_code: int, reason_code: str) -> None:
    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == status_code
    assert body["reasonCode"] == reason_code
    assert body["correlationId"] == response.headers["X-Correlation-Id"]


def _reset_pm_quality_postgres_singletons() -> None:
    for name in PM_QUALITY_POSTGRES_SINGLETONS:
        setattr(dependencies, name, None)
