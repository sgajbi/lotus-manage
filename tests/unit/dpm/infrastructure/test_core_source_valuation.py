"""Original export pagination, actual epoch and request provenance refusals."""

from copy import deepcopy
import base64
import hashlib
import json

import httpx
import pytest

from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
from src.infrastructure.composites.core_source_valuation import validate_valuation
from src.infrastructure.composites.core_source_decoder import decode_native
from src.infrastructure.composites.core_source_products import native_typed_root
from src.infrastructure.composites.core_financial_configuration import CoreReaderConfiguration
from src.infrastructure.composites.core_financial_sources import CoreMonthlyEligibilitySource
from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
from src.infrastructure.composites.core_source_wire import InputRow
from tests.unit.dpm.infrastructure.test_core_source_reader import (
    artifact,
    fixture,
    fixture_products,
    encoded,
    response,
    source_request,
)


def inputs():
    _, records, _ = fixture()
    selected = InputRow.model_validate_json(encoded(records[("P1", "INPUTS")][0]))
    commitment = {
        k: v
        for k, v in records[("P1", "CAPTURES")][0].items()
        if k not in {"row_kind", "segment_index", "segment_hash", "bytes_base64"}
    }
    capture = NativeCaptureCommitment.model_validate(commitment)
    payload = fixture_products("P1", large=True)[0][1]
    return payload, capture, selected.declaration.selections[0].selector, selected


def test_original_multi_page_export_is_retained_without_regeneration():
    payload, capture, selector, selected = inputs()
    original = deepcopy(payload)
    assert validate_valuation(payload, capture, selector, selected) == 2
    assert payload == original


@pytest.mark.parametrize(
    "mutation",
    [
        "epoch",
        "mixed_epoch",
        "scope",
        "tenant",
        "portfolio",
        "job",
        "capture_receipt",
        "request",
        "window",
        "gap",
        "loop",
        "missing_terminal",
        "bool_count",
        "count",
        "availability",
        "false_current",
        "integer_current",
        "period",
        "refresh",
        "naive_receipt",
    ],
)
def test_retained_export_refusals(mutation):
    payload, capture, selector, selected = inputs()
    pages = payload["result"]["source_evidence"]["pages"]
    first, last = pages
    if mutation == "epoch":
        first["source_metadata"]["page"]["snapshot_epoch"] = None
    elif mutation == "mixed_epoch":
        last["source_metadata"]["page"]["snapshot_epoch"] = 8
    elif mutation == "scope":
        first["source_metadata"]["page"]["request_scope_fingerprint"] = "other"
    elif mutation == "tenant":
        last["source_metadata"]["tenant_id"] = "foreign"
    elif mutation == "portfolio":
        last["source_metadata"]["portfolio_id"] = "P2"
    elif mutation == "job":
        payload["receipt"]["job_id"] = "other"
    elif mutation == "capture_receipt":
        context = capture.source_context.model_copy(update={"receipt_job_id": "wrong-receipt"})
        capture = capture.model_copy(update={"source_context": context})
    elif mutation == "request":
        payload["request"]["portfolio_id"] = "P2"
    elif mutation == "window":
        last["requested_scope"]["window"]["start_date"] = "2024-12-29"
    elif mutation == "gap":
        last["page_number"] = 3
    elif mutation == "loop":
        last["source_metadata"]["page"]["next_page_token"] = "native-original-token"
    elif mutation == "missing_terminal":
        payload["result"]["source_evidence"]["pages"] = [first]
    elif mutation == "bool_count":
        first["row_count"] = True
    elif mutation == "count":
        payload["result"]["result_row_count"] = 1
    elif mutation == "availability":
        payload["result"]["source_evidence"]["availability"] = "LIVE"
    elif mutation == "false_current":
        last["source_metadata"]["source_evidence_current"] = False
    elif mutation == "integer_current":
        last["source_metadata"]["source_evidence_current"] = 1
    elif mutation == "period":
        last["requested_scope"]["period"] = "YTD"
    elif mutation == "refresh":
        payload["request"]["refresh_of_job_id"] = "fabricated"
    else:
        payload["receipt"]["completed_at"] = "2026-10-16T00:00:00"
    with pytest.raises(ValueError):
        validate_valuation(payload, capture, selector, selected)


