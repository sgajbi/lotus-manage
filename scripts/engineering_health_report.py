from __future__ import annotations

import ast
import io
import subprocess
import sys
import tarfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_BASE_REF = "origin/main"
DEFAULT_OUTPUT = REPO_ROOT / "quality" / "refactor_health_report.md"
DEFAULT_BASELINE_OUTPUT = REPO_ROOT / "quality" / "baseline_report.md"
DEFAULT_SCORECARD_OUTPUT = REPO_ROOT / "quality" / "quality_scorecard.md"
DEFAULT_ARCHITECTURE_RULES_OUTPUT = REPO_ROOT / "quality" / "architecture_rules.md"
DEFAULT_API_GOVERNANCE_RULES_OUTPUT = REPO_ROOT / "quality" / "api_governance_rules.md"
DEFAULT_COMPLEXITY_OUTPUT = REPO_ROOT / "quality" / "complexity_report.md"
PYTHON_ROOTS = ("src", "tests", "scripts")
SERVICE_LEAKAGE_PATTERNS = (
    "from src.api.routers",
    "import src.api.routers",
    "HTTPException",
    "status.HTTP",
)
ROUTER_INFRA_PATTERNS = (
    "from src.infrastructure",
    "import src.infrastructure",
)


@dataclass(frozen=True)
class FileMetric:
    path: str
    lines: int


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    name: str
    lines: int


@dataclass(frozen=True)
class ComplexityMetric:
    path: str
    name: str
    complexity: int
    lines: int


@dataclass(frozen=True)
class SnapshotMetrics:
    label: str
    python_file_count: int
    total_loc: int
    test_count: int
    largest_files: list[FileMetric]
    largest_functions: list[FunctionMetric]
    most_complex_functions: list[ComplexityMetric]
    most_complex_source_functions: list[ComplexityMetric]
    most_complex_test_functions: list[ComplexityMetric]
    service_boundary_violations: list[str]
    router_infra_imports: list[str]


@dataclass(frozen=True)
class HealthReportContext:
    generated_at: str
    base_ref: str
    current_ref: str
    base: SnapshotMetrics
    current: SnapshotMetrics
    openapi: dict[str, int]


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _python_paths_from_worktree() -> list[str]:
    paths: list[str] = []
    for root in PYTHON_ROOTS:
        for path in (REPO_ROOT / root).rglob("*.py"):
            if any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts):
                continue
            paths.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(paths)


def _python_texts_from_git(ref: str) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "archive", "--format=tar", ref, "--", *PYTHON_ROOTS],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    texts: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            path = member.name.replace("\\", "/")
            if not member.isfile() or not path.endswith(".py"):
                continue
            if not path.startswith(tuple(f"{root}/" for root in PYTHON_ROOTS)):
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            texts[path] = extracted.read().decode("utf-8")
    return dict(sorted(texts.items()))


def _text_from_worktree(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _function_metrics(path: str, text: str) -> list[FunctionMetric]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    metrics: list[FunctionMetric] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            metrics.append(
                FunctionMetric(path=path, name=node.name, lines=end_lineno - node.lineno + 1)
            )
    return metrics


def _complexity_score(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            ast.If
            | ast.For
            | ast.AsyncFor
            | ast.While
            | ast.IfExp
            | ast.ExceptHandler
            | ast.Assert,
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, ast.Match):
            score += len(child.cases)
    return score


def _complexity_metrics(path: str, text: str) -> list[ComplexityMetric]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    metrics: list[ComplexityMetric] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            metrics.append(
                ComplexityMetric(
                    path=path,
                    name=node.name,
                    complexity=_complexity_score(node),
                    lines=end_lineno - node.lineno + 1,
                )
            )
    return metrics


def _test_count(text: str) -> int:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
    )


def _matching_lines(path: str, text: str, patterns: Iterable[str]) -> list[str]:
    matches: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if any(pattern in line for pattern in patterns):
            matches.append(f"{path}:{lineno}: {line.strip()}")
    return matches


