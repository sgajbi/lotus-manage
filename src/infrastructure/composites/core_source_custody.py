"""Internal retained-reader boundary; no HTTP DTO, decoder, signer or storage."""

import hashlib
from collections.abc import Sequence
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, StrictBool, StrictInt, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import BusinessDate, Digest, Identity
from src.core.composite_eligibility.observations import (
    Currency,
    MonthlyFlowObservation,
    MonthlyPortfolioObservations,
    UtcInstant,
)
from src.core.composite_eligibility.source_assembly import InputKind
from src.infrastructure.composites.core_financial_configuration import (
    ClosedSourceModel,
    CoreCutAddress,
    OpaqueIdentity,
)
from src.core.composite_eligibility.native_source_custody import (
    BareDigest,
    NativeDate,
    NativeInstant,
    NativeModel,
    NativeText,
    Positive,
    NativeRegistryCustody,
    NativePortfolioCustody,
)

Count = Annotated[StrictInt, Field(ge=0)]
CORE_ROLE_ORDER = ("PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS")


def core_digest(value: str) -> str:
    """Represent a validated producer digest; never hash its hexadecimal text."""
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("CORE_CUSTODY_DIGEST_INVALID")
    return "sha256:" + value


class CaptureSegment(ClosedSourceModel):
    capture_id: OpaqueIdentity
    scope_digest: Digest
    raw_digest: Digest
    segment_index: Count
    segment_count: Annotated[StrictInt, Field(ge=1)]
    data: bytes = Field(min_length=1)


def reconstruct_capture(segments: Sequence[CaptureSegment], *, scope_digest: str) -> bytes:
    """Preserve exact ordered bytes and reject missing, mixed or reordered segments."""
    if not segments:
        raise ValueError("CORE_CUSTODY_CAPTURE_MISSING")
    first = segments[0]
    identity = (first.capture_id, first.scope_digest, first.raw_digest, first.segment_count)
    if first.scope_digest != scope_digest or len(segments) != first.segment_count:
        raise ValueError("CORE_CUSTODY_CAPTURE_SCOPE_OR_COUNT")
    for index, segment in enumerate(segments):
        if (
            segment.capture_id,
            segment.scope_digest,
            segment.raw_digest,
            segment.segment_count,
        ) != (identity) or segment.segment_index != index:
            raise ValueError("CORE_CUSTODY_CAPTURE_SEQUENCE")
    raw = b"".join(segment.data for segment in segments)
    if not raw or "sha256:" + hashlib.sha256(raw).hexdigest() != first.raw_digest:
        raise ValueError("CORE_CUSTODY_CAPTURE_RAW_MISMATCH")
    return raw


class TraversalPage(ClosedSourceModel):
    """Reader-observed traversal metadata, independent of unfinished Core wire names."""

    scope_digest: Digest
    source_root: Digest
    total_count: Count
    row_keys: tuple[OpaqueIdentity, ...]
    request_token: str | None
    next_token: str | None


def _require_page_progress(page: TraversalPage, seen: set[str]) -> None:
    if page.next_token is not None and (
        not page.next_token or not page.row_keys or page.next_token in seen
    ):
        raise ValueError("CORE_CUSTODY_TRAVERSAL_NO_PROGRESS")


def validate_traversal(
    pages: Sequence[TraversalPage], *, scope_digest: str, source_root: str
) -> tuple[str, ...]:
    """Validate complete immutable traversal; the wire decoder owns native root recomputation."""
    if not pages:
        raise ValueError("CORE_CUSTODY_TRAVERSAL_MISSING")
    count = pages[0].total_count
    token: str | None = None
    keys: list[str] = []
    seen: set[str] = set()
    for index, page in enumerate(pages):
        if index and token is None:
            raise ValueError("CORE_CUSTODY_TRAVERSAL_AFTER_TERMINAL")
        if (page.scope_digest, page.source_root, page.total_count, page.request_token) != (
            scope_digest,
            source_root,
            count,
            token,
        ):
            raise ValueError("CORE_CUSTODY_TRAVERSAL_BINDING")
        _require_page_progress(page, seen)
        keys.extend(page.row_keys)
        token = page.next_token
        if token is not None:
            seen.add(token)
    if token is not None or len(keys) != count or keys != sorted(set(keys)):
        raise ValueError("CORE_CUSTODY_TRAVERSAL_INCOMPLETE")
    return tuple(keys)


