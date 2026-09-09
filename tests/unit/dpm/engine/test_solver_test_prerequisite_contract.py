"""Keep required solver proofs fail-closed instead of timing-sensitive."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path


SOLVER_TEST_FILES = (
    Path("tests/unit/dpm/engine/test_engine_solver_behavior.py"),
    Path("tests/unit/dpm/engine/test_engine_target_generation.py"),
    Path("tests/unit/dpm/golden/test_golden_scenarios.py"),
    Path("tests/e2e/demo/test_demo_scenarios.py"),
)


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _dotted_name(node.value)
        return None if owner is None else f"{owner}.{node.attr}"
    return None


def test_cvxpy_is_a_required_test_dependency() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]

    dev_dependencies = project["optional-dependencies"]["dev"]
    assert any(dependency.startswith("cvxpy") for dependency in dev_dependencies)


def test_required_solver_proofs_cannot_skip_or_use_a_subprocess_probe() -> None:
    violations: list[str] = []
    for path in SOLVER_TEST_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        pytest_modules = {"pytest"}
        pytest_marks: set[str] = set()
        pytest_skip_calls: set[str] = set()
        unittest_modules = {"unittest"}
        unittest_skip_calls: set[str] = set()
        unittest_skip_exceptions: set[str] = set()
        solver_capability_modules = {"src.core.common.capabilities"}
        solver_capability_calls = {"has_solver_dependencies"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pytest_modules.update(
                    alias.asname or alias.name for alias in node.names if alias.name == "pytest"
                )
                unittest_modules.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {"unittest", "unittest.case"}
                )
                solver_capability_modules.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "src.core.common.capabilities"
                )
            if isinstance(node, ast.ImportFrom) and node.module == "pytest":
                for alias in node.names:
                    local_name = alias.asname or alias.name
                    if alias.name == "mark":
                        pytest_marks.add(local_name)
                    if alias.name in {"skip", "skipif", "importorskip", "xfail"}:
                        pytest_skip_calls.add(local_name)
            if isinstance(node, ast.ImportFrom) and node.module in {"unittest", "unittest.case"}:
                for alias in node.names:
                    if alias.name in {"skip", "skipIf", "skipUnless", "expectedFailure"}:
                        unittest_skip_calls.add(alias.asname or alias.name)
                    if alias.name == "SkipTest":
                        unittest_skip_exceptions.add(alias.asname or alias.name)
            if isinstance(node, ast.ImportFrom) and node.module == "src.core.common.capabilities":
                solver_capability_calls.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "has_solver_dependencies"
                )

        forbidden_attributes = {
            *(f"{module}.skip" for module in pytest_modules),
            *(f"{module}.importorskip" for module in pytest_modules),
            *(f"{module}.xfail" for module in pytest_modules),
            *(f"{module}.mark.skip" for module in pytest_modules),
            *(f"{module}.mark.skipif" for module in pytest_modules),
            *(f"{module}.mark.xfail" for module in pytest_modules),
            *(f"{mark}.skip" for mark in pytest_marks),
            *(f"{mark}.skipif" for mark in pytest_marks),
            *(f"{mark}.xfail" for mark in pytest_marks),
            *(f"{module}.skip" for module in unittest_modules),
            *(f"{module}.skipIf" for module in unittest_modules),
            *(f"{module}.skipUnless" for module in unittest_modules),
            *(f"{module}.expectedFailure" for module in unittest_modules),
            *(f"{module}.SkipTest" for module in unittest_modules),
            *(f"{module}.has_solver_dependencies" for module in solver_capability_modules),
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name == "subprocess" for alias in node.names
            ):
                violations.append(f"{path}:{node.lineno}: import subprocess")
            if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                violations.append(f"{path}:{node.lineno}: from subprocess")
            dotted_name = _dotted_name(node) if isinstance(node, ast.Attribute) else None
            if dotted_name in forbidden_attributes or (
                dotted_name is not None and dotted_name.endswith(".skipTest")
            ):
                violations.append(f"{path}:{node.lineno}: {dotted_name}")
            if isinstance(node, ast.Name) and node.id in unittest_skip_exceptions:
                violations.append(f"{path}:{node.lineno}: {node.id}")
            if isinstance(node, ast.Call):
                call_name = _dotted_name(node.func)
                if call_name in pytest_skip_calls | unittest_skip_calls | solver_capability_calls:
                    violations.append(f"{path}:{node.lineno}: {call_name}")

    assert violations == []
