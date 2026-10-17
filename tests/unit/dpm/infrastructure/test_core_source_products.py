"""Source-family scalar fidelity and complete typed flow membership are independent."""

from copy import deepcopy

import pytest

from src.infrastructure.composites.core_source_products import native_typed_root, NATIVE_SERIALIZERS
from tests.unit.dpm.infrastructure.test_core_source_reader import (
    fixture_products,
    fact_hash,
    digest,
    typed,
)


def test_readiness_false_null_is_distinct_from_zero_and_true():
    payload = fixture_products("P1")[3][1]
    expected = fact_hash(payload["fact"], "funding_investment")
    assert native_typed_root(NATIVE_SERIALIZERS["READINESS"], payload) == expected
    invalid = deepcopy(payload)
    invalid["fact"]["funded"] = 0
    with pytest.raises(ValueError):
        native_typed_root(NATIVE_SERIALIZERS["READINESS"], invalid)
    changed = deepcopy(payload)
    changed["fact"]["funded"] = True
    changed["content_hash"] = changed["observation_id"] = fact_hash(
        changed["fact"], "funding_investment"
    )
    assert native_typed_root(NATIVE_SERIALIZERS["READINESS"], changed) != expected


def test_cash_decimal_scale_unicode_and_utc_offset_are_exact():
    payload = fixture_products("P1")[2][1]
    payload["fact"]["envelope"]["source_record_id"] = "Ω-α-零"
    payload["fact"]["envelope"]["observed_at"] = "2026-10-16T08:00:00+08:00"
    payload["content_hash"] = payload["observation_id"] = fact_hash(
        payload["fact"], "cash_availability"
    )
    expected = native_typed_root(NATIVE_SERIALIZERS["CASH"], payload)
    payload["fact"]["envelope"]["observed_at"] = "2026-10-16T00:00:00Z"
    assert native_typed_root(NATIVE_SERIALIZERS["CASH"], payload) == expected
    payload["fact"]["settled"] = "0.0"
    payload["content_hash"] = payload["observation_id"] = fact_hash(
        payload["fact"], "cash_availability"
    )
    assert native_typed_root(NATIVE_SERIALIZERS["CASH"], payload) != expected


@pytest.mark.parametrize("amount", ["-0.00", "0E+1", "1e2", "NaN", "Infinity", " 0.00", 1.0, False])
def test_noncanonical_or_coerced_cash_refuses(amount):
    payload = fixture_products("P1")[2][1]
    payload["fact"]["settled"] = amount
    with pytest.raises(ValueError):
        native_typed_root(NATIVE_SERIALIZERS["CASH"], payload)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "foreign",
        "extra",
        "naive",
        "unknown",
        "revision",
        "window",
        "dependency",
    ],
)
def test_complete_flow_cut_refuses_corruption(mutation):
    payload = fixture_products("P1")[4][1]
    if mutation == "missing":
        payload["events"] = []
    elif mutation == "duplicate":
        payload["events"].append(deepcopy(payload["events"][0]))
    elif mutation == "foreign":
        payload["events"][0]["fact"]["envelope"]["portfolio_id"] = "foreign"
    elif mutation == "extra":
        payload["events"][0]["fact"]["hidden"] = True
    elif mutation == "naive":
        payload["events"][0]["fact"]["envelope"]["observed_at"] = "2026-10-16T00:00:00"
    elif mutation == "unknown":
        payload["events"][0]["fact"]["posting_state"] = "UNKNOWN"
    elif mutation == "revision":
        payload["cut"]["cut_revision"] = True
    elif mutation == "window":
        payload["events"][0]["fact"]["business_date"] = "2025-02-01"
    else:
        payload["cut"]["dependency_pins"] = deepcopy(payload["cut"]["event_pins"])
    with pytest.raises(ValueError):
        native_typed_root(NATIVE_SERIALIZERS["FLOWS"], payload)


def reversal_payload():
    payload = fixture_products("P1")[4][1]
    original = deepcopy(payload["events"][0])
    original["fact"]["business_date"] = "2025-01-15"
    root = digest(
        {"contract": "PortfolioFlowEventObservation:v1", "observation": typed(original["fact"])}
    )
    pin = {
        "source_record_id": "record",
        "observation_id": root,
        "content_hash": root,
        "flow_source_record_revision": 1,
    }
    reverse = deepcopy(original)
    reverse["fact"].update(
        business_date="2025-01-31",
        amount="10.00",
        classification="REVERSAL",
        reversal_state="REVERSES",
        reverses_source_record_id="record",
        reversal_target=pin,
    )
    reverse["fact"]["envelope"]["source_record_id"] = "reversal"
    reverse_root = digest(
        {"contract": "PortfolioFlowEventObservation:v1", "observation": typed(reverse["fact"])}
    )
    payload["events"] = [reverse]
    payload["dependencies"] = [original]
    payload["cut"]["event_pins"] = [
        {
            "source_record_id": "reversal",
            "observation_id": reverse_root,
            "content_hash": reverse_root,
            "flow_source_record_revision": 1,
        }
    ]
    payload["cut"]["dependency_pins"] = [pin]
    return payload