def _snapshot_metrics(label: str, paths: list[str], reader: Any) -> SnapshotMetrics:
    files: list[FileMetric] = []
    functions: list[FunctionMetric] = []
    complexity_functions: list[ComplexityMetric] = []
    service_boundary_violations: list[str] = []
    router_infra_imports: list[str] = []
    total_loc = 0
    test_count = 0
    for path in paths:
        text = reader(path)
        lines = len(text.splitlines())
        total_loc += lines
        files.append(FileMetric(path=path, lines=lines))
        functions.extend(_function_metrics(path, text))
        complexity_functions.extend(_complexity_metrics(path, text))
        if path.startswith("tests/"):
            test_count += _test_count(text)
        if path.startswith("src/api/services/"):
            service_boundary_violations.extend(
                _matching_lines(path, text, SERVICE_LEAKAGE_PATTERNS)
            )
        if path.startswith("src/api/routers/"):
            router_infra_imports.extend(_matching_lines(path, text, ROUTER_INFRA_PATTERNS))
    sorted_complexity = sorted(
        complexity_functions,
        key=lambda item: (item.complexity, item.lines),
        reverse=True,
    )
    return SnapshotMetrics(
        label=label,
        python_file_count=len(paths),
        total_loc=total_loc,
        test_count=test_count,
        largest_files=sorted(files, key=lambda item: item.lines, reverse=True)[:10],
        largest_functions=sorted(functions, key=lambda item: item.lines, reverse=True)[:10],
        most_complex_functions=sorted_complexity[:10],
        most_complex_source_functions=[
            item for item in sorted_complexity if item.path.startswith("src/")
        ][:10],
        most_complex_test_functions=[
            item for item in sorted_complexity if item.path.startswith("tests/")
        ][:10],
        service_boundary_violations=service_boundary_violations,
        router_infra_imports=router_infra_imports,
    )


def _snapshot_metrics_from_texts(label: str, texts: dict[str, str]) -> SnapshotMetrics:
    return _snapshot_metrics(
        label=label,
        paths=list(texts),
        reader=texts.__getitem__,
    )


def _delta(current: int, baseline: int) -> str:
    value = current - baseline
    sign = "+" if value >= 0 else ""
    return f"{sign}{value}"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _metric_summary(base: SnapshotMetrics, current: SnapshotMetrics) -> str:
    rows = [
        [
            "Python files",
            str(base.python_file_count),
            str(current.python_file_count),
            _delta(current.python_file_count, base.python_file_count),
        ],
        [
            "Total Python LOC",
            str(base.total_loc),
            str(current.total_loc),
            _delta(current.total_loc, base.total_loc),
        ],
        [
            "Test functions",
            str(base.test_count),
            str(current.test_count),
            _delta(current.test_count, base.test_count),
        ],
        [
            "Service boundary findings",
            str(len(base.service_boundary_violations)),
            str(len(current.service_boundary_violations)),
            _delta(len(current.service_boundary_violations), len(base.service_boundary_violations)),
        ],
        [
            "Router infrastructure imports",
            str(len(base.router_infra_imports)),
            str(len(current.router_infra_imports)),
            _delta(len(current.router_infra_imports), len(base.router_infra_imports)),
        ],
    ]
    return _table(["Metric", base.label, current.label, "Delta"], rows)


def _top_file_table(title: str, files: list[FileMetric]) -> str:
    return f"### {title}\n\n" + _table(
        ["Rank", "File", "Lines"],
        [[str(index), item.path, str(item.lines)] for index, item in enumerate(files, start=1)],
    )


def _top_function_table(title: str, functions: list[FunctionMetric]) -> str:
    return f"### {title}\n\n" + _table(
        ["Rank", "Function", "File", "Lines"],
        [
            [str(index), item.name, item.path, str(item.lines)]
            for index, item in enumerate(functions, start=1)
        ],
    )


