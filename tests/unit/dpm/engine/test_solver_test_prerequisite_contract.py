"""Keep required solver proofs fail-closed instead of timing-sensitive."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path


SOLVER_TEST_FILES = (
    Path("tests/unit/dpm/engine/test_engine_solver_behavior.py"),
    Path("tests/unit/dpm/engine/test_engine_target_generation.py"),
    Path("tests/unit/dpm/golden/test_golden_scenarios.py"),
    Path("tests/e2e/demo/test_demo_scenarios.py"),
)
SOLVER_PREREQUISITE_FILE = Path("tests/shared/solver_prerequisites.py")
SOLVER_PREREQUISITE_MODULE = "tests.shared.solver_prerequisites"
SOLVER_PREREQUISITE_FUNCTION = "require_solver_test_dependencies"
DEPENDENCY_PROBE_IMPORT_ROOTS = {"importlib", "pkgutil", "subprocess"}
SOLVER_DEPENDENCY_IMPORT_ROOTS = {"cvxpy", "numpy"}
SOLVER_CAPABILITY_MODULE = "src.core.common.capabilities"
REQUIREMENT_NAME_END = re.compile(r"[\s\[<>=!~;@]")


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = _dotted_name(node.value)
        return None if owner is None else f"{owner}.{node.attr}"
    return None


def _imports_solver_dependency(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(
            alias.name.partition(".")[0] in SOLVER_DEPENDENCY_IMPORT_ROOTS for alias in node.names
        )
    return (
        isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.partition(".")[0] in SOLVER_DEPENDENCY_IMPORT_ROOTS
    )


def _caught_exception_names(node: ast.expr | None) -> set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Tuple):
        return {name for item in node.elts if (name := _dotted_name(item)) is not None}
    name = _dotted_name(node)
    return set() if name is None else {name}


def _normalized_requirement_name(requirement: str) -> str:
    name = REQUIREMENT_NAME_END.split(requirement.strip(), maxsplit=1)[0]
    return re.sub(r"[-_.]+", "-", name).lower()


def test_solver_packages_are_required_direct_test_dependencies() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]

    dev_dependencies = project["optional-dependencies"]["dev"]
    direct_dependency_names = {
        _normalized_requirement_name(dependency) for dependency in dev_dependencies
    }

    assert SOLVER_DEPENDENCY_IMPORT_ROOTS <= direct_dependency_names


def test_solver_prerequisite_imports_dependencies_at_module_load() -> None:
    tree = ast.parse(
        SOLVER_PREREQUISITE_FILE.read_text(encoding="utf-8"),
        filename=str(SOLVER_PREREQUISITE_FILE),
    )
    imported_roots = {
        alias.name.partition(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.partition(".")[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert SOLVER_DEPENDENCY_IMPORT_ROOTS <= imported_roots


def _module_load_prerequisite_calls(tree: ast.Module) -> set[str]:
    prerequisite_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == SOLVER_PREREQUISITE_MODULE
        for alias in node.names
        if alias.name == SOLVER_PREREQUISITE_FUNCTION
    }
    return {
        node.value.func.id
        for node in tree.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id in prerequisite_names
    }


def test_required_solver_proofs_cannot_skip_or_probe_dependency_availability() -> None:
    violations: list[str] = []
    for path in SOLVER_TEST_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assert _module_load_prerequisite_calls(tree), (
            f"{path} must call the solver prerequisite directly at module load"
        )
        pytest_modules = {"pytest"}
        pytest_marks: set[str] = set()
        pytest_skip_calls: set[str] = set()
        unittest_modules = {"unittest"}
        unittest_case_modules = {"unittest.case"}
        unittest_skip_calls: set[str] = set()
        unittest_skip_exceptions: set[str] = set()
        solver_capability_modules = {SOLVER_CAPABILITY_MODULE}
        solver_capability_calls = {"has_solver_dependencies"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pytest_modules.update(
                    alias.asname or alias.name for alias in node.names if alias.name == "pytest"
                )
                unittest_modules.update(
                    alias.asname or alias.name for alias in node.names if alias.name == "unittest"
                )
                unittest_case_modules.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "unittest.case"
                )
                for alias in node.names:
                    if SOLVER_CAPABILITY_MODULE == alias.name:
                        solver_capability_modules.add(alias.asname or alias.name)
                    elif alias.asname and SOLVER_CAPABILITY_MODULE.startswith(f"{alias.name}."):
                        suffix = SOLVER_CAPABILITY_MODULE.removeprefix(f"{alias.name}.")
                        solver_capability_modules.add(f"{alias.asname}.{suffix}")
            if isinstance(node, ast.ImportFrom) and node.module == "pytest":
                for alias in node.names:
                    local_name = alias.asname or alias.name
                    if alias.name == "mark":
                        pytest_marks.add(local_name)
                    if alias.name in {"skip", "skipif", "importorskip", "xfail"}:
                        pytest_skip_calls.add(local_name)
            if isinstance(node, ast.ImportFrom) and node.module in {"unittest", "unittest.case"}:
                for alias in node.names:
                    if node.module == "unittest" and alias.name == "case":
                        unittest_case_modules.add(alias.asname or alias.name)
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
            if (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and SOLVER_CAPABILITY_MODULE.startswith(f"{node.module}.")
            ):
                remaining_path = SOLVER_CAPABILITY_MODULE.removeprefix(f"{node.module}.")
                expected_symbol, _, suffix = remaining_path.partition(".")
                for alias in node.names:
                    if alias.name == expected_symbol:
                        local_name = alias.asname or alias.name
                        solver_capability_modules.add(
                            local_name if not suffix else f"{local_name}.{suffix}"
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
            *(f"{module}.case.skip" for module in unittest_modules),
            *(f"{module}.case.skipIf" for module in unittest_modules),
            *(f"{module}.case.skipUnless" for module in unittest_modules),
            *(f"{module}.case.expectedFailure" for module in unittest_modules),
            *(f"{module}.case.SkipTest" for module in unittest_modules),
            *(f"{module}.skip" for module in unittest_case_modules),
            *(f"{module}.skipIf" for module in unittest_case_modules),
            *(f"{module}.skipUnless" for module in unittest_case_modules),
            *(f"{module}.expectedFailure" for module in unittest_case_modules),
            *(f"{module}.SkipTest" for module in unittest_case_modules),
            *(f"{module}.has_solver_dependencies" for module in solver_capability_modules),
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.partition(".")[0] in DEPENDENCY_PROBE_IMPORT_ROOTS:
                        violations.append(f"{path}:{node.lineno}: import {alias.name}")
            if (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and node.module.partition(".")[0] in DEPENDENCY_PROBE_IMPORT_ROOTS
            ):
                violations.append(f"{path}:{node.lineno}: from {node.module}")
            if isinstance(node, ast.Try) and any(
                _imports_solver_dependency(descendant)
                for statement in node.body
                for descendant in ast.walk(statement)
            ):
                violations.append(f"{path}:{node.lineno}: guarded solver dependency import")
            if isinstance(node, ast.ExceptHandler) and any(
                name.rpartition(".")[2] in {"ImportError", "ModuleNotFoundError"}
                for name in _caught_exception_names(node.type)
            ):
                violations.append(f"{path}:{node.lineno}: swallowed dependency import failure")
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
