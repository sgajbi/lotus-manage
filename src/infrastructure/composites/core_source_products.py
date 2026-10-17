"""Closed producer product roots, exact amounts and flow dependency closure."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

from src.core.composite_eligibility.native_source_custody import (
    NativeModel,
    NativeCaptureCommitment,
    NativeRegistryManifest,
    native_domain_hash,
)
from src.infrastructure.composites.core_source_custody import (
    CashFact,
    ReadinessFact,
    FlowCut,
    FlowFact,
    FlowPin,
)
from src.infrastructure.composites.core_source_wire import (
    canonical_bytes,
    json_hash,
    closed_json,
    member_hash,
    ReadResponse,
    WireMember,
)

NATIVE_SERIALIZERS = {
    "CASH": "portfolio-cash-availability:domain-json:v1",
    "READINESS": "portfolio-funding-investment:domain-json:v1",
    "FLOWS": "portfolio-flow-source-cut:domain-json:v1",
    "PRIOR_ASSETS": "portfolio-timeseries-export:retained-json:v1",
    "MONTH_END_ASSETS": "portfolio-timeseries-export:retained-json:v1",
}
Model = TypeVar("Model", bound=NativeModel)


def require_fields(value: Any, fields: tuple[str, ...]) -> None:
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError("CORE_READER_NATIVE_CLOSED_SHAPE")


def domain_model(model: type[Model], value: Any) -> Model:
    result = model.model_validate_json(canonical_bytes(value))
    if result.model_dump(mode="json") != value:
        raise ValueError("CORE_READER_NATIVE_CANONICAL_DOMAIN")
    envelope = value.get("envelope")
    if isinstance(envelope, dict):
        for key in ("observed_at", "generated_at"):
            stamp = datetime.fromisoformat(envelope[key])
            if stamp.isoformat().replace("+00:00", "Z") != envelope[key]:
                raise ValueError("CORE_READER_NATIVE_CANONICAL_DOMAIN")
    return result


def domain_tags(value: Any, field: str = "") -> Any:
    if isinstance(value, dict):
        return {k: domain_tags(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [domain_tags(item) for item in value]
    if value is None:
        return None
    if field in {"effective_from", "effective_to", "business_date", "coverage_from", "coverage_to"}:
        return {"date": date.fromisoformat(value).isoformat()}
    if field in {"observed_at", "generated_at"}:
        return {"datetime": datetime.fromisoformat(value).astimezone(UTC).isoformat()}
    if field in {"settled", "encumbered", "available", "amount"}:
        return {"decimal": canonical_decimal(value)}
    return value


def canonical_decimal(value: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError("CORE_READER_DECIMAL_TEXT")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("CORE_READER_DECIMAL_TEXT") from exc
    exponent = _numeric_exponent(amount)
    if str(_canonical_numeric_amount(amount, exponent)) != value:
        raise ValueError("CORE_READER_DECIMAL_NONCANONICAL")
    return value


def fact_root(fact: CashFact | ReadinessFact | FlowFact) -> str:
    material = domain_tags(fact.model_dump(mode="json"))
    if isinstance(fact, FlowFact):
        return json_hash({"contract": "PortfolioFlowEventObservation:v1", "observation": material})
    return json_hash(
        {
            "contract": "PortfolioFinancialSourceObservations:v1",
            "family": "cash_availability" if isinstance(fact, CashFact) else "funding_investment",
            "observation": material,
        }
    )


def export_selection_root(result: dict[str, Any]) -> str:
    evidence = result["source_evidence"]
    pages = [_export_page_commitment(page) for page in evidence["pages"]]
    root = json_hash(
        {
            "identity_version": "analytics-export-selection-v1",
            "rows": result["data"],
            "source_evidence": {
                k: v for k, v in evidence.items() if k not in {"pages", "selection_digest"}
            },
            "pages": pages,
        }
    )
    if evidence.get("selection_digest") != "sha256:" + root:
        raise ValueError("CORE_READER_EXPORT_SELECTION_ROOT")
    return root


def native_typed_root(serializer: str, payload: dict[str, Any]) -> str:
    try:
        return _native_typed_root(serializer, payload)
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("CORE_READER_NATIVE_PAYLOAD_INVALID") from exc


def _native_typed_root(serializer: str, payload: dict[str, Any]) -> str:
    if serializer not in NATIVE_SERIALIZERS.values():
        raise ValueError("CORE_READER_SERIALIZER_UNSUPPORTED")
    if serializer in (NATIVE_SERIALIZERS["CASH"], NATIVE_SERIALIZERS["READINESS"]):
        require_fields(
            payload,
            (
                "product_name",
                "product_version",
                "fact",
                "observation_id",
                "content_hash",
                "received_at",
                "receipt",
            ),
        )
        fact = (
            domain_model(CashFact, payload["fact"])
            if serializer == NATIVE_SERIALIZERS["CASH"]
            else domain_model(ReadinessFact, payload["fact"])
        )
        root = fact_root(fact)
        if (
            payload["product_name"],
            payload["product_version"],
            payload["observation_id"],
            payload["content_hash"],
        ) != ("PortfolioFinancialSourceObservations", "v1", root, root):
            raise ValueError("CORE_READER_FACT_ROOT")
        return root
    if serializer == NATIVE_SERIALIZERS["FLOWS"]:
        require_fields(
            payload,
            (
                "product_name",
                "product_version",
                "cut",
                "events",
                "dependencies",
                "received_at",
                "receipt",
            ),
        )
        cut = domain_model(FlowCut, payload["cut"])
        require_flow_closure(cut, payload)
        if (payload["product_name"], payload["product_version"]) != (
            "PortfolioFinancialFlowObservations",
            "v1",
        ):
            raise ValueError("CORE_READER_FLOW_PRODUCT")
        return json_hash(
            {
                "contract": "PortfolioFlowSourceCut:v1",
                "cut": domain_tags(cut.model_dump(mode="json")),
            }
        )
    require_fields(payload, ("product_name", "product_version", "result", "request", "receipt"))
    if (payload["product_name"], payload["product_version"]) != ("PortfolioTimeseriesInput", "v1"):
        raise ValueError("CORE_READER_EXPORT_PRODUCT")
    return export_selection_root(payload["result"])


def _pinned_flow(fact: FlowFact, pin: FlowPin, cut: FlowCut, window: bool) -> None:
    env = fact.envelope
    if (
        env.tenant_id,
        env.portfolio_id,
        env.producer_id,
        env.definition_version,
        fact.currency,
        env.source_record_id,
        env.source_revision,
        fact_root(fact),
    ) != (
        cut.tenant_id,
        cut.portfolio_id,
        cut.source_system,
        cut.definition_version,
        cut.currency,
        pin.source_record_id,
        pin.flow_source_record_revision,
        pin.content_hash,
    ):
        raise ValueError("CORE_READER_FLOW_PIN_SCOPE")
    if window and not cut.coverage_from <= fact.business_date <= cut.coverage_to:
        raise ValueError("CORE_READER_FLOW_WINDOW")
    if (
        env.coverage != "complete"
        or fact.posting_state == "UNKNOWN"
        or fact.reversal_state == "UNKNOWN"
    ):
        raise ValueError("CORE_READER_FLOW_UNAVAILABLE")


def require_flow_closure(cut: FlowCut, payload: dict[str, Any]) -> None:
    events, all_facts = _flow_membership(cut, payload)
    if cut.coverage != "complete":
        raise ValueError("CORE_READER_FLOW_UNAVAILABLE")
    needed: set[str] = set()
    dependency_ids = {p.observation_id for p in cut.dependency_pins}
    for event in events:
        needed.update(_flow_dependency_chain(event, all_facts, cut, dependency_ids))
    if needed != dependency_ids:
        raise ValueError("CORE_READER_FLOW_UNREFERENCED_DEPENDENCY")


def require_receipt(
    value: Any, *, tenant: str, job: str, endpoint: str, entity: str, received: str
) -> None:
    require_fields(
        value,
        (
            "job_id",
            "tenant_id",
            "endpoint",
            "entity_type",
            "status",
            "completed_at",
            "accepted_count",
        ),
    )
    left, right = datetime.fromisoformat(received), datetime.fromisoformat(value["completed_at"])
    if (
        left.utcoffset() is None
        or right.utcoffset() is None
        or left > right
        or (
            value["tenant_id"],
            value["job_id"],
            value["endpoint"],
            value["entity_type"],
            value["status"],
        )
        != (tenant, job, endpoint, entity, "completed")
        or type(value["accepted_count"]) is not int
        or value["accepted_count"] < 1
    ):
        raise ValueError("CORE_READER_NATIVE_RECEIPT")


def validate_registry_capture(
    capture: NativeCaptureCommitment,
    raw: bytes,
    page: ReadResponse,
    manifest: Any,
    members: list[str],
    chunks: list[str],
) -> None:
    _require_registry_capture_catalog(capture, page)
    body = _registry_capture_body(capture, raw, page)
    if capture.source_page_index > 0:
        hashes, typed = _registry_chunk_commitment(body, capture, page, chunks)
        members.extend(hashes)
        chunks.append(typed)
    else:
        typed = _registry_manifest_commitment(body, page, manifest)
    if capture.typed_content_hash != typed:
        raise ValueError("CORE_READER_INGRESS_TYPED_ROOT")


def _numeric_exponent(amount: Decimal) -> int:
    """Admit the producer's PostgreSQL NUMERIC range before any expansion."""
    exponent = amount.as_tuple().exponent
    if (
        not amount.is_finite()
        or not isinstance(exponent, int)
        or exponent < -16383
        or (not amount.is_zero() and amount.adjusted() >= 131072)
    ):
        raise ValueError("CORE_READER_DECIMAL_RANGE")
    return exponent


