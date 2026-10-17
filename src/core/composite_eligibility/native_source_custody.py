"""Compact native commitments, distinct Core roots and Manage-owned role sets.

These closed retained models validate content consistency. They neither retrieve
Core bytes nor establish supplier authenticity, enrollment or financial authority.
Native hash recipes follow Core's pinned v3 declaration/read-root specification.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Identity, StrictAuthorityModel
from src.core.composite_eligibility.observations import (
    Currency,
    MonthlyEligibilityObservations,
    MonthlyPortfolioObservations,
)
from src.core.composite_eligibility.policy import month_window

NativeRole = Literal["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"]
NATIVE_ROLES: tuple[NativeRole, ...] = (
    "PRIOR_ASSETS",
    "MONTH_END_ASSETS",
    "CASH",
    "READINESS",
    "FLOWS",
)
ROLE_PRODUCTS = {
    "PRIOR_ASSETS": "PortfolioTimeseriesInput",
    "MONTH_END_ASSETS": "PortfolioTimeseriesInput",
    "CASH": "PortfolioFinancialSourceObservations",
    "READINESS": "PortfolioFinancialSourceObservations",
    "FLOWS": "PortfolioFinancialFlowObservations",
}
BareDigest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Nonnegative = Annotated[int, Field(ge=0)]
Positive = Annotated[int, Field(ge=1)]


def _opaque_text(value: str) -> str:
    if value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError("COMPOSITE_NATIVE_IDENTITY_INVALID")
    return value


NativeText = Annotated[
    str, StringConstraints(min_length=1, max_length=128), AfterValidator(_opaque_text)
]


def _business_date(value: str) -> str:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("COMPOSITE_NATIVE_DATE_INVALID")
    return value


def _aware_time(value: str) -> str:
    if datetime.fromisoformat(value).utcoffset() is None:
        raise ValueError("COMPOSITE_NATIVE_AWARE_TIME_REQUIRED")
    return value


NativeDate = Annotated[str, AfterValidator(_business_date)]
NativeInstant = Annotated[str, AfterValidator(_aware_time)]


class NativeModel(StrictAuthorityModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, revalidate_instances="always"
    )


def _immutable_array(value: Any) -> Any:
    """Preserve JSON arrays while owning immutable in-memory native collections."""
    return tuple(value) if isinstance(value, list) else value


class NativeSourceAddress(NativeModel):
    source_system: NativeText
    registry_scope_id: NativeText
    source_cut_id: NativeText
    revision: Positive


class NativeSourceIdentity(NativeModel):
    tenant_id: NativeText
    source_system: NativeText
    scope_id: NativeText
    source_cut_id: NativeText
    revision: Positive
    definition_version: NativeText
    coverage_from: NativeDate
    coverage_to: NativeDate
    calendar: NativeText
    observed_at: NativeInstant
    generated_at: NativeInstant
    predecessor_hash: BareDigest | None
    expected_head_hash: BareDigest | None

    @model_validator(mode="after")
    def require_source_identity(self) -> NativeSourceIdentity:
        if self.coverage_from > self.coverage_to:
            raise ValueError("COMPOSITE_NATIVE_COVERAGE_INVALID")
        if self.revision == 1:
            valid = self.predecessor_hash is None and self.expected_head_hash is None
        else:
            valid = self.predecessor_hash is not None and (
                self.predecessor_hash == self.expected_head_hash
            )
        if not valid:
            raise ValueError("COMPOSITE_NATIVE_CORRECTION_INVALID")
        return self


class NativeExpectedPopulation(NativeModel):
    reference: NativeText
    definition_version: NativeText
    count: Nonnegative
    content_hash: BareDigest


class NativeRegistryManifest(NativeModel):
    identity: NativeSourceIdentity
    expected_population: NativeExpectedPopulation
    declared_coverage: Literal["COMPLETE", "PARTIAL", "MISSING"]
    supplied_count: Nonnegative
    members_root: BareDigest
    chunk_count: Nonnegative
    chunks_root: BareDigest

    @model_validator(mode="after")
    def require_chunks(self) -> NativeRegistryManifest:
        if self.supplied_count and not self.chunk_count:
            raise ValueError("COMPOSITE_NATIVE_CHUNKS_REQUIRED")
        return self


class NativeFinancialManifest(NativeModel):
    identity: NativeSourceIdentity
    selection_count: Nonnegative
    selections_root: BareDigest
    chunk_count: Nonnegative
    chunks_root: BareDigest

    @model_validator(mode="after")
    def require_chunks(self) -> NativeFinancialManifest:
        if self.selection_count and not self.chunk_count:
            raise ValueError("COMPOSITE_NATIVE_CHUNKS_REQUIRED")
        return self


class NativeProductSelection(NativeModel):
    role: NativeRole
    product_name: NativeText
    product_version: Literal["v1"]
    selector_hash: BareDigest
    content_hash: BareDigest
    receipt_job_id: NativeText
    source_revision: NativeText

    @model_validator(mode="after")
    def require_product_family(self) -> NativeProductSelection:
        if self.product_name != ROLE_PRODUCTS[self.role]:
            raise ValueError("COMPOSITE_NATIVE_PRODUCT_FAMILY_MISMATCH")
        return self


class NativeCashDeclaration(NativeModel):
    amount: Annotated[str, StringConstraints(pattern=r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")] | None
    currency: Currency
    business_date: NativeDate
    semantic_definition: NativeText
    producer_revision: NativeText

    @model_validator(mode="after")
    def require_canonical_cash(self) -> NativeCashDeclaration:
        if self.amount is None:
            return self
        amount = Decimal(self.amount)
        if not amount.is_finite():
            raise ValueError("COMPOSITE_NATIVE_CASH_INVALID")
        exponent = amount.as_tuple().exponent
        if (
            not isinstance(exponent, int)
            or exponent < -16383
            or (not amount.is_zero() and amount.adjusted() >= 131072)
        ):
            raise ValueError("COMPOSITE_NATIVE_CASH_INVALID")
        canonical = (
            Decimal((0, (0,), min(exponent, 0)))
            if amount.is_zero()
            else Decimal(format(amount, "f"))
            if exponent > 0
            else amount
        )
        if str(canonical) != self.amount:
            raise ValueError("COMPOSITE_NATIVE_CASH_NONCANONICAL")
        return self


class NativeCompatibilityDeclaration(NativeModel):
    source_system: NativeText
    scope_id: NativeText
    definition_version: NativeText
    registry_root: BareDigest
    role_roots: Annotated[
        tuple[Annotated[tuple[NativeRole, BareDigest], BeforeValidator(_immutable_array)], ...],
        BeforeValidator(_immutable_array),
    ] = Field(min_length=5, max_length=5)
    coverage_from: NativeDate
    coverage_to: NativeDate
    currency: Currency
    basis_reference: NativeText
    original_evidence_digest: BareDigest


class NativeFinancialGraph(NativeModel):
    identity: NativeSourceIdentity
    portfolio_id: NativeText
    currency: Currency
    prior_date: NativeDate
    month_end_date: NativeDate
    registry_root: BareDigest
    member_revision: Positive
    selections: Annotated[tuple[NativeProductSelection, ...], BeforeValidator(_immutable_array)] = (
        Field(min_length=5, max_length=5)
    )
    settled_unencumbered: NativeCashDeclaration | None
    compatibility: NativeCompatibilityDeclaration | None

    @model_validator(mode="after")
    def require_graph(self) -> NativeFinancialGraph:
        if self.prior_date >= self.month_end_date or [s.role for s in self.selections] != list(
            NATIVE_ROLES
        ):
            raise ValueError("COMPOSITE_NATIVE_GRAPH_SHAPE_INVALID")
        cash = self.settled_unencumbered
        if cash is not None and (cash.currency, cash.business_date) != (
            self.currency,
            self.month_end_date,
        ):
            raise ValueError("COMPOSITE_NATIVE_CASH_BINDING_MISMATCH")
        declaration = self.compatibility
        if declaration is not None:
            self._require_compatibility(declaration)
        return self

    def _require_compatibility(self, declaration: NativeCompatibilityDeclaration) -> None:
        if (
            declaration.registry_root != self.registry_root
            or declaration.role_roots != tuple((s.role, s.content_hash) for s in self.selections)
            or declaration.currency != self.currency
            or (declaration.coverage_from, declaration.coverage_to)
            != (self.identity.coverage_from, self.identity.coverage_to)
            or declaration.source_system != self.identity.source_system
            or declaration.scope_id != self.identity.scope_id
        ):
            raise ValueError("COMPOSITE_NATIVE_COMPATIBILITY_MISMATCH")


def _domain_tags(value: Any, field: str = "") -> Any:
    """Rehydrate only the closed retained declaration's native date/Decimal fields."""
    if isinstance(value, dict):
        return {key: _domain_tags(item, key) for key, item in value.items()}
    if isinstance(value, list):
        return [_domain_tags(item) for item in value]
    return _native_scalar_tag(value, field)