def _top_complexity_table(title: str, functions: list[ComplexityMetric]) -> str:
    return f"### {title}\n\n" + _table(
        ["Rank", "Function", "File", "Complexity", "Lines"],
        [
            [str(index), item.name, item.path, str(item.complexity), str(item.lines)]
            for index, item in enumerate(functions, start=1)
        ],
    )


def _openapi_metrics() -> dict[str, int]:
    try:
        from src.api.main import app
    except Exception:
        return {
            "operations": 0,
            "missing_summary": -1,
            "missing_description": -1,
            "missing_tags": -1,
            "missing_error_response": -1,
            "missing_examples": -1,
        }
    schema = app.openapi()
    operations = 0
    missing_summary = 0
    missing_description = 0
    missing_tags = 0
    missing_error_response = 0
    missing_examples = 0
    for path_item in schema.get("paths", {}).values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            operations += 1
            if not operation.get("summary"):
                missing_summary += 1
            if not operation.get("description"):
                missing_description += 1
            if not operation.get("tags"):
                missing_tags += 1
            responses = operation.get("responses", {})
            if not any(str(code).startswith(("4", "5")) for code in responses):
                missing_error_response += 1
            if "examples" not in str(operation):
                missing_examples += 1
    return {
        "operations": operations,
        "missing_summary": missing_summary,
        "missing_description": missing_description,
        "missing_tags": missing_tags,
        "missing_error_response": missing_error_response,
        "missing_examples": missing_examples,
    }


def _bounded_findings(title: str, findings: list[str]) -> str:
    if not findings:
        return f"### {title}\n\nNo findings.\n"
    shown = findings[:20]
    suffix = "" if len(findings) <= len(shown) else f"\n\n... {len(findings) - len(shown)} more."
    return f"### {title}\n\n" + "\n".join(f"- `{item}`" for item in shown) + suffix + "\n"


def _report_context(base_ref: str = DEFAULT_BASE_REF) -> HealthReportContext:
    base_texts = _python_texts_from_git(base_ref)
    current_paths = _python_paths_from_worktree()
    base = _snapshot_metrics_from_texts(label=base_ref, texts=base_texts)
    current = _snapshot_metrics(
        label="current branch",
        paths=current_paths,
        reader=_text_from_worktree,
    )
    return HealthReportContext(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        base_ref=base_ref,
        current_ref=_git("rev-parse", "--short", "HEAD").strip(),
        base=base,
        current=current,
        openapi=_openapi_metrics(),
    )


def build_refactor_report(context: HealthReportContext) -> str:
    base = context.base
    current = context.current
    openapi = context.openapi
    sections = [
        "# lotus-manage Refactor Health Report",
        f"- Generated at: `{context.generated_at}`",
        f"- Baseline ref: `{context.base_ref}`",
        f"- Current ref: `{context.current_ref}`",
        "- Scope: Python code under `src/`, `tests/`, and `scripts/`; current OpenAPI schema.",
        "## Scorecard",
        _metric_summary(base, current),
        "## Current OpenAPI Completeness",
        _table(
            ["Metric", "Current"],
            [
                ["Operations", str(openapi["operations"])],
                ["Missing summary", str(openapi["missing_summary"])],
                ["Missing description", str(openapi["missing_description"])],
                ["Missing tags", str(openapi["missing_tags"])],
                ["Missing 4xx/5xx response", str(openapi["missing_error_response"])],
                ["Missing examples marker", str(openapi["missing_examples"])],
            ],
        ),
        "## Largest Files",
        _top_file_table(f"{base.label}", base.largest_files),
        _top_file_table(f"{current.label}", current.largest_files),
        "## Largest Functions",
        _top_function_table(f"{base.label}", base.largest_functions),
        _top_function_table(f"{current.label}", current.largest_functions),
        "## Most Complex Functions",
        _top_complexity_table(f"{base.label}", base.most_complex_functions),
        _top_complexity_table(f"{current.label}", current.most_complex_functions),
        "## Boundary Findings",
        _bounded_findings(
            f"Service boundary findings ({base.label})", base.service_boundary_violations
        ),
        _bounded_findings(
            "Service boundary findings (current branch)", current.service_boundary_violations
        ),
        _bounded_findings(
            f"Router infrastructure imports ({base.label})", base.router_infra_imports
        ),
        _bounded_findings(
            "Router infrastructure imports (current branch)", current.router_infra_imports
        ),
        "## Notes",
        "- This report is intentionally dependency-free and repeatable in local and CI environments.",
        "- It is a first measurable baseline; future phases can add radon, vulture, deptry, bandit, pip-audit, Spectral, import-linter, and coverage thresholds.",
    ]
    return "\n\n".join(sections) + "\n"


