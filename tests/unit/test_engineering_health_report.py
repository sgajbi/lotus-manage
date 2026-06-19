import io
import tarfile
from types import SimpleNamespace

from scripts import engineering_health_report as ehr
from scripts.engineering_health_report import (
    ComplexityMetric,
    FileMetric,
    FunctionMetric,
    HealthReportContext,
    SnapshotMetrics,
    build_api_governance_rules,
    build_architecture_rules,
    build_baseline_report,
    build_complexity_report,
    build_quality_scorecard,
)


def _tar_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for path, text in files.items():
            payload = text.encode("utf-8")
            info = tarfile.TarInfo(path)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _snapshot(*, label: str, router_imports: list[str] | None = None) -> SnapshotMetrics:
    return SnapshotMetrics(
        label=label,
        python_file_count=3,
        total_loc=120,
        test_count=4,
        largest_files=[FileMetric(path="src/api/main.py", lines=42)],
        largest_functions=[FunctionMetric(path="src/api/main.py", name="create_app", lines=12)],
        most_complex_functions=[
            ComplexityMetric(
                path="tests/unit/test_main.py", name="test_create_app", complexity=4, lines=16
            ),
            ComplexityMetric(path="src/api/main.py", name="create_app", complexity=3, lines=12),
        ],
        most_complex_source_functions=[
            ComplexityMetric(path="src/api/main.py", name="create_app", complexity=3, lines=12)
        ],
        most_complex_test_functions=[
            ComplexityMetric(
                path="tests/unit/test_main.py", name="test_create_app", complexity=4, lines=16
            )
        ],
        service_boundary_violations=[],
        router_infra_imports=router_imports or [],
    )


def test_python_texts_from_git_reads_python_files_from_one_archive(monkeypatch) -> None:
    calls: list[list[str]] = []
    archive_payload = _tar_bytes(
        {
            "src/api/main.py": "def create_app():\n    pass\n",
            "src/api/ignored.txt": "not python\n",
            "tests/unit/test_example.py": "def test_example():\n    pass\n",
        }
    )

    def fake_run(command: list[str], **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=archive_payload)

    monkeypatch.setattr(ehr.subprocess, "run", fake_run)

    texts = ehr._python_texts_from_git("origin/main")

    assert calls == [
        ["git", "archive", "--format=tar", "origin/main", "--", "src", "tests", "scripts"]
    ]
    assert texts == {
        "src/api/main.py": "def create_app():\n    pass\n",
        "tests/unit/test_example.py": "def test_example():\n    pass\n",
    }