def test_reversal_dependency_closure_and_ordered_pins():
    payload = reversal_payload()
    assert native_typed_root(NATIVE_SERIALIZERS["FLOWS"], payload) == digest(
        {"contract": "PortfolioFlowSourceCut:v1", "cut": typed(payload["cut"])}
    )
    payload["dependencies"] = []
    with pytest.raises(ValueError):
        native_typed_root(NATIVE_SERIALIZERS["FLOWS"], payload)


@pytest.mark.parametrize(
    "boundary",
    [
        "window",
        "event_coverage",
        "cut_coverage",
        "unused_dependency",
        "missing_target",
        "future_target",
    ],
)
def test_flow_closure_refuses_semantically_invalid_but_correctly_hashed_source(boundary):
    payload = reversal_payload()
    assert native_typed_root(NATIVE_SERIALIZERS["FLOWS"], payload) == digest(
        {"contract": "PortfolioFlowSourceCut:v1", "cut": typed(payload["cut"])}
    )
    event = payload["events"][0]["fact"]
    dependency = payload["dependencies"][0]["fact"]
    if boundary == "window":
        payload["cut"]["coverage_to"] = "2025-01-30"
        error = "FLOW_WINDOW"
    elif boundary == "event_coverage":
        event["envelope"]["coverage"] = "partial"
        error = "FLOW_UNAVAILABLE"
    elif boundary == "cut_coverage":
        payload["cut"]["coverage"] = "partial"
        error = "FLOW_UNAVAILABLE"
    elif boundary == "unused_dependency":
        event.update(
            classification="EXTERNAL_CASH",
            reversal_state="NONE",
            reversal_target=None,
            reverses_source_record_id=None,
        )
        error = "FLOW_UNREFERENCED_DEPENDENCY"
    elif boundary == "missing_target":
        payload["dependencies"] = []
        payload["cut"]["dependency_pins"] = []
        error = "FLOW_CLOSURE"
    else:
        dependency["business_date"] = "2025-02-01"
        root = digest(
            {"contract": "PortfolioFlowEventObservation:v1", "observation": typed(dependency)}
        )
        payload["cut"]["dependency_pins"][0].update(observation_id=root, content_hash=root)
        event["reversal_target"] = deepcopy(payload["cut"]["dependency_pins"][0])
        error = "FLOW_TARGET_CHRONOLOGY"
    root = digest({"contract": "PortfolioFlowEventObservation:v1", "observation": typed(event)})
    payload["cut"]["event_pins"][0].update(observation_id=root, content_hash=root)
    with pytest.raises(ValueError, match=error):
        native_typed_root(NATIVE_SERIALIZERS["FLOWS"], payload)


@pytest.mark.parametrize(
    "boundary",
    ["flow_product", "export_product", "export_shape", "decimal_text", "noncanonical_time"],
)
def test_native_product_catalog_and_scalar_admission_refuse_uninterpretable_payloads(boundary):
    if boundary.startswith("flow"):
        payload = fixture_products("P1")[4][1]
        serializer = NATIVE_SERIALIZERS["FLOWS"]
        payload["product_version"] = "v2"
        error = "FLOW_PRODUCT"
    elif boundary.startswith("export"):
        payload = fixture_products("P1")[0][1]
        serializer = NATIVE_SERIALIZERS["PRIOR_ASSETS"]
        if boundary == "export_product":
            payload["product_name"] = "OtherProduct"
            error = "EXPORT_PRODUCT"
        else:
            payload["result"]["source_evidence"]["pages"] = [{}]
            error = "NATIVE_PAYLOAD_INVALID"
    else:
        payload = fixture_products("P1")[2][1]
        serializer = NATIVE_SERIALIZERS["CASH"]
        if boundary == "decimal_text":
            payload["fact"]["settled"] = "not-a-decimal"
            error = "DECIMAL_TEXT"
        else:
            payload["fact"]["envelope"]["observed_at"] = "2026-10-16T00:00:00+00:00"
            error = "NATIVE_CANONICAL_DOMAIN"
    with pytest.raises(ValueError, match=error):
        native_typed_root(serializer, payload)