def _canonical_numeric_amount(amount: Decimal, exponent: int) -> Decimal:
    """Keep declared scale and canonical zero sign without caller-context arithmetic."""
    if amount.is_zero():
        return Decimal((0, (0,), min(exponent, 0)))
    if exponent > 0:
        return Decimal(format(amount, "f"))
    return amount


def _export_page_commitment(page: dict[str, Any]) -> dict[str, Any]:
    """Remove only the producer recipe's established volatile metadata fields."""
    metadata = dict(page["source_metadata"])
    for key in ("generated_at", "correlation_id"):
        metadata.pop(key, None)
    if isinstance(metadata.get("lineage"), dict):
        metadata["lineage"] = {
            k: v
            for k, v in metadata["lineage"].items()
            if k not in {"generated_at", "request_fingerprint"}
        }
    if isinstance(metadata.get("page"), dict):
        metadata["page"] = {k: v for k, v in metadata["page"].items() if k != "next_page_token"}
    return {**page, "source_metadata": metadata}


def _flow_membership(
    cut: FlowCut, payload: dict[str, Any]
) -> tuple[list[FlowFact], dict[str, FlowFact]]:
    all_facts: dict[str, FlowFact] = {}
    events: list[FlowFact] = []
    for name, pins in (("events", cut.event_pins), ("dependencies", cut.dependency_pins)):
        values = payload[name]
        if not isinstance(values, list) or len(values) != len(pins):
            raise ValueError("CORE_READER_FLOW_MEMBERSHIP")
        for value, pin in zip(values, pins, strict=True):
            require_fields(value, ("fact", "received_at", "receipt"))
            fact = domain_model(FlowFact, value["fact"])
            _pinned_flow(fact, pin, cut, name == "events")
            all_facts[pin.observation_id] = fact
            if name == "events":
                events.append(fact)
    return events, all_facts


