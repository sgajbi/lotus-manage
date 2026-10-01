from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from src.api.main import app
from src.api.routers.instruction_packages import get_instruction_package_application_service
from src.api.routers import instruction_packages as instruction_routes
from src.api.services.instruction_package_application import (
    DpmInstructionPackageApplicationService,
    DpmInstructionPackageNotFoundError,
    DpmInstructionPackageReleaseCommand,
    DpmInstructionPackageReleaseRefusedError,
    _decode_page_token,
    _instructions_from_result,
    _source_revisions,
)
from src.api.services.wave_aggregate_metrics import aggregate_wave_items
from src.core.instruction_packages import (
    DpmInstructionApprovalEvidence,
    DpmApprovedInstructionPackage,
    DpmInstructionFundingEvidence,
    DpmInstructionMappingEvidence,
    DpmInstructionPackageConflictError,
    DpmInstructionPackageSourceRevision,
)
from src.core.mandates import DpmMandateDigitalTwin
from src.core.models import EngineOptions, SecurityTradeIntent
from src.core.proof_packs.models import (
    DpmPreTradeProofPack,
    DpmProofPackDecisionSummary,
    DpmProofPackDecisionTimeline,
    DpmProofPackSection,
    DpmProofPackSupportability,
)
from src.core.rebalance.engine import run_simulation
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.rebalance_runs.service import DpmRunNotFoundError
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem, DpmWaveTrigger
from src.infrastructure.instruction_packages import InMemoryDpmInstructionPackageRepository
from src.infrastructure.instruction_packages import PostgresDpmInstructionPackageRepository
from src.infrastructure.instruction_packages import postgres as instruction_postgres
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from src.infrastructure.proof_packs import InMemoryDpmProofPackRepository
from src.infrastructure.rebalance_runs import InMemoryDpmRunRepository
from src.infrastructure.waves import InMemoryDpmWaveRepository
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


_NOW = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)
_TENANT = "tenant-instruction-test"


def _result():
    return run_simulation(
        portfolio=portfolio_snapshot(
            portfolio_id="PF-INSTRUCTION-001",
            base_currency="SGD",
            positions=[position("EQ-A", "100")],
            cash_balances=[cash("SGD", "0")],
        ),
        market_data=market_data_snapshot(
            prices=[price("EQ-A", "100", "SGD"), price("EQ-B", "50", "SGD")]
        ),
        model=model_portfolio(targets=[target("EQ-A", "0.50"), target("EQ-B", "0.50")]),
        shelf=[
            shelf_entry("EQ-A", status="APPROVED", asset_class="EQUITY"),
            shelf_entry("EQ-B", status="APPROVED", asset_class="EQUITY"),
        ],
        options=EngineOptions(),
        request_hash="sha256:instruction-package-source-run",
        correlation_id="corr-instruction-source-run",
    )


def _section(section_id: str, section_type: str) -> DpmProofPackSection:
    return DpmProofPackSection(
        section_id=section_id,
        section_type=section_type,  # type: ignore[arg-type]
        state="READY",
        title=section_type,
        summary="Ready evidence.",
        generated_at=_NOW.isoformat(),
        content_hash=f"sha256:{section_id}",
    )


def _proof_pack(*, run_id: str) -> DpmPreTradeProofPack:
    approval = _section("approval", "approval_requirements")
    operations = _section("operations", "operations_handoff")
    lineage = _section("lineage", "lineage")
    return DpmPreTradeProofPack(
        proof_pack_id="dpp-instruction-001",
        proof_pack_version="1.0.0",
        tenant_id=_TENANT,
        portfolio_id="PF-INSTRUCTION-001",
        mandate_id="MANDATE-INSTRUCTION-001",
        source_type="REBALANCE_RUN",
        rebalance_run_id=run_id,
        as_of_date="2026-10-01",
        status="READY",
        decision_summary=DpmProofPackDecisionSummary(
            decision_type="DPM_REBALANCE",
            recommended_action="RELEASE_APPROVED_PACKAGE",
            business_rationale="Reviewed economic intent set.",
            expected_benefit="Model alignment.",
            main_tradeoffs=[],
            top_risks=[],
            approval_state="APPROVED",
            operations_state="HANDOFF_READY",
        ),
        sections=[approval, operations, lineage],
        approval_requirements=approval,
        operations_handoff=operations,
        decision_timeline=DpmProofPackDecisionTimeline(events=[]),
        lineage=lineage,
        supportability=DpmProofPackSupportability(
            status="READY",
            section_state_counts={"READY": 3},
            ready_section_count=3,
            degraded_section_count=0,
            blocked_section_count=0,
            pending_review_section_count=0,
            reason_codes=[],
            section_hashes={"approval": approval.content_hash},
        ),
        content_hash="sha256:instruction-proof-pack",
        source_hashes={"run": "sha256:instruction-package-source-run"},
        created_at=_NOW,
        created_by="pm-approver",
        correlation_id="corr-instruction-proof-pack",
    )


def _mandate(*, version: str = "4", model_id: str = "MODEL-INSTRUCTION") -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin.model_validate(
        {
            "mandate_id": "MANDATE-INSTRUCTION-001",
            "portfolio_id": "PF-INSTRUCTION-001",
            "mandate_version": version,
            "as_of_date": "2026-10-01",
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": model_id,
            "model_portfolio_version": "2026.10",
            "constraints": {},
            "review_policy": {"review_frequency": "QUARTERLY"},
        }
    )