def _native_scalar_tag(value: Any, field: str) -> Any:
    """Encode the native scalar types that participate in Core domain hashes."""
    if value is None:
        return value
    if field in {
        "coverage_from",
        "coverage_to",
        "prior_date",
        "month_end_date",
        "business_date",
    }:
        return {"date": date.fromisoformat(value).isoformat()}
    if field in {"observed_at", "generated_at"}:
        return {"datetime": datetime.fromisoformat(value).astimezone(UTC).isoformat()}
    if field == "amount":
        return {"decimal": str(Decimal(value))}
    return value


def native_domain_hash(contract: str, field: str, model: NativeModel) -> str:
    """Core domain hash; never derive this by stripping a Manage digest prefix."""
    material = {"contract": contract, field: _domain_tags(model.model_dump(mode="json"))}
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def native_ordered_root(contract: str, hashes: Sequence[str]) -> str:
    state = hashlib.sha256((contract + "\0").encode()).digest()
    for digest in hashes:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("COMPOSITE_NATIVE_ROOT_ITEM_INVALID")
        state = hashlib.sha256(state + bytes.fromhex(digest)).digest()
    return hashlib.sha256(state + b"\0" + str(len(hashes)).encode("ascii")).hexdigest()


class NativeCutLocator(NativeModel):
    product_name: Literal["PortfolioHistoricalRegistry", "PortfolioFinancialSourceCut"]
    product_version: Literal["v1"] = "v1"
    source_address: NativeSourceAddress
    batch_manifest_hash: BareDigest