class RegistryDeclaration(ClosedSourceModel):
    effective_from: BusinessDate
    effective_to: BusinessDate | None
    definition_version: Identity
    currency: Currency
    included: StrictBool
    discretionary: StrictBool | None


class RegistryMember(ClosedSourceModel):
    provider_namespace: OpaqueIdentity
    source_member_id: OpaqueIdentity
    portfolio_id: Identity | None
    declarations: tuple[RegistryDeclaration, ...] = Field(min_length=1)


class RetainedRegistry(ClosedSourceModel):
    address: CoreCutAddress
    tenant_id: Identity
    definition_version: Identity
    coverage_from: BusinessDate
    coverage_to: BusinessDate
    generated_at: UtcInstant
    declared_coverage: Literal["COMPLETE", "PARTIAL", "MISSING"]
    population_verification: Literal["UNVERIFIED"] = "UNVERIFIED"
    expected_population_count: Count
    members: tuple[RegistryMember, ...]
    native_custody: NativeRegistryCustody | None = None


class RoleCapture(ClosedSourceModel):
    """Native producer pins remain distinct from locally decoded descriptor commitments."""

    role: InputKind
    product_name: Identity
    product_version: Literal["v1"]
    source_content_hash: Digest
    receipt_job_id: OpaqueIdentity
    descriptor_content_hash: Digest


class RetainedPortfolio(ClosedSourceModel):
    address: CoreCutAddress
    tenant_id: Identity
    registry_root: Digest
    generated_at: UtcInstant
    roles: tuple[RoleCapture, ...] = Field(min_length=5, max_length=5)
    observations: MonthlyPortfolioObservations
    cash_semantic_definition: Identity | None
    cash_semantic_revision: Identity | None
    reversal_dependencies: tuple[MonthlyFlowObservation, ...] = ()
    native_custody: NativePortfolioCustody | None = None

    @model_validator(mode="after")
    def require_role_descriptors(self) -> Self:
        if tuple(role.role for role in self.roles) != CORE_ROLE_ORDER:
            raise ValueError("CORE_CUSTODY_ROLE_ORDER")
        expected_products = (
            "PortfolioTimeseriesInput",
            "PortfolioTimeseriesInput",
            "PortfolioFinancialSourceObservations",
            "PortfolioFinancialSourceObservations",
            "PortfolioFinancialFlowObservations",
        )
        if tuple(role.product_name for role in self.roles) != expected_products:
            raise ValueError("CORE_CUSTODY_ROLE_FAMILY")
        # This is an internal normalized descriptor hash, not a native producer typed root.
        digest = hash_canonical_payload(self.observations.model_dump(mode="json"))
        if any(role.descriptor_content_hash != digest for role in self.roles):
            raise ValueError("CORE_CUSTODY_DESCRIPTOR_MISMATCH")
        return self


class CoreRetainedReader(Protocol):
    """A future admitted decoder must verify native typed roots before returning these records."""

    def registry(self, *, tenant_id: str, address: CoreCutAddress) -> RetainedRegistry | None: ...

    def portfolio(
        self, *, tenant_id: str, portfolio_id: str, address: CoreCutAddress
    ) -> RetainedPortfolio | None: ...


class ObservationEnvelope(NativeModel):
    tenant_id: NativeText
    portfolio_id: NativeText
    producer_id: NativeText
    source_record_id: NativeText
    source_revision: Positive
    source_cut_id: NativeText
    definition_version: NativeText
    effective_from: NativeDate
    effective_to: NativeDate | None
    observed_at: NativeInstant
    generated_at: NativeInstant
    coverage: Literal["complete", "partial", "missing"]
    coverage_scope: NativeText
    predecessor_id: NativeText | None
    expected_head_hash: BareDigest | None

    @model_validator(mode="after")
    def chronology_and_correction(self) -> Self:
        from datetime import datetime

        if self.effective_to is not None and self.effective_from >= self.effective_to:
            raise ValueError("CORE_READER_OBSERVATION_INTERVAL")
        if datetime.fromisoformat(self.generated_at) < datetime.fromisoformat(self.observed_at):
            raise ValueError("CORE_READER_OBSERVATION_CHRONOLOGY")
        if (self.predecessor_id is None) != (self.expected_head_hash is None) or (
            (self.source_revision == 1) != (self.predecessor_id is None)
        ):
            raise ValueError("CORE_READER_OBSERVATION_CORRECTION")
        return self


