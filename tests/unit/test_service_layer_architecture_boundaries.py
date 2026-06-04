from __future__ import annotations

import ast
from pathlib import Path


SERVICE_DIR = Path("src/api/services")
ALLOWED_INFRASTRUCTURE_IMPORTS: dict[str, set[str]] = {
    "src/api/services/authority_client_service.py": {
        "src.infrastructure.advise_authority",
        "src.infrastructure.risk_authority",
    },
    "src/api/services/core_resolver_service.py": {
        "src.infrastructure.core_sourcing",
    },
    "src/api/services/rebalance_policy_pack_repository.py": {
        "src.infrastructure.dpm_policy_packs",
    },
    "src/api/services/rebalance_run_support_repository.py": {
        "src.infrastructure.rebalance_runs",
    },
}


def _iter_service_files() -> list[Path]:
    return sorted(SERVICE_DIR.glob("**/*.py"))


def _extract_banned_import_messages(module_path: Path) -> list[str]:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    messages: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("src.api.routers"):
                messages.append(
                    f"{module_path.as_posix()}: imports service-layer-router module '{module}'"
                )
            if module == "fastapi":
                forbidden = {
                    alias.name
                    for alias in node.names
                    if alias.name in {"HTTPException", "status", "Request"}
                }
                if forbidden:
                    for name in sorted(forbidden):
                        messages.append(
                            f"{module_path.as_posix()}: imports '{name}' from fastapi layer"
                        )
            if module.startswith("fastapi") and module != "fastapi":
                messages.append(f"{module_path.as_posix()}: imports fastapi submodule '{module}'")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.api.routers"):
                    messages.append(
                        f"{module_path.as_posix()}: imports service-layer-router package '{alias.name}'"
                    )

    return messages


def _extract_banned_infrastructure_messages(module_path: Path) -> list[str]:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    messages: list[str] = []
    observed_imports: set[str] = set()
    expected_imports = ALLOWED_INFRASTRUCTURE_IMPORTS.get(
        module_path.as_posix(),
        set(),
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "src.infrastructure":
                messages.append(
                    f"{module_path.as_posix()}: imports top-level infrastructure package '{module}'"
                )
            elif module.startswith("src.infrastructure"):
                if module not in expected_imports:
                    messages.append(
                        f"{module_path.as_posix()}: imports infrastructure module '{module}'"
                    )
                observed_imports.add(module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("src.infrastructure"):
                    if alias.name not in expected_imports:
                        messages.append(
                            f"{module_path.as_posix()}: imports infrastructure package '{alias.name}'"
                        )
                    observed_imports.add(alias.name)

    missing_imports = expected_imports - observed_imports
    for expected_import in sorted(missing_imports):
        messages.append(
            f"{module_path.as_posix()}: expected infrastructure import '{expected_import}' is "
            "missing"
        )
    return messages


def test_service_modules_do_not_import_router_or_fastapi_http_errors() -> None:
    violations: list[str] = []
    for service_path in _iter_service_files():
        violations.extend(_extract_banned_import_messages(service_path))

    assert not violations, "service boundary violations found:\n" + "\n".join(
        f"- {item}" for item in violations
    )


def test_service_modules_only_use_allowed_infrastructure_imports() -> None:
    violations: list[str] = []
    for service_path in _iter_service_files():
        violations.extend(_extract_banned_infrastructure_messages(service_path))

    assert not violations, "service infrastructure boundary violations found:\n" + "\n".join(
        f"- {item}" for item in violations
    )
