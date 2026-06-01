from __future__ import annotations

import ast
import subprocess
import sys
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
class SnapshotMetrics:
    label: str
    python_file_count: int
    total_loc: int
    test_count: int
    largest_files: list[FileMetric]
    largest_functions: list[FunctionMetric]
    service_boundary_violations: list[str]
    router_infra_imports: list[str]


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


def _python_paths_from_git(ref: str) -> list[str]:
    paths = _git("ls-tree", "-r", "--name-only", ref).splitlines()
    return [
        path
        for path in paths
        if path.endswith(".py") and path.startswith(tuple(f"{root}/" for root in PYTHON_ROOTS))
    ]


def _python_paths_from_worktree() -> list[str]:
    paths: list[str] = []
    for root in PYTHON_ROOTS:
        for path in (REPO_ROOT / root).rglob("*.py"):
            if any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts):
                continue
            paths.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(paths)


def _text_from_git(ref: str, path: str) -> str:
    return _git("show", f"{ref}:{path}")


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
        if path.startswith("tests/"):
            test_count += _test_count(text)
        if path.startswith("src/api/services/"):
            service_boundary_violations.extend(
                _matching_lines(path, text, SERVICE_LEAKAGE_PATTERNS)
            )
        if path.startswith("src/api/routers/"):
            router_infra_imports.extend(_matching_lines(path, text, ROUTER_INFRA_PATTERNS))
    return SnapshotMetrics(
        label=label,
        python_file_count=len(paths),
        total_loc=total_loc,
        test_count=test_count,
        largest_files=sorted(files, key=lambda item: item.lines, reverse=True)[:10],
        largest_functions=sorted(functions, key=lambda item: item.lines, reverse=True)[:10],
        service_boundary_violations=service_boundary_violations,
        router_infra_imports=router_infra_imports,
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


def build_report(base_ref: str = DEFAULT_BASE_REF) -> str:
    base_paths = _python_paths_from_git(base_ref)
    current_paths = _python_paths_from_worktree()
    base = _snapshot_metrics(
        label=base_ref,
        paths=base_paths,
        reader=lambda path: _text_from_git(base_ref, path),
    )
    current = _snapshot_metrics(
        label="current branch",
        paths=current_paths,
        reader=_text_from_worktree,
    )
    openapi = _openapi_metrics()
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    sections = [
        "# lotus-manage Refactor Health Report",
        f"- Generated at: `{generated_at}`",
        f"- Baseline ref: `{base_ref}`",
        f"- Current ref: `{_git('rev-parse', '--short', 'HEAD').strip()}`",
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


def main() -> None:
    report = build_report()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(report, encoding="utf-8")
    print(f"Wrote {DEFAULT_OUTPUT.relative_to(REPO_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