def _service_and_command() -> tuple[
    DpmInstructionPackageApplicationService,
    DpmInstructionPackageReleaseCommand,
]:
    result = _result()
    assert result.status == "READY"
    security_intents = [
        intent for intent in result.intents if isinstance(intent, SecurityTradeIntent)
    ]
    assert len(security_intents) == len(result.intents) > 0

    run_service = DpmRunSupportService(repository=InMemoryDpmRunRepository())
    run_service.record_run(
        result=result,
        request_hash="sha256:instruction-package-source-run",
        portfolio_id="PF-INSTRUCTION-001",
        idempotency_key=None,
        tenant_id=_TENANT,
        created_at=_NOW,
    )
    proof_repository = InMemoryDpmProofPackRepository()
    proof_repository.save_proof_pack(
        proof_pack=_proof_pack(run_id=result.rebalance_run_id),
        idempotency_key=None,
        retention_expires_at=None,
        tenant_id=_TENANT,
    )
    item = DpmRebalanceWaveItem(
        wave_item_id="dwi-instruction-001",
        portfolio_id="PF-INSTRUCTION-001",
        mandate_id="MANDATE-INSTRUCTION-001",
        model_portfolio_id="MODEL-INSTRUCTION",
        state="HANDOFF_READY",
        proof_pack_id="dpp-instruction-001",
        diagnostics={
            "approval_actor_id": "pm-approver",
            "approval_reason_code": "APPROVED_AFTER_REVIEW",
            "external_execution_claimed": False,
        },
    )
    wave = DpmRebalanceWave(
        wave_id="dwv-instruction-001",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-instruction-test",
            rationale="Review and release immutable package.",
        ),
        as_of_date="2026-10-01",
        created_at=_NOW,
        created_by="pm-approver",
        correlation_id="corr-instruction-wave",
        tenant_id=_TENANT,
        items=[item],
        aggregate_metrics=aggregate_wave_items([item]),
    )
    wave_repository = InMemoryDpmWaveRepository()
    wave_repository.save_wave(
        wave=wave,
        idempotency_key=None,
        request_hash=None,
        tenant_id=_TENANT,
    )
    mandate_repository = InMemoryDpmMandateRepository()
    mandate_repository.save_mandate_snapshot(_mandate(), tenant_id=_TENANT)
    service = DpmInstructionPackageApplicationService(
        repository=InMemoryDpmInstructionPackageRepository(),
        wave_repository=wave_repository,
        proof_pack_repository=proof_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )
    mappings = [
        DpmInstructionMappingEvidence(
            original_intent_id=intent.intent_id,
            canonical_instrument_key=f"CORE-{intent.instrument_id}",
            account_key="CORE-ACCOUNT-001",
            mapping_revision="core-mapping.v7",
            mapping_content_hash=f"sha256:mapping-{intent.intent_id}",
            order_type="MARKET",
            time_in_force="DAY",
            settlement_date="2026-10-03",
        )
        for intent in security_intents
    ]
    command = DpmInstructionPackageReleaseCommand(
        tenant_id=_TENANT,
        package_id="dip-instruction-001",
        package_version="1",
        wave_id=wave.wave_id,
        wave_item_id=item.wave_item_id,
        rebalance_run_id=result.rebalance_run_id,
        mandate_id="MANDATE-INSTRUCTION-001",
        mandate_version="4",
        model_portfolio_id="MODEL-INSTRUCTION",
        model_portfolio_version="2026.10",
        policy_revision="dpm-release-policy.v1",
        account_key="CORE-ACCOUNT-001",
        mappings=mappings,
        source_revisions=[
            DpmInstructionPackageSourceRevision(
                source_type="CoreInstrumentAccountMapping",
                source_id="core-map-sg-001",
                source_version="v7",
                content_hash="sha256:core-map-sg-001",
            )
        ],
        funding_evidence=DpmInstructionFundingEvidence(
            disposition="DELEGATED_TO_EXECUTION_OWNER",
            policy_id="funding-policy-sg",
            policy_version="v3",
            evidence_hash="sha256:funding-delegation",
            settlement_awareness_enabled=True,
            delegated_source_product="ExecutionFundingEligibility:v1",
        ),
        approval_evidence=DpmInstructionApprovalEvidence(
            approval_id="approval-instruction-001",
            approved_by="pm-approver",
            approved_at=_NOW,
            approved_material_hash="pending-preview",
            approval_policy_version="dpm-approval.v1",
        ),
        supersedes_package_id=None,
        supersedes_package_version=None,
        released_by="release-manager",
        correlation_id="corr-instruction-release",
    )
    return service, command


def _approved_command(
    service: DpmInstructionPackageApplicationService,
    command: DpmInstructionPackageReleaseCommand,
) -> DpmInstructionPackageReleaseCommand:
    preview = service.preview_release(command=command)
    return replace(
        command,
        approval_evidence=command.approval_evidence.model_copy(
            update={"approved_material_hash": preview.approved_material_hash}
        ),
    )