def test_report_source_snapshot_marks_dirty_worktree(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(*args: str) -> str:
        calls.append(args)
        if args == ("rev-parse", "--short", "HEAD"):
            return "abc1234\n"
        if args == ("status", "--porcelain"):
            return " M scripts/engineering_health_report.py\n"
        raise AssertionError(args)

    monkeypatch.setattr(ehr, "_git", fake_git)

    assert ehr._report_source_snapshot() == "abc1234+worktree"
    assert calls == [
        ("rev-parse", "--short", "HEAD"),
        ("status", "--porcelain"),
    ]


def _context() -> HealthReportContext:
    return HealthReportContext(
        generated_at="2026-06-02T00:00:00+00:00",
        base_ref="origin/main",
        current_ref="abc1234",
        base=_snapshot(label="origin/main"),
        current=_snapshot(
            label="current branch",
            router_imports=["src/api/routers/example.py:1: from src.infrastructure.foo import Foo"],
        ),
        openapi={
            "operations": 10,
            "missing_summary": 0,
            "missing_description": 0,
            "missing_tags": 0,
            "missing_error_response": 2,
            "missing_examples": 0,
        },
    )


def test_baseline_report_declares_report_only_quality_coverage() -> None:
    report = build_baseline_report(_context())

    assert "# lotus-manage Baseline Quality Report" in report
    assert "- Report source snapshot: `abc1234`" in report
    assert "| Python files | 3 |" in report
    assert "| Router infrastructure imports | 1 |" in report
    assert (
        "| Router infrastructure imports | `scripts/router_infrastructure_gate.py` plus this report | 2 - active/new-regression |"
        in report
    )
    assert (
        "| Complexity/maintainability | `quality/complexity_report.md` | 1 - baseline |" in report
    )
    assert "does not enforce thresholds by itself" in report


def test_quality_scorecard_separates_active_gates_from_planned_gates() -> None:
    scorecard = build_quality_scorecard(_context())

    assert "# lotus-manage Quality Scorecard" in scorecard
    assert "- Report source snapshot: `abc1234`" in scorecard
    assert "| OpenAPI governance | Active gate | `scripts/openapi_quality_gate.py`. |" in scorecard
    assert "| Service boundary | Active gate | `scripts/service_boundary_gate.py`. |" in scorecard
    assert (
        "| Router infrastructure imports | Active gate | `scripts/router_infrastructure_gate.py`. |"
        in scorecard
    )
    assert "| Dependency architecture | Active gate |" in scorecard
    assert "| Dead code | Active gate |" in scorecard
    assert "| Quality report freshness | Active gate |" in scorecard
    assert "| Workflow policy | Active gate |" in scorecard
    assert "| Local CI parity | Active gate |" in scorecard
    assert "| Complexity | Report-only baseline |" in scorecard
    assert (
        "| 4 - enterprise-readiness gates | Block release on full readiness posture." in scorecard
    )


def test_complexity_metrics_count_branching_constructs() -> None:
    metrics = ehr._complexity_metrics(
        "src/api/example.py",
        """
def evaluate(flag, value):
    if flag and value:
        return 1
    for item in range(2):
        if item:
            return item
    return 0
""",
    )

    assert metrics == [
        ComplexityMetric(
            path="src/api/example.py",
            name="evaluate",
            complexity=5,
            lines=7,
        )
    ]


def test_complexity_report_is_report_only() -> None:
    report = build_complexity_report(_context())

    assert "# lotus-manage Complexity Report" in report
    assert "- Report source snapshot: `abc1234`" in report
    assert "| Highest complexity | 4 | 4 | +0 |" in report
    assert "### Most Complex Current Source Functions" in report
    assert "### Most Complex Current Test Functions" in report
    assert "phase 1/report-only" in report


def test_quality_rule_documents_state_report_only_architecture_and_api_rules() -> None:
    architecture_rules = build_architecture_rules()
    api_rules = build_api_governance_rules()

    assert "Routers call application services or use-case functions only." in architecture_rules
    assert "Service modules must not import FastAPI or Starlette transport packages." in (
        architecture_rules
    )
    assert "Current Gate Phase" in architecture_rules
    assert "Every endpoint should have a summary" in api_rules
    assert "OpenAPI and API vocabulary checks are active repo-native gates" in api_rules


def test_report_check_normalizes_volatile_provenance() -> None:
    current = "\n".join(
        [
            "# Report",
            "- Generated at: `2026-06-19T00:00:00+00:00`",
            "- Report source snapshot: `abc1234`",
        ]
    )
    regenerated = "\n".join(
        [
            "# Report",
            "- Generated at: `2026-06-19T01:00:00+00:00`",
            "- Report source snapshot: `abc1234`",
        ]
    )
    changed_snapshot = "\n".join(
        [
            "# Report",
            "- Generated at: `2026-06-19T01:00:00+00:00`",
            "- Report source snapshot: `def5678`",
        ]
    )

    assert ehr._normalize_report_for_check(current) == ehr._normalize_report_for_check(regenerated)
    assert ehr._normalize_report_for_check(current) == ehr._normalize_report_for_check(
        changed_snapshot
    )
    assert ehr._normalize_report_for_check(current) != ehr._normalize_report_for_check(
        changed_snapshot + "\n| Metric | Changed |\n"
    )


def test_stale_report_paths_detects_missing_or_changed_quality_artifacts(
    tmp_path, monkeypatch
) -> None:
    current_report = tmp_path / "current.md"
    stale_report = tmp_path / "stale.md"
    missing_report = tmp_path / "missing.md"
    current_report.write_text(
        "# Current\n- Generated at: `old`\n- Report source snapshot: `abc1234`\n",
        encoding="utf-8",
    )
    stale_report.write_text(
        "# Stale\n- Generated at: `old`\n- Report source snapshot: `old1234`\n| Metric | Old |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        ehr,
        "REPORT_OUTPUT_BUILDERS",
        (
            (
                current_report,
                lambda _context: (
                    "# Current\n- Generated at: `new`\n- Report source snapshot: `abc1234`\n"
                ),
            ),
            (
                stale_report,
                lambda _context: (
                    "# Stale\n- Generated at: `new`\n- Report source snapshot: `abc1234`\n| Metric | New |\n"
                ),
            ),
            (
                missing_report,
                lambda _context: (
                    "# Missing\n- Generated at: `new`\n- Report source snapshot: `abc1234`\n"
                ),
            ),
        ),
    )

    assert ehr.stale_report_paths(_context()) == [stale_report, missing_report]


def test_service_boundary_findings_include_transport_framework_imports() -> None:
    findings = ehr._matching_lines(
        "src/api/services/example.py",
        "\n".join(
            [
                "from fastapi import HTTPException",
                "from starlette.requests import Request",
                "from src.api.routers.example import router",
            ]
        ),
        ehr.SERVICE_LEAKAGE_PATTERNS,
    )

    assert findings == [
        "src/api/services/example.py:1: from fastapi import HTTPException",
        "src/api/services/example.py:2: from starlette.requests import Request",
        "src/api/services/example.py:3: from src.api.routers.example import router",
    ]
