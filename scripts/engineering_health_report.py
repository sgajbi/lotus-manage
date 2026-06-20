from __future__ import annotations

import ast
import argparse
import io
import subprocess
import sys
import tarfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


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
    "from fastapi",
    "import fastapi",
    "from starlette",
    "import starlette",
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


ReportBuilder = Callable[[HealthReportContext], str]
ReportOutput = tuple[Path, ReportBuilder]


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


def _git_status_porcelain() -> str:
    return _git("status", "--porcelain")


def _report_source_snapshot() -> str:
    short_head = _git("rev-parse", "--short", "HEAD").strip()
    suffix = "+worktree" if _git_status_porcelain().strip() else ""
    return f"{short_head}{suffix}"


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
        current_ref=_report_source_snapshot(),
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
        f"- Report source snapshot: `{context.current_ref}`",
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
        f"- Report source snapshot: `{context.current_ref}`",
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
                    "`scripts/router_infrastructure_gate.py` plus this report",
                    "2 - active/new-regression",
                ],
                [
                    "Complexity/maintainability",
                    "`quality/complexity_report.md`",
                    "2 - active source C gate; broader metrics baseline",
                ],
                [
                    "Duplicate implementation hotspots",
                    "`quality/duplicate_code_inventory.md` and `make duplicate-implementation-gate`",
                    "2 - active exact-duplicate non-regression gate",
                ],
                [
                    "Dead code",
                    "`make dead-code-gate` plus vulture baseline capture via `quality-baseline.yml`",
                    "2 - active/new-regression",
                ],
                [
                    "Dependency hygiene",
                    "`make dependency-hygiene-gate`, `pip check`, and `make security-audit`",
                    "2 - active/new-regression",
                ],
                [
                    "Security",
                    "`bandit` + project-scoped `pip-audit` via `quality-baseline.yml` and `make security-audit`",
                    "2 - active/new-regression",
                ],
                ["Documentation gaps", "current docs tests plus planned docs scorecard", "planned"],
                [
                    "Observability gaps",
                    "`scripts/validate_observability_contracts.py`; richer runtime gap report planned",
                    "2 - active/new-regression",
                ],
                [
                    "Demo certification",
                    "`make demo-certify` plus manual live workflow; command-contract tests in Quality Baseline",
                    "1 - manual/report-only live evidence",
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
        ["Service boundary", "Active gate", "`scripts/service_boundary_gate.py`."],
        [
            "Router infrastructure imports",
            "Active gate",
            "`scripts/router_infrastructure_gate.py`.",
        ],
        [
            "OpenAPI 4xx/5xx response markers",
            "Baseline debt",
            f"Current missing markers: {context.openapi['missing_error_response']}.",
        ],
        [
            "Complexity",
            "Active source C gate",
            "`make complexity-gate` blocks Radon C-or-worse source functions; `quality/complexity_report.md` keeps broader source/test metrics report-only.",
        ],
        [
            "Duplicate implementation hotspots",
            "Active exact-duplicate non-regression gate",
            "`make duplicate-implementation-gate` blocks newly introduced exact non-trivial Python function-body duplicates; `quality/duplicate_implementation_baseline.json` governs current accepted groups.",
        ],
        [
            "Quality report freshness",
            "Active gate",
            "`make quality-report-gate` blocks stale checked-in quality reports while ignoring volatile report provenance.",
        ],
        [
            "Workflow policy",
            "Active gate",
            "`make workflow-policy-gate` blocks unpinned action refs, permission creep, blocking quality-report drift, coverage-gate drift, and PR evidence drift.",
        ],
        [
            "Local CI parity",
            "Active gate",
            "`make check`, `make ci`, and `make ci-local` share `make static-quality-gates` so local proof cannot omit active static gates.",
        ],
        [
            "Coverage gate parity",
            "Active gate",
            "`scripts/coverage_gate.py` is the shared local and GitHub combined coverage gate.",
        ],
        [
            "Dead code",
            "Active gate",
            "`make dead-code-gate` runs vulture over `src` and `tests`; baseline workflow still captures expanded output.",
        ],
        [
            "Dependency architecture",
            "Active gate",
            "`make architecture-gate` and `make dependency-hygiene-gate` run import-linter and deptry.",
        ],
        [
            "Security depth",
            "Active project dependency gate",
            "`make security-audit` runs high-severity Bandit over `src` plus project-scoped "
            "`python -m pip_audit .`; `quality-baseline.yml` captures the same scanner family "
            "as report-only evidence.",
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
        [
            "Demo certification",
            "Manual/report-only live evidence",
            "`make demo-certify` certifies canonical live API demo proof and writes JSON evidence; "
            "`demo-certification.yml` is manual, while `quality-baseline.yml` keeps deterministic "
            "command-contract tests report-only until CI has a stable canonical stack lane.",
        ],
    ]
    sections = [
        "# lotus-manage Quality Scorecard",
        f"- Generated at: `{context.generated_at}`",
        f"- Report source snapshot: `{context.current_ref}`",
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
        f"- Report source snapshot: `{context.current_ref}`",
        "- Mode: active source C-or-worse gate via `make complexity-gate`; broader dependency-free "
        "AST branch metrics remain report-only.",
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
        "- Source functions at Radon C-or-worse are actively blocked by `make complexity-gate` "
        "(`python -m radon cc src -s -n C`).",
        "- Broader source/test complexity rankings in this report remain report-only until "
        "baselines, false positives, lane placement, and exception policy are clear.",
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
5. Service modules must not import FastAPI or Starlette transport packages.
6. Infrastructure sits behind explicit ports/adapters.
7. DTOs and persistence models must not leak into domain logic.

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


REPORT_OUTPUT_BUILDERS: tuple[ReportOutput, ...] = (
    (DEFAULT_OUTPUT, build_refactor_report),
    (DEFAULT_BASELINE_OUTPUT, build_baseline_report),
    (DEFAULT_SCORECARD_OUTPUT, build_quality_scorecard),
    (DEFAULT_COMPLEXITY_OUTPUT, build_complexity_report),
    (DEFAULT_ARCHITECTURE_RULES_OUTPUT, lambda _context: build_architecture_rules()),
    (DEFAULT_API_GOVERNANCE_RULES_OUTPUT, lambda _context: build_api_governance_rules()),
)


def build_report_outputs(context: HealthReportContext) -> dict[Path, str]:
    return {path: builder(context) for path, builder in REPORT_OUTPUT_BUILDERS}


def write_reports(context: HealthReportContext) -> None:
    for path, content in build_report_outputs(context).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _normalize_report_for_check(content: str) -> str:
    return "\n".join(
        "- Volatile report provenance: `<ignored>`"
        if line.startswith(("- Generated at: `", "- Report source snapshot: `"))
        else line
        for line in content.splitlines()
    )


def stale_report_paths(context: HealthReportContext) -> list[Path]:
    stale_paths: list[Path] = []
    for path, expected_content in build_report_outputs(context).items():
        if not path.exists():
            stale_paths.append(path)
            continue
        current_content = path.read_text(encoding="utf-8")
        if _normalize_report_for_check(current_content) != _normalize_report_for_check(
            expected_content
        ):
            stale_paths.append(path)
    return stale_paths


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or verify Lotus quality reports.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when checked-in quality reports are stale, ignoring volatile report provenance.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    context = _report_context()
    if args.check:
        stale_paths = stale_report_paths(context)
        if stale_paths:
            print("Quality reports are stale. Regenerate them with:")
            print("  python scripts/engineering_health_report.py")
            for path in stale_paths:
                print(f"Stale: {path.relative_to(REPO_ROOT).as_posix()}")
            raise SystemExit(1)
        print("Quality reports are current.")
        return

    write_reports(context)
    for path, _builder in REPORT_OUTPUT_BUILDERS:
        print(f"Wrote {path.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