def test_release_binds_exact_run_economics_and_replays_without_execution_claim() -> None:
    service, command = _service_and_command()
    approved = _approved_command(service, command)

    package, created = service.release(command=approved)
    replay, replay_created = service.release(command=approved)

    assert created is True
    assert replay_created is False
    assert replay == package
    assert package.external_execution_claimed is False
    assert package.external_execution_boundary == "MANAGE_PACKAGE_IS_NOT_ORDER_OR_BOOKING"
    assert package.approved_intent_hash
    assert all(instruction.quantity > 0 for instruction in package.instructions)
    assert all(instruction.currency == "SGD" for instruction in package.instructions)
    assert [instruction.original_intent_id for instruction in package.instructions] == [
        mapping.original_intent_id for mapping in approved.mappings
    ]

    receipt, receipt_created = service.acknowledge_receipt(
        tenant_id=_TENANT,
        package_id=package.package_id,
        package_version=package.package_version,
        consumer_id="synthetic-execution-adapter",
        receipt_evidence_hash="sha256:adapter-retrieved",
    )
    receipt_replay, receipt_replay_created = service.acknowledge_receipt(
        tenant_id=_TENANT,
        package_id=package.package_id,
        package_version=package.package_version,
        consumer_id="synthetic-execution-adapter",
        receipt_evidence_hash="sha256:adapter-retrieved",
    )
    assert receipt_created is True
    assert receipt_replay_created is False
    assert receipt_replay == receipt
    assert receipt.receipt_scope == "RETRIEVAL_ONLY"
    assert receipt.external_execution_claimed is False


def test_release_refuses_changed_approval_material_stale_model_and_insufficient_fee_reserve() -> (
    None
):
    service, command = _service_and_command()
    approved = _approved_command(service, command)
    package, _ = service.release(command=approved)
    changed_mapping = replace(
        approved,
        mappings=[
            approved.mappings[0].model_copy(update={"canonical_instrument_key": "CORE-CHANGED"}),
            *approved.mappings[1:],
        ],
    )
    with pytest.raises(DpmInstructionPackageConflictError, match="IMMUTABLE_CONFLICT"):
        service.release(command=changed_mapping)

    stale_service, stale_command = _service_and_command()
    stale_service.mandate_repository.save_mandate_snapshot(
        _mandate(version="5", model_id="MODEL-NEW"), tenant_id=_TENANT
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="MANDATE_OR_MODEL_STALE"):
        stale_service.preview_release(command=stale_command)

    reserve_service, reserve_command = _service_and_command()
    reserve_command = replace(
        reserve_command,
        funding_evidence=DpmInstructionFundingEvidence(
            disposition="CERTIFIED",
            policy_id="funding-policy-sg",
            policy_version="v3",
            evidence_hash="sha256:funding-reserve",
            settlement_awareness_enabled=True,
            fee_reserve_currency="SGD",
            fee_reserve_amount=Decimal("20"),
        ),
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="FEE_RESERVE_INSUFFICIENT"):
        reserve_service.preview_release(command=reserve_command)
    assert package.package_id == "dip-instruction-001"


def test_release_refuses_missing_mapping_and_converges_concurrent_exact_retries() -> None:
    service, command = _service_and_command()
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="MAPPING_COVERAGE_REQUIRED"):
        service.preview_release(command=replace(command, mappings=command.mappings[:-1]))

    approved = _approved_command(service, command)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: service.release(command=approved), range(4)))
    packages = [package for package, _ in results]
    assert len({package.content_hash for package in packages}) == 1
    assert sum(created for _, created in results) == 1


def test_limit_instruction_mapping_replays_with_exact_decimal_material() -> None:
    service, command = _service_and_command()
    command = replace(
        command,
        mappings=[
            command.mappings[0].model_copy(
                update={"order_type": "LIMIT", "limit_price": Decimal("49.9500")}
            ),
            *command.mappings[1:],
        ],
    )
    approved = _approved_command(service, command)

    first, created = service.release(command=approved)
    replay, replay_created = service.release(command=approved)

    assert created is True
    assert replay_created is False
    assert replay == first
    assert first.instructions[0].order_type == "LIMIT"
    assert first.instructions[0].limit_price == Decimal("49.9500")


def test_new_approved_set_for_same_wave_item_requires_explicit_supersession() -> None:
    service, command = _service_and_command()
    original = _approved_command(service, command)
    service.release(command=original)
    replacement = replace(
        command,
        package_id="dip-instruction-002",
        package_version="1",
        correlation_id="corr-instruction-release-002",
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="SUPERSESSION_REQUIRED"):
        service.preview_release(command=replacement)

    superseding = _approved_command(
        service,
        replace(
            replacement,
            supersedes_package_id=original.package_id,
            supersedes_package_version=original.package_version,
        ),
    )
    package, created = service.release(command=superseding)

    assert created is True
    assert package.supersedes_package_id == original.package_id
    assert package.supersedes_package_version == original.package_version


def test_batch_release_keeps_a_mapping_blocked_item_out_of_partial_release() -> None:
    service, command = _service_and_command()
    eligible = _approved_command(service, _add_second_portfolio_candidate(service, command))
    blocked = replace(
        command,
        package_id="dip-instruction-mapping-blocked",
        package_version="1",
        mappings=command.mappings[:-1],
    )

    released = service.release_batch(commands=[eligible, blocked])

    assert released.partial_release_policy == "RELEASE_ELIGIBLE_ITEMS_ONLY"
    assert [package.package_id for package in released.packages] == [eligible.package_id]
    assert released.packages[0].portfolio_id == "PF-INSTRUCTION-002"
    assert [(refusal.package_id, refusal.reason_code) for refusal in released.refusals] == [
        (blocked.package_id, "INSTRUCTION_PACKAGE_MAPPING_COVERAGE_REQUIRED")
    ]
    assert blocked.wave_item_id == "dwi-instruction-001"