class NativeCutReceipt(NativeModel):
    receipt_job_id: NativeText
    received_at: NativeInstant
    completed_at: NativeInstant
    generated_at: NativeInstant

    @model_validator(mode="after")
    def require_completed_receipt(self) -> NativeCutReceipt:
        if datetime.fromisoformat(self.received_at) > datetime.fromisoformat(self.completed_at):
            raise ValueError("COMPOSITE_NATIVE_RECEIPT_WINDOW_INVALID")
        return self


class NativeViewRoot(NativeModel):
    view: Literal["CUT", "MEMBERS", "INPUTS", "CAPTURES"]
    total_count: Nonnegative
    ordered_set_hash: BareDigest
    root_item_count: Nonnegative
    root_kind: Literal[
        "CUT_HEADERS", "REGISTRY_MEMBERS", "SELECTED_FINANCIAL_INPUTS", "CAPTURE_ARTIFACTS"
    ]
    ordering: Literal[
        "single_cut",
        "provider_namespace,source_member_id",
        "selected_portfolio",
        "role,source_page_index,capture_id,segment_index",
    ]


class NativeCaptureContext(NativeModel):
    capture_origin: Literal["ACQUIRED_NATIVE_DTO", "INGRESS_JSON"]
    captured_at: NativeInstant
    snapshot_epoch: str | None
    request_scope: str | None
    receipt_job_id: NativeText
    source_revision: str | None
    selector_json: str | None
    export_job_id: str | None
    refresh_of_job_id: str | None
    returned_count: Nonnegative | None
    total_count: Nonnegative | None
    next_page_token: str | None


