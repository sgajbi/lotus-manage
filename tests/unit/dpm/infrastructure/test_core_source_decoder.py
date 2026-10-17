"""Frozen producer-owned bytes and roots; generated source fixtures never enroll trust."""

import base64
import hashlib
import json
from copy import deepcopy

import pytest

from src.infrastructure.composites.core_source_products import native_typed_root
from src.infrastructure.composites.core_source_wire import closed_json

# Core #1227 catalog a6bbdfdfe714b62f005fb0db1d75503dbfa66b27cd67915fcf34f70b4495d258.
FIXED_VECTORS = json.loads(
    r"""[{"serializer_id":"portfolio-cash-availability:domain-json:v1","schema_version":"v1","typed_root":"0b19b6e4708fc39113ff88985cbd0a4ddeb3944139d05e4d8f6e9d53ed971d48","raw_sha256":"b22121e814cc22c2dacdadd54159d327e08bb4a3cb8c297d5e0f97e7026daa22","bytes_base64":"eyJwYXlsb2FkIjp7ImNvbnRlbnRfaGFzaCI6IjBiMTliNmU0NzA4ZmMzOTExM2ZmODg5ODVjYmQwYTRkZGViMzk0NDEzOWQwNWU0ZDhmNmU5ZDUzZWQ5NzFkNDgiLCJmYWN0Ijp7ImF2YWlsYWJsZSI6bnVsbCwiY3VycmVuY3kiOiJVU0QiLCJlbmN1bWJlcmVkIjpudWxsLCJlbnZlbG9wZSI6eyJjb3ZlcmFnZSI6ImNvbXBsZXRlIiwiY292ZXJhZ2Vfc2NvcGUiOiJkZWNsYXJlZC1zY29wZSIsImRlZmluaXRpb25fdmVyc2lvbiI6InYxIiwiZWZmZWN0aXZlX2Zyb20iOiIyMDI1LTAxLTAxIiwiZWZmZWN0aXZlX3RvIjpudWxsLCJleHBlY3RlZF9oZWFkX2hhc2giOm51bGwsImdlbmVyYXRlZF9hdCI6IjIwMjYtMTAtMTZUMDA6MDA6MDBaIiwib2JzZXJ2ZWRfYXQiOiIyMDI2LTEwLTE2VDAwOjAwOjAwWiIsInBvcnRmb2xpb19pZCI6InBvcnRmb2xpbyIsInByZWRlY2Vzc29yX2lkIjpudWxsLCJwcm9kdWNlcl9pZCI6InByb2R1Y2VyIiwic291cmNlX2N1dF9pZCI6ImN1dCIsInNvdXJjZV9yZWNvcmRfaWQiOiJyZWNvcmQiLCJzb3VyY2VfcmV2aXNpb24iOjEsInRlbmFudF9pZCI6InRlbmFudCJ9LCJzZXR0bGVkIjoiMC4wMCJ9LCJvYnNlcnZhdGlvbl9pZCI6IjBiMTliNmU0NzA4ZmMzOTExM2ZmODg5ODVjYmQwYTRkZGViMzk0NDEzOWQwNWU0ZDhmNmU5ZDUzZWQ5NzFkNDgiLCJwcm9kdWN0X25hbWUiOiJQb3J0Zm9saW9GaW5hbmNpYWxTb3VyY2VPYnNlcnZhdGlvbnMiLCJwcm9kdWN0X3ZlcnNpb24iOiJ2MSIsInJlY2VpcHQiOnsiYWNjZXB0ZWRfY291bnQiOjEsImNvbXBsZXRlZF9hdCI6IjIwMjYtMTAtMTZUMDA6MDA6MDArMDA6MDAiLCJlbmRwb2ludCI6Ii9pbmdlc3QvcG9ydGZvbGlvLWNhc2gtYXZhaWxhYmlsaXR5LW9ic2VydmF0aW9ucyIsImVudGl0eV90eXBlIjoicG9ydGZvbGlvX2Nhc2hfYXZhaWxhYmlsaXR5X29ic2VydmF0aW9uIiwiam9iX2lkIjoicmVjZWlwdCIsInN0YXR1cyI6ImNvbXBsZXRlZCIsInRlbmFudF9pZCI6InRlbmFudCJ9LCJyZWNlaXZlZF9hdCI6IjIwMjYtMTAtMTZUMDA6MDA6MDArMDA6MDAifSwic2VyaWFsaXplciI6InBvcnRmb2xpby1jYXNoLWF2YWlsYWJpbGl0eTpkb21haW4tanNvbjp2MSJ9"},{"serializer_id":"portfolio-flow-source-cut:domain-json:v1","schema_version":"v1","typed_root":"ae7cf233e1dc231ef4a23796c1d1df812b1e3f3ae557473599bd0d3f79b5797a","raw_sha256":"795eb18580f26783feab8a1bad4130b8595c5bbc6f3d2123cec4a4dfe90e552b","bytes_base64":"eyJwYXlsb2FkIjp7ImN1dCI6eyJjb3ZlcmFnZSI6ImNvbXBsZXRlIiwiY292ZXJhZ2VfZnJvbSI6IjIwMjUtMDEtMDEiLCJjb3ZlcmFnZV90byI6IjIwMjUtMDEtMzEiLCJjdXJyZW5jeSI6IlVTRCIsImN1dF9yZXZpc2lvbiI6MSwiZGVmaW5pdGlvbl92ZXJzaW9uIjoidjEiLCJkZXBlbmRlbmN5X3BpbnMiOltdLCJldmVudF9waW5zIjpbeyJjb250ZW50X2hhc2giOiIyZDk4YTE4YjdhYWZkMmM4MDI5ODczZDA1MmRmMDc0ZDRhNzgxZmM3ZjMyYzFiZmI4MTgwNGMwODYyOWQxOWU4IiwiZmxvd19zb3VyY2VfcmVjb3JkX3JldmlzaW9uIjoxLCJvYnNlcnZhdGlvbl9pZCI6IjJkOThhMThiN2FhZmQyYzgwMjk4NzNkMDUyZGYwNzRkNGE3ODFmYzdmMzJjMWJmYjgxODA0YzA4NjI5ZDE5ZTgiLCJzb3VyY2VfcmVjb3JkX2lkIjoicmVjb3JkIn1dLCJleHBlY3RlZF9oZWFkX2hhc2giOm51bGwsInBvcnRmb2xpb19pZCI6InBvcnRmb2xpbyIsInByZWRlY2Vzc29yX2N1dF9oYXNoIjpudWxsLCJzb3VyY2VfY3V0X2lkIjoiZmxvdy1jdXQiLCJzb3VyY2Vfc3lzdGVtIjoicHJvZHVjZXIiLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQifSwiZGVwZW5kZW5jaWVzIjpbXSwiZXZlbnRzIjpbeyJmYWN0Ijp7ImFtb3VudCI6Ii0xMC4wMCIsImJ1c2luZXNzX2RhdGUiOiIyMDI1LTAxLTMxIiwiY2xhc3NpZmljYXRpb24iOiJFWFRFUk5BTF9DQVNIIiwiY3VycmVuY3kiOiJVU0QiLCJlY29ub21pY19ldmVudF9pZCI6bnVsbCwiZW52ZWxvcGUiOnsiY292ZXJhZ2UiOiJjb21wbGV0ZSIsImNvdmVyYWdlX3Njb3BlIjoiZGVjbGFyZWQtc2NvcGUiLCJkZWZpbml0aW9uX3ZlcnNpb24iOiJ2MSIsImVmZmVjdGl2ZV9mcm9tIjoiMjAyNS0wMS0wMSIsImVmZmVjdGl2ZV90byI6bnVsbCwiZXhwZWN0ZWRfaGVhZF9oYXNoIjpudWxsLCJnZW5lcmF0ZWRfYXQiOiIyMDI2LTEwLTE2VDAwOjAwOjAwWiIsIm9ic2VydmVkX2F0IjoiMjAyNi0xMC0xNlQwMDowMDowMFoiLCJwb3J0Zm9saW9faWQiOiJwb3J0Zm9saW8iLCJwcmVkZWNlc3Nvcl9pZCI6bnVsbCwicHJvZHVjZXJfaWQiOiJwcm9kdWNlciIsInNvdXJjZV9jdXRfaWQiOiJjdXQiLCJzb3VyY2VfcmVjb3JkX2lkIjoicmVjb3JkIiwic291cmNlX3JldmlzaW9uIjoxLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQifSwicG9zdGluZ19zdGF0ZSI6IlBPU1RFRCIsInJldmVyc2FsX3N0YXRlIjoiTk9ORSIsInJldmVyc2FsX3RhcmdldCI6bnVsbCwicmV2ZXJzZXNfc291cmNlX3JlY29yZF9pZCI6bnVsbCwidHJhbnNhY3Rpb25faWQiOm51bGx9LCJyZWNlaXB0Ijp7ImFjY2VwdGVkX2NvdW50IjoxLCJjb21wbGV0ZWRfYXQiOiIyMDI2LTEwLTE2VDAwOjAwOjAwKzAwOjAwIiwiZW5kcG9pbnQiOiIvaW5nZXN0L3BvcnRmb2xpby1mbG93LWV2ZW50LW9ic2VydmF0aW9ucyIsImVudGl0eV90eXBlIjoicG9ydGZvbGlvX2Zsb3dfZXZlbnRfb2JzZXJ2YXRpb24iLCJqb2JfaWQiOiJldmVudC1yZWNlaXB0Iiwic3RhdHVzIjoiY29tcGxldGVkIiwidGVuYW50X2lkIjoidGVuYW50In0sInJlY2VpdmVkX2F0IjoiMjAyNi0xMC0xNlQwMDowMDowMCswMDowMCJ9XSwicHJvZHVjdF9uYW1lIjoiUG9ydGZvbGlvRmluYW5jaWFsRmxvd09ic2VydmF0aW9ucyIsInByb2R1Y3RfdmVyc2lvbiI6InYxIiwicmVjZWlwdCI6eyJhY2NlcHRlZF9jb3VudCI6MSwiY29tcGxldGVkX2F0IjoiMjAyNi0xMC0xNlQwMDowMDowMCswMDowMCIsImVuZHBvaW50IjoiL2luZ2VzdC9wb3J0Zm9saW8tZmxvdy1zb3VyY2UtY3V0cyIsImVudGl0eV90eXBlIjoicG9ydGZvbGlvX2Zsb3dfc291cmNlX2N1dCIsImpvYl9pZCI6ImN1dC1yZWNlaXB0Iiwic3RhdHVzIjoiY29tcGxldGVkIiwidGVuYW50X2lkIjoidGVuYW50In0sInJlY2VpdmVkX2F0IjoiMjAyNi0xMC0xNlQwMDowMDowMCswMDowMCJ9LCJzZXJpYWxpemVyIjoicG9ydGZvbGlvLWZsb3ctc291cmNlLWN1dDpkb21haW4tanNvbjp2MSJ9"},{"serializer_id":"portfolio-timeseries-export:retained-json:v1","schema_version":"v1","typed_root":"19190e048d9a398e271229a5bcd0bc09ab772c49f0938f401c92fbb409d7fb25","raw_sha256":"fb715b6a491cfca4954c819c92e0864da7e8d909cc3526a28061abc6cfcc6a3c","bytes_base64":"eyJwYXlsb2FkIjp7InByb2R1Y3RfbmFtZSI6IlBvcnRmb2xpb1RpbWVzZXJpZXNJbnB1dCIsInByb2R1Y3RfdmVyc2lvbiI6InYxIiwicmVjZWlwdCI6eyJjb21wbGV0ZWRfYXQiOiIyMDI2LTEwLTE2VDAwOjAwOjAwKzAwOjAwIiwiZGF0YXNldF90eXBlIjoicG9ydGZvbGlvX3RpbWVzZXJpZXMiLCJqb2JfaWQiOiJleHBvcnQiLCJwb3J0Zm9saW9faWQiOiJwb3J0Zm9saW8iLCJyZXN1bHRfcm93X2NvdW50IjoxLCJzdGF0dXMiOiJjb21wbGV0ZWQifSwicmVxdWVzdCI6eyJkYXRhc2V0X3R5cGUiOiJwb3J0Zm9saW9fdGltZXNlcmllcyIsInBvcnRmb2xpb19pZCI6InBvcnRmb2xpbyIsInBvcnRmb2xpb190aW1lc2VyaWVzX3JlcXVlc3QiOnsiYXNfb2ZfZGF0ZSI6IjIwMjUtMDEtMzEiLCJjb25zdW1lcl9zeXN0ZW0iOiJsb3R1cy1tYW5hZ2UiLCJwZXJpb2QiOm51bGwsInJlcG9ydGluZ19jdXJyZW5jeSI6IlVTRCIsIndpbmRvdyI6eyJlbmRfZGF0ZSI6IjIwMjUtMDEtMzEiLCJzdGFydF9kYXRlIjoiMjAyNS0wMS0zMSJ9fX0sInJlc3VsdCI6eyJkYXRhIjpbeyJlb2RfbWFya2V0X3ZhbHVlIjoiMTAwLjAwIiwidmFsdWF0aW9uX2RhdGUiOiIyMDI1LTAxLTMxIn1dLCJkYXRhc2V0X3R5cGUiOiJwb3J0Zm9saW9fdGltZXNlcmllcyIsImpvYl9pZCI6ImV4cG9ydCIsInJlc3VsdF9yb3dfY291bnQiOjEsInNvdXJjZV9ldmlkZW5jZSI6eyJhdmFpbGFiaWxpdHkiOiJSRVRBSU5FRCIsInBhZ2VzIjpbeyJwYWdlX251bWJlciI6MSwicmVxdWVzdGVkX3Njb3BlIjp7ImFzX29mX2RhdGUiOiIyMDI1LTAxLTMxIiwiY29uc3VtZXJfc3lzdGVtIjoibG90dXMtbWFuYWdlIiwicGVyaW9kIjpudWxsLCJyZXBvcnRpbmdfY3VycmVuY3kiOiJVU0QiLCJ3aW5kb3ciOnsiZW5kX2RhdGUiOiIyMDI1LTAxLTMxIiwic3RhcnRfZGF0ZSI6IjIwMjUtMDEtMzEifX0sInJvd19jb3VudCI6MSwic291cmNlX21ldGFkYXRhIjp7ImRhdGFfcXVhbGl0eV9zdGF0dXMiOiJDT01QTEVURSIsImZyZXNobmVzc19zdGF0dXMiOiJDVVJSRU5UIiwicGFnZSI6eyJuZXh0X3BhZ2VfdG9rZW4iOm51bGwsInJlcXVlc3Rfc2NvcGVfZmluZ2VycHJpbnQiOiJhY3R1YWwtc2NvcGUiLCJyZXR1cm5lZF9yb3dfY291bnQiOjEsInNuYXBzaG90X2Vwb2NoIjo3fSwicG9ydGZvbGlvX2lkIjoicG9ydGZvbGlvIiwicmVwb3J0aW5nX2N1cnJlbmN5IjoiVVNEIiwicmVzb2x2ZWRfd2luZG93Ijp7ImVuZF9kYXRlIjoiMjAyNS0wMS0zMSIsInN0YXJ0X2RhdGUiOiIyMDI1LTAxLTMxIn0sInNvdXJjZV9ldmlkZW5jZV9jdXJyZW50Ijp0cnVlLCJ0ZW5hbnRfaWQiOiJ0ZW5hbnQifX1dLCJzZWxlY3Rpb25fZGlnZXN0Ijoic2hhMjU2OjE5MTkwZTA0OGQ5YTM5OGUyNzEyMjlhNWJjZDBiYzA5YWI3NzJjNDlmMDkzOGY0MDFjOTJmYmI0MDlkN2ZiMjUifX19LCJzZXJpYWxpemVyIjoicG9ydGZvbGlvLXRpbWVzZXJpZXMtZXhwb3J0OnJldGFpbmVkLWpzb246djEifQ=="}]"""
)


