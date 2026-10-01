"""HTTP contract for immutable Manage-approved instruction packages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, model_validator

from src.api.dependencies import (
    get_instruction_package_repository,
    get_mandate_repository,
    get_proof_pack_repository,
    get_wave_repository,
)
from src.api.routers.rebalance_runs import get_dpm_run_support_service
from src.api.services.instruction_package_application import (
    DpmInstructionPackageApplicationService,
    DpmInstructionPackageBatchRelease,
    DpmInstructionPackageNotFoundError,
    DpmInstructionPackageReleaseCommand,
    DpmInstructionPackageReleaseRefusedError,
)
from src.core.instruction_packages import (
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
from src.core.proof_packs.repository import DpmProofPackRepository
from src.core.rebalance_runs.service import DpmRunSupportService
from src.core.waves.repository import DpmWaveRepository


router = APIRouter(
    prefix="/rebalance/instruction-packages",
    tags=["lotus-manage Approved Instruction Packages"],
)


@dataclass(frozen=True)
class InstructionPackageTrustedIdentity:
    tenant_id: str
    actor_id: str
    role: str


class InstructionPackageReleaseRequest(BaseModel):
    wave_id: str = Field(min_length=1, examples=["dwv_001"])
    wave_item_id: str = Field(min_length=1, examples=["dwi_001"])
    rebalance_run_id: str = Field(min_length=1, examples=["rr_001"])
    mandate_id: str = Field(min_length=1, examples=["MANDATE_PB_SG_GLOBAL_BAL_001"])
    mandate_version: str = Field(min_length=1, examples=["12"])
    model_portfolio_id: str = Field(min_length=1, examples=["MODEL_SG_BALANCED"])
    model_portfolio_version: str | None = Field(default=None, examples=["2026.10"])
    policy_revision: str = Field(min_length=1, examples=["dpm-release-policy.v1"])
    account_key: str = Field(min_length=1, examples=["ACCOUNT-PB-SG-001"])
    mappings: list[DpmInstructionMappingEvidence] = Field(min_length=1)
    source_revisions: list[DpmInstructionPackageSourceRevision] = Field(default_factory=list)
    funding_evidence: DpmInstructionFundingEvidence
    approval_evidence: DpmInstructionApprovalEvidence
    supersedes_package_id: str | None = Field(default=None, examples=["dip_001"])
    supersedes_package_version: str | None = Field(default=None, examples=["1"])
    correlation_id: str = Field(min_length=1, examples=["corr-instruction-release-001"])


class InstructionPackagePreviewResponse(BaseModel):
    approved_material_hash: str
    approved_intent_hash: str
    instruction_count: int
    approval_material: DpmInstructionPackageApprovalMaterial


class InstructionPackageBatchReleaseItem(BaseModel):
    package_id: str = Field(min_length=1, examples=["dip_001"])
    package_version: str = Field(min_length=1, examples=["1"])
    release: InstructionPackageReleaseRequest


class InstructionPackageBatchReleaseRequest(BaseModel):
    items: list[InstructionPackageBatchReleaseItem] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def _require_distinct_package_identities(self) -> "InstructionPackageBatchReleaseRequest":
        identities = {(item.package_id, item.package_version) for item in self.items}
        if len(identities) != len(self.items):
            raise ValueError("INSTRUCTION_PACKAGE_BATCH_DUPLICATE_IDENTITY")
        return self


class InstructionPackageBatchRefusalResponse(BaseModel):
    package_id: str
    package_version: str
    wave_id: str
    wave_item_id: str
    reason_code: str


class InstructionPackageBatchReleaseResponse(BaseModel):
    packages: list[DpmApprovedInstructionPackage]
    refusals: list[InstructionPackageBatchRefusalResponse]
    partial_release_policy: str


class InstructionPackageReceiptRequest(BaseModel):
    consumer_id: str = Field(min_length=1, examples=["synthetic-bank-execution-adapter"])
    receipt_evidence_hash: str = Field(min_length=1, examples=["sha256:adapter-retrieval-001"])


def instruction_package_trusted_identity_required(
    request: Request,
) -> InstructionPackageTrustedIdentity:
    identity = InstructionPackageTrustedIdentity(
        tenant_id=request.headers.get("X-Tenant-Id", "").strip(),
        actor_id=request.headers.get("X-Actor-Id", "").strip(),
        role=request.headers.get("X-Role", "").strip(),
    )
    if not all((identity.tenant_id, identity.actor_id, identity.role)):
        raise _problem(status.HTTP_403_FORBIDDEN, "INSTRUCTION_PACKAGE_TRUSTED_IDENTITY_REQUIRED")
    return identity


def _release_identity_required(
    identity: InstructionPackageTrustedIdentity = Depends(
        instruction_package_trusted_identity_required
    ),
) -> InstructionPackageTrustedIdentity:
    if identity.role != "DPM_EXECUTION_RELEASE_MANAGER":
        raise _problem(status.HTTP_403_FORBIDDEN, "INSTRUCTION_PACKAGE_RELEASE_ROLE_FORBIDDEN")
    return identity


def _read_identity_required(
    identity: InstructionPackageTrustedIdentity = Depends(
        instruction_package_trusted_identity_required
    ),
) -> InstructionPackageTrustedIdentity:
    if identity.role not in {
        "DPM_EXECUTION_RELEASE_MANAGER",
        "DPM_EXECUTION_ADAPTER",
        "DPM_AUDITOR",
    }:
        raise _problem(status.HTTP_403_FORBIDDEN, "INSTRUCTION_PACKAGE_READ_ROLE_FORBIDDEN")
    return identity


def _receipt_identity_required(
    identity: InstructionPackageTrustedIdentity = Depends(
        instruction_package_trusted_identity_required
    ),
) -> InstructionPackageTrustedIdentity:
    if identity.role != "DPM_EXECUTION_ADAPTER":
        raise _problem(status.HTTP_403_FORBIDDEN, "INSTRUCTION_PACKAGE_RECEIPT_ROLE_FORBIDDEN")
    return identity


def get_instruction_package_application_service(
    repository: DpmInstructionPackageRepository = Depends(get_instruction_package_repository),
    wave_repository: DpmWaveRepository = Depends(get_wave_repository),
    proof_pack_repository: DpmProofPackRepository = Depends(get_proof_pack_repository),
    mandate_repository: DpmMandateRepository = Depends(get_mandate_repository),
    run_service: DpmRunSupportService = Depends(get_dpm_run_support_service),
) -> DpmInstructionPackageApplicationService:
    return DpmInstructionPackageApplicationService(
        repository=repository,
        wave_repository=wave_repository,
        proof_pack_repository=proof_pack_repository,
        mandate_repository=mandate_repository,
        run_service=run_service,
    )


@router.post(
    "/{package_id}/versions/{package_version}/preview",
    response_model=InstructionPackagePreviewResponse,
    summary="Canonicalize material for a governed instruction-package approval",
    description=(
        "Builds no package and sends no order. It validates the persisted run, READY proof pack, "
        "current mandate/model, mappings, funding evidence and exact quantities, then returns the "
        "hash which the approval system must bind before package release. Caller-asserted headers "
        "are an integration seam, not production identity-provider certification."
    ),
)
def preview_instruction_package(
    package_id: str,
    package_version: str,
    request: InstructionPackageReleaseRequest,
    identity: InstructionPackageTrustedIdentity = Depends(_release_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> InstructionPackagePreviewResponse:
    try:
        preview = service.preview_release(
            command=_command(
                request=request,
                identity=identity,
                package_id=package_id,
                package_version=package_version,
            )
        )
        return InstructionPackagePreviewResponse(
            approved_material_hash=preview.approved_material_hash,
            approved_intent_hash=preview.approved_intent_hash,
            instruction_count=preview.instruction_count,
            approval_material=preview.approval_material,
        )
    except (DpmInstructionPackageNotFoundError, DpmInstructionPackageReleaseRefusedError) as exc:
        raise _from_domain_error(exc) from exc


@router.post(
    "/batch-release",
    response_model=InstructionPackageBatchReleaseResponse,
    summary="Release only independently eligible items from a bounded reviewed batch",
    description=(
        "Processes at most 20 independent package candidates synchronously. The explicit policy is "
        "RELEASE_ELIGIBLE_ITEMS_ONLY: a source, approval, mapping, or funding refusal for one item "
        "does not authorize it and does not suppress another eligible item. Immutable identity "
        "conflicts fail the request rather than being converted into a partial result. This endpoint "
        "does not submit orders or claim execution, fills, settlement, or core booking."
    ),
)
def release_instruction_package_batch(
    request: InstructionPackageBatchReleaseRequest,
    identity: InstructionPackageTrustedIdentity = Depends(_release_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> InstructionPackageBatchReleaseResponse:
    try:
        released = service.release_batch(
            commands=[
                _command(
                    request=item.release,
                    identity=identity,
                    package_id=item.package_id,
                    package_version=item.package_version,
                )
                for item in request.items
            ]
        )
        return _batch_response(released)
    except DpmInstructionPackageConflictError as exc:
        raise _from_domain_error(exc) from exc


@router.put(
    "/{package_id}/versions/{package_version}",
    response_model=DpmApprovedInstructionPackage,
    summary="Release one immutable approved instruction package",
    description=(
        "Persists an immutable package only after the supplied approval material hash matches the "
        "exact mapped reviewed economic material. Exact retries return the original package; a "
        "changed payload at the same identity conflicts. This endpoint does not submit an order or "
        "claim an external execution, fill, settlement, or core booking."
    ),
)
def release_instruction_package(
    package_id: str,
    package_version: str,
    request: InstructionPackageReleaseRequest,
    identity: InstructionPackageTrustedIdentity = Depends(_release_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> DpmApprovedInstructionPackage:
    try:
        package, _ = service.release(
            command=_command(
                request=request,
                identity=identity,
                package_id=package_id,
                package_version=package_version,
            )
        )
        return package
    except (
        DpmInstructionPackageConflictError,
        DpmInstructionPackageNotFoundError,
        DpmInstructionPackageReleaseRefusedError,
    ) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/{package_id}/versions/{package_version}",
    response_model=DpmApprovedInstructionPackage,
    summary="Retrieve one exact immutable instruction package",
)
def get_instruction_package(
    package_id: str,
    package_version: str,
    identity: InstructionPackageTrustedIdentity = Depends(_read_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> DpmApprovedInstructionPackage:
    try:
        return service.get_package(
            tenant_id=identity.tenant_id,
            package_id=package_id,
            package_version=package_version,
        )
    except DpmInstructionPackageNotFoundError as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "",
    response_model=DpmInstructionPackagePage,
    summary="List immutable instruction packages from a deterministic snapshot",
)
def list_instruction_packages(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    page_token: str | None = Query(default=None, min_length=1),
    identity: InstructionPackageTrustedIdentity = Depends(_read_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> DpmInstructionPackagePage:
    try:
        return service.list_packages(
            tenant_id=identity.tenant_id,
            limit=limit,
            page_token=page_token,
        )
    except DpmInstructionPackageReleaseRefusedError as exc:
        raise _from_domain_error(exc) from exc


@router.post(
    "/{package_id}/versions/{package_version}/receipts",
    response_model=DpmInstructionPackageReceipt,
    summary="Acknowledge package retrieval without claiming execution",
    description=(
        "Records one durable consumer receipt keyed by package version and consumer. A receipt says "
        "only that the adapter retrieved the immutable package; it cannot create an order, fill, "
        "settlement, cancellation, or booking state."
    ),
)
def acknowledge_instruction_package_receipt(
    package_id: str,
    package_version: str,
    request: InstructionPackageReceiptRequest,
    identity: InstructionPackageTrustedIdentity = Depends(_receipt_identity_required),
    service: DpmInstructionPackageApplicationService = Depends(
        get_instruction_package_application_service
    ),
) -> DpmInstructionPackageReceipt:
    try:
        receipt, _ = service.acknowledge_receipt(
            tenant_id=identity.tenant_id,
            package_id=package_id,
            package_version=package_version,
            consumer_id=request.consumer_id,
            receipt_evidence_hash=request.receipt_evidence_hash,
        )
        return receipt
    except (
        DpmInstructionPackageConflictError,
        DpmInstructionPackageNotFoundError,
        DpmInstructionPackageReleaseRefusedError,
    ) as exc:
        raise _from_domain_error(exc) from exc


def _command(
    *,
    request: InstructionPackageReleaseRequest,
    identity: InstructionPackageTrustedIdentity,
    package_id: str,
    package_version: str,
) -> DpmInstructionPackageReleaseCommand:
    return DpmInstructionPackageReleaseCommand(
        tenant_id=identity.tenant_id,
        package_id=package_id,
        package_version=package_version,
        released_by=identity.actor_id,
        wave_id=request.wave_id,
        wave_item_id=request.wave_item_id,
        rebalance_run_id=request.rebalance_run_id,
        mandate_id=request.mandate_id,
        mandate_version=request.mandate_version,
        model_portfolio_id=request.model_portfolio_id,
        model_portfolio_version=request.model_portfolio_version,
        policy_revision=request.policy_revision,
        account_key=request.account_key,
        mappings=request.mappings,
        source_revisions=request.source_revisions,
        funding_evidence=request.funding_evidence,
        approval_evidence=request.approval_evidence,
        supersedes_package_id=request.supersedes_package_id,
        supersedes_package_version=request.supersedes_package_version,
        correlation_id=request.correlation_id,
    )


def _batch_response(
    released: DpmInstructionPackageBatchRelease,
) -> InstructionPackageBatchReleaseResponse:
    return InstructionPackageBatchReleaseResponse(
        packages=released.packages,
        refusals=[
            InstructionPackageBatchRefusalResponse(
                package_id=refusal.package_id,
                package_version=refusal.package_version,
                wave_id=refusal.wave_id,
                wave_item_id=refusal.wave_item_id,
                reason_code=refusal.reason_code,
            )
            for refusal in released.refusals
        ],
        partial_release_policy=released.partial_release_policy,
    )


def _from_domain_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code.endswith("NOT_FOUND"):
        return _problem(status.HTTP_404_NOT_FOUND, code)
    if "CONFLICT" in code:
        return _problem(status.HTTP_409_CONFLICT, code)
    return _problem(status.HTTP_422_UNPROCESSABLE_CONTENT, code)


def _problem(status_code: int, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": code})


__all__ = ["get_instruction_package_application_service", "router"]