class NativeCaptureCommitment(NativeModel):
    capture_id: BareDigest
    role: NativeRole | None
    source_page_index: Nonnegative
    source_product: NativeText
    product_version: NativeText
    selector_hash: BareDigest | None
    typed_content_hash: BareDigest
    raw_hash: BareDigest
    byte_count: Positive
    segment_count: Positive
    serializer_id: NativeText
    schema_version: NativeText
    mime_type: Literal["application/json", "application/x-ndjson"]
    source_context: NativeCaptureContext
    original_supplier_digest: BareDigest | None
    original_supplier_reference: str | None

    @model_validator(mode="after")
    def require_artifact_shape(self) -> NativeCaptureCommitment:
        if self.segment_count != (self.byte_count + 524287) // 524288:
            raise ValueError("COMPOSITE_NATIVE_SEGMENT_COUNT_MISMATCH")
        if (self.original_supplier_digest is None) != (self.original_supplier_reference is None):
            raise ValueError("COMPOSITE_NATIVE_SUPPLIER_PAIR_INVALID")
        context = self.source_context
        if context.refresh_of_job_id is not None and context.export_job_id is None:
            raise ValueError("COMPOSITE_NATIVE_EXPORT_REFERENCE_INVALID")
        if context.capture_origin == "ACQUIRED_NATIVE_DTO":
            self._require_acquired_context()
        if self.source_product == "PortfolioTimeseriesInput" and not context.snapshot_epoch:
            raise ValueError("COMPOSITE_NATIVE_VALUATION_EPOCH_REQUIRED")
        return self

    def _require_acquired_context(self) -> None:
        context = self.source_context
        if (
            self.role is None
            or self.selector_hash is None
            or context.returned_count is None
            or context.total_count is None
            or context.returned_count > context.total_count
            or context.source_revision is None
        ):
            raise ValueError("COMPOSITE_NATIVE_ACQUIRED_CONTEXT_INVALID")


class NativeRegistryMemberBinding(NativeModel):
    portfolio_id: Identity
    provider_id: Identity
    provider_namespace: NativeText
    source_member_id: NativeText
    member_revision: Positive
    member_content_hash: BareDigest


def _capture_key(capture: NativeCaptureCommitment) -> tuple[int, int, str]:
    return (
        NATIVE_ROLES.index(capture.role) if capture.role is not None else -1,
        capture.source_page_index,
        capture.capture_id,
    )


def _require_captures(captures: Sequence[NativeCaptureCommitment]) -> None:
    keys = [_capture_key(capture) for capture in captures]
    if keys != sorted(set(keys)):
        raise ValueError("COMPOSITE_NATIVE_CAPTURES_NONCANONICAL")


def native_capture_root(captures: Sequence[NativeCaptureCommitment]) -> str:
    hashes = [
        hash_canonical_payload(
            {"contract": "PortfolioNeutralSourceCaptureArtifact:v1", **c.model_dump(mode="json")}
        ).removeprefix("sha256:")
        for c in captures
    ]
    return native_ordered_root("PortfolioNeutralSourceCaptureArtifacts:v1", hashes)


def _require_view(
    root: NativeViewRoot, view: str, kind: str, ordering: str, total: int, count: int, digest: str
) -> None:
    if (
        root.view,
        root.root_kind,
        root.ordering,
        root.total_count,
        root.root_item_count,
        root.ordered_set_hash,
    ) != (view, kind, ordering, total, count, digest):
        raise ValueError("COMPOSITE_NATIVE_VIEW_ROOT_MISMATCH")


def _require_header(
    locator: NativeCutLocator,
    receipt: NativeCutReceipt,
    identity: NativeSourceIdentity,
    product: str,
    digest: str,
) -> None:
    address = locator.source_address
    if (
        locator.product_name,
        locator.batch_manifest_hash,
        address.source_system,
        address.registry_scope_id,
        address.source_cut_id,
        address.revision,
        receipt.generated_at,
    ) != (
        product,
        digest,
        identity.source_system,
        identity.scope_id,
        identity.source_cut_id,
        identity.revision,
        identity.generated_at,
    ):
        raise ValueError("COMPOSITE_NATIVE_LOCATOR_MANIFEST_MISMATCH")


def _require_capture_view(
    root: NativeViewRoot, captures: Sequence[NativeCaptureCommitment]
) -> None:
    _require_captures(captures)
    _require_view(
        root,
        "CAPTURES",
        "CAPTURE_ARTIFACTS",
        "role,source_page_index,capture_id,segment_index",
        sum(c.segment_count for c in captures),
        len(captures),
        native_capture_root(captures),
    )


