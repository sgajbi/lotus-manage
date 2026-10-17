"""Closed read wire and four independently published read-root domains."""

import json
from copy import deepcopy

import httpx
import pytest

from src.core.composite_eligibility.native_source_custody import native_ordered_root
from src.infrastructure.composites.core_source_wire import ReadResponse, SegmentRow
from src.infrastructure.composites.core_source_wire import (
    WireInput,
    WireMember,
    closed_json,
    utc_text,
)
from tests.unit.dpm.infrastructure.test_core_source_reader import encoded, fixture, response
from tests.unit.dpm.infrastructure.test_core_source_reader import digest


@pytest.mark.parametrize(
    "domain,empty,one",
    [
        (
            "NeutralSourceCutHeaders:v1",
            "5ff7ff1990ce3e35590aadb304d03ad5912832d2394b80cf378dff321f35d706",
            "7e7b5fb16c96bb10ab9555b580fc3a625522220e4982baef04d0bc95d94f3a4e",
        ),
        (
            "PortfolioHistoricalRegistryMembers:v1",
            "1f170cc6ad2a8d93447670608183c3aa9c06d9b44b5ece794542cda793317096",
            "42c115d1936776870eec30bf6a462fb66d9d395c6db926df550ab5292f4d15bd",
        ),
        (
            "PortfolioFinancialSourceCutInputs:v1",
            "9b2c1afb73504e69ec2430e863eae1b066c881d8440f585097ec656f64089f65",
            "28e7280783d3a619108c22eaaa08396b72ca91f0a26e4582a2d200a1936221a7",
        ),
        (
            "PortfolioNeutralSourceCaptureArtifacts:v1",
            "c770e5490f4a6106b4652bd2fea398a280fd8ff4fb9c3c1fcb18bfd909ac9c76",
            "7ce002690531e89a0701cecea93eece0983ff6e35978ed25723122143fd51bf0",
        ),
    ],
)
def test_owner_fixed_read_root_vectors(domain, empty, one):
    assert native_ordered_root(domain, []) == empty
    assert native_ordered_root(domain, ["a" * 64]) == one


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown",
        "unknown_member",
        "bool_revision",
        "wrong_manifest",
        "wrong_receipt",
        "naive_time",
        "wrong_graph",
        "unknown_selector",
        "extra_pagination",
    ],
)
def test_closed_response_and_native_binding_refusals(mutation):
    config, records, roots = fixture()
    body = {
        **config.registry.model_dump(mode="json", exclude={"content_hash"}),
        "content_hash": roots[None],
        "view": "CUT",
        "page": {"page_size": 2, "page_token": None},
    }
    if mutation in {"wrong_graph", "unknown_selector"}:
        body.update(portfolio_id="P1", source_cut_id="financial", view="INPUTS")
    if mutation == "unknown_member":
        body["view"] = "MEMBERS"
    payload = response(httpx.Request("POST", "https://core.example", json=body), records, roots)
    if mutation == "unknown":
        payload["guessed"] = True
    elif mutation == "unknown_member":
        payload["rows"][0]["member"]["guessed"] = True
    elif mutation == "bool_revision":
        payload["source_address"]["revision"] = True
    elif mutation == "wrong_manifest":
        payload["rows"][0]["manifest"]["supplied_count"] = 2
    elif mutation == "wrong_receipt":
        payload["rows"][0]["receipt_job_id"] = "other"
    elif mutation == "naive_time":
        payload["generated_at"] = "2026-10-16T00:00:00"
    elif mutation == "wrong_graph":
        payload["rows"][0]["graph"]["portfolio_id"] = "P2"
    elif mutation == "unknown_selector":
        payload["rows"][0]["declaration"]["selections"][0]["selector"]["kind"] = "VALUATION_V2"
    else:
        payload["pagination"]["view"] = "CUT"
    with pytest.raises(ValueError):
        ReadResponse.model_validate_json(encoded(payload))


@pytest.mark.parametrize(
    "mutation", ["raw", "stride", "index", "count", "base64", "context", "schema"]
)
def test_native_segment_and_commitment_refusals(mutation):
    _, records, _ = fixture()
    row = deepcopy(records[("P1", "CAPTURES")][0])
    if mutation == "raw":
        row["segment_hash"] = "f" * 64
    elif mutation == "stride":
        row["byte_count"] += 524288
    elif mutation == "index":
        row["segment_index"] = 1
    elif mutation == "count":
        row["segment_count"] += 1
    elif mutation == "base64":
        row["bytes_base64"] += "="
    elif mutation == "context":
        row["source_context"]["snapshot_epoch"] = None
    else:
        row["source_context"]["unknown"] = "extra"
    with pytest.raises(ValueError):
        SegmentRow.model_validate_json(json.dumps(row))


