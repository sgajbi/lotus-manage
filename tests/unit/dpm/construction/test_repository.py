from src.core.construction.models import ConstructionAlternativeSelection
from src.infrastructure.construction import InMemoryConstructionRepository
from tests.unit.dpm.construction.test_alternative_engine import _ready_rebalance_result
from src.core.construction import build_alternative_set, build_do_nothing_baseline


def _alternative_set():
    result = _ready_rebalance_result()
    return build_alternative_set(
        alternative_set_id="cas_repo_001",
        portfolio_id="pf_construct_1",
        as_of="2026-05-03",
        alternatives=[build_do_nothing_baseline(result=result)],
    ).model_copy(update={"request_hash": "sha256:repo"})


def test_in_memory_repository_persists_alternative_set_and_idempotency_lookup() -> None:
    repository = InMemoryConstructionRepository()
    alternative_set = _alternative_set()

    repository.save_alternative_set(
        alternative_set=alternative_set,
        idempotency_key="idem-repo-001",
    )

    by_id = repository.get_alternative_set(alternative_set_id="cas_repo_001")
    by_idempotency = repository.get_alternative_set_by_idempotency(
        idempotency_key="idem-repo-001"
    )

    assert by_id == alternative_set
    assert by_idempotency == alternative_set
    assert by_id is not alternative_set


def test_in_memory_repository_records_latest_selection_decision() -> None:
    repository = InMemoryConstructionRepository()
    repository.save_alternative_set(
        alternative_set=_alternative_set(),
        idempotency_key="idem-repo-002",
    )
    selection = ConstructionAlternativeSelection(
        selection_id="casel_repo_001",
        alternative_set_id="cas_repo_001",
        alternative_id="alt_do_nothing_baseline",
        actor_id="pm_001",
        reason_code="CLIENT_TAX_SENSITIVITY",
        comment="Keep turnover at zero.",
        correlation_id="corr-selection-repo",
    )

    repository.save_selection(selection=selection)

    assert repository.get_selection(alternative_set_id="cas_repo_001") == selection
