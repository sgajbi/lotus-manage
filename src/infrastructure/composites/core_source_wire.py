"""Closed Core v3 retained-read wire, with distinct domain and JSON commitments."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from src.core.composite_eligibility.native_source_custody import (
    BareDigest,
    NativeCaptureCommitment,
    NativeCashDeclaration,
    NativeCompatibilityDeclaration,
    NativeDate,
    NativeFinancialGraph,
    NativeFinancialManifest,
    NativeInstant,
    NativeModel,
    NativeProductSelection,
    NativeRegistryManifest,
    NativeSourceAddress,
    NativeText,
    NATIVE_ROLES,
    Nonnegative,
    Positive,
    native_domain_hash,
)
from src.core.composite_eligibility.observations import Currency


def json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def closed_json(raw: bytes | str) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("CORE_READER_DUPLICATE_JSON_MEMBER")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ValueError("CORE_READER_NONFINITE_JSON")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
    except RecursionError as exc:
        raise ValueError("CORE_READER_JSON_DEPTH") from exc


def utc_text(value: str) -> str:
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError("CORE_READER_AWARE_TIME_REQUIRED")
    return stamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class WireDeclaration(NativeModel):
    effective_from: NativeDate
    effective_to: NativeDate | None
    definition_version: NativeText
    provenance_reference: NativeText
    currency: Currency
    discretionary: bool | None
    included: bool


class WireMember(NativeModel):
    source_member_id: NativeText
    provider_namespace: NativeText
    core_portfolio_id: NativeText | None
    member_revision: Positive
    declarations: tuple[WireDeclaration, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def intervals(self) -> Self:
        previous = None
        for item in self.declarations:
            if item.effective_to is not None and item.effective_from >= item.effective_to:
                raise ValueError("CORE_READER_MEMBER_INTERVAL")
            if previous is not None and (
                previous.effective_to is None or item.effective_from < previous.effective_to
            ):
                raise ValueError("CORE_READER_MEMBER_INTERVAL")
            previous = item
        return self


def member_hash(member: WireMember) -> str:
    material = member.model_dump(mode="json")
    for item in material["declarations"]:
        for field in ("effective_from", "effective_to"):
            if item[field] is not None:
                item[field] = {"date": item[field]}
    return json_hash({"contract": "PortfolioHistoricalRegistryMember:v1", "member": material})


class ValuationSelector(NativeModel):
    kind: Literal["VALUATION"]
    as_of_date: NativeDate
    from_date: NativeDate
    to_date: NativeDate
    reporting_currency: Currency
    consumer_system: NativeText
    export_job_id: NativeText | None
    export_content_hash: BareDigest | None
    refresh_of_job_id: NativeText | None

    @model_validator(mode="after")
    def exact_window(self) -> Self:
        if (
            not self.from_date <= self.to_date <= self.as_of_date
            or ((self.export_job_id is None) != (self.export_content_hash is None))
            or (self.refresh_of_job_id is not None and self.export_job_id is None)
        ):
            raise ValueError("CORE_READER_VALUATION_SELECTOR")
        return self


class ObservationSelector(NativeModel):
    kind: Literal["CASH", "READINESS"]
    as_of_date: NativeDate
    producer_id: NativeText
    source_record_id: NativeText
    observation_id: BareDigest
    content_hash: BareDigest
    source_cut_id: NativeText
    source_version: Positive


class FlowSelector(NativeModel):
    kind: Literal["FLOWS"]
    source_system: NativeText
    source_cut_id: NativeText
    cut_revision: Positive
    manifest_hash: BareDigest
    from_date: NativeDate
    to_date: NativeDate
    currency: Currency


class WireSelection(NativeProductSelection):
    selector: Annotated[
        ValuationSelector | ObservationSelector | FlowSelector, Field(discriminator="kind")
    ]

    @model_validator(mode="after")
    def selector_binding(self) -> Self:
        expected = "VALUATION" if self.role in ("PRIOR_ASSETS", "MONTH_END_ASSETS") else self.role
        if (
            self.selector.kind != expected
            or json_hash(self.selector.model_dump(mode="json")) != self.selector_hash
        ):
            raise ValueError("CORE_READER_SELECTOR_HASH")
        return self


class WireInput(NativeModel):
    portfolio_id: NativeText
    currency: Currency
    prior_date: NativeDate
    month_end_date: NativeDate
    registry_root: BareDigest
    member_revision: Positive
    selections: tuple[WireSelection, ...] = Field(min_length=5, max_length=5)
    settled_unencumbered: NativeCashDeclaration | None
    compatibility: NativeCompatibilityDeclaration | None

    def graph(self, identity: Any) -> NativeFinancialGraph:
        value = self.model_dump(mode="json")
        for selection in value["selections"]:
            selection.pop("selector")
        return NativeFinancialGraph.model_validate({"identity": identity, **value})

    @model_validator(mode="after")
    def role_scope(self) -> Self:
        if (
            self.prior_date >= self.month_end_date
            or tuple(s.role for s in self.selections) != NATIVE_ROLES
        ):
            raise ValueError("CORE_READER_ROLE_ORDER")
        for selection in self.selections:
            self._require_selection_scope(selection)
        return self

    def _require_selection_scope(self, selection: WireSelection) -> None:
        selector = selection.selector
        if isinstance(selector, ValuationSelector):
            day = self.prior_date if selection.role == "PRIOR_ASSETS" else self.month_end_date
            if (
                not selector.from_date <= day <= selector.to_date
                or selector.reporting_currency != self.currency
            ):
                raise ValueError("CORE_READER_ROLE_SCOPE")
        elif isinstance(selector, ObservationSelector):
            if selector.as_of_date != self.month_end_date:
                raise ValueError("CORE_READER_ROLE_SCOPE")
        elif (
            selector.currency != self.currency
            or selector.to_date != self.month_end_date
            or selector.from_date > selector.to_date
        ):
            raise ValueError("CORE_READER_ROLE_SCOPE")


class RegistryHeader(NativeModel):
    row_kind: Literal["REGISTRY_CUT"]
    manifest: NativeRegistryManifest
    receipt_job_id: NativeText
    received_at: NativeInstant
    completed_at: NativeInstant


class FinancialHeader(NativeModel):
    row_kind: Literal["FINANCIAL_CUT"]
    manifest: NativeFinancialManifest
    receipt_job_id: NativeText
    received_at: NativeInstant
    completed_at: NativeInstant


class MemberRow(NativeModel):
    row_kind: Literal["REGISTRY_MEMBER"]
    member: WireMember
    member_content_hash: BareDigest

    @model_validator(mode="after")
    def typed_hash(self) -> Self:
        if self.member_content_hash != member_hash(self.member):
            raise ValueError("CORE_READER_MEMBER_HASH")
        return self


class InputRow(NativeModel):
    row_kind: Literal["FINANCIAL_INPUT"]
    declaration: WireInput
    input_content_hash: BareDigest
    graph: NativeFinancialGraph
    graph_content_hash: BareDigest

    @model_validator(mode="after")
    def typed_hashes(self) -> Self:
        expected = json_hash(
            {
                "contract": "PortfolioFinancialSourceCutInput:v1",
                "selection": self.declaration.model_dump(mode="json"),
            }
        )
        reconstructed = self.declaration.graph(self.graph.identity.model_dump(mode="json"))
        if (
            expected != self.input_content_hash
            or reconstructed != self.graph
            or self.graph_content_hash
            != native_domain_hash("PortfolioFinancialSourceCut:v1", "cut", self.graph)
        ):
            raise ValueError("CORE_READER_INPUT_GRAPH_HASH")
        return self


class SegmentRow(NativeCaptureCommitment):
    row_kind: Literal["CAPTURE_SEGMENT"]
    segment_index: Nonnegative
    segment_hash: BareDigest
    bytes_base64: str = Field(max_length=699052)

    def raw(self) -> bytes:
        raw = base64.b64decode(self.bytes_base64, validate=True)
        if (
            base64.b64encode(raw).decode("ascii") != self.bytes_base64
            or hashlib.sha256(raw).hexdigest() != self.segment_hash
        ):
            raise ValueError("CORE_READER_SEGMENT_HASH_OR_BASE64")
        if self.segment_index >= self.segment_count or len(raw) != min(
            524288, self.byte_count - self.segment_index * 524288
        ):
            raise ValueError("CORE_READER_SEGMENT_STRIDE")
        return raw

    def commitment(self) -> NativeCaptureCommitment:
        return NativeCaptureCommitment.model_validate(
            self.model_dump(
                mode="json", exclude={"row_kind", "segment_index", "segment_hash", "bytes_base64"}
            )
        )

    @model_validator(mode="after")
    def segment_bytes(self) -> Self:
        self.raw()
        return self


class Pagination(NativeModel):
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
    returned_count: Nonnegative
    next_page_token: str | None = Field(min_length=1, max_length=8192)


class DegradationDetail(NativeModel):
    section: str
    record_key: str | None = None
    affected_fields: tuple[str, ...] = ()
    source_kind: Literal["AUTHORITATIVE", "FALLBACK", "DERIVED_DEFAULT", "UNAVAILABLE"]
    source_product_name: str
    source_product_version: str = "v1"
    source_as_of_date: NativeDate | None = None
    latest_evidence_timestamp: NativeInstant | None = None
    freshness_status: Literal["CURRENT", "STALE", "PARTIAL", "UNAVAILABLE", "UNKNOWN"]
    reason_code: str


class Degradation(NativeModel):
    status: Literal["NONE", "PARTIAL", "STALE", "UNAVAILABLE", "UNKNOWN"] = "NONE"
    reason_codes: tuple[str, ...] = ()
    details: tuple[DegradationDetail, ...] = ()


class ReadResponse(NativeModel):
    product_name: Literal["PortfolioHistoricalRegistry", "PortfolioFinancialSourceCut"]
    product_version: Literal["v1"]
    tenant_id: NativeText
    generated_at: NativeInstant
    as_of_date: NativeDate
    restatement_version: str
    reconciliation_status: str
    data_quality_status: str
    latest_evidence_timestamp: NativeInstant | None
    source_cut_id: str | None
    source_batch_fingerprint: str | None
    snapshot_id: str | None
    content_hash: str
    source_digest: str
    source_refs: tuple[str, ...]
    source_lineage: dict[str, str]
    degradation: Degradation
    source_evidence_current: bool
    freshness_status: str
    policy_version: str | None
    correlation_id: str | None
    source_address: NativeSourceAddress
    batch_manifest_hash: BareDigest
    portfolio_id: NativeText | None
    view: Literal["CUT", "MEMBERS", "INPUTS", "CAPTURES"]
    receipt_job_id: NativeText
    received_at: NativeInstant
    completed_at: NativeInstant
    qualification: Literal["UNQUALIFIED"]
    population_verification: Literal["UNVERIFIED"]
    compatibility_posture: Literal["DECLARED_UNVERIFIED", "UNAVAILABLE"]
    authoritative_use_available: Literal[False]
    pagination: Pagination
    rows: tuple[
        Annotated[
            RegistryHeader | FinancialHeader | MemberRow | InputRow | SegmentRow,
            Field(discriminator="row_kind"),
        ],
        ...,
    ] = Field(max_length=500)

    @model_validator(mode="after")
    def envelope(self) -> Self:
        self._require_product_view()
        self._require_page_binding()
        for row in self.rows:
            self._require_row_binding(row)
        return self

    def _require_product_view(self) -> None:
        expected = {
            ("PortfolioHistoricalRegistry", "CUT"): "REGISTRY_CUT",
            ("PortfolioFinancialSourceCut", "CUT"): "FINANCIAL_CUT",
            ("PortfolioHistoricalRegistry", "MEMBERS"): "REGISTRY_MEMBER",
            ("PortfolioFinancialSourceCut", "INPUTS"): "FINANCIAL_INPUT",
        }.get(
            (self.product_name, self.view), "CAPTURE_SEGMENT" if self.view == "CAPTURES" else None
        )
        if (
            expected is None
            or any(row.row_kind != expected for row in self.rows)
            or (self.product_name == "PortfolioHistoricalRegistry") != (self.portfolio_id is None)
        ):
            raise ValueError("CORE_READER_PRODUCT_VIEW")

    def _require_page_binding(self) -> None:
        paging = self.pagination
        if (
            self.content_hash != "sha256:" + self.batch_manifest_hash
            or self.source_digest != self.content_hash
            or paging.returned_count != len(self.rows)
            or paging.returned_count > paging.total_count
        ):
            raise ValueError("CORE_READER_ENVELOPE_BINDING")
        if self.view == "CUT" and (len(self.rows), paging.total_count, paging.next_page_token) != (
            1,
            1,
            None,
        ):
            raise ValueError("CORE_READER_HEADER_REQUIRED")
        if datetime.fromisoformat(self.received_at) > datetime.fromisoformat(self.completed_at):
            raise ValueError("CORE_READER_RECEIPT_CHRONOLOGY")

    def _require_header_binding(self, row: RegistryHeader | FinancialHeader) -> None:
        contract, field = (
            ("PortfolioHistoricalRegistry:v1", "cut")
            if isinstance(row, RegistryHeader)
            else ("PortfolioFinancialSourceCutManifest:v1", "manifest")
        )
        if native_domain_hash(contract, field, row.manifest) != self.batch_manifest_hash or (
            row.receipt_job_id,
            row.received_at,
            row.completed_at,
        ) != (self.receipt_job_id, self.received_at, self.completed_at):
            raise ValueError("CORE_READER_HEADER_BINDING")

    def _require_row_binding(
        self, row: RegistryHeader | FinancialHeader | MemberRow | InputRow | SegmentRow
    ) -> None:
        if isinstance(row, (RegistryHeader, FinancialHeader)):
            self._require_header_binding(row)
            identity = row.manifest.identity
        elif isinstance(row, InputRow):
            if row.graph.portfolio_id != self.portfolio_id:
                raise ValueError("CORE_READER_GRAPH_PORTFOLIO")
            identity = row.graph.identity
        else:
            return
        address = self.source_address
        if (
            identity.tenant_id,
            identity.source_system,
            identity.scope_id,
            identity.source_cut_id,
            identity.revision,
        ) != (
            self.tenant_id,
            address.source_system,
            address.registry_scope_id,
            address.source_cut_id,
            address.revision,
        ):
            raise ValueError("CORE_READER_ROW_ADDRESS")