def _add_second_portfolio_candidate(
    service: DpmInstructionPackageApplicationService,
    command: DpmInstructionPackageReleaseCommand,
) -> DpmInstructionPackageReleaseCommand:
    """Add a second portfolio/wave candidate to the same durable source stores."""

    result = _result().model_copy(
        update={
            "rebalance_run_id": "rr-instruction-002",
            "correlation_id": "corr-instruction-source-run-002",
        }
    )
    service.run_service.record_run(
        result=result,
        request_hash="sha256:instruction-package-source-run-002",
        portfolio_id="PF-INSTRUCTION-002",
        idempotency_key=None,
        tenant_id=_TENANT,
        created_at=_NOW,
    )
    proof_pack = _proof_pack(run_id=result.rebalance_run_id).model_copy(
        update={
            "proof_pack_id": "dpp-instruction-002",
            "portfolio_id": "PF-INSTRUCTION-002",
            "mandate_id": "MANDATE-INSTRUCTION-002",
        }
    )
    service.proof_pack_repository.save_proof_pack(
        proof_pack=proof_pack,
        idempotency_key=None,
        retention_expires_at=None,
        tenant_id=_TENANT,
    )
    second_item = DpmRebalanceWaveItem(
        wave_item_id="dwi-instruction-002",
        portfolio_id="PF-INSTRUCTION-002",
        mandate_id="MANDATE-INSTRUCTION-002",
        model_portfolio_id="MODEL-INSTRUCTION",
        state="HANDOFF_READY",
        proof_pack_id=proof_pack.proof_pack_id,
        diagnostics={
            "approval_actor_id": "pm-approver",
            "approval_reason_code": "APPROVED_AFTER_REVIEW",
            "external_execution_claimed": False,
        },
    )
    second_wave = DpmRebalanceWave(
        wave_id="dwv-instruction-002",
        state="HANDOFF_READY",
        trigger=DpmWaveTrigger(
            trigger_type="EXPLICIT_PORTFOLIO_LIST",
            trigger_id="manual-instruction-test-002",
            rationale="Review and release immutable package.",
        ),
        as_of_date="2026-10-01",
        created_at=_NOW,
        created_by="pm-approver",
        correlation_id="corr-instruction-wave-002",
        tenant_id=_TENANT,
        items=[second_item],
        aggregate_metrics=aggregate_wave_items([second_item]),
    )
    service.wave_repository.save_wave(
        wave=second_wave,
        idempotency_key=None,
        request_hash=None,
        tenant_id=_TENANT,
    )
    service.mandate_repository.save_mandate_snapshot(
        _mandate().model_copy(
            update={
                "mandate_id": "MANDATE-INSTRUCTION-002",
                "portfolio_id": "PF-INSTRUCTION-002",
            }
        ),
        tenant_id=_TENANT,
    )
    return replace(
        command,
        package_id="dip-instruction-002",
        wave_id=second_wave.wave_id,
        wave_item_id=second_item.wave_item_id,
        rebalance_run_id=result.rebalance_run_id,
        mandate_id="MANDATE-INSTRUCTION-002",
        correlation_id="corr-instruction-release-002",
    )


def test_snapshot_paging_is_tenant_scoped_and_stable_after_newer_write() -> None:
    service, command = _service_and_command()
    first_command = _approved_command(service, command)
    service.release(command=first_command)
    second_command = _approved_command(service, _add_second_portfolio_candidate(service, command))
    service.release(command=second_command)
    page_one = service.list_packages(tenant_id=_TENANT, limit=1, page_token=None)
    assert page_one.total_count == 2
    assert page_one.next_page_token is not None
    page_two = service.list_packages(
        tenant_id=_TENANT, limit=1, page_token=page_one.next_page_token
    )
    assert page_two.next_page_token is None
    assert {item.package_id for item in [*page_one.items, *page_two.items]} == {
        first_command.package_id,
        second_command.package_id,
    }
    assert page_one.completeness == "SNAPSHOT_COMPLETE_WHEN_ALL_PAGES_RETRIEVED"
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="PAGE_TOKEN_INVALID"):
        service.list_packages(
            tenant_id="other-tenant", limit=1, page_token=page_one.next_page_token
        )
    assert service.list_packages(tenant_id="other-tenant", limit=10, page_token=None).items == []


def _release_headers(*, role: str, tenant: str = _TENANT) -> dict[str, str]:
    return {"X-Tenant-Id": tenant, "X-Actor-Id": "instruction-test-actor", "X-Role": role}


def _request_payload(command: DpmInstructionPackageReleaseCommand) -> dict[str, object]:
    return {
        "wave_id": command.wave_id,
        "wave_item_id": command.wave_item_id,
        "rebalance_run_id": command.rebalance_run_id,
        "mandate_id": command.mandate_id,
        "mandate_version": command.mandate_version,
        "model_portfolio_id": command.model_portfolio_id,
        "model_portfolio_version": command.model_portfolio_version,
        "policy_revision": command.policy_revision,
        "account_key": command.account_key,
        "mappings": [mapping.model_dump(mode="json") for mapping in command.mappings],
        "source_revisions": [
            revision.model_dump(mode="json") for revision in command.source_revisions
        ],
        "funding_evidence": command.funding_evidence.model_dump(mode="json"),
        "approval_evidence": command.approval_evidence.model_dump(mode="json"),
        "supersedes_package_id": command.supersedes_package_id,
        "supersedes_package_version": command.supersedes_package_version,
        "correlation_id": command.correlation_id,
    }