@pytest.mark.parametrize(
    "boundary", ["tenant", "job", "endpoint", "entity", "pending", "count", "naive", "clock"]
)
def test_ingestion_receipt_is_bound_to_actual_job_scope_and_completion(boundary):
    from src.infrastructure.composites.core_source_products import require_receipt

    payload = fixture_products("P1")[2][1]
    receipt = payload["receipt"]
    args = dict(
        tenant="tenant",
        job=receipt["job_id"],
        endpoint=receipt["endpoint"],
        entity=receipt["entity_type"],
        received=payload["received_at"],
    )
    require_receipt(receipt, **args)
    field, value = {
        "tenant": ("tenant_id", "foreign"),
        "job": ("job_id", "foreign"),
        "endpoint": ("endpoint", "/other"),
        "entity": ("entity_type", "other"),
        "pending": ("status", "pending"),
        "count": ("accepted_count", 0),
        "naive": ("completed_at", "2026-10-16T00:00:00"),
        "clock": ("completed_at", "2026-10-15T23:59:59Z"),
    }[boundary]
    receipt[field] = value
    with pytest.raises(ValueError, match="NATIVE_RECEIPT"):
        require_receipt(receipt, **args)


def registry_capture_fixture(page_index):
    import base64
    import httpx
    from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
    from src.infrastructure.composites.core_source_wire import ReadResponse
    from tests.unit.dpm.infrastructure.test_core_source_reader import encoded, fixture, response

    config, records, roots = fixture()
    request = {
        **config.registry.model_dump(mode="json", exclude={"content_hash"}),
        "view": "CUT",
        "page": {"page_size": 2, "page_token": None},
    }
    page = ReadResponse.model_validate_json(
        encoded(
            response(httpx.Request("POST", "https://core.example", json=request), records, roots)
        )
    )
    segment = records[(None, "CAPTURES")][page_index]
    capture = NativeCaptureCommitment.model_validate(
        {
            k: v
            for k, v in segment.items()
            if k not in {"row_kind", "segment_index", "segment_hash", "bytes_base64"}
        }
    )
    return capture, base64.b64decode(segment["bytes_base64"]), page


def test_retained_export_ignores_only_declared_volatile_lineage_fields():
    from tests.unit.dpm.infrastructure.test_core_source_reader import export_hash

    payload = fixture_products("P1")[0][1]
    metadata = payload["result"]["source_evidence"]["pages"][0]["source_metadata"]
    metadata["lineage"] = {"source_revision": "retained-1"}
    root = export_hash(payload["result"])
    payload["result"]["source_evidence"]["selection_digest"] = "sha256:" + root
    assert native_typed_root(NATIVE_SERIALIZERS["PRIOR_ASSETS"], payload) == root
    metadata["lineage"].update(
        generated_at="2027-01-01T00:00:00Z", request_fingerprint="different-request"
    )
    assert native_typed_root(NATIVE_SERIALIZERS["PRIOR_ASSETS"], payload) == root
    metadata["lineage"]["source_revision"] = "retained-2"
    with pytest.raises(ValueError, match="EXPORT_SELECTION_ROOT"):
        native_typed_root(NATIVE_SERIALIZERS["PRIOR_ASSETS"], payload)


@pytest.mark.parametrize(
    "boundary",
    [
        "address",
        "capture_id",
        "chunk_shape",
        "chunk_hash",
        "manifest_shape",
        "manifest_root",
        "typed_root",
    ],
)
def test_registry_ingress_refuses_rebound_raw_bytes_with_invalid_closed_meaning(boundary):
    from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
    from src.infrastructure.composites.core_source_products import validate_registry_capture
    from tests.unit.dpm.infrastructure.test_core_source_reader import artifact, encoded
    import json

    capture, raw, page = registry_capture_fixture(1 if boundary.startswith("chunk") else 0)
    manifest = page.rows[0].manifest
    members, chunks = [], []
    validate_registry_capture(capture, raw, page, manifest, members, chunks)
    body = json.loads(raw)
    error = {
        "address": "INGRESS_ADDRESS",
        "capture_id": "INGRESS_CAPTURE_ID",
        "chunk_shape": "INGRESS_CHUNK",
        "chunk_hash": "INGRESS_CHUNK_HASH",
        "manifest_shape": "INGRESS_MANIFEST",
        "manifest_root": "INGRESS_MANIFEST",
        "typed_root": "INGRESS_TYPED_ROOT",
    }[boundary]
    if boundary == "address":
        body["registry_scope_id"] = "foreign"
    elif boundary == "chunk_shape":
        body["chunk_index"] = 1
    elif boundary == "chunk_hash":
        body["typed_content_hash"] = "f" * 64
    elif boundary == "manifest_shape":
        body["extra"] = True
    elif boundary == "manifest_root":
        body["expected_population"]["reference"] = "foreign-population"
    new_raw = encoded(body)
    material, _ = artifact(
        new_raw,
        role=None,
        product=capture.source_product,
        root="f" * 64 if boundary == "typed_root" else capture.typed_content_hash,
        page=capture.source_page_index,
        serializer=capture.serializer_id,
    )
    if boundary == "capture_id":
        material["capture_id"] = "f" * 64
    with pytest.raises(ValueError, match=error):
        validate_registry_capture(
            NativeCaptureCommitment.model_validate(material), new_raw, page, manifest, [], []
        )
