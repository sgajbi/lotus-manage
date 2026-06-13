from pathlib import Path

from scripts.service_boundary_gate import evaluate_service_boundary


def test_service_boundary_gate_detects_router_and_http_framework_leakage(
    tmp_path: Path,
) -> None:
    service_dir = tmp_path / "src" / "api" / "services"
    service_dir.mkdir(parents=True)
    (service_dir / "leaky_service.py").write_text(
        "\n".join(
            [
                "from fastapi import HTTPException",
                "from starlette.requests import Request",
                "from src.api.routers.example import router",
            ]
        ),
        encoding="utf-8",
    )

    violations = evaluate_service_boundary(service_dir)

    assert violations == [
        f"{(service_dir / 'leaky_service.py').as_posix()}:1: from fastapi import HTTPException",
        f"{(service_dir / 'leaky_service.py').as_posix()}:2: from starlette.requests import Request",
        f"{(service_dir / 'leaky_service.py').as_posix()}:3: from src.api.routers.example import router",
    ]


def test_service_boundary_gate_allows_transport_free_services(tmp_path: Path) -> None:
    service_dir = tmp_path / "src" / "api" / "services"
    service_dir.mkdir(parents=True)
    (service_dir / "clean_service.py").write_text(
        "\n".join(
            [
                "from src.core.models import Portfolio",
                "",
                "def load_portfolio() -> Portfolio | None:",
                "    return None",
            ]
        ),
        encoding="utf-8",
    )

    assert evaluate_service_boundary(service_dir) == []