@pytest.mark.parametrize("boundary", ["empty_interval", "overlap", "open_predecessor"])
def test_registry_member_rejects_non_half_open_history(boundary):
    _, records, _ = fixture()
    member = deepcopy(records[(None, "MEMBERS")][0]["member"])
    assert WireMember.model_validate_json(encoded(member)).declarations[0].included
    first = member["declarations"][0]
    if boundary == "empty_interval":
        first["effective_to"] = first["effective_from"]
    else:
        second = {**first, "effective_from": "2025-01-15"}
        if boundary == "overlap":
            first["effective_to"] = "2025-01-16"
        member["declarations"].append(second)
    with pytest.raises(ValueError, match="MEMBER_INTERVAL"):
        WireMember.model_validate_json(encoded(member))


@pytest.mark.parametrize(
    "boundary",
    [
        "selector_window",
        "selector_export_pair",
        "selector_hash",
        "role_order",
        "valuation_currency",
        "cash_date",
        "flow_date",
    ],
)
def test_input_declaration_rejects_selector_scope_even_with_rebound_selector_hash(boundary):
    _, records, _ = fixture()
    declaration = deepcopy(records[("P1", "INPUTS")][0]["declaration"])
    assert WireInput.model_validate_json(encoded(declaration)).portfolio_id == "P1"
    selection = declaration["selections"][0]
    error = "ROLE_SCOPE"
    if boundary == "selector_window":
        selection["selector"]["from_date"] = "2025-01-01"
        error = "VALUATION_SELECTOR"
    elif boundary == "selector_export_pair":
        selection["selector"]["export_content_hash"] = None
        error = "VALUATION_SELECTOR"
    elif boundary == "selector_hash":
        selection["selector_hash"] = "f" * 64
        error = "SELECTOR_HASH"
    elif boundary == "role_order":
        declaration["selections"].reverse()
        error = "ROLE_ORDER"
    elif boundary == "valuation_currency":
        selection["selector"]["reporting_currency"] = "SGD"
    elif boundary == "cash_date":
        selection = declaration["selections"][2]
        selection["selector"]["as_of_date"] = "2025-01-30"
    else:
        selection = declaration["selections"][4]
        selection["selector"]["to_date"] = "2025-01-30"
    if boundary != "selector_hash":
        selection["selector_hash"] = digest(selection["selector"])
    with pytest.raises(ValueError, match=error):
        WireInput.model_validate_json(encoded(declaration))


@pytest.mark.parametrize(
    "boundary", ["digest", "header_absent", "receipt_clock", "graph_portfolio"]
)
def test_response_envelope_binds_complete_header_clock_and_selected_portfolio(boundary):
    config, records, roots = fixture()
    body = {
        **config.registry.model_dump(mode="json", exclude={"content_hash"}),
        "view": "CUT",
        "page": {"page_size": 2, "page_token": None},
    }
    if boundary == "graph_portfolio":
        body.update(portfolio_id="P1", source_cut_id="financial", view="INPUTS")
    payload = response(httpx.Request("POST", "https://core.example", json=body), records, roots)
    assert ReadResponse.model_validate_json(encoded(payload)).view == body["view"]
    if boundary == "digest":
        payload["source_digest"] = "sha256:" + "f" * 64
        error = "ENVELOPE_BINDING"
    elif boundary == "header_absent":
        payload["rows"] = []
        payload["pagination"].update(returned_count=0, total_count=0)
        error = "HEADER_REQUIRED"
    elif boundary == "receipt_clock":
        payload["received_at"] = "2027-01-01T00:00:00Z"
        error = "RECEIPT_CHRONOLOGY"
    else:
        payload["portfolio_id"] = "P2"
        error = "GRAPH_PORTFOLIO"
    with pytest.raises(ValueError, match=error):
        ReadResponse.model_validate_json(encoded(payload))


def test_json_depth_and_naive_receipt_time_have_explicit_refusals():
    with pytest.raises(ValueError, match="JSON_DEPTH"):
        closed_json("[" * 10000 + "0" + "]" * 10000)
    with pytest.raises(ValueError, match="AWARE_TIME_REQUIRED"):
        utc_text("2025-01-01T00:00:00")
    assert closed_json('{"cash":null}') == {"cash": None}
    assert utc_text("2025-01-01T08:00:00+08:00") == "2025-01-01T00:00:00.000000Z"