def _flow_dependency_chain(
    event: FlowFact,
    all_facts: dict[str, FlowFact],
    cut: FlowCut,
    dependency_ids: set[str],
) -> set[str]:
    needed: set[str] = set()
    seen = {event.envelope.source_record_id}
    current = event
    while current.reversal_target is not None:
        pin = current.reversal_target
        target = all_facts.get(pin.observation_id)
        if target is None or target.envelope.source_record_id in seen:
            raise ValueError("CORE_READER_FLOW_CLOSURE")
        _pinned_flow(target, pin, cut, False)
        if target.business_date > current.business_date:
            raise ValueError("CORE_READER_FLOW_TARGET_CHRONOLOGY")
        seen.add(target.envelope.source_record_id)
        if pin.observation_id in dependency_ids:
            needed.add(pin.observation_id)
        current = target
    return needed


def _require_registry_capture_catalog(capture: NativeCaptureCommitment, page: ReadResponse) -> None:
    context = capture.source_context
    tag = (
        "portfolio-historical-registry-chunk:ingress-json:v1"
        if capture.source_page_index > 0
        else "portfolio-historical-registry-cut:ingress-json:v1"
    )
    if (
        capture.source_product,
        capture.product_version,
        capture.serializer_id,
        capture.schema_version,
        capture.mime_type,
        context.capture_origin,
        context.receipt_job_id,
        context.source_revision,
        capture.role,
        capture.selector_hash,
    ) != (
        "PortfolioHistoricalRegistry",
        "v1",
        tag,
        "v1",
        "application/json",
        "INGRESS_JSON",
        page.receipt_job_id,
        str(page.source_address.revision),
        None,
        None,
    ) or any(
        v is not None
        for v in (
            context.snapshot_epoch,
            context.request_scope,
            context.selector_json,
            context.export_job_id,
            context.refresh_of_job_id,
            context.returned_count,
            context.total_count,
            context.next_page_token,
            capture.original_supplier_digest,
            capture.original_supplier_reference,
        )
    ):
        raise ValueError("CORE_READER_INGRESS_CATALOG_CONTEXT")