def build_report(base_ref: str = DEFAULT_BASE_REF) -> str:
    return build_refactor_report(_report_context(base_ref))


def build_baseline_report(context: HealthReportContext) -> str:
    current = context.current
    sections = [
        "# lotus-manage Baseline Quality Report",
        f"- Generated at: `{context.generated_at}`",
        f"- Baseline commit: `{context.current_ref}`",
        "- Mode: report-only baseline. This records current posture; it does not enforce "
        "thresholds by itself.",
        "## Current Code Size",
        _table(
            ["Metric", "Value"],
            [
                ["Python files", str(current.python_file_count)],
                ["Total Python LOC", str(current.total_loc)],
                ["Test functions", str(current.test_count)],
                ["Service boundary findings", str(len(current.service_boundary_violations))],
                ["Router infrastructure imports", str(len(current.router_infra_imports))],
            ],
        ),
        "## Current OpenAPI Completeness",
        _table(
            ["Metric", "Value"],
            [
                ["Operations", str(context.openapi["operations"])],
                ["Missing summary", str(context.openapi["missing_summary"])],
                ["Missing description", str(context.openapi["missing_description"])],
                ["Missing tags", str(context.openapi["missing_tags"])],
                ["Missing 4xx/5xx response", str(context.openapi["missing_error_response"])],
                ["Missing examples marker", str(context.openapi["missing_examples"])],
            ],
        ),
        "## Report-Only Coverage Map",
        _table(
            ["Quality area", "Current evidence", "Gate phase"],
            [
                ["Code size", "`scripts/engineering_health_report.py`", "1 - baseline"],
                ["Largest files/functions", "`quality/refactor_health_report.md`", "1 - baseline"],
                [
                    "OpenAPI completeness",
                    "`scripts/openapi_quality_gate.py` plus this report",
                    "2 - active/new-regression",
                ],
                [
                    "Service boundary leakage",
                    "service leakage scan plus this report",
                    "2 - active/new-regression",
                ],
                [
                    "Router infrastructure imports",
                    "reported as known baseline debt",
                    "1 - baseline",
                ],
                [
                    "Complexity/maintainability",
                    "`quality/complexity_report.md`",
                    "1 - baseline",
                ],
                [
                    "Dead code",
                    "vulture baseline capture via `quality-baseline.yml`",
                    "1 - report-only baseline",
                ],
                [
                    "Dependency hygiene",
                    "`deptry` + `pip check` via `quality-baseline.yml` and `make security-audit`",
                    "2 - active/new-regression",
                ],
                [
                    "Security",
                    "`bandit` + `pip-audit` via `quality-baseline.yml` and `make security-audit`",
                    "2 - active/new-regression",
                ],
                ["Documentation gaps", "current docs tests plus planned docs scorecard", "planned"],
                [
                    "Observability gaps",
                    "`scripts/validate_observability_contracts.py`; richer runtime gap report planned",
                    "2 - active/new-regression",
                ],
            ],
        ),
        "## Notes",
        "- Future slices should add optional-tool measurements without converting unstable baselines "
        "into blocking gates prematurely.",
    ]
    return "\n\n".join(sections) + "\n"