class CashFact(NativeModel):
    envelope: ObservationEnvelope
    currency: Currency
    settled: str | None
    encumbered: str | None
    available: str | None


class ReadinessFact(NativeModel):
    envelope: ObservationEnvelope
    funded: bool | None
    invested: bool | None


class FlowPin(NativeModel):
    source_record_id: NativeText
    observation_id: BareDigest
    content_hash: BareDigest
    flow_source_record_revision: Positive

    @model_validator(mode="after")
    def identical_pins(self) -> Self:
        if self.observation_id != self.content_hash:
            raise ValueError("CORE_READER_FLOW_PIN")
        return self


class FlowFact(NativeModel):
    envelope: ObservationEnvelope
    business_date: NativeDate
    currency: Currency
    amount: str
    classification: Literal["EXTERNAL_CASH", "INTERNAL_TRANSFER", "REVERSAL", "IN_KIND"]
    posting_state: Literal["POSTED", "CANCELLED", "UNKNOWN"]
    reversal_state: Literal["NONE", "REVERSES", "UNKNOWN"]
    reverses_source_record_id: NativeText | None
    reversal_target: FlowPin | None
    economic_event_id: NativeText | None
    transaction_id: NativeText | None

    @model_validator(mode="after")
    def effective_reversal(self) -> Self:
        env = self.envelope
        if not env.effective_from <= self.business_date or (
            env.effective_to is not None and self.business_date >= env.effective_to
        ):
            raise ValueError("CORE_READER_FLOW_EFFECTIVE_DATE")
        reverses = self.reversal_state == "REVERSES"
        if (
            any(
                reverses != value
                for value in (
                    self.reverses_source_record_id is not None,
                    self.reversal_target is not None,
                    self.classification == "REVERSAL",
                )
            )
            or self.reverses_source_record_id == env.source_record_id
        ):
            raise ValueError("CORE_READER_FLOW_REVERSAL")
        if (
            self.reversal_target is not None
            and self.reversal_target.source_record_id != self.reverses_source_record_id
        ):
            raise ValueError("CORE_READER_FLOW_TARGET")
        return self


class FlowCut(NativeModel):
    tenant_id: NativeText
    portfolio_id: NativeText
    source_system: NativeText
    source_cut_id: NativeText
    cut_revision: Positive
    definition_version: NativeText
    currency: Currency
    coverage_from: NativeDate
    coverage_to: NativeDate
    coverage: Literal["complete", "partial", "missing"]
    event_pins: tuple[FlowPin, ...] = Field(max_length=1000)
    dependency_pins: tuple[FlowPin, ...] = Field(max_length=1000)
    predecessor_cut_hash: BareDigest | None
    expected_head_hash: BareDigest | None

    @model_validator(mode="after")
    def membership(self) -> Self:
        self._require_pin_membership()
        self._require_cut_revision()
        return self

    def _require_pin_membership(self) -> None:
        ids = [p.source_record_id for p in self.event_pins]
        deps = [
            (p.source_record_id, p.flow_source_record_revision, p.observation_id)
            for p in self.dependency_pins
        ]
        pins = self.event_pins + self.dependency_pins
        if (
            ids != sorted(set(ids))
            or deps != sorted(set(deps))
            or len(pins) > 1000
            or len({p.observation_id for p in pins}) != len(pins)
            or len({(p.source_record_id, p.flow_source_record_revision) for p in pins}) != len(pins)
        ):
            raise ValueError("CORE_READER_FLOW_MEMBERSHIP")

    def _require_cut_revision(self) -> None:
        if (
            self.coverage_from > self.coverage_to
            or (
                self.cut_revision == 1
                and (self.predecessor_cut_hash is not None or self.expected_head_hash is not None)
            )
            or (
                self.cut_revision > 1
                and (
                    self.predecessor_cut_hash is None
                    or self.predecessor_cut_hash != self.expected_head_hash
                )
            )
        ):
            raise ValueError("CORE_READER_FLOW_CUT")
