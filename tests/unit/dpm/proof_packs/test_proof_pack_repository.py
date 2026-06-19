from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core.models import EngineOptions, RebalanceResult
from src.core.proof_packs import build_proof_pack_from_run
from src.core.proof_packs.models import DpmProofPackStoredRef
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import DpmRunRecord
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.proof_packs.in_memory import (
    _ProofPackListFilters,
    _ensure_proof_pack_content_is_immutable,
    _idempotency_binding,
    _list_proof_packs,
    _optional_match,
    _proof_pack_matches_filters,
    _proof_pack_sort_key,
    _retention_metadata,
)
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


ROOT = Path(__file__).resolve().parents[4]
CREATED_AT = datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc)
RETENTION_EXPIRES_AT = CREATED_AT + timedelta(days=365 * 7)


def _ready_rebalance_result() -> RebalanceResult:
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_repo_1",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_A", "100", "USD"),
                price("EQ_B", "100", "USD"),
            ]
        ),
        model=model_portfolio(
            targets=[
                target("EQ_A", "0.50"),
                target("EQ_B", "0.50"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash="sha256:proof-pack-repository",
        correlation_id="corr-proof-pack-repository",
    )


def _proof_pack(reason: str = "Rebalance back to target."):
    result = _ready_rebalance_result()
    run = DpmRunRecord(
        rebalance_run_id="rr_repo_001",
        correlation_id=result.correlation_id,
        request_hash="sha256:proof-pack-repository",
        idempotency_key="idem-proof-pack-repository",
        portfolio_id="pf_repo_1",
        created_at=CREATED_AT,
        result_json=result.model_dump(mode="json"),
    )
    return build_proof_pack_from_run(
        run=run,
        created_by="pm_repo",
        reason=reason,
        created_at=CREATED_AT,
        mandate_id="mandate_repo_1",
    )


def test_in_memory_repository_round_trips_immutable_proof_pack_and_retention() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()

    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-repository",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )

    by_id = repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id)
    by_idempotency = repository.get_proof_pack_by_idempotency(
        idempotency_key="idem-proof-pack-repository"
    )
    listed = repository.list_proof_packs(portfolio_id="pf_repo_1")
    retention = repository.get_retention_metadata(proof_pack_id=proof_pack.proof_pack_id)

    assert by_id == proof_pack
    assert by_idempotency == proof_pack
    assert listed == [proof_pack]
    assert by_id is not proof_pack
    assert retention is not None
    assert retention.retention_policy == "DPM_PRE_TRADE_PROOF_PACK_7Y"
    assert retention.retention_expires_at == RETENTION_EXPIRES_AT.isoformat()
    assert by_id.supportability.section_hashes == proof_pack.supportability.section_hashes


def test_in_memory_repository_replays_same_identity_but_rejects_mutation() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack(reason="Initial rationale.")

    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-repository",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key="idem-proof-pack-repository",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )

    mutated = _proof_pack(reason="Changed rationale.")
    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IMMUTABLE_CONFLICT"):
        repository.save_proof_pack(
            proof_pack=mutated,
            idempotency_key="idem-proof-pack-repository",
            retention_expires_at=RETENTION_EXPIRES_AT,
        )


def test_in_memory_repository_rejects_idempotency_conflict() -> None:
    repository = InMemoryDpmProofPackRepository()
    first = _proof_pack()
    second = first.model_copy(update={"proof_pack_id": "dpp_repo_other"})

    repository.save_proof_pack(
        proof_pack=first,
        idempotency_key="idem-proof-pack-repository",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )

    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT"):
        repository.save_proof_pack(
            proof_pack=second,
            idempotency_key="idem-proof-pack-repository",
            retention_expires_at=RETENTION_EXPIRES_AT,
        )


def test_proof_pack_immutability_helper_allows_matching_content_hash() -> None:
    proof_pack = _proof_pack()
    replay = proof_pack.model_copy(deep=True)

    _ensure_proof_pack_content_is_immutable(existing=proof_pack, proof_pack=replay)


def test_proof_pack_immutability_helper_rejects_changed_content_hash() -> None:
    proof_pack = _proof_pack(reason="Initial rationale.")
    mutated = _proof_pack(reason="Changed rationale.")

    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IMMUTABLE_CONFLICT"):
        _ensure_proof_pack_content_is_immutable(existing=proof_pack, proof_pack=mutated)


def test_idempotency_binding_helper_returns_optional_binding_and_rejects_conflicts() -> None:
    assert (
        _idempotency_binding(
            idempotency_key=None,
            existing_proof_pack_id=None,
            proof_pack_id="dpp_none",
        )
        is None
    )
    assert _idempotency_binding(
        idempotency_key="idem-proof-pack-repository",
        existing_proof_pack_id="dpp_repo_001",
        proof_pack_id="dpp_repo_001",
    ) == ("idem-proof-pack-repository", "dpp_repo_001")

    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IDEMPOTENCY_CONFLICT"):
        _idempotency_binding(
            idempotency_key="idem-proof-pack-repository",
            existing_proof_pack_id="dpp_repo_001",
            proof_pack_id="dpp_repo_002",
        )


def test_retention_metadata_helper_preserves_policy_and_optional_expiry() -> None:
    expiring = _retention_metadata(
        proof_pack_id="dpp_repo_001",
        retention_expires_at=RETENTION_EXPIRES_AT,
    )
    non_expiring = _retention_metadata(
        proof_pack_id="dpp_repo_002",
        retention_expires_at=None,
    )

    assert expiring.retention_policy == "DPM_PRE_TRADE_PROOF_PACK_7Y"
    assert expiring.retention_expires_at == RETENTION_EXPIRES_AT.isoformat()
    assert non_expiring.retention_policy == "DPM_PRE_TRADE_PROOF_PACK_7Y"
    assert non_expiring.retention_expires_at is None


def test_proof_pack_list_helpers_filter_sort_and_page_results() -> None:
    first = _proof_pack().model_copy(
        update={
            "proof_pack_id": "dpp_repo_001",
            "portfolio_id": "pf_repo_1",
            "mandate_id": "mandate_repo_1",
            "created_at": CREATED_AT,
        }
    )
    second = first.model_copy(
        update={
            "proof_pack_id": "dpp_repo_002",
            "portfolio_id": "pf_repo_1",
            "mandate_id": "mandate_repo_1",
            "created_at": CREATED_AT + timedelta(days=1),
        }
    )
    other_portfolio = first.model_copy(
        update={
            "proof_pack_id": "dpp_repo_003",
            "portfolio_id": "pf_repo_other",
            "created_at": CREATED_AT + timedelta(days=2),
        }
    )

    filters = _ProofPackListFilters(
        portfolio_id="pf_repo_1",
        mandate_id="mandate_repo_1",
        status=None,
    )

    assert _optional_match(None, first.portfolio_id)
    assert _optional_match("pf_repo_1", first.portfolio_id)
    assert not _optional_match("pf_repo_other", first.portfolio_id)
    assert _proof_pack_matches_filters(proof_pack=first, filters=filters)
    assert not _proof_pack_matches_filters(proof_pack=other_portfolio, filters=filters)
    assert _proof_pack_sort_key(second) > _proof_pack_sort_key(first)
    assert _list_proof_packs(
        proof_packs=[first, second, other_portfolio],
        filters=filters,
        limit=1,
        offset=0,
    ) == [second]
    assert _list_proof_packs(
        proof_packs=[first, second, other_portfolio],
        filters=filters,
        limit=1,
        offset=1,
    ) == [first]


def test_in_memory_repository_appends_refs_without_mutating_body() -> None:
    repository = InMemoryDpmProofPackRepository()
    proof_pack = _proof_pack()
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=RETENTION_EXPIRES_AT,
    )

    ref = DpmProofPackStoredRef(
        proof_pack_id=proof_pack.proof_pack_id,
        ref_type="REPORT_INPUT",
        ref_id="dpri_repo_001",
        source_system="lotus-manage",
        content_hash="sha256:report-input",
        created_at=CREATED_AT.isoformat(),
    )
    repository.append_ref(ref=ref)

    assert repository.list_refs(proof_pack_id=proof_pack.proof_pack_id) == [ref]
    assert repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id) == proof_pack


def test_postgres_migration_declares_proof_pack_persistence_tables() -> None:
    migration = (
        ROOT
        / "src"
        / "infrastructure"
        / "postgres_migrations"
        / "dpm"
        / "0006_pre_trade_proof_packs.sql"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "dpm_pre_trade_proof_packs",
        "dpm_pre_trade_proof_pack_sections",
        "dpm_pre_trade_proof_pack_refs",
        "content_hash TEXT NOT NULL",
        "retention_expires_at TIMESTAMPTZ NULL",
        "payload_json JSONB NOT NULL",
    ]
    missing = [token for token in required_tokens if token not in migration]

    assert missing == []
