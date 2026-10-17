"""Pinned native catalog/context orchestration; content integrity grants no authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
from src.infrastructure.composites.core_source_custody import CashFact, ReadinessFact, FlowCut
from src.infrastructure.composites.core_source_products import (
    NATIVE_SERIALIZERS,
    domain_model,
    fact_root,
    native_typed_root,
    require_fields,
    require_receipt,
)
from src.infrastructure.composites.core_source_valuation import validate_valuation
from src.infrastructure.composites.core_source_wire import (
    InputRow,
    FlowSelector,
    ObservationSelector,
    ValuationSelector,
    WireSelection,
    canonical_bytes,
    closed_json,
    json_hash,
)


@dataclass(frozen=True)
class DecodedProduct:
    payload: dict[str, Any]
    selection: WireSelection


def decode_native(
    capture: NativeCaptureCommitment, raw: bytes, selected: InputRow
) -> DecodedProduct:
    try:
        return _decode_native(capture, raw, selected)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("CORE_READER_NATIVE_PAYLOAD_INVALID") from exc


def _decode_native(
    capture: NativeCaptureCommitment, raw: bytes, selected: InputRow
) -> DecodedProduct:
    selection = next((s for s in selected.declaration.selections if s.role == capture.role), None)
    if selection is None or capture.role is None:
        raise ValueError("CORE_READER_NATIVE_ROLE")
    _require_capture_selection(capture, selection, selected)
    payload = _native_payload(capture, raw)
    count = _native_scope(payload, capture, selection, selected)
    context = capture.source_context
    if capture.source_page_index != 0 or (
        context.returned_count,
        context.total_count,
        context.next_page_token,
    ) != (count, count, None):
        raise ValueError("CORE_READER_NATIVE_COMPLETE_ARTIFACT")
    return DecodedProduct(payload, selection)


def _native_scope(
    payload: dict[str, Any],
    capture: NativeCaptureCommitment,
    selection: WireSelection,
    selected: InputRow,
) -> int:
    selector = selection.selector
    if isinstance(selector, ValuationSelector):
        return validate_valuation(payload, capture, selector, selected)
    context = capture.source_context
    if any(
        v is not None
        for v in (
            context.snapshot_epoch,
            context.request_scope,
            context.export_job_id,
            context.refresh_of_job_id,
        )
    ):
        raise ValueError("CORE_READER_FACT_CONTEXT_MUST_BE_NULL")
    if isinstance(selector, ObservationSelector):
        return _observation_scope(payload, selection, selector, selected)
    return _flow_scope(payload, capture, selection, selector, selected)


def _require_capture_selection(
    capture: NativeCaptureCommitment, selection: WireSelection, selected: InputRow
) -> None:
    context = capture.source_context
    expected_id = json_hash(
        {
            "contract": "NativeSourceCaptureRequest:v1",
            "tenant": selected.graph.identity.tenant_id,
            "portfolio": selected.graph.portfolio_id,
            "product": selection.product_name,
            "version": selection.product_version,
            "selector": selection.selector_hash,
            "content": selection.content_hash,
            "receipt": selection.receipt_job_id,
            "revision": selection.source_revision,
            "page_index": capture.source_page_index,
        }
    )
    if (
        capture.serializer_id,
        capture.schema_version,
        capture.mime_type,
        context.capture_origin,
        capture.capture_id,
    ) != (
        NATIVE_SERIALIZERS[selection.role],
        "v1",
        "application/json",
        "ACQUIRED_NATIVE_DTO",
        expected_id,
    ):
        raise ValueError("CORE_READER_NATIVE_CATALOG")
    if (
        capture.source_product,
        capture.product_version,
        capture.selector_hash,
        capture.typed_content_hash,
        context.receipt_job_id,
        context.source_revision,
        closed_json(context.selector_json or "null"),
    ) != (
        selection.product_name,
        selection.product_version,
        selection.selector_hash,
        selection.content_hash,
        selection.receipt_job_id,
        selection.source_revision,
        selection.selector.model_dump(mode="json"),
    ):
        raise ValueError("CORE_READER_NATIVE_CONTEXT")


def _native_payload(capture: NativeCaptureCommitment, raw: bytes) -> dict[str, Any]:
    if len(raw) != capture.byte_count or hashlib.sha256(raw).hexdigest() != capture.raw_hash:
        raise ValueError("CORE_READER_NATIVE_RAW")
    wrapper = closed_json(raw)
    require_fields(wrapper, ("serializer", "payload"))
    if (
        wrapper["serializer"] != capture.serializer_id
        or canonical_bytes(wrapper) != raw
        or not isinstance(wrapper["payload"], dict)
    ):
        raise ValueError("CORE_READER_NATIVE_WRAPPER")
    payload: dict[str, Any] = wrapper["payload"]
    if native_typed_root(capture.serializer_id, payload) != capture.typed_content_hash:
        raise ValueError("CORE_READER_NATIVE_TYPED_ROOT")
    return payload


def _observation_scope(
    payload: dict[str, Any],
    selection: WireSelection,
    selector: ObservationSelector,
    selected: InputRow,
) -> int:
    tenant = selected.graph.identity.tenant_id
    fact = (
        domain_model(CashFact, payload["fact"])
        if selector.kind == "CASH"
        else domain_model(ReadinessFact, payload["fact"])
    )
    _require_observation_selection(fact, selection, selector, selected)
    family = "cash-availability" if selector.kind == "CASH" else "funding-investment"
    require_receipt(
        payload["receipt"],
        tenant=tenant,
        job=selection.receipt_job_id,
        endpoint=f"/ingest/portfolio-{family}-observations",
        entity="portfolio_" + family.replace("-", "_") + "_observation",
        received=payload["received_at"],
    )
    return 1


def _require_observation_selection(
    fact: CashFact | ReadinessFact,
    selection: WireSelection,
    selector: ObservationSelector,
    selected: InputRow,
) -> None:
    tenant, portfolio = selected.graph.identity.tenant_id, selected.graph.portfolio_id
    env = fact.envelope
    if (
        (
            env.tenant_id,
            env.portfolio_id,
            env.definition_version,
            env.producer_id,
            env.source_record_id,
            env.source_cut_id,
            env.source_revision,
            selection.source_revision,
            selector.observation_id,
            selector.content_hash,
        )
        != (
            tenant,
            portfolio,
            selected.graph.identity.definition_version,
            selector.producer_id,
            selector.source_record_id,
            selector.source_cut_id,
            selector.source_version,
            str(env.source_revision),
            fact_root(fact),
            fact_root(fact),
        )
        or env.coverage != "complete"
        or not env.effective_from <= selector.as_of_date
        or (env.effective_to is not None and selector.as_of_date >= env.effective_to)
    ):
        raise ValueError("CORE_READER_FACT_SCOPE")
    if isinstance(fact, CashFact) and fact.currency != selected.graph.currency:
        raise ValueError("CORE_READER_CASH_CURRENCY")


def _flow_scope(
    payload: dict[str, Any],
    capture: NativeCaptureCommitment,
    selection: WireSelection,
    selector: FlowSelector,
    selected: InputRow,
) -> int:
    tenant, portfolio = selected.graph.identity.tenant_id, selected.graph.portfolio_id
    cut = domain_model(FlowCut, payload["cut"])
    if (
        cut.tenant_id,
        cut.portfolio_id,
        cut.definition_version,
        cut.source_system,
        cut.source_cut_id,
        cut.cut_revision,
        cut.coverage_from,
        cut.coverage_to,
        cut.currency,
        selection.source_revision,
        selector.manifest_hash,
    ) != (
        tenant,
        portfolio,
        selected.graph.identity.definition_version,
        selector.source_system,
        selector.source_cut_id,
        selector.cut_revision,
        selector.from_date,
        selector.to_date,
        selected.graph.currency,
        str(cut.cut_revision),
        capture.typed_content_hash,
    ):
        raise ValueError("CORE_READER_FLOW_SELECTION_SCOPE")
    require_receipt(
        payload["receipt"],
        tenant=tenant,
        job=selection.receipt_job_id,
        endpoint="/ingest/portfolio-flow-source-cuts",
        entity="portfolio_flow_source_cut",
        received=payload["received_at"],
    )
    for value in payload["events"] + payload["dependencies"]:
        require_receipt(
            value["receipt"],
            tenant=tenant,
            job=value["receipt"]["job_id"],
            endpoint="/ingest/portfolio-flow-event-observations",
            entity="portfolio_flow_event_observation",
            received=value["received_at"],
        )
    return len(cut.event_pins) + len(cut.dependency_pins)
