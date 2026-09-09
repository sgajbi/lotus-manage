"""Proof-pack tenant isolation, proven through the PostgreSQL adapter (#694)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.dependencies import (
    get_mandate_repository,
    get_outcome_review_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.main import app
from src.core.models import EngineOptions
from src.core.proof_packs import build_proof_pack_from_run
from src.core.proof_packs.repository import DpmProofPackConflictError
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.models import DpmRunRecord
from src.infrastructure.proof_packs.postgres import PostgresDpmProofPackRepository
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.outcomes import InMemoryDpmOutcomeReviewRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip
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

_PROOF = "proof-pack tenant fence proof"


@pytest.fixture
def repository() -> PostgresDpmProofPackRepository:
    return PostgresDpmProofPackRepository(dsn=postgres_dsn_or_skip(_PROOF))


@pytest.fixture
def tenants() -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:10]
    return f"tenant-alpha-{suffix}", f"tenant-beta-{suffix}"


def _proof_pack(*, tenant_id: str, created_at: datetime, reason: str):
    run_id = f"rr_{uuid.uuid4().hex[:12]}"
    result = run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="PB_TENANT_FENCE_001",
            base_currency="USD",
            positions=[position("EQ_A", "10")],
            cash_balances=[cash("USD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[price("EQ_A", "100", "USD"), price("EQ_B", "100", "USD")]
        ),
        model=model_portfolio(targets=[target("EQ_A", "0.50"), target("EQ_B", "0.50")]),
        shelf=[
            shelf_entry("EQ_A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ_B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash=f"sha256:{run_id}",
        correlation_id=f"corr-{run_id}",
    )
    run = DpmRunRecord(
        rebalance_run_id=run_id,
        correlation_id=result.correlation_id,
        request_hash=f"sha256:{run_id}",
        idempotency_key=f"source-{run_id}",
        portfolio_id="PB_TENANT_FENCE_001",
        created_at=created_at,
        result_json=result.model_dump(mode="json"),
    )
    return build_proof_pack_from_run(
        tenant_id=tenant_id,
        run=run,
        created_by="pm-tenant-fence",
        reason=reason,
        created_at=created_at,
        mandate_id="MANDATE_TENANT_FENCE_001",
    )


def _save(
    repository: PostgresDpmProofPackRepository,
    *,
    tenant_id: str,
    created_at: datetime,
    reason: str,
    idempotency_key: str | None = None,
):
    proof_pack = _proof_pack(tenant_id=tenant_id, created_at=created_at, reason=reason)
    repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=idempotency_key,
        retention_expires_at=None,
        tenant_id=tenant_id,
    )
    return proof_pack


def test_all_four_http_reads_refuse_another_tenants_pack(
    repository: PostgresDpmProofPackRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    proof_pack = _save(
        repository,
        tenant_id=tenant_a,
        created_at=datetime.now(timezone.utc),
        reason="Prove the HTTP tenant fence.",
    )
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_proof_pack_repository] = lambda: repository
    app.dependency_overrides[get_wave_repository] = lambda: InMemoryDpmWaveRepository()
    app.dependency_overrides[get_outcome_review_repository] = lambda: (
        InMemoryDpmOutcomeReviewRepository()
    )
    app.dependency_overrides[get_mandate_repository] = lambda: InMemoryDpmMandateRepository()
    try:
        with TestClient(app) as client:
            for suffix in ["", "/summary.md", "/report-input", "/ai-evidence-input"]:
                response = client.get(
                    f"/api/v1/rebalance/proof-packs/{proof_pack.proof_pack_id}{suffix}"
                    f"?tenant_id={tenant_b}"
                )
                assert response.status_code == 404
                assert response.json()["detail"] == "DPM_PROOF_PACK_NOT_FOUND"
    finally:
        app.dependency_overrides = original_overrides


def test_null_tenant_pack_is_matched_by_no_caller(
    repository: PostgresDpmProofPackRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    proof_pack = _save(
        repository,
        tenant_id=tenant_a,
        created_at=datetime.now(timezone.utc),
        reason="Represent a pre-migration unattributed pack.",
    )
    with repository._connect() as connection:
        connection.execute(
            "UPDATE dpm_pre_trade_proof_packs "
            "SET tenant_id = NULL, payload_json = payload_json - 'tenant_id' "
            "WHERE proof_pack_id = %s",
            (proof_pack.proof_pack_id,),
        )
        connection.commit()

    assert (
        repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id, tenant_id=tenant_a)
        is None
    )
    assert (
        repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id, tenant_id=tenant_b)
        is None
    )
    assert all(
        item.proof_pack_id != proof_pack.proof_pack_id
        for item in repository.list_proof_packs(tenant_id=tenant_a)
    )


def test_replay_and_direct_read_both_refuse_disagreeing_aggregate_owner(
    repository: PostgresDpmProofPackRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    caller_key = f"idem-{uuid.uuid4().hex[:10]}"
    proof_pack = _save(
        repository,
        tenant_id=tenant_a,
        created_at=datetime.now(timezone.utc),
        reason="Prove aggregate-owner agreement on replay.",
        idempotency_key=caller_key,
    )
    with repository._connect() as connection:
        connection.execute(
            "UPDATE dpm_pre_trade_proof_packs SET tenant_id = %s WHERE proof_pack_id = %s",
            (tenant_b, proof_pack.proof_pack_id),
        )
        connection.commit()

    assert (
        repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id, tenant_id=tenant_a)
        is None
    )
    assert (
        repository.get_proof_pack_by_idempotency(idempotency_key=caller_key, tenant_id=tenant_a)
        is None
    )
    assert (
        repository.get_proof_pack(proof_pack_id=proof_pack.proof_pack_id, tenant_id=tenant_b)
        is None
    )


def test_repeated_save_rejects_a_quarantined_existing_pack(
    repository: PostgresDpmProofPackRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    proof_pack = _save(
        repository,
        tenant_id=tenant_a,
        created_at=datetime.now(timezone.utc),
        reason="Prove save does not accept an unreadable replay.",
    )
    with repository._connect() as connection:
        connection.execute(
            "UPDATE dpm_pre_trade_proof_packs SET tenant_id = %s WHERE proof_pack_id = %s",
            (tenant_b, proof_pack.proof_pack_id),
        )
        connection.commit()

    with pytest.raises(DpmProofPackConflictError, match="DPM_PROOF_PACK_IMMUTABLE_CONFLICT"):
        repository.save_proof_pack(
            proof_pack=proof_pack,
            idempotency_key=None,
            retention_expires_at=None,
            tenant_id=tenant_a,
        )


def test_list_filters_tenant_and_owner_agreement_before_paging(
    repository: PostgresDpmProofPackRepository, tenants: tuple[str, str]
) -> None:
    tenant_a, tenant_b = tenants
    older = datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc)
    owned = _save(
        repository,
        tenant_id=tenant_a,
        created_at=older,
        reason="Owned older pack.",
    )
    _save(
        repository,
        tenant_id=tenant_b,
        created_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        reason="Foreign newer pack.",
    )

    page = repository.list_proof_packs(
        tenant_id=tenant_a,
        portfolio_id="PB_TENANT_FENCE_001",
        limit=1,
    )

    assert [item.proof_pack_id for item in page] == [owned.proof_pack_id]
