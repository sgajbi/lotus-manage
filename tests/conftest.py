"""
FILE: tests/conftest.py
Shared fixtures for lotus-manage/advisory tests.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from src.core.rebalance.policy_packs import DpmPolicyPackDefinition, parse_policy_pack_catalog
from src.core.models import CashBalance, EngineOptions, PortfolioSnapshot
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.infrastructure.proposals import InMemoryProposalRepository

TESTS_ROOT = Path(__file__).resolve().parent
UNIT_TESTS_PATH = str(TESTS_ROOT / "unit")
if UNIT_TESTS_PATH not in sys.path:
    sys.path.insert(0, UNIT_TESTS_PATH)


def _has_marker(item: pytest.Item, name: str) -> bool:
    return item.get_closest_marker(name) is not None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if (
            _has_marker(item, "unit")
            or _has_marker(item, "integration")
            or _has_marker(item, "e2e")
        ):
            continue
        path = Path(str(item.fspath)).as_posix().lower()
        if "/tests/integration/" in path or "_integration.py" in path:
            item.add_marker(pytest.mark.integration)
            continue
        if "/tests/e2e/" in path or "/tests/shared/demo/" in path:
            item.add_marker(pytest.mark.e2e)
            continue
        item.add_marker(pytest.mark.unit)


@pytest.fixture
def base_portfolio() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options() -> EngineOptions:
    return EngineOptions(
        allow_restricted=False,
        suppress_dust_trades=True,
        block_on_missing_prices=True,
        single_position_max_weight=None,
    )


class _TestPolicyPackRepository:
    def __init__(self) -> None:
        self._overrides: dict[str, DpmPolicyPackDefinition] = {}
        self._deleted_ids: set[str] = set()

    def _effective_catalog(self) -> dict[str, DpmPolicyPackDefinition]:
        catalog = parse_policy_pack_catalog(os.getenv("DPM_POLICY_PACK_CATALOG_JSON"))
        catalog.update(self._overrides)
        for policy_pack_id in self._deleted_ids:
            catalog.pop(policy_pack_id, None)
        return catalog

    def list_policy_packs(self) -> list[DpmPolicyPackDefinition]:
        return sorted(self._effective_catalog().values(), key=lambda item: item.policy_pack_id)

    def get_policy_pack(self, *, policy_pack_id: str) -> DpmPolicyPackDefinition | None:
        return self._effective_catalog().get(policy_pack_id)

    def upsert_policy_pack(self, policy_pack: DpmPolicyPackDefinition) -> None:
        self._overrides[policy_pack.policy_pack_id] = policy_pack
        self._deleted_ids.discard(policy_pack.policy_pack_id)

    def delete_policy_pack(self, *, policy_pack_id: str) -> bool:
        if self.get_policy_pack(policy_pack_id=policy_pack_id) is None:
            return False
        self._overrides.pop(policy_pack_id, None)
        self._deleted_ids.add(policy_pack_id)
        return True


@pytest.fixture(autouse=True)
def postgres_runtime_test_harness(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DPM_SUPPORTABILITY_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("DPM_POLICY_PACK_CATALOG_BACKEND", "POSTGRES")
    monkeypatch.setenv(
        "DPM_SUPPORTABILITY_POSTGRES_DSN", "postgresql://test:test@localhost:5432/dpm"
    )
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgresql://test:test@localhost:5432/proposals")
    monkeypatch.setenv(
        "DPM_POLICY_PACK_POSTGRES_DSN", "postgresql://test:test@localhost:5432/policy"
    )

    policy_repo = _TestPolicyPackRepository()

    monkeypatch.setattr(
        "src.api.routers.rebalance_runs_config.PostgresDpmRunRepository",
        lambda **_kwargs: InMemoryDpmRunRepository(),
    )
    monkeypatch.setattr(
        "src.api.routers.proposals_config.PostgresProposalRepository",
        lambda **_kwargs: InMemoryProposalRepository(),
    )
    monkeypatch.setattr(
        "src.api.routers.rebalance_policy_packs.PostgresDpmPolicyPackRepository",
        lambda **_kwargs: policy_repo,
    )
