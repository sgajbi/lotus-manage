from scripts.engineering_health_report import (
    FileMetric,
    FunctionMetric,
    HealthReportContext,
    SnapshotMetrics,
    build_api_governance_rules,
    build_architecture_rules,
    build_baseline_report,
    build_quality_scorecard,
)


def _snapshot(*, label: str, router_imports: list[str] | None = None) -> SnapshotMetrics:
    return SnapshotMetrics(
        label=label,
        python_file_count=3,
        total_loc=120,
        test_count=4,
        largest_files=[FileMetric(path="src/api/main.py", lines=42)],
        largest_functions=[FunctionMetric(path="src/api/main.py", name="create_app", lines=12)],
        service_boundary_violations=[],
        router_infra_imports=router_imports or [],
    )


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
    assert "| Python files | 3 |" in report
    assert "| Router infrastructure imports | 1 |" in report
    assert "| Complexity/maintainability | not instrumented yet | planned |" in report
    assert "does not enforce thresholds by itself" in report


def test_quality_scorecard_separates_active_gates_from_planned_gates() -> None:
    scorecard = build_quality_scorecard(_context())

    assert "# lotus-manage Quality Scorecard" in scorecard
    assert "| OpenAPI governance | Active gate | `scripts/openapi_quality_gate.py`. |" in scorecard
    assert "| Complexity | Not yet instrumented |" in scorecard
    assert (
        "| 4 - enterprise-readiness gates | Block release on full readiness posture." in scorecard
    )


def test_quality_rule_documents_state_report_only_architecture_and_api_rules() -> None:
    architecture_rules = build_architecture_rules()
    api_rules = build_api_governance_rules()

    assert "Routers call application services or use-case functions only." in architecture_rules
    assert "Current Gate Phase" in architecture_rules
    assert "Every endpoint should have a summary" in api_rules
    assert "OpenAPI and API vocabulary checks are active repo-native gates" in api_rules