def _registry_capture_body(capture: NativeCaptureCommitment, raw: bytes, page: ReadResponse) -> Any:
    body = closed_json(raw)
    address = page.source_address.model_dump(mode="json")
    if any(body.get(k) != v for k, v in address.items()):
        raise ValueError("CORE_READER_INGRESS_ADDRESS")
    expected_id = json_hash(
        {
            "contract": "NeutralIngressSourceCapture:v1",
            "tenant_id": page.tenant_id,
            "product_name": page.product_name,
            **address,
            "source_page_index": capture.source_page_index,
            "raw_hash": capture.raw_hash,
        }
    )
    if expected_id != capture.capture_id:
        raise ValueError("CORE_READER_INGRESS_CAPTURE_ID")
    return body


def _registry_chunk_commitment(
    body: dict[str, Any],
    capture: NativeCaptureCommitment,
    page: ReadResponse,
    chunks: list[str],
) -> tuple[list[str], str]:
    address = page.source_address.model_dump(mode="json")
    if (
        set(body) != {*address, "chunk_index", "members", "typed_content_hash"}
        or type(body["chunk_index"]) is not int
        or body["chunk_index"] + 1 != capture.source_page_index
        or len(body["members"]) > 500
        or body["chunk_index"] != len(chunks)
    ):
        raise ValueError("CORE_READER_INGRESS_CHUNK")
    hashes = [
        member_hash(WireMember.model_validate_json(canonical_bytes(value)))
        for value in body["members"]
    ]
    typed = json_hash({"contract": "PortfolioHistoricalRegistryChunk:v1", "members": hashes})
    if body["typed_content_hash"] != typed:
        raise ValueError("CORE_READER_INGRESS_CHUNK_HASH")
    return hashes, typed


def _registry_manifest_commitment(body: dict[str, Any], page: ReadResponse, manifest: Any) -> str:
    value = manifest.model_dump(mode="json")
    identity = value.pop("identity")
    identity.pop("tenant_id")
    identity["registry_scope_id"] = identity.pop("scope_id")
    if set(body) != set(identity) | set(value):
        raise ValueError("CORE_READER_INGRESS_MANIFEST")
    raw_identity = {key: body[key] for key in identity}
    raw_identity["tenant_id"] = page.tenant_id
    raw_identity["scope_id"] = raw_identity.pop("registry_scope_id")
    raw_manifest = NativeRegistryManifest.model_validate(
        {"identity": raw_identity, **{key: body[key] for key in value}}
    )
    typed = native_domain_hash("PortfolioHistoricalRegistry:v1", "cut", raw_manifest)
    if typed != page.batch_manifest_hash:
        raise ValueError("CORE_READER_INGRESS_MANIFEST")
    return typed