def test_synthetic_adapter_retrieves_http_package_and_records_one_receipt() -> None:
    service, command = _service_and_command()
    app.dependency_overrides[get_instruction_package_application_service] = lambda: service
    path = f"/api/v1/rebalance/instruction-packages/{command.package_id}/versions/{command.package_version}"
    try:
        with TestClient(app) as client:
            payload = _request_payload(command)
            assert (
                client.put(
                    path, headers=_release_headers(role="DPM_EXECUTION_ADAPTER"), json=payload
                ).status_code
                == 403
            )
            preview = client.post(
                f"{path}/preview",
                headers=_release_headers(role="DPM_EXECUTION_RELEASE_MANAGER"),
                json=payload,
            )
            assert preview.status_code == 200
            assert (
                preview.json()["approval_material"]["approval_status"]
                == "PENDING_EXTERNAL_APPROVAL"
            )
            assert "release_eligibility" not in preview.json()["approval_material"]
            payload["approval_evidence"]["approved_material_hash"] = preview.json()[
                "approved_material_hash"
            ]
            released = client.put(
                path,
                headers=_release_headers(role="DPM_EXECUTION_RELEASE_MANAGER"),
                json=payload,
            )
            assert released.status_code == 200
            assert released.json()["external_execution_claimed"] is False
            blocked_payload = _request_payload(command)
            blocked_payload["mappings"] = blocked_payload["mappings"][:-1]  # type: ignore[index]
            batch = client.post(
                "/api/v1/rebalance/instruction-packages/batch-release",
                headers=_release_headers(role="DPM_EXECUTION_RELEASE_MANAGER"),
                json={
                    "items": [
                        {
                            "package_id": command.package_id,
                            "package_version": command.package_version,
                            "release": payload,
                        },
                        {
                            "package_id": "dip-http-mapping-blocked",
                            "package_version": "1",
                            "release": blocked_payload,
                        },
                    ]
                },
            )
            assert batch.status_code == 200
            assert batch.json()["partial_release_policy"] == "RELEASE_ELIGIBLE_ITEMS_ONLY"
            assert [package["package_id"] for package in batch.json()["packages"]] == [
                command.package_id
            ]
            assert batch.json()["refusals"][0]["reason_code"] == (
                "INSTRUCTION_PACKAGE_MAPPING_COVERAGE_REQUIRED"
            )
            duplicate_batch = client.post(
                "/api/v1/rebalance/instruction-packages/batch-release",
                headers=_release_headers(role="DPM_EXECUTION_RELEASE_MANAGER"),
                json={
                    "items": [
                        {
                            "package_id": command.package_id,
                            "package_version": command.package_version,
                            "release": payload,
                        },
                        {
                            "package_id": command.package_id,
                            "package_version": command.package_version,
                            "release": payload,
                        },
                    ]
                },
            )
            assert duplicate_batch.status_code == 422
            adapter_get = client.get(path, headers=_release_headers(role="DPM_EXECUTION_ADAPTER"))
            assert adapter_get.status_code == 200
            assert adapter_get.json()["content_hash"] == released.json()["content_hash"]
            receipt_payload = {
                "consumer_id": "synthetic-bank-execution-adapter",
                "receipt_evidence_hash": "sha256:http-retrieval",
            }
            first_receipt = client.post(
                f"{path}/receipts",
                headers=_release_headers(role="DPM_EXECUTION_ADAPTER"),
                json=receipt_payload,
            )
            second_receipt = client.post(
                f"{path}/receipts",
                headers=_release_headers(role="DPM_EXECUTION_ADAPTER"),
                json=receipt_payload,
            )
            assert first_receipt.status_code == second_receipt.status_code == 200
            assert first_receipt.json()["receipt_id"] == second_receipt.json()["receipt_id"]
            assert first_receipt.json()["receipt_scope"] == "RETRIEVAL_ONLY"
            assert (
                client.get(
                    path, headers=_release_headers(role="DPM_EXECUTION_ADAPTER", tenant="other")
                ).status_code
                == 404
            )
    finally:
        app.dependency_overrides.clear()


def test_release_refusal_and_replay_gap_paths_are_explicit() -> None:
    service, command = _service_and_command()
    with pytest.raises(
        DpmInstructionPackageReleaseRefusedError, match="APPROVAL_MATERIAL_MISMATCH"
    ):
        service.release(command=command)

    approved = _approved_command(service, command)
    replay_gap = Mock()
    replay_gap.get_package.side_effect = [None, None]
    replay_gap.get_package_by_wave_item.return_value = []
    replay_gap.save_package.return_value = False
    replay_service = replace(service, repository=replay_gap)
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="REPLAY_UNAVAILABLE"):
        replay_service.release(command=approved)
    recovered = Mock()
    recovered_package = Mock()
    recovered.get_package.side_effect = [None, recovered_package]
    recovered.get_package_by_wave_item.return_value = []
    recovered.save_package.return_value = False
    replayed, created = replace(service, repository=recovered).release(command=approved)
    assert replayed is recovered_package
    assert created is False

    package, _ = service.release(command=approved)
    receipt_gap = Mock()
    receipt_gap.get_package.return_value = package
    receipt_gap.save_receipt.return_value = False
    receipt_gap.get_receipt.return_value = None
    receipt_service = replace(service, repository=receipt_gap)
    with pytest.raises(
        DpmInstructionPackageReleaseRefusedError, match="RECEIPT_REPLAY_UNAVAILABLE"
    ):
        receipt_service.acknowledge_receipt(
            tenant_id=_TENANT,
            package_id=package.package_id,
            package_version=package.package_version,
            consumer_id="adapter",
            receipt_evidence_hash="sha256:receipt-gap",
        )


