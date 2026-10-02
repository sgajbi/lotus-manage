"""Application service for immutable approved instruction-package publication."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import cast

from src.core.common.canonical import hash_canonical_payload
from src.core.common.derived_identity import derived_identity
from src.core.instruction_packages import (
    DpmApprovedInstruction,
    DpmApprovedInstructionPackage,
    DpmInstructionApprovalEvidence,
    DpmInstructionFundingEvidence,
    DpmInstructionMappingEvidence,
    DpmInstructionPackageApprovalMaterial,
    DpmInstructionPackageConflictError,
    DpmInstructionPackagePage,
    DpmInstructionPackageReceipt,
    DpmInstructionPackageRepository,
    DpmInstructionPackageSourceRevision,
)
from src.core.mandate_repository import DpmMandateRepository
from src.core.mandate_models import DpmMandateDigitalTwin
from src.core.models import RebalanceResult, SecurityTradeIntent
from src.core.proof_packs.models import DpmPreTradeProofPack
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunNotFoundError, DpmRunSupportService
from src.core.waves.models import DpmRebalanceWave, DpmRebalanceWaveItem
from src.core.waves.repository import DpmWaveRepository


class DpmInstructionPackageNotFoundError(ValueError):
    """The tenant does not own the requested immutable package."""


class DpmInstructionPackageReleaseRefusedError(ValueError):
    """A source, approval, mapping, or funding prerequisite is not releaseable."""


@dataclass(frozen=True)
class DpmInstructionPackageReleaseCommand:
    tenant_id: str
    package_id: str
    package_version: str
    wave_id: str
    wave_item_id: str
    rebalance_run_id: str
    mandate_id: str
    mandate_version: str
    model_portfolio_id: str
    model_portfolio_version: str | None
    policy_revision: str
    account_key: str
    mappings: list[DpmInstructionMappingEvidence]
    source_revisions: list[DpmInstructionPackageSourceRevision]
    funding_evidence: DpmInstructionFundingEvidence
    approval_evidence: DpmInstructionApprovalEvidence
    supersedes_package_id: str | None
    supersedes_package_version: str | None
    released_by: str
    correlation_id: str


@dataclass(frozen=True)
class DpmInstructionPackageReleasePreview:
    approved_material_hash: str
    approved_intent_hash: str
    instruction_count: int
    approval_material: DpmInstructionPackageApprovalMaterial


@dataclass(frozen=True)
class DpmInstructionPackageBatchRefusal:
    package_id: str
    package_version: str
    wave_id: str
    wave_item_id: str
    reason_code: str


@dataclass(frozen=True)
class DpmInstructionPackageBatchRelease:
    packages: list[DpmApprovedInstructionPackage]
    refusals: list[DpmInstructionPackageBatchRefusal]
    partial_release_policy: str = "RELEASE_ELIGIBLE_ITEMS_ONLY"


@dataclass(frozen=True)
class DpmInstructionPackageApplicationService:
    repository: DpmInstructionPackageRepository
    wave_repository: DpmWaveRepository
    proof_pack_repository: DpmProofPackRepository
    mandate_repository: DpmMandateRepository
    run_service: DpmRunSupportService

    def preview_release(
        self, *, command: DpmInstructionPackageReleaseCommand
    ) -> DpmInstructionPackageReleasePreview:
        package, approved_material_hash = self._build_package(command=command)
        return DpmInstructionPackageReleasePreview(
            approved_material_hash=approved_material_hash,
            approved_intent_hash=package.approved_intent_hash,
            instruction_count=len(package.instructions),
            approval_material=DpmInstructionPackageApprovalMaterial(
                package_id=package.package_id,
                package_version=package.package_version,
                tenant_id=package.tenant_id,
                portfolio_id=package.portfolio_id,
                account_key=package.account_key,
                wave_id=package.wave_id,
                wave_item_id=package.wave_item_id,
                rebalance_run_id=package.rebalance_run_id,
                proof_pack_id=package.proof_pack_id,
                mandate_id=package.mandate_id,
                mandate_version=package.mandate_version,
                model_portfolio_id=package.model_portfolio_id,
                model_portfolio_version=package.model_portfolio_version,
                policy_revision=package.policy_revision,
                source_revisions=package.source_revisions,
                approved_intent_hash=package.approved_intent_hash,
                instructions=package.instructions,
                funding_evidence=package.funding_evidence,
            ),
        )

    def release_batch(
        self, *, commands: list[DpmInstructionPackageReleaseCommand]
    ) -> DpmInstructionPackageBatchRelease:
        """Release eligible independent wave items without authorizing blocked peers.

        This is a bounded synchronous orchestration endpoint, not a campaign
        worker. Immutable conflicts deliberately abort rather than being
        reclassified as an eligibility refusal.
        """

        packages: list[DpmApprovedInstructionPackage] = []
        refusals: list[DpmInstructionPackageBatchRefusal] = []
        for command in commands:
            try:
                package, _ = self.release(command=command)
                packages.append(package)
            except (
                DpmInstructionPackageNotFoundError,
                DpmInstructionPackageReleaseRefusedError,
            ) as exc:
                refusals.append(
                    DpmInstructionPackageBatchRefusal(
                        package_id=command.package_id,
                        package_version=command.package_version,
                        wave_id=command.wave_id,
                        wave_item_id=command.wave_item_id,
                        reason_code=str(exc),
                    )
                )
        return DpmInstructionPackageBatchRelease(packages=packages, refusals=refusals)

    def release(
        self, *, command: DpmInstructionPackageReleaseCommand
    ) -> tuple[DpmApprovedInstructionPackage, bool]:
        existing = self.repository.get_package(
            tenant_id=command.tenant_id,
            package_id=command.package_id,
            package_version=command.package_version,
        )
        if existing is not None:
            if not _matches_immutable_replay(existing=existing, command=command):
                raise DpmInstructionPackageConflictError("INSTRUCTION_PACKAGE_IMMUTABLE_CONFLICT")
            return existing, False

        package, approved_material_hash = self._build_package(command=command)
        if command.approval_evidence.approved_material_hash != approved_material_hash:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_APPROVAL_MATERIAL_MISMATCH"
            )
        created = self.repository.save_package(package=package)
        if created:
            return package, True
        replayed = self.repository.get_package(
            tenant_id=command.tenant_id,
            package_id=command.package_id,
            package_version=command.package_version,
        )
        if replayed is None:
            raise DpmInstructionPackageReleaseRefusedError("INSTRUCTION_PACKAGE_REPLAY_UNAVAILABLE")
        return replayed, False

    def get_package(
        self, *, tenant_id: str, package_id: str, package_version: str
    ) -> DpmApprovedInstructionPackage:
        package = self.repository.get_package(
            tenant_id=tenant_id,
            package_id=package_id,
            package_version=package_version,
        )
        if package is None:
            raise DpmInstructionPackageNotFoundError("INSTRUCTION_PACKAGE_NOT_FOUND")
        return package

    def list_packages(
        self, *, tenant_id: str, limit: int, page_token: str | None
    ) -> DpmInstructionPackagePage:
        snapshot_at, offset = (
            _decode_page_token(page_token=page_token, tenant_id=tenant_id)
            if page_token
            else (
                datetime.now(timezone.utc),
                0,
            )
        )
        items, total_count = self.repository.list_packages(
            tenant_id=tenant_id,
            created_before=snapshot_at,
            limit=limit,
            offset=offset,
        )
        next_offset = offset + len(items)
        return DpmInstructionPackagePage(
            items=items,
            count=len(items),
            total_count=total_count,
            limit=limit,
            snapshot_at=snapshot_at,
            next_page_token=(
                _encode_page_token(tenant_id=tenant_id, snapshot_at=snapshot_at, offset=next_offset)
                if next_offset < total_count
                else None
            ),
        )

    def acknowledge_receipt(
        self,
        *,
        tenant_id: str,
        package_id: str,
        package_version: str,
        consumer_id: str,
        receipt_evidence_hash: str,
    ) -> tuple[DpmInstructionPackageReceipt, bool]:
        self.get_package(
            tenant_id=tenant_id,
            package_id=package_id,
            package_version=package_version,
        )
        receipt = DpmInstructionPackageReceipt(
            receipt_id=derived_identity(
                "dipr", tenant_id, package_id, package_version, consumer_id
            ),
            tenant_id=tenant_id,
            package_id=package_id,
            package_version=package_version,
            consumer_id=consumer_id,
            receipt_evidence_hash=receipt_evidence_hash,
        )
        created = self.repository.save_receipt(receipt=receipt)
        if created:
            return receipt, True
        replayed = self.repository.get_receipt(
            tenant_id=tenant_id,
            package_id=package_id,
            package_version=package_version,
            consumer_id=consumer_id,
        )
        if replayed is None:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_RECEIPT_REPLAY_UNAVAILABLE"
            )
        return replayed, False

    def _build_package(
        self, *, command: DpmInstructionPackageReleaseCommand
    ) -> tuple[DpmApprovedInstructionPackage, str]:
        wave, wave_item = self._load_releaseable_wave_item(command=command)
        proof_pack = self._load_releaseable_proof_pack(command=command, wave_item=wave_item)
        mandate = self._load_current_mandate(command=command, portfolio_id=wave_item.portfolio_id)
        result = self._load_releaseable_run(command=command, portfolio_id=wave_item.portfolio_id)
        self._validate_funding(command=command, result=result)
        instructions, approved_intent_hash = _instructions_from_result(
            tenant_id=command.tenant_id,
            package_id=command.package_id,
            package_version=command.package_version,
            result=result,
            mappings=command.mappings,
            account_key=command.account_key,
        )
        source_revisions = _source_revisions(
            command=command,
            proof_pack_id=proof_pack.proof_pack_id,
            proof_pack_hash=proof_pack.content_hash,
            mandate_hash=hash_canonical_payload(mandate.model_dump(mode="json")),
            run_request_hash=result.lineage.request_hash,
        )
        approved_material_hash = _approved_material_hash(
            command=command,
            approved_intent_hash=approved_intent_hash,
            instructions=instructions,
            source_revisions=source_revisions,
        )
        self._validate_supersession(command=command)
        package = DpmApprovedInstructionPackage.from_material(
            package_id=command.package_id,
            package_version=command.package_version,
            tenant_id=command.tenant_id,
            portfolio_id=wave_item.portfolio_id,
            account_key=command.account_key,
            wave_id=command.wave_id,
            wave_item_id=command.wave_item_id,
            rebalance_run_id=command.rebalance_run_id,
            proof_pack_id=proof_pack.proof_pack_id,
            mandate_id=mandate.mandate_id,
            mandate_version=mandate.mandate_version,
            model_portfolio_id=mandate.model_portfolio_id,
            model_portfolio_version=mandate.model_portfolio_version,
            policy_revision=command.policy_revision,
            source_revisions=source_revisions,
            approved_intent_hash=approved_intent_hash,
            approval_evidence=command.approval_evidence,
            funding_evidence=command.funding_evidence,
            instructions=instructions,
            supersedes_package_id=command.supersedes_package_id,
            supersedes_package_version=command.supersedes_package_version,
            released_by=command.released_by,
            correlation_id=command.correlation_id,
        )
        return package, approved_material_hash

    def _load_releaseable_wave_item(
        self, *, command: DpmInstructionPackageReleaseCommand
    ) -> tuple[DpmRebalanceWave, DpmRebalanceWaveItem]:
        wave = self.wave_repository.get_wave(wave_id=command.wave_id, tenant_id=command.tenant_id)
        if wave is None:
            raise DpmInstructionPackageNotFoundError("INSTRUCTION_PACKAGE_WAVE_NOT_FOUND")
        item = next(
            (item for item in wave.items if item.wave_item_id == command.wave_item_id), None
        )
        if item is None:
            raise DpmInstructionPackageNotFoundError("INSTRUCTION_PACKAGE_WAVE_ITEM_NOT_FOUND")
        if item.state != "HANDOFF_READY":
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_WAVE_ITEM_NOT_RELEASE_READY"
            )
        if not item.proof_pack_id:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_PROOF_PACK_REQUIRED"
            )
        if not item.diagnostics.get("approval_actor_id") or not item.diagnostics.get(
            "approval_reason_code"
        ):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_WAVE_APPROVAL_EVIDENCE_REQUIRED"
            )
        return wave, item

    def _load_releaseable_proof_pack(
        self, *, command: DpmInstructionPackageReleaseCommand, wave_item: DpmRebalanceWaveItem
    ) -> DpmPreTradeProofPack:
        proof_pack = self.proof_pack_repository.get_proof_pack(
            proof_pack_id=wave_item.proof_pack_id or "", tenant_id=command.tenant_id
        )
        if proof_pack is None:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_PROOF_PACK_NOT_FOUND"
            )
        if proof_pack.status != "READY":
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_PROOF_PACK_NOT_READY"
            )
        if (
            proof_pack.portfolio_id != wave_item.portfolio_id
            or proof_pack.rebalance_run_id != command.rebalance_run_id
        ):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_PROOF_PACK_LINEAGE_MISMATCH"
            )
        return proof_pack

    def _load_current_mandate(
        self, *, command: DpmInstructionPackageReleaseCommand, portfolio_id: str
    ) -> DpmMandateDigitalTwin:
        mandate = self.mandate_repository.get_latest_mandate_by_portfolio(
            portfolio_id=portfolio_id, tenant_id=command.tenant_id
        )
        if mandate is None:
            raise DpmInstructionPackageReleaseRefusedError("INSTRUCTION_PACKAGE_MANDATE_REQUIRED")
        if (
            mandate.mandate_id != command.mandate_id
            or mandate.mandate_version != command.mandate_version
            or mandate.model_portfolio_id != command.model_portfolio_id
            or mandate.model_portfolio_version != command.model_portfolio_version
        ):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_MANDATE_OR_MODEL_STALE"
            )
        return mandate

    def _load_releaseable_run(
        self, *, command: DpmInstructionPackageReleaseCommand, portfolio_id: str
    ) -> RebalanceResult:
        try:
            run = self.run_service.get_run_record_for_tenant(
                tenant_id=command.tenant_id, rebalance_run_id=command.rebalance_run_id
            )
        except DpmRunNotFoundError as exc:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_RUN_NOT_FOUND"
            ) from exc
        if run.portfolio_id != portfolio_id:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_RUN_PORTFOLIO_MISMATCH"
            )
        result = RebalanceResult.model_validate(run.result_json)
        if result.status != "READY":
            raise DpmInstructionPackageReleaseRefusedError("INSTRUCTION_PACKAGE_RUN_NOT_READY")
        policy = result.client_restriction_policy
        if (
            policy is None
            or policy.decision != "READY"
            or policy.source_product_name != "ClientRestrictionProfile"
            or not policy.content_hash
            or not policy.stateful_context_hash
            or policy.portfolio_id != portfolio_id
            or not policy.client_id
            or policy.as_of_date is None
        ):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_CLIENT_POLICY_NOT_READY"
            )
        if result.lineage.model_portfolio_id not in {None, command.model_portfolio_id} or (
            result.lineage.model_portfolio_version not in {None, command.model_portfolio_version}
        ):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_RUN_MODEL_LINEAGE_MISMATCH"
            )
        return result

    def _validate_funding(
        self, *, command: DpmInstructionPackageReleaseCommand, result: RebalanceResult
    ) -> None:
        evidence = command.funding_evidence
        if evidence.disposition != "CERTIFIED" or evidence.fee_reserve_amount in {
            None,
            Decimal("0"),
        }:
            return
        balance = next(
            (
                balance
                for balance in result.after_simulated.cash_balances
                if balance.currency == evidence.fee_reserve_currency
            ),
            None,
        )
        available = (
            None
            if balance is None
            else (
                balance.settled
                if evidence.settlement_awareness_enabled and balance.settled is not None
                else balance.amount
            )
        )
        if available is None or available < evidence.fee_reserve_amount:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_FEE_RESERVE_INSUFFICIENT"
            )

    def _validate_supersession(self, *, command: DpmInstructionPackageReleaseCommand) -> None:
        prior_packages = self.repository.get_package_by_wave_item(
            tenant_id=command.tenant_id,
            wave_id=command.wave_id,
            wave_item_id=command.wave_item_id,
        )
        if command.supersedes_package_id is None:
            if command.supersedes_package_version is not None:
                raise DpmInstructionPackageReleaseRefusedError(
                    "INSTRUCTION_PACKAGE_SUPERSESSION_INCOMPLETE"
                )
            if prior_packages:
                raise DpmInstructionPackageReleaseRefusedError(
                    "INSTRUCTION_PACKAGE_SUPERSESSION_REQUIRED"
                )
            return
        if command.supersedes_package_version is None:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_SUPERSESSION_INCOMPLETE"
            )
        previous = self.repository.get_package(
            tenant_id=command.tenant_id,
            package_id=command.supersedes_package_id,
            package_version=command.supersedes_package_version,
        )
        if previous is None:
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_SUPERSEDED_VERSION_NOT_FOUND"
            )
        if (previous.wave_id, previous.wave_item_id) != (command.wave_id, command.wave_item_id):
            raise DpmInstructionPackageReleaseRefusedError(
                "INSTRUCTION_PACKAGE_SUPERSESSION_SCOPE_MISMATCH"
            )


def _instructions_from_result(
    *,
    tenant_id: str,
    package_id: str,
    package_version: str,
    result: RebalanceResult,
    mappings: list[DpmInstructionMappingEvidence],
    account_key: str,
) -> tuple[list[DpmApprovedInstruction], str]:
    security_intents = _security_intents_for_package(result=result)
    mapping_by_intent = _mappings_for_security_intents(
        mappings=mappings, security_intents=security_intents, account_key=account_key
    )
    instruction_id_by_intent = {
        intent.intent_id: derived_identity(
            "dpi", tenant_id, package_id, package_version, intent.intent_id
        )
        for intent in security_intents
    }
    if any(set(intent.dependencies) - set(instruction_id_by_intent) for intent in security_intents):
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_UNSUPPORTED_INTENT_DEPENDENCY"
        )
    instructions = [
        DpmApprovedInstruction(
            instruction_id=instruction_id_by_intent[intent.intent_id],
            original_intent_id=intent.intent_id,
            canonical_instrument_key=mapping_by_intent[intent.intent_id].canonical_instrument_key,
            account_key=account_key,
            side=intent.side,
            quantity=cast(Decimal, intent.quantity),
            currency=cast(str, intent.notional.currency if intent.notional is not None else None),
            order_type=mapping_by_intent[intent.intent_id].order_type,
            time_in_force=mapping_by_intent[intent.intent_id].time_in_force,
            settlement_date=mapping_by_intent[intent.intent_id].settlement_date,
            limit_price=mapping_by_intent[intent.intent_id].limit_price,
            dependencies=[
                instruction_id_by_intent[dependency] for dependency in intent.dependencies
            ],
            mapping_revision=mapping_by_intent[intent.intent_id].mapping_revision,
            mapping_content_hash=mapping_by_intent[intent.intent_id].mapping_content_hash,
        )
        for intent in security_intents
    ]
    approved_intent_hash = hash_canonical_payload(
        [intent.model_dump(mode="json") for intent in security_intents]
    )
    return instructions, approved_intent_hash


def _security_intents_for_package(*, result: RebalanceResult) -> list[SecurityTradeIntent]:
    security_intents = [
        intent for intent in result.intents if isinstance(intent, SecurityTradeIntent)
    ]
    if len(security_intents) != len(result.intents) or not security_intents:
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_UNSUPPORTED_INTENT_TYPE"
        )
    if any(intent.quantity is None or intent.notional is None for intent in security_intents):
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_EXACT_QUANTITY_REQUIRED"
        )
    return security_intents


def _mappings_for_security_intents(
    *,
    mappings: list[DpmInstructionMappingEvidence],
    security_intents: list[SecurityTradeIntent],
    account_key: str,
) -> dict[str, DpmInstructionMappingEvidence]:
    mapping_by_intent = {mapping.original_intent_id: mapping for mapping in mappings}
    if len(mapping_by_intent) != len(mappings) or set(mapping_by_intent) != {
        intent.intent_id for intent in security_intents
    }:
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_MAPPING_COVERAGE_REQUIRED"
        )
    if any(mapping.account_key != account_key for mapping in mappings):
        raise DpmInstructionPackageReleaseRefusedError("INSTRUCTION_PACKAGE_ACCOUNT_SCOPE_MISMATCH")
    return mapping_by_intent


def _source_revisions(
    *,
    command: DpmInstructionPackageReleaseCommand,
    proof_pack_id: str,
    proof_pack_hash: str,
    mandate_hash: str,
    run_request_hash: str,
) -> list[DpmInstructionPackageSourceRevision]:
    derived = [
        DpmInstructionPackageSourceRevision(
            source_type="DpmRunArtifact",
            source_id=command.rebalance_run_id,
            source_version="v1",
            content_hash=run_request_hash,
        ),
        DpmInstructionPackageSourceRevision(
            source_type="DpmPreTradeProofPack",
            source_id=proof_pack_id,
            source_version="v1",
            content_hash=proof_pack_hash,
        ),
        DpmInstructionPackageSourceRevision(
            source_type="DpmMandateDigitalTwin",
            source_id=command.mandate_id,
            source_version=command.mandate_version,
            content_hash=mandate_hash,
        ),
    ]
    revisions = [*derived, *command.source_revisions]
    identities = {(revision.source_type, revision.source_id) for revision in revisions}
    if len(identities) != len(revisions):
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_DUPLICATE_SOURCE_REVISION"
        )
    return sorted(revisions, key=lambda revision: (revision.source_type, revision.source_id))


def _approved_material_hash(
    *,
    command: DpmInstructionPackageReleaseCommand,
    approved_intent_hash: str,
    instructions: list[DpmApprovedInstruction],
    source_revisions: list[DpmInstructionPackageSourceRevision],
) -> str:
    return hash_canonical_payload(
        {
            "tenant_id": command.tenant_id,
            "portfolio_account_scope": command.account_key,
            "wave_id": command.wave_id,
            "wave_item_id": command.wave_item_id,
            "rebalance_run_id": command.rebalance_run_id,
            "mandate_id": command.mandate_id,
            "mandate_version": command.mandate_version,
            "model_portfolio_id": command.model_portfolio_id,
            "model_portfolio_version": command.model_portfolio_version,
            "policy_revision": command.policy_revision,
            "approved_intent_hash": approved_intent_hash,
            "instructions": [instruction.model_dump(mode="json") for instruction in instructions],
            "source_revisions": [revision.model_dump(mode="json") for revision in source_revisions],
            "funding_evidence": command.funding_evidence.model_dump(mode="json"),
        }
    )


def _matches_immutable_replay(
    *,
    existing: DpmApprovedInstructionPackage,
    command: DpmInstructionPackageReleaseCommand,
) -> bool:
    """Compare caller material with the immutable package without rereading mutable sources.

    A response-loss retry must return the original package even if the mandate
    changed after first release.  It still must not turn a changed mapping,
    quantity constraint, funding policy, or approval into a benign replay.
    """

    expected_mappings = _stored_mapping_material(existing=existing)
    received_mappings = _received_mapping_material(command=command)
    return (
        _same_package_scope(existing=existing, command=command)
        and _same_package_governance(existing=existing, command=command)
        and expected_mappings == received_mappings
        and _stored_external_source_revisions(existing=existing)
        == _received_source_revisions(command=command)
    )


def _stored_mapping_material(*, existing: DpmApprovedInstructionPackage) -> list[dict[str, object]]:
    return sorted(
        (
            {
                "original_intent_id": instruction.original_intent_id,
                "canonical_instrument_key": instruction.canonical_instrument_key,
                "account_key": instruction.account_key,
                "mapping_revision": instruction.mapping_revision,
                "mapping_content_hash": instruction.mapping_content_hash,
                "order_type": instruction.order_type,
                "time_in_force": instruction.time_in_force,
                "settlement_date": instruction.settlement_date,
                "limit_price": (
                    str(instruction.limit_price) if instruction.limit_price is not None else None
                ),
            }
            for instruction in existing.instructions
        ),
        key=lambda mapping: str(mapping["original_intent_id"]),
    )


def _received_mapping_material(
    *, command: DpmInstructionPackageReleaseCommand
) -> list[dict[str, object]]:
    return sorted(
        (mapping.model_dump(mode="json") for mapping in command.mappings),
        key=lambda mapping: str(mapping["original_intent_id"]),
    )


def _received_source_revisions(
    *, command: DpmInstructionPackageReleaseCommand
) -> list[dict[str, object]]:
    return sorted(
        (revision.model_dump(mode="json") for revision in command.source_revisions),
        key=lambda revision: (str(revision["source_type"]), str(revision["source_id"])),
    )


def _stored_external_source_revisions(
    *, existing: DpmApprovedInstructionPackage
) -> list[dict[str, object]]:
    return sorted(
        (
            revision.model_dump(mode="json")
            for revision in existing.source_revisions
            if revision.source_type
            not in {"DpmRunArtifact", "DpmPreTradeProofPack", "DpmMandateDigitalTwin"}
        ),
        key=lambda revision: (str(revision["source_type"]), str(revision["source_id"])),
    )


def _same_package_scope(
    *, existing: DpmApprovedInstructionPackage, command: DpmInstructionPackageReleaseCommand
) -> bool:
    return (
        existing.tenant_id == command.tenant_id
        and existing.wave_id == command.wave_id
        and existing.wave_item_id == command.wave_item_id
        and existing.rebalance_run_id == command.rebalance_run_id
        and existing.mandate_id == command.mandate_id
        and existing.mandate_version == command.mandate_version
        and existing.model_portfolio_id == command.model_portfolio_id
        and existing.model_portfolio_version == command.model_portfolio_version
        and existing.account_key == command.account_key
    )


def _same_package_governance(
    *, existing: DpmApprovedInstructionPackage, command: DpmInstructionPackageReleaseCommand
) -> bool:
    return (
        existing.policy_revision == command.policy_revision
        and existing.funding_evidence == command.funding_evidence
        and existing.approval_evidence == command.approval_evidence
        and existing.supersedes_package_id == command.supersedes_package_id
        and existing.supersedes_package_version == command.supersedes_package_version
        and existing.correlation_id == command.correlation_id
    )


def _encode_page_token(*, tenant_id: str, snapshot_at: datetime, offset: int) -> str:
    raw = json.dumps(
        {"tenant_id": tenant_id, "snapshot_at": snapshot_at.isoformat(), "offset": offset},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_page_token(*, page_token: str, tenant_id: str) -> tuple[datetime, int]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(page_token.encode("ascii")).decode("utf-8"))
        snapshot_at = datetime.fromisoformat(payload["snapshot_at"])
        offset = int(payload["offset"])
        token_tenant_id = str(payload["tenant_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise DpmInstructionPackageReleaseRefusedError(
            "INSTRUCTION_PACKAGE_PAGE_TOKEN_INVALID"
        ) from exc
    if snapshot_at.tzinfo is None or offset < 0 or token_tenant_id != tenant_id:
        raise DpmInstructionPackageReleaseRefusedError("INSTRUCTION_PACKAGE_PAGE_TOKEN_INVALID")
    return snapshot_at, offset


__all__ = [
    "DpmInstructionPackageApplicationService",
    "DpmInstructionPackageBatchRefusal",
    "DpmInstructionPackageBatchRelease",
    "DpmInstructionPackageNotFoundError",
    "DpmInstructionPackageReleaseCommand",
    "DpmInstructionPackageReleasePreview",
    "DpmInstructionPackageReleaseRefusedError",
]
