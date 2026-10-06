"""Authenticated HTTP source product for composite eligibility revisions."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.api.composite_identity import (
    CompositeTrustedIdentity,
    composite_trusted_identity_required,
    composite_write_identity_required,
)
from src.api.composite_definition_requests import CompositeDefinitionV2Request
from src.core.composite_definition_versions import (
    CompositeDefinition,
    DpmCompositeDefinitionV2,
    parse_composite_definition_json,
)

from src.api.dependencies import get_composite_membership_application_service
from src.api.services.composite_membership_application import (
    DpmCompositeDefinitionCommand,
    DpmCompositeMembershipApplicationService,
    DpmCompositeMembershipRevisionCommand,
    DpmCompositeUniverseAttestationCommand,
    DpmCompositeReceiptCommand,
    DpmCompositeNotFoundError,
)
from src.core.composite_membership import (
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
    DpmCompositeSourceAuthority,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_publication import (
    DpmCompositeMembershipPublication,
    DpmCompositePublicationPage,
    DpmCompositePublicationReceipt,
    DpmCompositePublicationReconciliation,
)
from src.core.composite_universe import (
    CompositeUniversePosture,
    DpmCompositeUniverseAttestation,
    DpmCompositeUniverseSourceProduct,
)

router = APIRouter(
    prefix="/rebalance/composites",
    tags=["lotus-manage Composite Membership"],
)


class CompositeDefinitionRequest(BaseModel):
    product_version: Literal["v1"] = "v1"
    display_name: str = Field(min_length=1, examples=["Private Banking Global Balanced Composite"])
    strategy_code: str = Field(min_length=1, examples=["GLOBAL_BALANCED"])
    reporting_currency: str = Field(examples=["USD"])
    inception_date: str = Field(examples=["2024-01-01"])
    termination_date: str | None = Field(default=None, examples=["2026-12-31"])
    eligibility_policy_version: str = Field(examples=["composite-eligibility.v1"])
    source_authority: DpmCompositeSourceAuthority
    correlation_id: str = Field(min_length=1, examples=["corr-composite-definition-001"])

    @model_validator(mode="before")
    @classmethod
    def forbid_silent_version_downgrade(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            key in value for key in ("definition_payload_digest", "authority_approval")
        ):
            raise ValueError("COMPOSITE_DEFINITION_EXPLICIT_V2_REQUIRED")
        return value


class CompositeMembershipRevisionRequest(BaseModel):
    policy_version: str = Field(examples=["composite-eligibility.v1"])
    source_cut_id: str = Field(examples=["core-cut-2026-10-01"])
    decisions: list[DpmCompositeMembershipDecision] = Field(min_length=1)
    correlation_id: str = Field(min_length=1, examples=["corr-composite-membership-001"])
    supersedes_membership_revision: str | None = Field(default=None, examples=["2026.10.1"])
    affected_from: str | None = Field(default=None, examples=["2026-02-01"])
    affected_to: str | None = Field(default=None, examples=["2026-02-28"])


class CompositeDefinitionPage(BaseModel):
    items: list[CompositeDefinition]
    count: int = Field(
        ge=0, description="Total tenant-scoped definitions at this page's read snapshot."
    )
    limit: int
    offset: int


class CompositeMembershipRevisionPage(BaseModel):
    items: list[DpmCompositeMembershipRevision]
    count: int = Field(ge=0, description="Total scoped revisions at this page's read snapshot.")
    limit: int
    offset: int


class CompositeMembershipAsOfResponse(BaseModel):
    composite_id: str
    definition_version: str
    membership_revision: str
    as_of_date: str
    decisions: list[DpmCompositeMembershipDecision]
    source_cut_id: str
    content_hash: str


class CompositePublicationReceiptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_content_hash: str = Field(min_length=1)
    receipt_evidence_hash: str = Field(min_length=1)
    disposition: Literal["RECEIVED", "REJECTED"]
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    correlation_id: str = Field(min_length=1)


class CompositePublicationReceiptResponse(BaseModel):
    receipt: DpmCompositePublicationReceipt
    created: bool


class CompositeUniverseAttestationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage_from: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    coverage_to: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    policy_version: str = Field(min_length=1)
    source_cut_id: str = Field(min_length=1)
    source_products: list[DpmCompositeUniverseSourceProduct] = Field(min_length=1)
    posture: CompositeUniversePosture
    expected_portfolio_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,63}$")
    correlation_id: str = Field(min_length=1)


class CompositeUniverseAttestationPage(BaseModel):
    items: list[DpmCompositeUniverseAttestation]
    count: int = Field(ge=0)
    limit: int
    offset: int


def _publication_consumer_identity_required(
    request: Request,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
) -> CompositeTrustedIdentity:
    if (
        identity.role != "DPM_COMPOSITE_CONSUMER"
        or request.headers.get("X-Service-Identity", "").strip() != "lotus-performance"
    ):
        raise _problem(status.HTTP_403_FORBIDDEN, "COMPOSITE_CONSUMER_ROLE_FORBIDDEN")
    return identity


def _universe_attester_identity_required(
    request: Request,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
) -> CompositeTrustedIdentity:
    if (
        identity.role != "DPM_COMPOSITE_UNIVERSE_ATTESTER"
        or request.headers.get("X-Service-Identity", "").strip() != "lotus-manage"
    ):
        raise _problem(status.HTTP_403_FORBIDDEN, "COMPOSITE_UNIVERSE_ATTESTER_ROLE_FORBIDDEN")
    return identity


async def _raw_definition_json_required(request: Request) -> None:
    try:
        parse_composite_definition_json((await request.body()).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        code = (
            str(exc)
            if str(exc).startswith("COMPOSITE_DEFINITION_")
            else "COMPOSITE_DEFINITION_RAW_JSON_INVALID"
        )
        raise _problem(status.HTTP_422_UNPROCESSABLE_CONTENT, code) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}",
    response_model=CompositeDefinition,
    summary="Persist an immutable composite definition version",
)
def put_definition(
    composite_id: str,
    definition_version: str,
    request: CompositeDefinitionRequest | CompositeDefinitionV2Request,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
    _raw_json: None = Depends(_raw_definition_json_required),
) -> CompositeDefinition:
    try:
        if isinstance(request, CompositeDefinitionV2Request):
            definition = DpmCompositeDefinitionV2.model_validate(
                {
                    **request.model_dump(mode="json"),
                    "product_name": "CompositeDefinition",
                    "tenant_id": identity.tenant_id,
                    "composite_id": composite_id,
                    "definition_version": definition_version,
                    "created_by": identity.actor_id,
                }
            )
            return service.save_versioned_definition(definition=definition)
        return service.save_definition(
            command=DpmCompositeDefinitionCommand(
                tenant_id=identity.tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                actor_id=identity.actor_id,
                **request.model_dump(exclude={"product_version"}),
            )
        )
    except ValidationError as exc:
        raise _problem(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "COMPOSITE_DEFINITION_V2_INVALID"
        ) from exc
    except (DpmCompositeConflictError, ValueError) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/definitions", response_model=CompositeDefinitionPage, summary="List composite definitions"
)
def list_definitions(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositeDefinitionPage:
    page = service.list_definitions(tenant_id=identity.tenant_id, limit=limit, offset=offset)
    return CompositeDefinitionPage(items=page.items, count=page.count, limit=limit, offset=offset)


@router.get("/{composite_id}/definitions/{definition_version}", response_model=CompositeDefinition)
def get_definition(
    composite_id: str,
    definition_version: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositeDefinition:
    try:
        return service.get_definition(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
        )
    except DpmCompositeNotFoundError as exc:
        raise _from_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}",
    response_model=DpmCompositeMembershipRevision,
    summary="Persist an immutable effective-dated membership revision",
)
def put_membership_revision(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    request: CompositeMembershipRevisionRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositeMembershipRevision:
    try:
        return service.save_membership_revision(
            command=DpmCompositeMembershipRevisionCommand(
                tenant_id=identity.tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                membership_revision=membership_revision,
                actor_id=identity.actor_id,
                **request.model_dump(),
            )
        )
    except (DpmCompositeConflictError, ValueError) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/membership",
    response_model=CompositeMembershipRevisionPage,
)
def list_membership_revisions(
    composite_id: str,
    definition_version: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositeMembershipRevisionPage:
    page = service.list_membership_revisions(
        tenant_id=identity.tenant_id,
        composite_id=composite_id,
        definition_version=definition_version,
        limit=limit,
        offset=offset,
    )
    return CompositeMembershipRevisionPage(
        items=page.items, count=page.count, limit=limit, offset=offset
    )


@router.get(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}",
    response_model=DpmCompositeMembershipRevision,
)
def get_membership_revision(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositeMembershipRevision:
    try:
        return service.get_membership_revision(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
        )
    except DpmCompositeNotFoundError as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}/as-of",
    response_model=CompositeMembershipAsOfResponse,
)
def get_membership_as_of(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    as_of_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositeMembershipAsOfResponse:
    try:
        revision = service.get_membership_revision(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
        )
        decisions = service.membership_as_of(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            as_of_date=as_of_date,
        )
        return CompositeMembershipAsOfResponse(
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            as_of_date=as_of_date,
            decisions=decisions,
            source_cut_id=revision.source_cut_id,
            content_hash=revision.content_hash,
        )
    except (DpmCompositeNotFoundError, ValueError) as exc:
        raise _from_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}"
    "/universe-attestations/{attestation_version}",
    response_model=DpmCompositeUniverseAttestation,
    summary="Persist immutable source-universe completeness evidence",
)
def put_universe_attestation(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    attestation_version: str,
    request: CompositeUniverseAttestationRequest,
    identity: CompositeTrustedIdentity = Depends(_universe_attester_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositeUniverseAttestation:
    try:
        return service.save_universe_attestation(
            command=DpmCompositeUniverseAttestationCommand(
                tenant_id=identity.tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                membership_revision=membership_revision,
                attestation_version=attestation_version,
                actor_id=identity.actor_id,
                **request.model_dump(),
            )
        )
    except (DpmCompositeNotFoundError, DpmCompositeConflictError, ValueError) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}"
    "/universe-attestations/{attestation_version}",
    response_model=DpmCompositeUniverseAttestation,
)
def get_universe_attestation(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    attestation_version: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositeUniverseAttestation:
    try:
        return service.get_universe_attestation(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            attestation_version=attestation_version,
        )
    except (DpmCompositeNotFoundError, DpmCompositeConflictError) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/membership/{membership_revision}"
    "/universe-attestations",
    response_model=CompositeUniverseAttestationPage,
)
def list_universe_attestations(
    composite_id: str,
    definition_version: str,
    membership_revision: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositeUniverseAttestationPage:
    try:
        page = service.list_universe_attestations(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=membership_revision,
            limit=limit,
            offset=offset,
        )
    except DpmCompositeConflictError as exc:
        raise _from_domain_error(exc) from exc
    return CompositeUniverseAttestationPage(
        items=page.items, count=page.count, limit=limit, offset=offset
    )


@router.get(
    "/publications",
    response_model=DpmCompositePublicationPage,
    summary="List committed composite membership publications by tenant cursor",
)
def list_publications(
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositePublicationPage:
    try:
        return service.list_publications(
            tenant_id=identity.tenant_id, after_sequence=after_sequence, limit=limit
        )
    except DpmCompositeConflictError as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/publications/{sequence}",
    response_model=DpmCompositeMembershipPublication,
    summary="Read one pinned composite publication",
)
def get_publication(
    sequence: int,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositeMembershipPublication:
    try:
        return service.get_publication(tenant_id=identity.tenant_id, sequence=sequence)
    except (DpmCompositeNotFoundError, DpmCompositeConflictError) as exc:
        raise _from_domain_error(exc) from exc


@router.get(
    "/publications/{sequence}/reconciliation",
    response_model=DpmCompositePublicationReconciliation,
    summary="Inspect publication receipt without claiming fact materialization",
)
def get_publication_reconciliation(
    sequence: int,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> DpmCompositePublicationReconciliation:
    try:
        return service.publication_reconciliation(tenant_id=identity.tenant_id, sequence=sequence)
    except (DpmCompositeNotFoundError, DpmCompositeConflictError) as exc:
        raise _from_domain_error(exc) from exc


@router.put(
    "/publications/{sequence}/receipts/lotus-performance",
    response_model=CompositePublicationReceiptResponse,
    summary="Acknowledge retrieval of one immutable composite source publication",
)
def acknowledge_publication(
    sequence: int,
    request: CompositePublicationReceiptRequest,
    identity: CompositeTrustedIdentity = Depends(_publication_consumer_identity_required),
    service: DpmCompositeMembershipApplicationService = Depends(
        get_composite_membership_application_service
    ),
) -> CompositePublicationReceiptResponse:
    try:
        receipt, created = service.acknowledge_receipt(
            command=DpmCompositeReceiptCommand(
                tenant_id=identity.tenant_id,
                publication_sequence=sequence,
                consumer_id="lotus-performance",
                **request.model_dump(),
            )
        )
        return CompositePublicationReceiptResponse(receipt=receipt, created=created)
    except (DpmCompositeConflictError, ValueError) as exc:
        raise _from_domain_error(exc) from exc


def _from_domain_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code in {
        "COMPOSITE_PROVIDER_TRUST_UNAVAILABLE",
        "COMPOSITE_AUTHORITY_ATTESTATION_VERIFIER_UNAVAILABLE",
    }:
        return _problem(status.HTTP_503_SERVICE_UNAVAILABLE, code)
    status_code = (
        status.HTTP_404_NOT_FOUND
        if code.endswith("NOT_FOUND")
        else (
            status.HTTP_409_CONFLICT
            if "CONFLICT" in code or "MISMATCH" in code or "CURSOR_AHEAD" in code
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
    )
    return _problem(status_code, code)


def _problem(status_code: int, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": code})