def malformed_original_request(records, nested, malformed):
    selected = InputRow.model_validate_json(encoded(records[("P1", "INPUTS")][0]))
    selection = selected.declaration.selections[0]
    rows = records[("P1", "CAPTURES")]
    original = b"".join(
        base64.b64decode(row["bytes_base64"]) for row in rows if row["role"] == "PRIOR_ASSETS"
    )
    wrapper = json.loads(original)
    if nested:
        wrapper["payload"]["request"]["portfolio_timeseries_request"] = malformed
    else:
        wrapper["payload"]["request"] = malformed
    # The request is outside this existing typed product identity. Keep the
    # selected typed root valid while regenerating every raw-byte commitment.
    serializer = rows[0]["serializer_id"]
    assert native_typed_root(serializer, wrapper["payload"]) == selection.content_hash
    raw = encoded(wrapper)
    commitment, rebuilt = artifact(
        raw,
        role="PRIOR_ASSETS",
        product=selection.product_name,
        root=selection.content_hash,
        selector=selection.selector.model_dump(mode="json"),
        job=selection.receipt_job_id,
        revision=selection.source_revision,
        serializer=serializer,
        portfolio="P1",
        count=2,
    )
    assert commitment["raw_hash"] == hashlib.sha256(raw).hexdigest()
    records[("P1", "CAPTURES")] = rebuilt + [r for r in rows if r["role"] != "PRIOR_ASSETS"]
    return selected, NativeCaptureCommitment.model_validate(commitment), raw


@pytest.mark.parametrize("nested", [False, True], ids=["request", "portfolio-timeseries-request"])
@pytest.mark.parametrize("malformed", [[], None, "invalid", 0, False])
def test_canonically_rehashed_non_object_request_refuses_without_identity_changes(
    nested, malformed
):
    _, records, _ = fixture()
    selected, capture, raw = malformed_original_request(records, nested, malformed)
    with pytest.raises(ValueError, match="^CORE_READER_EXPORT_REQUEST$"):
        decode_native(capture, raw, selected)


@pytest.mark.parametrize("nested", [False, True], ids=["request-array", "nested-request-array"])
def test_rehashed_malformed_request_refuses_through_http_before_verifier(monkeypatch, nested):
    config, records, roots = fixture()
    malformed_original_request(records, nested, [])
    requests, verification_requests = [], []
    monkeypatch.setenv("CORE_READER_F1_TEST_TOKEN", "synthetic-only-no-authority")

    def transport(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=response(request, records, roots))

    class CountingVerifier:
        def verify_with_proof(self, request):
            verification_requests.append(request)
            return None

    from src.core.composite_eligibility.observations import MonthlyEligibilityObservations

    placeholder = MonthlyEligibilityObservations(
        product_name="CompositeMonthlyEligibilityObservations",
        product_version="v1",
        evidence_class="SYNTHETIC_UNQUALIFIED",
        tenant_id="tenant",
        composite_id="composite",
        definition_version="v1",
        month="2025-01",
        source_cut_id="normalized-cut",
        source_revision="1",
        reporting_currency="USD",
        source_generated_at="2026-10-16T00:00:00.000000Z",
        expected_portfolio_ids=["P1", "P2", "P3"],
        portfolios=[],
    )
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        reader = CoreHttpRetainedReader(
            CoreReaderConfiguration(
                tenant_id="tenant",
                endpoint="https://core.example",
                credential_env="CORE_READER_F1_TEST_TOKEN",
                page_size=2,
            ),
            client,
            members=config.members,
        )
        source = CoreMonthlyEligibilitySource(
            config, reader, verifier=CountingVerifier(), controlled_synthetic=True
        )
        with pytest.raises(ValueError, match="^CORE_READER_EXPORT_REQUEST$"):
            source.resolve(source_request(config, placeholder))
    assert len(requests) == 8
    assert verification_requests == []