def build_quality_scorecard(context: HealthReportContext) -> str:
    rows = [
        ["Lint and formatting", "Active gate", "`make check` runs Ruff check and format check."],
        ["Type checking", "Active gate", "`make check` runs mypy over source files."],
        ["Unit tests", "Active gate", "`make check` runs `tests/unit`."],
        ["OpenAPI governance", "Active gate", "`scripts/openapi_quality_gate.py`."],
        ["API vocabulary", "Active gate", "`scripts/api_vocabulary_inventory.py --validate-only`."],
        [
            "Service boundary leakage",
            "Report plus focused scans",
            "Current service boundary findings: 0.",
        ],
        [
            "Router infrastructure imports",
            "Baseline debt",
            f"Current router infra imports: {len(context.current.router_infra_imports)}.",
        ],
        [
            "OpenAPI 4xx/5xx response markers",
            "Baseline debt",
            f"Current missing markers: {context.openapi['missing_error_response']}.",
        ],
        [
            "Complexity",
            "Report-only baseline",
            "`quality/complexity_report.md`; add thresholds after baseline review.",
        ],
        [
            "Dead code",
            "Report-only baseline",
            "`quality-baseline.yml` captures `vulture` output; add thresholds after baseline review.",
        ],
        [
            "Dependency architecture",
            "Report-only baseline",
            "`quality-baseline.yml` captures `importlinter` and `deptry`; add thresholds after baseline review.",
        ],
        [
            "Security depth",
            "Partially active",
            "`make security-audit` is active; `bandit` and `pip-audit` are report-only in `quality-baseline.yml`.",
        ],
        [
            "Documentation coverage",
            "Partially active",
            "Docs current-state tests exist; add docs-gap scoring later.",
        ],
        [
            "Observability",
            "Partially active",
            "Observability contract validator exists; add runtime posture scoring later.",
        ],
    ]
    sections = [
        "# lotus-manage Quality Scorecard",
        f"- Generated at: `{context.generated_at}`",
        f"- Current ref: `{context.current_ref}`",
        "- Purpose: make enterprise-readiness progress measurable without pretending report-only "
        "baselines are mature enforcement gates.",
        _table(["Area", "Status", "Evidence / next gate"], rows),
        "## Progressive Gate Policy",
        _table(
            ["Phase", "Meaning", "Current posture"],
            [
                [
                    "1 - baseline/report-only",
                    "Measure current posture without failing builds.",
                    "Active for refactor health and baseline report.",
                ],
                [
                    "2 - fail new regressions",
                    "Block newly introduced violations once the detector is stable.",
                    "Active for existing repo-native gates; planned for richer quality tools.",
                ],
                [
                    "3 - enforce thresholds",
                    "Require agreed numeric thresholds.",
                    "Not active for new quality tools yet.",
                ],
                [
                    "4 - enterprise-readiness gates",
                    "Block release on full readiness posture.",
                    "Target state, not yet complete.",
                ],
            ],
        ),
    ]
    return "\n\n".join(sections) + "\n"


def build_complexity_report(context: HealthReportContext) -> str:
    base = context.base
    current = context.current
    base_highest = base.most_complex_functions[0].complexity if base.most_complex_functions else 0
    current_highest = (
        current.most_complex_functions[0].complexity if current.most_complex_functions else 0
    )
    sections = [
        "# lotus-manage Complexity Report",
        f"- Generated at: `{context.generated_at}`",
        f"- Current ref: `{context.current_ref}`",
        "- Mode: report-only maintainability baseline using dependency-free AST branch counting.",
        "## Summary",
        _table(
            ["Metric", context.base_ref, "current branch", "Delta"],
            [
                [
                    "Reported top functions",
                    str(len(base.most_complex_functions)),
                    str(len(current.most_complex_functions)),
                    _delta(
                        len(current.most_complex_functions),
                        len(base.most_complex_functions),
                    ),
                ],
                [
                    "Highest complexity",
                    str(base_highest),
                    str(current_highest),
                    _delta(current_highest, base_highest),
                ],
            ],
        ),
        _top_complexity_table(
            "Most Complex Current Functions",
            current.most_complex_functions,
        ),
        _top_complexity_table(
            "Most Complex Current Source Functions",
            current.most_complex_source_functions,
        ),
        _top_complexity_table(
            "Most Complex Current Test Functions",
            current.most_complex_test_functions,
        ),
        "## Gate Posture",
        "- This report is phase 1/report-only. It intentionally does not fail builds until the "
        "baseline is reviewed and thresholds are agreed.",
    ]
    return "\n\n".join(sections) + "\n"


