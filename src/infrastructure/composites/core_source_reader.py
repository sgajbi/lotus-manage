"""Bounded retained Core HTTP traversal and exact artifact reconstruction."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from tempfile import TemporaryFile
from typing import Any, BinaryIO, Callable, cast

import httpx

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.native_source_custody import (
    NATIVE_ROLES,
    NativeCaptureCommitment,
    NativeCutLocator,
    NativeCutReceipt,
    NativePortfolioCustody,
    NativeRegistryCustody,
    NativeRegistryMemberBinding,
    NativeViewRoot,
    native_domain_hash,
    native_ordered_root,
)
from src.core.composite_eligibility.observations import (
    MonthlyFlowObservation,
    MonthlyPortfolioObservations,
)
from src.infrastructure.authority_http import AuthorityHttpError, post_json_with_retries
from src.infrastructure.composites.core_financial_configuration import (
    CoreCutAddress,
    CoreMemberBinding,
    CoreReaderConfiguration,
)
from src.infrastructure.composites.core_source_custody import (
    RegistryDeclaration,
    RegistryMember,
    RetainedPortfolio,
    RetainedRegistry,
    RoleCapture,
)
from src.infrastructure.composites.core_source_decoder import DecodedProduct, decode_native
from src.infrastructure.composites.core_source_products import validate_registry_capture
from src.infrastructure.composites.core_source_wire import (
    FinancialHeader,
    InputRow,
    MemberRow,
    ReadResponse,
    RegistryHeader,
    SegmentRow,
    canonical_bytes,
    json_hash,
    utc_text,
)

ROOT_RECIPES = {
    "CUT": ("CUT_HEADERS", "single_cut", "NeutralSourceCutHeaders:v1"),
    "MEMBERS": (
        "REGISTRY_MEMBERS",
        "provider_namespace,source_member_id",
        "PortfolioHistoricalRegistryMembers:v1",
    ),
    "INPUTS": (
        "SELECTED_FINANCIAL_INPUTS",
        "selected_portfolio",
        "PortfolioFinancialSourceCutInputs:v1",
    ),
    "CAPTURES": (
        "CAPTURE_ARTIFACTS",
        "role,source_page_index,capture_id,segment_index",
        "PortfolioNeutralSourceCaptureArtifacts:v1",
    ),
}


@dataclass
class Artifact:
    commitment: NativeCaptureCommitment
    spool: BinaryIO
    segments: int = 0

    def append(self, row: SegmentRow) -> None:
        if row.commitment() != self.commitment or row.segment_index != self.segments:
            raise ValueError("CORE_READER_ARTIFACT_SEQUENCE")
        self.spool.write(row.raw())
        self.segments += 1

    def raw(self) -> bytes:
        if self.segments != self.commitment.segment_count:
            raise ValueError("CORE_READER_ARTIFACT_INCOMPLETE")
        self.spool.seek(0)
        raw = self.spool.read()
        if (
            len(raw) != self.commitment.byte_count
            or hashlib.sha256(raw).hexdigest() != self.commitment.raw_hash
        ):
            raise ValueError("CORE_READER_ARTIFACT_RAW")
        return raw


def _key(row: Any) -> tuple[Any, ...]:
    if isinstance(row, MemberRow):
        return (row.member.provider_namespace, row.member.source_member_id)
    if isinstance(row, SegmentRow):
        return (
            NATIVE_ROLES.index(row.role) if row.role is not None else -1,
            row.source_page_index,
            row.capture_id,
            row.segment_index,
        )
    if isinstance(row, InputRow):
        return (row.graph.portfolio_id,)
    return (0,)


def _row_hash(row: Any) -> str | None:
    if isinstance(row, MemberRow):
        return row.member_content_hash
    if isinstance(row, InputRow):
        return row.input_content_hash
    if isinstance(row, RegistryHeader):
        return native_domain_hash("PortfolioHistoricalRegistry:v1", "cut", row.manifest)
    if isinstance(row, FinancialHeader):
        return native_domain_hash(
            "PortfolioFinancialSourceCutManifest:v1", "manifest", row.manifest
        )
    if row.segment_index == 0:
        return json_hash(
            {
                "contract": "PortfolioNeutralSourceCaptureArtifact:v1",
                **row.commitment().model_dump(mode="json"),
            }
        )
    return None


def _reader_configuration(configuration: CoreReaderConfiguration) -> CoreReaderConfiguration:
    """Revalidate copied/constructed deployment models before selecting authentication."""
    try:
        return CoreReaderConfiguration.model_validate_json(
            configuration.model_dump_json(warnings="error")
        )
    except (TypeError, ValueError):
        raise ValueError("CORE_READER_CONFIGURATION_INVALID") from None


class CoreHttpRetainedReader:
    """An independent instance owns its client/configuration; no source/proof cache is shared."""

    def __init__(
        self,
        configuration: CoreReaderConfiguration | None,
        client: httpx.Client,
        *,
        members: tuple[CoreMemberBinding, ...] = (),
    ) -> None:
        self.configuration, self.client, self.members = configuration, client, members

    def _request_headers(self, configuration: CoreReaderConfiguration) -> dict[str, str] | None:
        """A client Auth is a transport prerequisite, not proof of enterprise admission."""
        credential = os.getenv(configuration.credential_env)
        if not credential or not credential.strip():
            return None
        headers = {"Accept-Encoding": "identity"}
        if configuration.authentication_mode == "bearer":
            headers["Authorization"] = f"Bearer {credential}"
        else:
            if "Authorization" in self.client.headers:
                raise ValueError("CORE_READER_AUTHORIZATION_HEADER_FORBIDDEN")
            if self.client.auth is None:
                return None
        return headers

    def _page(
        self,
        tenant: str,
        address: CoreCutAddress,
        portfolio: str | None,
        view: str,
        token: str | None,
    ) -> ReadResponse | None:
        config = self.configuration
        if config is None:
            return None
        config = _reader_configuration(config)
        if config.tenant_id != tenant:
            raise ValueError("CORE_READER_TENANT_CONFIG")
        headers = self._request_headers(config)
        if headers is None:
            return None
        payload = {
            **address.model_dump(mode="json", exclude={"content_hash"}),
            "content_hash": address.content_hash.removeprefix("sha256:"),
            "view": view,
            "page": {"page_size": config.page_size, "page_token": token},
        }
        route = "/integration/portfolio-historical-registries/query"
        if portfolio is not None:
            payload["portfolio_id"] = portfolio
            route = "/integration/financial-source-cuts/query"
        try:
            body = post_json_with_retries(
                client=self.client,
                url=config.endpoint.rstrip("/") + route,
                payload=payload,
                headers=headers,
                attempts=config.attempts,
                unavailable_error="CORE_READER_UNAVAILABLE",
                rejected_error="CORE_READER_REJECTED",
                invalid_response_error="CORE_READER_RESPONSE_INVALID",
                source_service="lotus-core",
                maximum_response_bytes=config.maximum_response_bytes,
                reject_duplicate_members=True,
            )
        except AuthorityHttpError as exc:
            if exc.code == "CORE_READER_UNAVAILABLE":
                return None
            raise ValueError(exc.code) from exc
        response = ReadResponse.model_validate_json(canonical_bytes(body))
        expected_product = (
            "PortfolioHistoricalRegistry" if portfolio is None else "PortfolioFinancialSourceCut"
        )
        if (
            response.product_name,
            response.tenant_id,
            response.source_address.model_dump(mode="json"),
            response.batch_manifest_hash,
            response.portfolio_id,
            response.view,
        ) != (
            expected_product,
            tenant,
            address.model_dump(mode="json", exclude={"content_hash"}),
            address.content_hash.removeprefix("sha256:"),
            portfolio,
            view,
        ):
            raise ValueError("CORE_READER_PAGE_ADDRESS")
        return response

    def _read(
        self,
        tenant: str,
        address: CoreCutAddress,
        portfolio: str | None,
        view: str,
        consume: Callable[[Any], None],
    ) -> tuple[ReadResponse, NativeViewRoot] | None:
        first = None
        token = None
        tokens: set[str] = set()
        previous = None
        count = 0
        hashes: list[str] = []
        while True:
            page = self._page(tenant, address, portfolio, view, token)
            if page is None:
                return None
            if first is None:
                first = page
            elif _stable_page(page) != _stable_page(first):
                raise ValueError("CORE_READER_PAGE_DRIFT")
            previous = _consume_page_rows(page, consume, previous, hashes)
            count += len(page.rows)
            if count > first.pagination.total_count:
                raise ValueError("CORE_READER_ROW_COUNT")
            token = _continuation_token(page, tokens)
            if token is None:
                break
        return first, _complete_view_root(first, view, count, hashes)

    def _captures(
        self,
        tenant: str,
        address: CoreCutAddress,
        portfolio: str | None,
        verify: Callable[[NativeCaptureCommitment, bytes], None],
    ) -> tuple[ReadResponse, NativeViewRoot, tuple[NativeCaptureCommitment, ...]] | None:
        artifacts: list[Artifact] = []

        def consume(row: SegmentRow) -> None:
            if not artifacts or artifacts[-1].commitment != row.commitment():
                if artifacts:
                    previous = artifacts[-1]
                    verify(previous.commitment, previous.raw())
                    previous.spool.close()
                artifacts.append(Artifact(row.commitment(), cast(BinaryIO, TemporaryFile())))
            artifacts[-1].append(row)

        try:
            result = self._read(tenant, address, portfolio, "CAPTURES", consume)
            if result is None:
                return None
            if artifacts:
                verify(artifacts[-1].commitment, artifacts[-1].raw())
            return *result, tuple(a.commitment for a in artifacts)
        finally:
            for artifact in artifacts:
                artifact.spool.close()

    def registry(self, *, tenant_id: str, address: CoreCutAddress) -> RetainedRegistry | None:
        headers: list[RegistryHeader] = []
        members: list[MemberRow] = []
        header = self._read(tenant_id, address, None, "CUT", headers.append)
        if header is None:
            return None

        def consume(row: MemberRow) -> None:
            if len(members) >= 1000:
                raise ValueError("CORE_READER_MANAGE_POPULATION_UNREPRESENTABLE")
            members.append(row)

        member_view = self._read(tenant_id, address, None, "MEMBERS", consume)
        if member_view is None:
            return None
        manifest = headers[0].manifest
        ingress_members: list[str] = []
        chunks: list[str] = []

        def verify(capture: NativeCaptureCommitment, raw: bytes) -> None:
            validate_registry_capture(capture, raw, header[0], manifest, ingress_members, chunks)

        captured = self._captures(tenant_id, address, None, verify)
        if captured is None:
            return None
        _same_receipt(header[0], member_view[0], captured[0])
        if (
            ingress_members != [m.member_content_hash for m in members]
            or len(chunks) != manifest.chunk_count
            or native_ordered_root("PortfolioHistoricalRegistryChunks:v1", chunks)
            != manifest.chunks_root
        ):
            raise ValueError("CORE_READER_INGRESS_MEMBER_CHUNK_ROOT")
        bindings = _registry_member_bindings(members, self.members)
        custody = NativeRegistryCustody(
            locator=_locator(header[0]),
            manifest=manifest,
            receipt=_receipt(header[0]),
            view_roots=(header[1], member_view[1], captured[1]),
            member_bindings=tuple(bindings),
            captures=captured[2],
        )
        return RetainedRegistry(
            address=address,
            tenant_id=tenant_id,
            definition_version=manifest.identity.definition_version,
            coverage_from=manifest.identity.coverage_from,
            coverage_to=manifest.identity.coverage_to,
            generated_at=utc_text(manifest.identity.generated_at),
            declared_coverage=manifest.declared_coverage,
            expected_population_count=manifest.expected_population.count,
            members=_normalized_registry_members(members),
            native_custody=custody,
        )

    def portfolio(
        self, *, tenant_id: str, portfolio_id: str, address: CoreCutAddress
    ) -> RetainedPortfolio | None:
        headers: list[FinancialHeader] = []
        inputs: list[InputRow] = []
        header = self._read(tenant_id, address, portfolio_id, "CUT", headers.append)

        def consume_input(row: InputRow) -> None:
            if inputs:
                raise ValueError("CORE_READER_SELECTED_INPUT")
            inputs.append(row)

        selected = self._read(tenant_id, address, portfolio_id, "INPUTS", consume_input)
        if header is None or selected is None:
            return None
        if (
            len(inputs) != 1
            or inputs[0].graph.portfolio_id != portfolio_id
            or inputs[0].graph.identity != headers[0].manifest.identity
        ):
            raise ValueError("CORE_READER_SELECTED_INPUT")
        products: dict[str, DecodedProduct] = {}

        def verify(capture: NativeCaptureCommitment, raw: bytes) -> None:
            decoded = decode_native(capture, raw, inputs[0])
            if capture.role in products or capture.role is None:
                raise ValueError("CORE_READER_AMBIGUOUS_NATIVE_PRODUCT")
            products[capture.role] = decoded

        captured = self._captures(tenant_id, address, portfolio_id, verify)
        if captured is None:
            return None
        _same_receipt(header[0], selected[0], captured[0])
        custody = NativePortfolioCustody(
            portfolio_id=portfolio_id,
            locator=_locator(header[0]),
            manifest=headers[0].manifest,
            receipt=_receipt(header[0]),
            view_roots=(header[1], selected[1], captured[1]),
            input_content_hash=inputs[0].input_content_hash,
            graph=inputs[0].graph,
            graph_content_hash=inputs[0].graph_content_hash,
            captures=captured[2],
        )
        observation, dependencies = _observations(custody, products)
        descriptor = hash_canonical_payload(observation.model_dump(mode="json"))
        roles = tuple(
            RoleCapture(
                role=s.role,
                product_name=s.product_name,
                product_version=s.product_version,
                source_content_hash="sha256:" + s.content_hash,
                receipt_job_id=s.receipt_job_id,
                descriptor_content_hash=descriptor,
            )
            for s in custody.graph.selections
        )
        cash = custody.graph.settled_unencumbered
        return RetainedPortfolio(
            address=address,
            tenant_id=tenant_id,
            registry_root="sha256:" + custody.graph.registry_root,
            generated_at=utc_text(custody.graph.identity.generated_at),
            roles=roles,
            observations=observation,
            cash_semantic_definition=cash.semantic_definition if cash else None,
            cash_semantic_revision=cash.producer_revision if cash else None,
            reversal_dependencies=dependencies,
            native_custody=custody,
        )


def _stable_page(page: ReadResponse) -> dict[str, Any]:
    value = page.model_dump(mode="json", exclude={"rows", "correlation_id", "pagination"})
    value["pagination"] = page.pagination.model_dump(
        mode="json", exclude={"returned_count", "next_page_token"}
    )
    return value


def _same_receipt(*pages: ReadResponse) -> None:
    if any(
        _receipt(page) != _receipt(pages[0])
        or page.compatibility_posture != pages[0].compatibility_posture
        for page in pages[1:]
    ):
        raise ValueError("CORE_READER_CROSS_VIEW_RECEIPT")


def _receipt(page: ReadResponse) -> NativeCutReceipt:
    return NativeCutReceipt(
        receipt_job_id=page.receipt_job_id,
        received_at=page.received_at,
        completed_at=page.completed_at,
        generated_at=page.generated_at,
    )


def _locator(page: ReadResponse) -> NativeCutLocator:
    return NativeCutLocator(
        product_name=page.product_name,
        source_address=page.source_address,
        batch_manifest_hash=page.batch_manifest_hash,
    )


def _flow(value: dict[str, Any]) -> MonthlyFlowObservation:
    fact = value["fact"]
    target = fact["reversal_target"]
    return MonthlyFlowObservation(
        event_id=fact["envelope"]["source_record_id"],
        business_date=fact["business_date"],
        received_at=utc_text(value["received_at"]),
        currency=fact["currency"],
        amount=fact["amount"],
        classification=fact["classification"],
        status=fact["posting_state"],
        reverses_event_id=target["source_record_id"] if target else None,
    )


def _asset(product: DecodedProduct, day: str) -> str | None:
    rows = [row for row in product.payload["result"]["data"] if row.get("valuation_date") == day]
    if len(rows) != 1:
        raise ValueError("CORE_READER_VALUATION_DATE_AMBIGUOUS")
    value = rows[0].get("eod_market_value")
    if value is not None and not isinstance(value, str):
        raise ValueError("CORE_READER_ASSET_EXACT_TEXT")
    return value


def _observations(
    custody: NativePortfolioCustody, products: dict[str, DecodedProduct]
) -> tuple[MonthlyPortfolioObservations, tuple[MonthlyFlowObservation, ...]]:
    if set(products) != set(NATIVE_ROLES):
        raise ValueError("CORE_READER_ROLE_PRODUCTS_MISSING")
    graph = custody.graph
    flow = products["FLOWS"].payload
    readiness = products["READINESS"].payload["fact"]
    cash = graph.settled_unencumbered
    return MonthlyPortfolioObservations(
        portfolio_id=custody.portfolio_id,
        currency=graph.currency,
        prior_month_end_assets=_asset(products["PRIOR_ASSETS"], graph.prior_date),
        prior_assets_as_of=graph.prior_date,
        month_end_assets=_asset(products["MONTH_END_ASSETS"], graph.month_end_date),
        settled_unencumbered_cash=cash.amount if cash else None,
        cash_as_of=cash.business_date if cash else None,
        discretionary=None,
        funded=readiness["funded"],
        invested=readiness["invested"],
        readiness_as_of=graph.month_end_date,
        flow_coverage_from=flow["cut"]["coverage_from"],
        flow_coverage_to=flow["cut"]["coverage_to"],
        flows=[_flow(v) for v in flow["events"]],
    ), tuple(_flow(v) for v in flow["dependencies"])


def _consume_page_rows(
    page: ReadResponse,
    consume: Callable[[Any], None],
    previous: tuple[Any, ...] | None,
    hashes: list[str],
) -> tuple[Any, ...] | None:
    for row in page.rows:
        key = _key(row)
        if previous is not None and key <= previous:
            raise ValueError("CORE_READER_ROW_ORDER")
        previous = key
        item_hash = _row_hash(row)
        if item_hash is not None:
            hashes.append(item_hash)
        consume(row)
    return previous


def _continuation_token(page: ReadResponse, tokens: set[str]) -> str | None:
    token = page.pagination.next_page_token
    if token is None:
        return None
    if token in tokens or not page.rows:
        raise ValueError("CORE_READER_TOKEN_PROGRESS")
    tokens.add(token)
    return token


def _complete_view_root(
    page: ReadResponse, view: str, count: int, hashes: list[str]
) -> NativeViewRoot:
    kind, ordering, domain = ROOT_RECIPES[view]
    pagination = page.pagination
    if (
        count,
        pagination.root_item_count,
        pagination.root_kind,
        pagination.ordering,
        pagination.ordered_set_hash,
    ) != (
        pagination.total_count,
        len(hashes),
        kind,
        ordering,
        native_ordered_root(domain, hashes),
    ):
        raise ValueError("CORE_READER_VIEW_ROOT")
    return NativeViewRoot.model_validate(
        dict(
            view=view,
            total_count=count,
            ordered_set_hash=pagination.ordered_set_hash,
            root_item_count=len(hashes),
            root_kind=kind,
            ordering=ordering,
        )
    )


def _registry_member_bindings(
    members: list[MemberRow], configured: tuple[CoreMemberBinding, ...]
) -> tuple[NativeRegistryMemberBinding, ...]:
    mapping = {(m.provider_namespace, m.source_member_id): m for m in configured}
    bindings = []
    for row in members:
        member = row.member
        binding = mapping.get((member.provider_namespace, member.source_member_id))
        if binding is None or binding.portfolio_id != member.core_portfolio_id:
            raise ValueError("CORE_READER_MEMBER_MAPPING")
        bindings.append(
            NativeRegistryMemberBinding(
                portfolio_id=binding.portfolio_id,
                provider_id=binding.provider_id,
                provider_namespace=member.provider_namespace,
                source_member_id=member.source_member_id,
                member_revision=member.member_revision,
                member_content_hash=row.member_content_hash,
            )
        )
    return tuple(bindings)


def _normalized_registry_members(members: list[MemberRow]) -> tuple[RegistryMember, ...]:
    return tuple(
        RegistryMember(
            provider_namespace=m.member.provider_namespace,
            source_member_id=m.member.source_member_id,
            portfolio_id=m.member.core_portfolio_id,
            declarations=tuple(
                RegistryDeclaration.model_validate(
                    d.model_dump(mode="json", exclude={"provenance_reference"})
                )
                for d in m.member.declarations
            ),
        )
        for m in members
    )
