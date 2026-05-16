from decimal import Decimal

import json
import sys
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import pytest

from src.core.pm_quality import (
    DpmPmOperatingQualityPolicy,
    DpmPmQualityFairnessAnalysisConflictError,
    DpmPmQualityGovernanceApproval,
    DpmPmQualityPolicyConflictError,
    DpmPmQualityScoreRunConflictError,
    DpmPmQualityWeight,
    DpmPmQualityFairnessSegmentInput,
    build_pm_operating_quality_fairness_analysis,
    build_pm_operating_quality_score_run,
)
from src.infrastructure.pm_quality import (
    InMemoryDpmPmQualityFairnessAnalysisRepository,
    InMemoryDpmPmQualityPolicyRepository,
    InMemoryDpmPmQualityScoreRunRepository,
)
from src.infrastructure.pm_quality import postgres as postgres_module
from src.infrastructure.pm_quality.postgres import (
    PostgresDpmPmQualityFairnessAnalysisRepository,
    PostgresDpmPmQualityPolicyRepository,
    PostgresDpmPmQualityScoreRunRepository,
)


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
        self.policies: dict[tuple[str, str], dict[str, Any]] = {}
        self.score_runs: dict[str, dict[str, Any]] = {}
        self.fairness_analyses: dict[str, dict[str, Any]] = {}
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, query: str, params: Sequence[Any] = ()) -> _FakeCursor:
        normalized = " ".join(query.split())
        if normalized.startswith("INSERT INTO dpm_pm_quality_score_runs"):
            score_run_id = str(params[0])
            if score_run_id not in self.score_runs:
                self.score_runs[score_run_id] = {
                    "score_run_id": score_run_id,
                    "pm_id": str(params[1]),
                    "book_id": str(params[2]),
                    "policy_id": str(params[3]),
                    "policy_version": str(params[4]),
                    "as_of_date": str(params[5]),
                    "state": str(params[6]),
                    "content_hash": str(params[8]),
                    "generated_at": str(params[9]),
                    "payload_json": json.loads(str(params[12])),
                }
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
            rows = self._filter_score_runs(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_fairness_analyses"):
            fairness_analysis_id = str(params[0])
            if fairness_analysis_id not in self.fairness_analyses:
                self.fairness_analyses[fairness_analysis_id] = {
                    "fairness_analysis_id": fairness_analysis_id,
                    "policy_id": str(params[1]),
                    "policy_version": str(params[2]),
                    "as_of_date": str(params[3]),
                    "state": str(params[4]),
                    "content_hash": str(params[6]),
                    "generated_at": str(params[7]),
                    "payload_json": json.loads(str(params[10])),
                }
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
            rows = self._filter_fairness_analyses(normalized=normalized, params=params)
            return _FakeCursor(rows=rows)
        if normalized.startswith("INSERT INTO dpm_pm_quality_policies"):
            key = (str(params[0]), str(params[1]))
            if key not in self.policies:
                self.policies[key] = {
                    "policy_id": str(params[0]),
                    "policy_version": str(params[1]),
                    "enabled": bool(params[2]),
                    "as_of_date": str(params[3]),
                    "access_purpose": str(params[4]),
                    "content_hash": str(params[5]),
                    "payload_json": json.loads(str(params[6])),
                }
            return _FakeCursor()
        if normalized.startswith("SELECT content_hash FROM dpm_pm_quality_policies"):
            row = self.policies.get((str(params[0]), str(params[1])))
            return _FakeCursor({"content_hash": row["content_hash"]} if row else None)
        if normalized.startswith("SELECT payload_json FROM dpm_pm_quality_policies WHERE"):
            if "policy_version = %s" in normalized:
                return _FakeCursor(self.policies.get((str(params[0]), str(params[1]))))
            rows = list(self.policies.values())
            param_index = 0
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
                self.policies.values(),
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
        rows = list(self.score_runs.values())
        param_index = 0
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
        rows = list(self.fairness_analyses.values())
        param_index = 0
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

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


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


def test_in_memory_pm_quality_repository_persists_immutable_policies() -> None:
    repository = InMemoryDpmPmQualityPolicyRepository()
    policy = _policy()

    repository.save_policy(policy=policy)
    repository.save_policy(policy=policy)

    stored = repository.get_policy(policy_id=policy.policy_id, policy_version=policy.policy_version)
    assert stored == policy

    changed = policy.model_copy(update={"ready_threshold": Decimal("90")})
    with pytest.raises(DpmPmQualityPolicyConflictError):
        repository.save_policy(policy=changed)


def test_in_memory_pm_quality_repository_lists_policy_versions() -> None:
    repository = InMemoryDpmPmQualityPolicyRepository()
    enabled = _policy(policy_id="pmq_enabled", enabled=True)
    disabled = _policy(policy_id="pmq_disabled", enabled=False)
    repository.save_policy(policy=enabled)
    repository.save_policy(policy=disabled)

    assert repository.list_policies(policy_id="pmq_enabled") == [enabled]
    assert repository.list_policies(enabled=False) == [disabled]
    assert repository.list_policies(as_of_date="missing") == []
    assert repository.list_policies(limit=1, offset=1) == [disabled]


def test_postgres_pm_quality_policy_repository_round_trips_policy_versions(
    fake_postgres_policy_repository: tuple[
        PostgresDpmPmQualityPolicyRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_policy_repository
    enabled = _policy(policy_id="pmq_enabled", enabled=True)
    disabled = _policy(policy_id="pmq_disabled", enabled=False)

    repository.save_policy(policy=enabled)
    repository.save_policy(policy=disabled)
    repository.save_policy(policy=enabled)

    assert (
        repository.get_policy(
            policy_id=enabled.policy_id,
            policy_version=enabled.policy_version,
        )
        == enabled
    )
    assert repository.get_policy(policy_id="missing", policy_version="2026.05") is None
    assert repository.list_policies(policy_id="pmq_enabled") == [enabled]
    assert repository.list_policies(enabled=False) == [disabled]
    assert repository.list_policies(as_of_date="missing") == []
    assert repository.list_policies(limit=1, offset=1) == [disabled]
    assert connection.commits == 3


def test_postgres_pm_quality_policy_repository_conflict_and_configuration_paths(
    fake_postgres_policy_repository: tuple[
        PostgresDpmPmQualityPolicyRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_policy_repository
    policy = _policy()
    repository.save_policy(policy=policy)

    changed = policy.model_copy(update={"ready_threshold": Decimal("90")})
    with pytest.raises(DpmPmQualityPolicyConflictError, match="IMMUTABLE"):
        repository.save_policy(policy=changed)

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

    repository.save_score_run(score_run=score_run)
    repository.save_score_run(score_run=other)
    repository.save_score_run(score_run=score_run)

    assert repository.get_score_run(score_run_id=score_run.score_run_id) == score_run
    assert repository.get_score_run(score_run_id="missing") is None
    assert repository.list_score_runs(pm_id="pm_001") == [score_run]
    assert repository.list_score_runs(book_id="missing") == []
    assert repository.list_score_runs(policy_id="pmq_other") == [other]
    assert repository.list_score_runs(as_of_date="missing") == []
    assert len(repository.list_score_runs(state=score_run.state, limit=1, offset=1)) == 1
    assert connection.commits == 3


def test_postgres_pm_quality_score_run_repository_conflict_and_configuration_paths(
    fake_postgres_score_run_repository: tuple[
        PostgresDpmPmQualityScoreRunRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_score_run_repository
    score_run = _score_run()
    repository.save_score_run(score_run=score_run)

    changed = score_run.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityScoreRunConflictError, match="IMMUTABLE"):
        repository.save_score_run(score_run=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityScoreRunRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityScoreRunRepository(dsn="postgresql://unit-test")


def test_in_memory_pm_quality_repository_persists_immutable_fairness_analyses() -> None:
    repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    analysis = _fairness_analysis()

    repository.save_fairness_analysis(analysis=analysis)
    repository.save_fairness_analysis(analysis=analysis)

    stored = repository.get_fairness_analysis(fairness_analysis_id=analysis.fairness_analysis_id)
    assert stored == analysis

    changed = analysis.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityFairnessAnalysisConflictError):
        repository.save_fairness_analysis(analysis=changed)


def test_in_memory_pm_quality_repository_lists_fairness_analyses() -> None:
    repository = InMemoryDpmPmQualityFairnessAnalysisRepository()
    analysis = _fairness_analysis()
    repository.save_fairness_analysis(analysis=analysis)

    assert repository.list_fairness_analyses(policy_id="pmq_sg_dpm") == [analysis]
    assert repository.list_fairness_analyses(policy_version="2026.05") == [analysis]
    assert repository.list_fairness_analyses(as_of_date="missing") == []
    assert repository.list_fairness_analyses(state=analysis.state) == [analysis]
    assert repository.list_fairness_analyses(limit=1, offset=1) == []


def test_postgres_pm_quality_fairness_analysis_repository_round_trips_analyses(
    fake_postgres_fairness_analysis_repository: tuple[
        PostgresDpmPmQualityFairnessAnalysisRepository, _FakePolicyConnection
    ],
) -> None:
    repository, connection = fake_postgres_fairness_analysis_repository
    analysis = _fairness_analysis()

    repository.save_fairness_analysis(analysis=analysis)
    repository.save_fairness_analysis(analysis=analysis)

    assert (
        repository.get_fairness_analysis(fairness_analysis_id=analysis.fairness_analysis_id)
        == analysis
    )
    assert repository.get_fairness_analysis(fairness_analysis_id="missing") is None
    assert repository.list_fairness_analyses(policy_id="pmq_sg_dpm") == [analysis]
    assert repository.list_fairness_analyses(policy_version="2026.05") == [analysis]
    assert repository.list_fairness_analyses(as_of_date="missing") == []
    assert repository.list_fairness_analyses(state=analysis.state) == [analysis]
    assert connection.commits == 2


def test_postgres_pm_quality_fairness_analysis_repository_conflict_and_configuration_paths(
    fake_postgres_fairness_analysis_repository: tuple[
        PostgresDpmPmQualityFairnessAnalysisRepository, _FakePolicyConnection
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, connection = fake_postgres_fairness_analysis_repository
    analysis = _fairness_analysis()
    repository.save_fairness_analysis(analysis=analysis)

    changed = analysis.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityFairnessAnalysisConflictError, match="IMMUTABLE"):
        repository.save_fairness_analysis(analysis=changed)

    assert connection.rollbacks == 1

    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DSN_REQUIRED"):
        PostgresDpmPmQualityFairnessAnalysisRepository(dsn="")

    monkeypatch.setattr(postgres_module, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="DPM_PM_QUALITY_POSTGRES_DRIVER_MISSING"):
        PostgresDpmPmQualityFairnessAnalysisRepository(dsn="postgresql://unit-test")


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


def test_in_memory_pm_quality_repository_persists_immutable_score_runs() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    score_run = _score_run()

    repository.save_score_run(score_run=score_run)
    repository.save_score_run(score_run=score_run)

    stored = repository.get_score_run(score_run_id=score_run.score_run_id)
    assert stored == score_run

    changed = score_run.model_copy(update={"content_hash": "sha256:different"})
    with pytest.raises(DpmPmQualityScoreRunConflictError):
        repository.save_score_run(score_run=changed)


def test_in_memory_pm_quality_repository_lists_with_bounded_filters() -> None:
    repository = InMemoryDpmPmQualityScoreRunRepository()
    first = _score_run(pm_id="pm_001", policy_id="pmq_sg_dpm")
    second = _score_run(pm_id="pm_002", policy_id="pmq_hk_dpm")
    repository.save_score_run(score_run=first)
    repository.save_score_run(score_run=second)

    assert repository.list_score_runs(pm_id="pm_001") == [first]
    assert repository.list_score_runs(policy_id="pmq_hk_dpm") == [second]
    assert repository.list_score_runs(book_id="missing") == []
    assert repository.list_score_runs(limit=1, offset=1) == [first]