class NativeRegistryCustody(NativeModel):
    locator: NativeCutLocator
    manifest: NativeRegistryManifest
    receipt: NativeCutReceipt
    view_roots: Annotated[tuple[NativeViewRoot, ...], BeforeValidator(_immutable_array)] = Field(
        min_length=3, max_length=3
    )
    member_bindings: Annotated[
        tuple[NativeRegistryMemberBinding, ...], BeforeValidator(_immutable_array)
    ] = Field(max_length=1000)
    captures: Annotated[tuple[NativeCaptureCommitment, ...], BeforeValidator(_immutable_array)]

    @model_validator(mode="after")
    def require_registry_custody(self) -> NativeRegistryCustody:
        manifest = self.manifest
        digest = native_domain_hash("PortfolioHistoricalRegistry:v1", "cut", manifest)
        _require_header(
            self.locator, self.receipt, manifest.identity, "PortfolioHistoricalRegistry", digest
        )
        keys = [(m.provider_namespace, m.source_member_id) for m in self.member_bindings]
        ids = [m.portfolio_id for m in self.member_bindings]
        if keys != sorted(set(keys)) or len(ids) != len(set(ids)):
            raise ValueError("COMPOSITE_NATIVE_MEMBERS_NONCANONICAL")
        members_root = native_ordered_root(
            "PortfolioHistoricalRegistryMembers:v1",
            [m.member_content_hash for m in self.member_bindings],
        )
        if manifest.supplied_count != len(keys) or manifest.members_root != members_root:
            raise ValueError("COMPOSITE_NATIVE_MEMBER_ROOT_MISMATCH")
        _require_view(
            self.view_roots[0],
            "CUT",
            "CUT_HEADERS",
            "single_cut",
            1,
            1,
            native_ordered_root("NeutralSourceCutHeaders:v1", [digest]),
        )
        _require_view(
            self.view_roots[1],
            "MEMBERS",
            "REGISTRY_MEMBERS",
            "provider_namespace,source_member_id",
            len(keys),
            len(keys),
            members_root,
        )
        _require_capture_view(self.view_roots[2], self.captures)
        _require_registry_captures(self.captures, self.receipt.receipt_job_id)
        return self


def _require_registry_captures(
    captures: Sequence[NativeCaptureCommitment], receipt_job_id: str
) -> None:
    if not captures or any(
        c.role is not None
        or c.source_context.capture_origin != "INGRESS_JSON"
        or c.source_context.receipt_job_id != receipt_job_id
        for c in captures
    ):
        raise ValueError("COMPOSITE_NATIVE_REGISTRY_CAPTURE_MISMATCH")


def _require_role_captures(
    selection: NativeProductSelection, captures: Sequence[NativeCaptureCommitment]
) -> None:
    pages = [c for c in captures if c.role == selection.role]
    if not pages or [c.source_page_index for c in pages] != list(range(len(pages))):
        raise ValueError("COMPOSITE_NATIVE_ROLE_CAPTURE_INCOMPLETE")
    for capture in pages:
        _require_selection_capture(selection, capture)
    _require_role_pagination([p.source_context for p in pages])


def _require_selection_capture(
    selection: NativeProductSelection, capture: NativeCaptureCommitment
) -> None:
    context = capture.source_context
    if (
        capture.source_product,
        capture.product_version,
        capture.selector_hash,
        capture.typed_content_hash,
        context.receipt_job_id,
        context.source_revision,
        context.capture_origin,
    ) != (
        selection.product_name,
        selection.product_version,
        selection.selector_hash,
        selection.content_hash,
        selection.receipt_job_id,
        selection.source_revision,
        "ACQUIRED_NATIVE_DTO",
    ):
        raise ValueError("COMPOSITE_NATIVE_SELECTION_CAPTURE_MISMATCH")


def _require_role_pagination(contexts: Sequence[NativeCaptureContext]) -> None:
    total = contexts[0].total_count
    if (
        any(c.total_count != total for c in contexts)
        or sum(c.returned_count or 0 for c in contexts) != total
    ):
        raise ValueError("COMPOSITE_NATIVE_ROLE_PAGINATION_INCOMPLETE")
    if contexts[-1].next_page_token is not None or any(
        c.next_page_token is None or not c.returned_count for c in contexts[:-1]
    ):
        raise ValueError("COMPOSITE_NATIVE_ROLE_PAGINATION_INCOMPLETE")