def build_architecture_rules() -> str:
    return """# lotus-manage Architecture Rules

These rules define the report-only architecture baseline for the enterprise-readiness refactor.
They are explicit so later validators can enforce them without changing their meaning.

## Layering

1. Routers call application services or use-case functions only.
2. Routers must not call repositories, database clients, HTTP clients, Kafka, Redis, or downstream adapters directly.
3. Middleware stays thin, cross-cutting, and business-logic-free.
4. Domain and application code must not depend on FastAPI, framework objects, infrastructure clients, or persistence models.
5. Infrastructure sits behind explicit ports/adapters.
6. DTOs and persistence models must not leak into domain logic.

## Reliability And Auditability

1. Downstream failures map to consistent platform errors.
2. Every request must support and propagate a correlation identifier.
3. Relevant mutations must be auditable.
4. Idempotent operations must define replay/conflict behavior.
5. Logs must be structured and must not leak sensitive data.

## Current Gate Phase

These rules are in phase 1/report-only except for checks already covered by repo-native gates.
"""


def build_api_governance_rules() -> str:
    return """# lotus-manage API Governance Rules

These rules define the report-only API-governance baseline for the enterprise-readiness refactor.

## OpenAPI Contract

1. Every endpoint should have a summary, description, tags, stable operation ID, request/response model, examples, and standard errors.
2. Error responses should use consistent platform problem-details semantics where applicable.
3. Public and internal endpoints should remain clearly separated.
4. Health, readiness, liveness, metrics, internal, and public endpoints should be documented as distinct operational surfaces.

## API Behavior

1. Pagination, filtering, sorting, versioning, and deprecation should be consistent across list/read APIs.
2. Correlation IDs should be accepted or generated and propagated to downstream calls.
3. Idempotent mutations should document idempotency key behavior, replay behavior, and conflict behavior.
4. Downstream unavailable/degraded states should be exposed as bounded supportability posture rather than hidden behind generic success.

## Current Gate Phase

OpenAPI and API vocabulary checks are active repo-native gates. The broader rule set is phase
1/report-only until each detector has a stable baseline and agreed thresholds.
"""


def write_reports(context: HealthReportContext) -> None:
    outputs = {
        DEFAULT_OUTPUT: build_refactor_report(context),
        DEFAULT_BASELINE_OUTPUT: build_baseline_report(context),
        DEFAULT_SCORECARD_OUTPUT: build_quality_scorecard(context),
        DEFAULT_COMPLEXITY_OUTPUT: build_complexity_report(context),
        DEFAULT_ARCHITECTURE_RULES_OUTPUT: build_architecture_rules(),
        DEFAULT_API_GOVERNANCE_RULES_OUTPUT: build_api_governance_rules(),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> None:
    context = _report_context()
    write_reports(context)
    for path in (
        DEFAULT_OUTPUT,
        DEFAULT_BASELINE_OUTPUT,
        DEFAULT_SCORECARD_OUTPUT,
        DEFAULT_COMPLEXITY_OUTPUT,
        DEFAULT_ARCHITECTURE_RULES_OUTPUT,
        DEFAULT_API_GOVERNANCE_RULES_OUTPUT,
    ):
        print(f"Wrote {path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