def test_source_refusal_helpers_cover_missing_and_invalid_source_material() -> None:
    service, command = _service_and_command()
    wave = service.wave_repository.get_wave(wave_id=command.wave_id, tenant_id=_TENANT)
    assert wave is not None
    item = wave.items[0]

    absent_wave_service = replace(service, wave_repository=Mock(get_wave=Mock(return_value=None)))
    with pytest.raises(DpmInstructionPackageNotFoundError, match="WAVE_NOT_FOUND"):
        absent_wave_service.preview_release(command=command)
    missing_item_service = replace(
        service,
        wave_repository=Mock(get_wave=Mock(return_value=wave.model_copy(update={"items": []}))),
    )
    with pytest.raises(DpmInstructionPackageNotFoundError, match="WAVE_ITEM_NOT_FOUND"):
        missing_item_service.preview_release(command=command)
    for updated_item, reason in (
        (item.model_copy(update={"state": "BLOCKED"}), "WAVE_ITEM_NOT_RELEASE_READY"),
        (item.model_copy(update={"proof_pack_id": None}), "PROOF_PACK_REQUIRED"),
        (item.model_copy(update={"diagnostics": {}}), "WAVE_APPROVAL_EVIDENCE_REQUIRED"),
    ):
        invalid_wave = wave.model_copy(update={"items": [updated_item]})
        invalid_service = replace(
            service, wave_repository=Mock(get_wave=Mock(return_value=invalid_wave))
        )
        with pytest.raises(DpmInstructionPackageReleaseRefusedError, match=reason):
            invalid_service.preview_release(command=command)

    missing_proof_service = replace(
        service, proof_pack_repository=Mock(get_proof_pack=Mock(return_value=None))
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="PROOF_PACK_NOT_FOUND"):
        missing_proof_service._load_releaseable_proof_pack(command=command, wave_item=item)
    not_ready_proof = _proof_pack(run_id=command.rebalance_run_id).model_copy(
        update={"status": "PENDING"}
    )
    not_ready_service = replace(
        service, proof_pack_repository=Mock(get_proof_pack=Mock(return_value=not_ready_proof))
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="PROOF_PACK_NOT_READY"):
        not_ready_service._load_releaseable_proof_pack(command=command, wave_item=item)

    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="PAGE_TOKEN_INVALID"):
        _decode_page_token(page_token="not-a-token", tenant_id=_TENANT)
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="UNSUPPORTED_INTENT_TYPE"):
        _instructions_from_result(
            tenant_id=_TENANT,
            package_id=command.package_id,
            package_version=command.package_version,
            result=_result().model_copy(update={"intents": []}),
            mappings=command.mappings,
            account_key=command.account_key,
        )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="DUPLICATE_SOURCE_REVISION"):
        _source_revisions(
            command=replace(
                command,
                source_revisions=[
                    DpmInstructionPackageSourceRevision(
                        source_type="DpmRunArtifact",
                        source_id=command.rebalance_run_id,
                        source_version="v1",
                        content_hash="sha256:duplicate",
                    )
                ],
            ),
            proof_pack_id="proof",
            proof_pack_hash="sha256:proof",
            mandate_hash="sha256:mandate",
            run_request_hash="sha256:run",
        )