class NativePortfolioCustody(NativeModel):
    portfolio_id: Identity
    locator: NativeCutLocator
    manifest: NativeFinancialManifest
    receipt: NativeCutReceipt
    view_roots: Annotated[tuple[NativeViewRoot, ...], BeforeValidator(_immutable_array)] = Field(
        min_length=3, max_length=3
    )
    input_content_hash: BareDigest
    graph: NativeFinancialGraph
    graph_content_hash: BareDigest
    captures: Annotated[tuple[NativeCaptureCommitment, ...], BeforeValidator(_immutable_array)]

    @model_validator(mode="after")
    def require_portfolio_custody(self) -> NativePortfolioCustody:
        digest = native_domain_hash(
            "PortfolioFinancialSourceCutManifest:v1", "manifest", self.manifest
        )
        _require_header(
            self.locator,
            self.receipt,
            self.manifest.identity,
            "PortfolioFinancialSourceCut",
            digest,
        )
        if (
            self.graph.identity != self.manifest.identity
            or self.graph.portfolio_id != self.portfolio_id
        ):
            raise ValueError("COMPOSITE_NATIVE_GRAPH_IDENTITY_MISMATCH")
        if self.graph_content_hash != native_domain_hash(
            "PortfolioFinancialSourceCut:v1", "cut", self.graph
        ):
            raise ValueError("COMPOSITE_NATIVE_GRAPH_ROOT_MISMATCH")
        _require_view(
            self.view_roots[0],
            "CUT",
            "CUT_HEADERS",
            "single_cut",
            1,
            1,
            native_ordered_root("NeutralSourceCutHeaders:v1", [digest]),
        )
        _require_view(
            self.view_roots[1],
            "INPUTS",
            "SELECTED_FINANCIAL_INPUTS",
            "selected_portfolio",
            1,
            1,
            native_ordered_root("PortfolioFinancialSourceCutInputs:v1", [self.input_content_hash]),
        )
        _require_capture_view(self.view_roots[2], self.captures)
        if any(c.role is None for c in self.captures) or not self.manifest.selection_count:
            raise ValueError("COMPOSITE_NATIVE_FINANCIAL_CAPTURE_MISMATCH")
        for selection in self.graph.selections:
            _require_role_captures(selection, self.captures)
        return self


def _require_financial_membership(portfolios: Sequence[NativePortfolioCustody]) -> None:
    """Prove each exact manifest from its complete, canonically ordered consumed group."""
    groups: dict[tuple[str, NativeCutLocator], tuple[NativeFinancialManifest, list[str]]] = {}
    for portfolio in portfolios:
        manifest = portfolio.manifest
        key = (manifest.identity.tenant_id, portfolio.locator)
        if key not in groups:
            groups[key] = (manifest, [])
        retained_manifest, hashes = groups[key]
        if manifest != retained_manifest:
            raise ValueError("COMPOSITE_NATIVE_FINANCIAL_MEMBERSHIP_MANIFEST_MISMATCH")
        hashes.append(portfolio.input_content_hash)
    for manifest, hashes in groups.values():
        if (len(hashes), native_ordered_root("PortfolioFinancialSourceCutInputs:v1", hashes)) != (
            manifest.selection_count,
            manifest.selections_root,
        ):
            raise ValueError("COMPOSITE_NATIVE_FINANCIAL_MEMBERSHIP_INCOMPLETE_OR_MISMATCH")


class MonthlyNativeCustody(NativeModel):
    product_name: Literal["CompositeMonthlyNativeCustody"] = "CompositeMonthlyNativeCustody"
    product_version: Literal["v1"] = "v1"
    registry: NativeRegistryCustody
    portfolios: Annotated[tuple[NativePortfolioCustody, ...], BeforeValidator(_immutable_array)] = (
        Field(min_length=1, max_length=1000)
    )
    content_hash: str = ""

    @model_validator(mode="after")
    def require_complete_custody(self) -> MonthlyNativeCustody:
        ids = [p.portfolio_id for p in self.portfolios]
        members = {m.portfolio_id: m for m in self.registry.member_bindings}
        if ids != sorted(set(ids)) or set(ids) != set(members):
            raise ValueError("COMPOSITE_NATIVE_PORTFOLIO_SET_MISMATCH")
        registry_identity = self.registry.manifest.identity
        for portfolio in self.portfolios:
            graph = portfolio.graph
            identity = graph.identity
            if (
                graph.registry_root,
                graph.member_revision,
                identity.tenant_id,
                identity.definition_version,
                identity.coverage_from,
                identity.coverage_to,
                identity.calendar,
            ) != (
                self.registry.locator.batch_manifest_hash,
                members[portfolio.portfolio_id].member_revision,
                registry_identity.tenant_id,
                registry_identity.definition_version,
                registry_identity.coverage_from,
                registry_identity.coverage_to,
                registry_identity.calendar,
            ):
                raise ValueError("COMPOSITE_NATIVE_REGISTRY_GRAPH_BINDING_MISMATCH")
        _require_financial_membership(self.portfolios)
        digest = hash_canonical_payload(self.model_dump(mode="json", exclude={"content_hash"}))
        if self.content_hash and self.content_hash != digest:
            raise ValueError("COMPOSITE_NATIVE_CUSTODY_CONTENT_MISMATCH")
        object.__setattr__(self, "content_hash", digest)
        return self


