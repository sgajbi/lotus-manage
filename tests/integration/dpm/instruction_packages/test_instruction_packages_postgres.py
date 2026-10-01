"""Real PostgreSQL restart and concurrency proof for approved instruction packages."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import uuid

import pytest

from src.core.instruction_packages import (
    DpmApprovedInstruction,
    DpmApprovedInstructionPackage,
    DpmInstructionApprovalEvidence,
    DpmInstructionFundingEvidence,
    DpmInstructionPackageConflictError,
    DpmInstructionPackageReceipt,
    DpmInstructionPackageSourceRevision,
)
from src.infrastructure.instruction_packages import PostgresDpmInstructionPackageRepository
from tests.integration.dpm.postgres_prerequisite import postgres_dsn_or_skip


_PROOF = "approved instruction package PostgreSQL restart and concurrency proof"


def _package(
    *, tenant_id: str, package_id: str, policy_revision: str = "dpm-release-policy.v1"
) -> DpmApprovedInstructionPackage:
    return DpmApprovedInstructionPackage.from_material(
        package_id=package_id,
        package_version="1",
        tenant_id=tenant_id,
        portfolio_id="PF-PACKAGE-001",
        account_key="CORE-ACCOUNT-001",
        wave_id="dwv-package-001",
        wave_item_id="dwi-package-001",
        rebalance_run_id="rr-package-001",
        proof_pack_id="dpp-package-001",
        mandate_id="MANDATE-PACKAGE-001",
        mandate_version="4",
        model_portfolio_id="MODEL-PACKAGE",
        model_portfolio_version="2026.10",
        policy_revision=policy_revision,
        source_revisions=[
            DpmInstructionPackageSourceRevision(
                source_type="DpmRunArtifact",
                source_id="rr-package-001",
                source_version="v1",
                content_hash="sha256:run-package-001",
            )
        ],
        approved_intent_hash="sha256:approved-intents-package-001",
        approval_evidence=DpmInstructionApprovalEvidence(
            approval_id="approval-package-001",
            approved_by="pm-approver",
            approved_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            approved_material_hash="sha256:approval-material-package-001",
            approval_policy_version="dpm-approval.v1",
        ),
        funding_evidence=DpmInstructionFundingEvidence(
            disposition="DELEGATED_TO_EXECUTION_OWNER",
            policy_id="funding-policy-sg",
            policy_version="v3",
            evidence_hash="sha256:funding-package-001",
            settlement_awareness_enabled=True,
            delegated_source_product="ExecutionFundingEligibility:v1",
        ),
        instructions=[
            DpmApprovedInstruction(
                instruction_id="dpi-package-001",
                original_intent_id="oi_1",
                canonical_instrument_key="CORE-EQ-A",
                account_key="CORE-ACCOUNT-001",
                side="SELL",
                quantity=Decimal("25"),
                currency="SGD",
                order_type="MARKET",
                time_in_force="DAY",
                settlement_date="2026-10-03",
                mapping_revision="core-mapping.v7",
                mapping_content_hash="sha256:core-mapping-package-001",
            )
        ],
        released_by="release-manager",
        correlation_id="corr-package-001",
        created_at=datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc),
    )


def test_postgres_restart_tenant_fence_exact_replay_and_receipt_concurrency() -> None:
    suffix = uuid.uuid4().hex[:12]
    tenant_id = f"tenant-package-{suffix}"
    package_id = f"dip-package-{suffix}"
    package = _package(tenant_id=tenant_id, package_id=package_id)
    dsn = postgres_dsn_or_skip(_PROOF)
    repository = PostgresDpmInstructionPackageRepository(dsn=dsn)

    with ThreadPoolExecutor(max_workers=4) as executor:
        inserted = list(executor.map(lambda _: repository.save_package(package=package), range(4)))
    assert sum(inserted) == 1

    restarted = PostgresDpmInstructionPackageRepository(dsn=dsn)
    assert (
        restarted.get_package(
            tenant_id=tenant_id,
            package_id=package.package_id,
            package_version=package.package_version,
        )
        == package
    )
    assert (
        restarted.get_package(
            tenant_id="other-tenant",
            package_id=package.package_id,
            package_version=package.package_version,
        )
        is None
    )
    page, total_count = restarted.list_packages(
        tenant_id=tenant_id,
        created_before=datetime(2026, 10, 2, tzinfo=timezone.utc),
        limit=10,
        offset=0,
    )
    assert page == [package]
    assert total_count == 1
    assert restarted.get_package_by_wave_item(
        tenant_id=tenant_id,
        wave_id=package.wave_id,
        wave_item_id=package.wave_item_id,
    ) == [package]

    receipt = DpmInstructionPackageReceipt(
        receipt_id=f"dipr-{suffix}",
        tenant_id=tenant_id,
        package_id=package.package_id,
        package_version=package.package_version,
        consumer_id="synthetic-bank-execution-adapter",
        receipt_evidence_hash="sha256:adapter-retrieval-package-001",
        received_at=datetime(2026, 10, 1, 9, 31, tzinfo=timezone.utc),
    )
    with ThreadPoolExecutor(max_workers=4) as executor:
        receipt_inserted = list(
            executor.map(lambda _: restarted.save_receipt(receipt=receipt), range(4))
        )
    assert sum(receipt_inserted) == 1
    assert (
        restarted.get_receipt(
            tenant_id=tenant_id,
            package_id=package.package_id,
            package_version=package.package_version,
            consumer_id=receipt.consumer_id,
        )
        == receipt
    )
    with pytest.raises(DpmInstructionPackageConflictError, match="RECEIPT_IMMUTABLE_CONFLICT"):
        restarted.save_receipt(
            receipt=receipt.model_copy(update={"receipt_evidence_hash": "sha256:changed"})
        )

    with pytest.raises(DpmInstructionPackageConflictError, match="IMMUTABLE_CONFLICT"):
        restarted.save_package(
            package=_package(
                tenant_id=tenant_id,
                package_id=package_id,
                policy_revision="changed-policy",
            )
        )