def test_remaining_domain_refusals_and_immutable_adapter_conflicts() -> None:
    service, command = _service_and_command()
    result = _result()
    for result_update, reason in (
        ({"status": "BLOCKED"}, "RUN_NOT_READY"),
        (
            {"lineage": result.lineage.model_copy(update={"model_portfolio_id": "OTHER"})},
            "RUN_MODEL_LINEAGE_MISMATCH",
        ),
    ):
        invalid_result = result.model_copy(update=result_update)
        run = Mock(
            portfolio_id="PF-INSTRUCTION-001", result_json=invalid_result.model_dump(mode="json")
        )
        invalid_service = replace(
            service, run_service=Mock(get_run_record_for_tenant=Mock(return_value=run))
        )
        with pytest.raises(DpmInstructionPackageReleaseRefusedError, match=reason):
            invalid_service._load_releaseable_run(
                command=command, portfolio_id="PF-INSTRUCTION-001"
            )
    absent_run_service = replace(
        service,
        run_service=Mock(
            get_run_record_for_tenant=Mock(side_effect=DpmRunNotFoundError("missing"))
        ),
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="RUN_NOT_FOUND"):
        absent_run_service._load_releaseable_run(command=command, portfolio_id="PF-INSTRUCTION-001")
    wrong_portfolio_service = replace(
        service,
        run_service=Mock(
            get_run_record_for_tenant=Mock(
                return_value=Mock(portfolio_id="OTHER", result_json=result.model_dump(mode="json"))
            )
        ),
    )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="RUN_PORTFOLIO_MISMATCH"):
        wrong_portfolio_service._load_releaseable_run(
            command=command, portfolio_id="PF-INSTRUCTION-001"
        )

    for supersedes, reason in (
        ((None, "1"), "SUPERSESSION_INCOMPLETE"),
        (("missing", None), "SUPERSESSION_INCOMPLETE"),
        (("missing", "1"), "SUPERSEDED_VERSION_NOT_FOUND"),
    ):
        with pytest.raises(DpmInstructionPackageReleaseRefusedError, match=reason):
            service._validate_supersession(
                command=replace(
                    command,
                    supersedes_package_id=supersedes[0],
                    supersedes_package_version=supersedes[1],
                )
            )

    package, _ = service.release(command=_approved_command(service, command))
    assert service.repository.save_package(package=package) is False
    with pytest.raises(DpmInstructionPackageConflictError, match="IMMUTABLE_CONFLICT"):
        service.repository.save_package(
            package=package.model_copy(update={"content_hash": "sha256:changed"})
        )
    receipt, _ = service.acknowledge_receipt(
        tenant_id=_TENANT,
        package_id=package.package_id,
        package_version=package.package_version,
        consumer_id="adapter",
        receipt_evidence_hash="sha256:one",
    )
    with pytest.raises(DpmInstructionPackageConflictError, match="RECEIPT_IMMUTABLE_CONFLICT"):
        service.repository.save_receipt(
            receipt=receipt.model_copy(update={"receipt_evidence_hash": "sha256:changed"})
        )


def test_package_models_reject_incomplete_funding_mapping_and_supersession() -> None:
    with pytest.raises(ValueError, match="FEE_RESERVE_INCOMPLETE"):
        DpmInstructionFundingEvidence(
            disposition="CERTIFIED",
            policy_id="p",
            policy_version="1",
            evidence_hash="h",
            settlement_awareness_enabled=True,
            fee_reserve_currency="SGD",
        )
    with pytest.raises(ValueError, match="FUNDING_DELEGATION_EVIDENCE_REQUIRED"):
        DpmInstructionFundingEvidence(
            disposition="DELEGATED_TO_EXECUTION_OWNER",
            policy_id="p",
            policy_version="1",
            evidence_hash="h",
            settlement_awareness_enabled=True,
        )
    with pytest.raises(ValueError, match="LIMIT_PRICE_REQUIRED"):
        command = _service_and_command()[1]
        command.mappings[0].model_copy(update={"order_type": "LIMIT", "limit_price": None})
        DpmInstructionMappingEvidence.model_validate(
            {**command.mappings[0].model_dump(), "order_type": "LIMIT", "limit_price": None}
        )
    service, command = _service_and_command()
    package, _ = service.release(command=_approved_command(service, command))
    with pytest.raises(ValueError, match="SUPERSESSION_INCOMPLETE"):
        DpmApprovedInstructionPackage.model_validate(
            {**package.model_dump(mode="json"), "supersedes_package_id": "prior"}
        )


def test_router_identity_and_domain_error_mapping_paths() -> None:
    service, command = _service_and_command()
    request = instruction_routes.InstructionPackageReleaseRequest.model_validate(
        _request_payload(command)
    )
    identity = instruction_routes.InstructionPackageTrustedIdentity(
        tenant_id=_TENANT, actor_id="actor", role="DPM_EXECUTION_RELEASE_MANAGER"
    )
    assert isinstance(
        instruction_routes.get_instruction_package_application_service(
            service.repository,
            service.wave_repository,
            service.proof_pack_repository,
            service.mandate_repository,
            service.run_service,
        ),
        DpmInstructionPackageApplicationService,
    )
    with pytest.raises(Exception):
        instruction_routes.instruction_package_trusted_identity_required(
            Request({"type": "http", "headers": []})
        )
    with pytest.raises(Exception):
        instruction_routes._read_identity_required(
            instruction_routes.InstructionPackageTrustedIdentity(_TENANT, "actor", "OTHER")
        )
    with pytest.raises(Exception):
        instruction_routes._receipt_identity_required(identity)
    for handler, failure in (
        (
            instruction_routes.preview_instruction_package,
            DpmInstructionPackageReleaseRefusedError("bad"),
        ),
        (
            instruction_routes.release_instruction_package,
            DpmInstructionPackageConflictError("CONFLICT"),
        ),
    ):
        failing = Mock()
        failing.preview_release.side_effect = failure
        failing.release.side_effect = failure
        with pytest.raises(Exception):
            handler(command.package_id, command.package_version, request, identity, failing)
    reader = instruction_routes.InstructionPackageTrustedIdentity(
        _TENANT, "actor", "DPM_EXECUTION_ADAPTER"
    )
    for handler, failure in (
        (
            instruction_routes.get_instruction_package,
            DpmInstructionPackageNotFoundError("NOT_FOUND"),
        ),
        (
            instruction_routes.list_instruction_packages,
            DpmInstructionPackageReleaseRefusedError("bad"),
        ),
    ):
        failing = Mock()
        failing.get_package.side_effect = failure
        failing.list_packages.side_effect = failure
        with pytest.raises(Exception):
            if handler is instruction_routes.get_instruction_package:
                handler(command.package_id, command.package_version, reader, failing)
            else:
                handler(1, "bad", reader, failing)
    receipt_service = Mock()
    receipt_service.acknowledge_receipt.side_effect = DpmInstructionPackageConflictError("CONFLICT")
    with pytest.raises(Exception):
        instruction_routes.acknowledge_instruction_package_receipt(
            command.package_id,
            command.package_version,
            instruction_routes.InstructionPackageReceiptRequest(
                consumer_id="adapter", receipt_evidence_hash="sha256:receipt"
            ),
            reader,
            receipt_service,
        )
    batch_service = Mock()
    batch_service.release_batch.side_effect = DpmInstructionPackageConflictError("CONFLICT")
    with pytest.raises(Exception):
        instruction_routes.release_instruction_package_batch(
            instruction_routes.InstructionPackageBatchReleaseRequest(
                items=[
                    instruction_routes.InstructionPackageBatchReleaseItem(
                        package_id="other", package_version="1", release=request
                    )
                ]
            ),
            identity,
            batch_service,
        )