def require_native_observation_scope(
    custody: MonthlyNativeCustody, observations: MonthlyEligibilityObservations
) -> None:
    """Validate scope and declared cash meaning, without re-decoding source products."""
    ids = [p.portfolio_id for p in custody.portfolios]
    first, last = month_window(observations.month)
    prior = date.fromordinal(date.fromisoformat(first).toordinal() - 1).isoformat()
    registry = custody.registry.manifest
    identity_adapter = TypeAdapter(Identity)
    for member in custody.registry.member_bindings:
        # The downstream candidate contract uses global Identity; never sanitize opaque pins.
        identity_adapter.validate_python(member.provider_namespace)
        identity_adapter.validate_python(member.source_member_id)
    if ids != observations.expected_portfolio_ids or (
        registry.identity.tenant_id,
        registry.identity.definition_version,
        registry.declared_coverage,
        registry.expected_population.count,
    ) != (observations.tenant_id, observations.definition_version, "COMPLETE", len(ids)):
        raise ValueError("COMPOSITE_NATIVE_OBSERVATION_SCOPE_MISMATCH")
    for portfolio in custody.portfolios:
        _require_observation_window(
            portfolio.graph, first, last, prior, observations.reporting_currency
        )
    normalized = {p.portfolio_id: p for p in observations.portfolios}
    if len(normalized) != len(observations.portfolios) or set(normalized) != set(ids):
        raise ValueError("COMPOSITE_NATIVE_NORMALIZED_PORTFOLIOS_MISMATCH")
    for portfolio in custody.portfolios:
        _require_normalized_cash(portfolio.graph, normalized[portfolio.portfolio_id])


def _require_observation_window(
    graph: NativeFinancialGraph, first: str, last: str, prior: str, currency: str
) -> None:
    if (graph.prior_date, graph.month_end_date, graph.currency) != (
        prior,
        last,
        currency,
    ) or not (graph.identity.coverage_from <= first <= last <= graph.identity.coverage_to):
        raise ValueError("COMPOSITE_NATIVE_OBSERVATION_WINDOW_MISMATCH")


def _require_normalized_cash(
    graph: NativeFinancialGraph, observed: MonthlyPortfolioObservations
) -> None:
    cash = graph.settled_unencumbered
    if (
        observed.currency != graph.currency
        or (cash is None and observed.settled_unencumbered_cash is not None)
        or (cash is not None and cash.amount != observed.settled_unencumbered_cash)
    ):
        raise ValueError("COMPOSITE_NATIVE_NORMALIZED_CASH_MISMATCH")


def native_role_set_digest(custody: MonthlyNativeCustody, kind: NativeRole) -> str:
    """Manage all-member commitment; none of the nested Core roots substitutes for it."""
    if kind not in NATIVE_ROLES:
        raise ValueError("COMPOSITE_NATIVE_ROLE_INVALID")
    members = {m.portfolio_id: m for m in custody.registry.member_bindings}
    roles = [
        {
            "portfolio_id": p.portfolio_id,
            "financial_locator": p.locator.model_dump(mode="json"),
            "receipt": p.receipt.model_dump(mode="json"),
            "input_content_hash": p.input_content_hash,
            "graph_content_hash": p.graph_content_hash,
            "member_content_hash": members[p.portfolio_id].member_content_hash,
            "selection": next(
                s.model_dump(mode="json") for s in p.graph.selections if s.role == kind
            ),
            "captures": [c.model_dump(mode="json") for c in p.captures if c.role == kind],
        }
        for p in custody.portfolios
    ]
    return hash_canonical_payload(
        {
            "contract": "CompositeMonthlyRoleSet:v1",
            "kind": kind,
            "registry_content_hash": hash_canonical_payload(
                custody.registry.model_dump(mode="json")
            ),
            "portfolio_roles": roles,
        }
    )
