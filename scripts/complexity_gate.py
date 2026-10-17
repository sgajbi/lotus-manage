"""Read-only Radon function/method non-degradation gate for first-party source."""

from __future__ import annotations

import argparse
import ast
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_NEW_COMPLEXITY = 10
BASELINE_PREFIX = "- Baseline source snapshot: `"
MAINLINE_NAMES = {"main", "master"}
Scanner = Callable[[ast.AST], list[Any]]


class GateError(ValueError):
    """The input or measurement cannot establish a valid complexity comparison."""


@dataclass(frozen=True)
class FunctionComplexity:
    path: str
    name: str
    line: int
    complexity: int

    @property
    def identity(self) -> tuple[str, str]:
        return self.path, self.name


@dataclass(frozen=True)
class Evaluation:
    violations: tuple[str, ...]
    legacy_debt: tuple[FunctionComplexity, ...]


def git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def resolve_commit(repo_root: Path, ref: str) -> str:
    if not ref or ref.startswith("-"):
        raise GateError("Baseline ref must name a Git commit")
    resolved = git(repo_root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if not re.fullmatch(r"[0-9a-f]{40}", resolved):
        raise GateError("Git did not resolve an immutable commit SHA")
    return resolved


def recorded_baseline(repo_root: Path) -> str | None:
    report = repo_root / "quality/refactor_health_report.md"
    if not report.exists():
        return None
    lines = [
        line
        for line in report.read_text(encoding="utf-8").splitlines()
        if line.startswith(BASELINE_PREFIX)
    ]
    if len(lines) != 1 or not re.fullmatch(re.escape(BASELINE_PREFIX) + r"[0-9a-f]{40}`", lines[0]):
        raise GateError("Recorded quality baseline must contain exactly one immutable commit SHA")
    return lines[0][len(BASELINE_PREFIX) : -1]


def select_baseline(repo_root: Path, explicit_ref: str | None = None) -> str:
    """Pin the actual integration baseline, distinct from historical report provenance."""
    head = resolve_commit(repo_root, "HEAD")
    recorded = recorded_baseline(repo_root)
    if recorded is not None:
        resolve_commit(
            repo_root, recorded
        )  # An unresolved recorded baseline never silently falls back.
    branch = os.environ.get("LOTUS_QUALITY_REF_NAME") or os.environ.get("GITHUB_REF_NAME")
    branch = branch or git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    if explicit_ref is not None:
        candidate = explicit_ref
    elif branch in MAINLINE_NAMES:
        candidate = "HEAD" if source_differs_from_commit(repo_root, head) else "HEAD^"
    else:
        candidate = f"origin/{os.environ.get('GITHUB_BASE_REF') or 'main'}"
    baseline = resolve_commit(repo_root, candidate)
    ancestor = resolve_commit(repo_root, git(repo_root, "merge-base", head, baseline))
    if explicit_ref is not None and ancestor != baseline:
        raise GateError("Explicit baseline must be an ancestor of HEAD")
    if baseline == head and (
        explicit_ref is not None or not source_differs_from_commit(repo_root, head)
    ):
        raise GateError(
            "Baseline and current source are identical; comparing source to itself is forbidden"
        )
    return baseline


def source_differs_from_commit(repo_root: Path, commit: str) -> bool:
    """Compare actual source snapshots, including untracked Python source, before allowing HEAD."""
    return baseline_sources(repo_root, commit) != current_sources(repo_root)


def is_mainline(repo_root: Path) -> bool:
    branch = os.environ.get("LOTUS_QUALITY_REF_NAME") or os.environ.get("GITHUB_REF_NAME")
    return (branch or git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")) in MAINLINE_NAMES


def release_baseline(repo_root: Path, head: str) -> str:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        candidate = event.get("before")
        if not isinstance(candidate, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate):
            raise GateError("Main push event must pin its before commit")
    else:
        candidate = recorded_baseline(repo_root)
    if candidate is None:
        raise GateError("Main release history requires a recorded or push-before baseline")
    baseline = resolve_commit(repo_root, candidate)
    if baseline == head or git(repo_root, "merge-base", head, baseline) != baseline:
        raise GateError("Main release baseline must be a distinct ancestor of HEAD")
    return baseline


def released_revision_violations(repo_root: Path, scanner: Scanner) -> tuple[str, ...]:
    """Audit every released first-parent revision, including intermediate rebased commits."""
    if not is_mainline(repo_root):
        return ()
    head = resolve_commit(repo_root, "HEAD")
    if source_differs_from_commit(repo_root, head):
        print(
            "Uncommitted Main source: development comparison only; release history is not qualified."
        )
        return ()
    baseline = release_baseline(repo_root, head)
    revisions = git(
        repo_root, "rev-list", "--first-parent", "--reverse", f"{baseline}..{head}", "--"
    ).splitlines()
    if not revisions:
        raise GateError("Main release revision range is empty")
    violations: list[str] = []
    previous_revision = baseline
    previous = measure_sources(baseline_sources(repo_root, baseline), scanner)
    for ref in revisions:
        revision = resolve_commit(repo_root, ref)
        predecessor = resolve_commit(repo_root, f"{revision}^")
        if predecessor != previous_revision:
            raise GateError("Main release baseline must be on the first-parent release chain")
        current = measure_sources(baseline_sources(repo_root, revision), scanner)
        violations.extend(
            f"released revision {revision}: {item}"
            for item in evaluate(previous, current).violations
        )
        previous, previous_revision = current, revision
    print(
        f"Main release history: {baseline}..{head}; audited {len(revisions)} first-parent revisions."
    )
    return tuple(violations)


def baseline_sources(repo_root: Path, baseline: str) -> dict[str, str]:
    result = subprocess.run(
        ["git", "archive", "--format=tar", baseline, "--", "src"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    texts: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            if (
                not member.isfile()
                or not member.name.startswith("src/")
                or not member.name.endswith(".py")
            ):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise GateError(f"Cannot read baseline source: {member.name}")
            texts[member.name] = (
                stream.read().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
            )
    return texts


def current_sources(repo_root: Path) -> dict[str, str]:
    root = repo_root / "src"
    if not root.is_dir():
        raise GateError("Source directory is missing")
    return {
        path.relative_to(repo_root).as_posix(): path.read_text(encoding="utf-8-sig")
        for path in sorted(root.rglob("*.py"))
    }


class FunctionNames(ast.NodeVisitor):
    """Lexical identities only; Radon remains the sole complexity implementation."""

    def __init__(self) -> None:
        self.scope: list[str] = []
        self.occurrences: dict[tuple[str, ...], int] = {}
        self.functions: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def scoped_visit(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        key = (*self.scope, node.name)
        occurrence = self.occurrences.get(key, 0) + 1
        self.occurrences[key] = occurrence
        name = node.name if occurrence == 1 else f"{node.name}#{occurrence}"
        self.scope.append(name)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            self.functions.append((".".join(self.scope), node))
        self.generic_visit(node)
        self.scope.pop()

    visit_ClassDef = scoped_visit
    visit_FunctionDef = scoped_visit
    visit_AsyncFunctionDef = scoped_visit


def radon_scanner() -> Scanner:
    module = importlib.import_module("radon.complexity")
    return cast(Scanner, module.cc_visit_ast)


def measure_sources(texts: Mapping[str, str], scanner: Scanner) -> tuple[FunctionComplexity, ...]:
    if not texts:
        raise GateError("Source snapshot is empty")
    metrics: list[FunctionComplexity] = []
    for path, source in sorted(texts.items()):
        tree = ast.parse(source, filename=path)
        names = FunctionNames()
        names.visit(tree)
        for name, node in names.functions:
            blocks = scanner(node)
            matches = [
                block
                for block in blocks
                if (block.lineno, block.col_offset, block.name)
                == (node.lineno, node.col_offset, node.name)
            ]
            if len(matches) != 1:
                raise GateError(f"Radon did not uniquely measure {path}:{name}")
            score = matches[0].complexity
            if type(score) is not int or score < 1:
                raise GateError(f"Invalid Radon score for {path}:{name}")
            metrics.append(FunctionComplexity(path, name, node.lineno, score))
    if not metrics:
        raise GateError("Source snapshot contains no functions or methods")
    return tuple(metrics)


def evaluate(
    baseline: tuple[FunctionComplexity, ...], current: tuple[FunctionComplexity, ...]
) -> Evaluation:
    if not baseline or not current:
        raise GateError("Baseline and current function measurements must both be nonempty")
    previous = {metric.identity: metric.complexity for metric in baseline}
    violations: list[str] = []
    debt: list[FunctionComplexity] = []
    for metric in current:
        old_score = previous.get(metric.identity)
        ceiling = max(MAX_NEW_COMPLEXITY, old_score or 0)
        if metric.complexity > ceiling:
            reason = "new function/method" if old_score is None else f"baseline CC {old_score}"
            violations.append(
                f"{metric.path}:{metric.line} {metric.name}: CC {metric.complexity} exceeds {ceiling} ({reason})"
            )
        elif metric.complexity > MAX_NEW_COMPLEXITY:
            debt.append(metric)
    return Evaluation(tuple(violations), tuple(debt))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref", help="Explicit ancestor commit; otherwise use quality-report baseline policy"
    )
    args = parser.parse_args(argv)
    try:
        baseline = select_baseline(REPO_ROOT, args.base_ref)
        scanner = radon_scanner()
        old = measure_sources(baseline_sources(REPO_ROOT, baseline), scanner)
        current = measure_sources(current_sources(REPO_ROOT), scanner)
        result = evaluate(old, current)
        released_violations = released_revision_violations(REPO_ROOT, scanner)
    except Exception as exc:
        print(
            f"Complexity gate cannot establish a valid comparison: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1
    print(
        f"Radon function/method policy: new CC <= {MAX_NEW_COMPLEXITY}; existing high CC cannot increase. Baseline: {baseline}"
    )
    print(
        f"Measured {len(old)} baseline and {len(current)} current functions/methods; {len(result.legacy_debt)} unchanged/improved legacy findings remain measured debt."
    )
    print("Class aggregates and maintainability index remain report-only.")
    for metric in result.legacy_debt:
        print(f"LEGACY DEBT {metric.path}:{metric.line} {metric.name}: CC {metric.complexity}")
    for violation in result.violations:
        print(f"FAIL {violation}")
    for violation in released_violations:
        print(f"FAIL {violation}")
    return 1 if result.violations or released_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