def test_remaining_package_model_and_service_guardrails() -> None:
    service, command = _service_and_command()
    mapping = command.mappings[0]
    with pytest.raises(ValueError, match="FUNDING_DELEGATION_NOT_ALLOWED"):
        DpmInstructionFundingEvidence(
            disposition="CERTIFIED",
            policy_id="p",
            policy_version="1",
            evidence_hash="h",
            settlement_awareness_enabled=True,
            delegated_source_product="owner",
        )
    with pytest.raises(ValueError, match="LIMIT_PRICE_NOT_ALLOWED"):
        DpmInstructionMappingEvidence.model_validate({**mapping.model_dump(), "limit_price": "1"})
    package, _ = service.release(command=_approved_command(service, command))
    duplicated = package.model_dump(mode="json")
    duplicated["instructions"].append(duplicated["instructions"][0])
    with pytest.raises(ValueError, match="DUPLICATE_INSTRUCTION_ID"):
        DpmApprovedInstructionPackage.model_validate(duplicated)
    with pytest.raises(
        DpmInstructionPackageReleaseRefusedError, match="PROOF_PACK_LINEAGE_MISMATCH"
    ):
        service._load_releaseable_proof_pack(
            command=command,
            wave_item=service.wave_repository.get_wave(wave_id=command.wave_id, tenant_id=_TENANT)
            .items[0]
            .model_copy(update={"portfolio_id": "OTHER"}),  # type: ignore[union-attr]
        )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="MANDATE_REQUIRED"):
        replace(
            service,
            mandate_repository=Mock(get_latest_mandate_by_portfolio=Mock(return_value=None)),
        )._load_current_mandate(command=command, portfolio_id="PF-INSTRUCTION-001")
    with pytest.raises(
        DpmInstructionPackageReleaseRefusedError, match="SUPERSESSION_SCOPE_MISMATCH"
    ):
        service._validate_supersession(
            command=replace(
                command,
                supersedes_package_id=package.package_id,
                supersedes_package_version=package.package_version,
                wave_item_id="other",
            )
        )
    with pytest.raises(
        DpmInstructionPackageReleaseRefusedError, match="UNSUPPORTED_INTENT_DEPENDENCY"
    ):
        _instructions_from_result(
            tenant_id=_TENANT,
            package_id="x",
            package_version="1",
            result=_result().model_copy(
                update={
                    "intents": [
                        _result().intents[0].model_copy(update={"dependencies": ["missing"]})
                    ]
                }
            ),
            mappings=[mapping],
            account_key=command.account_key,
        )
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="ACCOUNT_SCOPE_MISMATCH"):
        _instructions_from_result(
            tenant_id=_TENANT,
            package_id="x",
            package_version="1",
            result=_result(),
            mappings=[mapping.model_copy(update={"account_key": "other"}), *command.mappings[1:]],
            account_key=command.account_key,
        )


def test_postgres_adapter_fails_closed_without_dsn_or_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, command = _service_and_command()
    mapping = command.mappings[0]
    with pytest.raises(RuntimeError, match="POSTGRES_DSN_REQUIRED"):
        PostgresDpmInstructionPackageRepository(dsn="")
    monkeypatch.setattr(instruction_postgres, "has_psycopg", lambda: False)
    with pytest.raises(RuntimeError, match="POSTGRES_DRIVER_MISSING"):
        PostgresDpmInstructionPackageRepository(dsn="postgresql://example")
    with pytest.raises(DpmInstructionPackageReleaseRefusedError, match="EXACT_QUANTITY_REQUIRED"):
        _instructions_from_result(
            tenant_id=_TENANT,
            package_id="x",
            package_version="1",
            result=_result().model_copy(
                update={"intents": [_result().intents[0].model_copy(update={"quantity": None})]}
            ),
            mappings=[mapping],
            account_key=command.account_key,
        )


def test_postgres_adapter_payload_and_driver_helpers_preserve_auditable_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored records must survive both jsonb and driver-normalized payload forms."""
    assert instruction_postgres._payload({"payload_json": {"package_id": "dip-001"}}) == {
        "package_id": "dip-001"
    }
    assert instruction_postgres._payload({"payload_json": Decimal("1.25")}) == '"1.25"'

    fake_psycopg = object()
    fake_dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", SimpleNamespace(dict_row=fake_dict_row))

    imported_psycopg, imported_dict_row = instruction_postgres._import_psycopg()
    assert imported_psycopg is fake_psycopg
    assert imported_dict_row is fake_dict_row
