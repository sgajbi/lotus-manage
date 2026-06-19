from pathlib import Path

from scripts.router_infrastructure_gate import evaluate_router_infrastructure_imports


def test_router_infrastructure_gate_detects_infrastructure_imports(tmp_path: Path) -> None:
    router_dir = tmp_path / "src" / "api" / "routers"
    router_dir.mkdir(parents=True)
    (router_dir / "leaky_router.py").write_text(
        "\n".join(
            [
                "from src.infrastructure.rebalance_runs.postgres import PostgresRunRepository",
                "import src.infrastructure.authority_http",
            ]
        ),
        encoding="utf-8",
    )

    violations = evaluate_router_infrastructure_imports(router_dir)

    assert violations == [
        f"{(router_dir / 'leaky_router.py').as_posix()}:1: "
        "from src.infrastructure.rebalance_runs.postgres import PostgresRunRepository",
        f"{(router_dir / 'leaky_router.py').as_posix()}:2: import src.infrastructure.authority_http",
    ]


def test_router_infrastructure_gate_allows_service_imports(tmp_path: Path) -> None:
    router_dir = tmp_path / "src" / "api" / "routers"
    router_dir.mkdir(parents=True)
    (router_dir / "clean_router.py").write_text(
        "\n".join(
            [
                "from src.api.services.rebalance_simulation_service import simulate",
                "",
                "def route() -> None:",
                "    simulate",
            ]
        ),
        encoding="utf-8",
    )

    assert evaluate_router_infrastructure_imports(router_dir) == []
