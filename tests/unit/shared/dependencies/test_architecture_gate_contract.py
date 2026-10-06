"""Prove production architecture contracts against valid and forbidden graphs."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[4]


def _gate(tmp_path: Path, imports: dict[str, str]) -> subprocess.CompletedProcess[str]:
    for module in ("src", "src.api", "src.api.routers", "src.api.services", "src.infrastructure"):
        directory = tmp_path.joinpath(*module.split("."))
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").write_text("", encoding="utf-8")
    for module, content in imports.items():
        tmp_path.joinpath(*module.split(".")).with_suffix(".py").write_text(
            content, encoding="utf-8"
        )
    for layer in ("routers", "services"):
        (tmp_path / "src" / "api" / layer / "fixture.py").write_text("", encoding="utf-8")
    (tmp_path / ".importlinter").write_text(
        (ROOT / ".importlinter").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return _run_gate(tmp_path)


def _run_gate(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    recipe = (ROOT / "Makefile").read_text(encoding="utf-8").split("architecture-gate:\n", 1)[1]
    command = recipe.splitlines()[0].strip()
    assert command.startswith('python -c "') and command.endswith('"')
    return subprocess.run(
        [sys.executable, "-c", command[len('python -c "') : -1]],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_valid_composition_keeps_all_contracts(tmp_path: Path) -> None:
    result = _gate(
        tmp_path,
        {
            "src.api.routers.valid": "from src.api import dependencies\n",
            "src.api.dependencies": "from src import infrastructure\n",
            "src.api.services.valid": "from decimal import Decimal\n",
        },
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 kept, 0 broken" in result.stdout


@pytest.mark.parametrize(
    ("module", "content"),
    [
        ("src.api.routers.bad", "from src import infrastructure\n"),
        ("src.api.services.bad", "from src import infrastructure\n"),
        ("src.api.services.bad", "from src.api import routers\n"),
        ("src.api.services.bad", "import fastapi\n"),
        ("src.api.services.bad", "import starlette\n"),
        ("src.api.services.bad", "from src.api import dependencies\n"),
    ],
)
def test_forbidden_graph_fails_real_gate(tmp_path: Path, module: str, content: str) -> None:
    result = _gate(
        tmp_path,
        {module: content, "src.api.dependencies": "from src import infrastructure\n"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "BROKEN" in result.stdout


def test_missing_root_cannot_report_green(tmp_path: Path) -> None:
    result = _gate(tmp_path, {})
    assert result.returncode == 0, result.stdout + result.stderr
    config = tmp_path / ".importlinter"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "root_package = src", "root_package = absent_architecture_root"
        ),
        encoding="utf-8",
    )
    result = _run_gate(tmp_path)
    assert result.returncode != 0, result.stdout + result.stderr


def test_transport_and_application_share_metric_collectors() -> None:
    from src.api import observability as transport
    from src.observability import metrics

    assert transport.DPM_EXECUTION_TOTAL is metrics.DPM_EXECUTION_TOTAL
    assert transport.HTTP_REQUESTS_TOTAL is metrics.HTTP_REQUESTS_TOTAL
    assert transport.record_execution_call is metrics.record_execution_call
    collector = metrics.DPM_EXECUTION_TOTAL.labels(
        operation="simulate", input_mode="unknown", outcome="error", result_status="unknown"
    )
    before = collector._value.get()
    metrics.record_execution_call(
        operation="simulate", input_mode="untrusted", outcome="untrusted", result_status="untrusted"
    )
    assert collector._value.get() == before + 1


def test_empty_application_tree_cannot_report_green(tmp_path: Path) -> None:
    result = _gate(tmp_path, {})
    assert result.returncode == 0, result.stdout + result.stderr
    (tmp_path / "src" / "api" / "services" / "fixture.py").unlink()
    result = _run_gate(tmp_path)
    assert result.returncode == 1
    assert "Architecture source tree missing or empty" in result.stderr
