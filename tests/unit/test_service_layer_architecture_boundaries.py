from __future__ import annotations

import ast
from pathlib import Path


SERVICE_DIR = Path("src/api/services")


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


def test_service_modules_do_not_import_router_or_fastapi_http_errors() -> None:
    violations: list[str] = []
    for service_path in _iter_service_files():
        violations.extend(_extract_banned_import_messages(service_path))

    assert not violations, "service boundary violations found:\n" + "\n".join(
        f"- {item}" for item in violations
    )