@pytest.mark.parametrize("vector", FIXED_VECTORS)
def test_producer_owned_catalog_vectors(vector):
    raw = base64.b64decode(vector["bytes_base64"], validate=True)
    assert hashlib.sha256(raw).hexdigest() == vector["raw_sha256"]
    wrapper = closed_json(raw)
    assert wrapper["serializer"] == vector["serializer_id"]
    assert native_typed_root(vector["serializer_id"], wrapper["payload"]) == vector["typed_root"]


@pytest.mark.parametrize("vector", FIXED_VECTORS)
def test_product_root_substitution_refuses(vector):
    payload = deepcopy(closed_json(base64.b64decode(vector["bytes_base64"]))["payload"])
    if "fact" in payload:
        payload["fact"]["settled"] = "0.0"
    elif "cut" in payload:
        payload["events"][0]["fact"]["amount"] = "-10.0"
    else:
        payload["result"]["data"][0]["eod_market_value"] = "100.0"
    with pytest.raises(ValueError):
        native_typed_root(vector["serializer_id"], payload)


def test_unknown_native_serializer_refuses():
    with pytest.raises(ValueError, match="SERIALIZER_UNSUPPORTED"):
        native_typed_root("cash:guessed:v2", {})


@pytest.mark.parametrize("raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'])
def test_closed_raw_json_refuses_ambiguity(raw):
    with pytest.raises(ValueError):
        closed_json(raw)


@pytest.mark.parametrize(
    "mutation",
    [
        "serializer",
        "schema",
        "mime",
        "selection",
        "root",
        "epoch",
        "scope",
        "count",
        "page",
        "raw",
        "wrapper",
        "payload",
        "canonical",
    ],
)
def test_native_decoder_refuses_substitution_before_any_source_result(mutation):
    from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
    from src.infrastructure.composites.core_source_decoder import decode_native
    from src.infrastructure.composites.core_source_wire import InputRow
    from tests.unit.dpm.infrastructure.test_core_source_reader import fixture, encoded

    _, records, _ = fixture()
    parts = records[("P1", "CAPTURES")][:2]
    material = {
        k: v
        for k, v in parts[0].items()
        if k not in {"row_kind", "segment_index", "segment_hash", "bytes_base64"}
    }
    raw = b"".join(base64.b64decode(part["bytes_base64"]) for part in parts)
    selected = InputRow.model_validate_json(encoded(records[("P1", "INPUTS")][0]))
    if mutation == "serializer":
        material["serializer_id"] = "guessed:v2"
    elif mutation == "schema":
        material["schema_version"] = "v2"
    elif mutation == "mime":
        material["mime_type"] = "application/x-ndjson"
    elif mutation == "selection":
        material["source_context"]["selector_json"] = "{}"
    elif mutation == "root":
        material["typed_content_hash"] = "f" * 64
    elif mutation == "epoch":
        material["source_context"]["snapshot_epoch"] = "8"
    elif mutation == "scope":
        material["source_context"]["request_scope"] = "mixed"
    elif mutation == "count":
        material["source_context"]["total_count"] = 3
    elif mutation == "page":
        material["source_page_index"] = 1
    elif mutation == "raw":
        raw = raw[:-1] + b" "
    else:
        wrapper = json.loads(raw)
        if mutation == "wrapper":
            wrapper["serializer"] = "wrong:v1"
        elif mutation == "payload":
            wrapper["payload"]["extra"] = True
        raw = (
            encoded(wrapper) if mutation != "canonical" else json.dumps(wrapper, indent=2).encode()
        )
        material.update(
            raw_hash=hashlib.sha256(raw).hexdigest(),
            byte_count=len(raw),
            segment_count=(len(raw) + 524287) // 524288,
        )
    capture = NativeCaptureCommitment.model_validate(material)
    with pytest.raises(ValueError):
        decode_native(capture, raw, selected)


def rebound_native_product(role, mutate_payload=None, *, declared_root=None):
    """Rebind test-owned source hashes, retaining real public DTO/decoder validation."""
    from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
    from src.infrastructure.composites.core_source_wire import InputRow
    from tests.unit.dpm.infrastructure.test_core_source_reader import (
        artifact,
        digest,
        encoded,
        export_hash,
        fact_hash,
        fixture,
        fixture_products,
        typed,
    )
    from tests.unit.dpm.composites.test_native_source_custody import owner_domain_digest

    value = next(value for value in fixture_products("P1") if value[0] == role)
    _, payload, selector, root, job, revision, serializer, count = value
    if mutate_payload:
        mutate_payload(payload)
    if role in ("CASH", "READINESS"):
        root = fact_hash(
            payload["fact"], "cash_availability" if role == "CASH" else "funding_investment"
        )
        payload["content_hash"] = payload["observation_id"] = root
        selector.update(content_hash=root, observation_id=root)
    elif role == "FLOWS":
        root = digest({"contract": "PortfolioFlowSourceCut:v1", "cut": typed(payload["cut"])})
        selector["manifest_hash"] = root
    else:
        root = export_hash(payload["result"])
        payload["result"]["source_evidence"]["selection_digest"] = "sha256:" + root
        selector["export_content_hash"] = root
    root = declared_root or root
    _, records, _ = fixture()
    selected = deepcopy(records[("P1", "INPUTS")][0])
    selection = next(s for s in selected["declaration"]["selections"] if s["role"] == role)
    selection.update(content_hash=root, selector=selector, selector_hash=digest(selector))
    graph = selected["graph"]
    graph["selections"] = [
        {k: v for k, v in item.items() if k != "selector"}
        for item in selected["declaration"]["selections"]
    ]
    selected["graph_content_hash"] = owner_domain_digest(
        "PortfolioFinancialSourceCut:v1", "cut", graph
    )
    selected["input_content_hash"] = digest(
        {"contract": "PortfolioFinancialSourceCutInput:v1", "selection": selected["declaration"]}
    )
    raw = encoded({"serializer": serializer, "payload": payload})
    commitment, _ = artifact(
        raw,
        role=role,
        product=payload["product_name"],
        root=root,
        selector=selector,
        job=job,
        revision=revision,
        serializer=serializer,
        portfolio="P1",
        count=count,
    )
    return (
        NativeCaptureCommitment.model_validate(commitment),
        raw,
        InputRow.model_validate_json(encoded(selected)),
    )


@pytest.mark.parametrize("role", ["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"])
def test_rebound_product_fixture_has_valid_independent_hashes_and_public_decoder_control(role):
    from src.infrastructure.composites.core_source_decoder import decode_native

    capture, raw, selected = rebound_native_product(role)
    result = decode_native(capture, raw, selected)
    assert result.selection.role == role
    assert result.payload["product_name"] == capture.source_product


@pytest.mark.parametrize("role", ["CASH", "READINESS", "FLOWS"])
@pytest.mark.parametrize("definition", ["v1", "foreign-definition"])
def test_decoder_product_definition_matches_graph_after_rehash(role, definition):
    from src.infrastructure.composites.core_source_decoder import decode_native
    from tests.unit.dpm.infrastructure.test_core_source_reader import set_product_definition

    capture, raw, selected = rebound_native_product(
        role, lambda payload: set_product_definition(payload, definition)
    )
    assert selected.graph.identity.definition_version == "v1"
    if definition == "v1":
        assert decode_native(capture, raw, selected).selection.role == role
    else:
        error = "FLOW_SELECTION_SCOPE" if role == "FLOWS" else "FACT_SCOPE"
        with pytest.raises(ValueError, match=error):
            decode_native(capture, raw, selected)


@pytest.mark.parametrize(
    "boundary",
    [
        "receipt_shape",
        "fact_scope",
        "cash_currency",
        "flow_scope",
        "typed_root",
        "fact_context",
        "role",
    ],
)
def test_decoder_refuses_semantic_substitution_after_valid_content_rebinding(boundary):
    from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
    from src.infrastructure.composites.core_source_decoder import decode_native

    role = "FLOWS" if boundary == "flow_scope" else "CASH"

    def change(payload):
        if boundary == "receipt_shape":
            payload["receipt"]["completed_at"] = None
        elif boundary == "fact_scope":
            payload["fact"]["envelope"]["tenant_id"] = "foreign"
        elif boundary == "cash_currency":
            payload["fact"]["currency"] = "SGD"
        elif boundary == "flow_scope":
            payload["cut"]["source_cut_id"] = "foreign-cut"

    capture, raw, selected = rebound_native_product(
        role, change, declared_root="f" * 64 if boundary == "typed_root" else None
    )
    if boundary in ("fact_context", "role"):
        material = capture.model_dump(mode="json")
        if boundary == "fact_context":
            material["source_context"]["request_scope"] = "unrelated-export-scope"
        else:
            material.update(role=None, selector_hash=None)
            material["source_context"]["capture_origin"] = "INGRESS_JSON"
        capture = NativeCaptureCommitment.model_validate(material)
    error = {
        "receipt_shape": "NATIVE_PAYLOAD_INVALID",
        "fact_scope": "FACT_SCOPE",
        "cash_currency": "CASH_CURRENCY",
        "flow_scope": "FLOW_SELECTION_SCOPE",
        "typed_root": "NATIVE_TYPED_ROOT",
        "fact_context": "FACT_CONTEXT_MUST_BE_NULL",
        "role": "NATIVE_ROLE",
    }[boundary]
    with pytest.raises(ValueError, match=error):
        decode_native(capture, raw, selected)
