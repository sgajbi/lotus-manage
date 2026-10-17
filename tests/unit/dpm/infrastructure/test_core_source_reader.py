"""Actual httpx synthetic transport proves retained traversal before source assembly."""

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime

import httpx
import pytest

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.native_source_custody import native_role_set_digest
from src.core.composite_eligibility.policy import MonthlyPolicyScope
from src.core.composite_eligibility.source import MonthlyEligibilitySourceRequest
from src.infrastructure.composites.core_financial_configuration import (
    CoreFinancialConfiguration,
    CoreReaderConfiguration,
)
from src.infrastructure.composites.core_financial_sources import CoreMonthlyEligibilitySource
from src.infrastructure.composites.core_source_reader import CoreHttpRetainedReader
from tests.unit.dpm.composites.test_native_source_custody import owner_root, owner_domain_digest
from tests.unit.dpm.infrastructure.test_core_source_decoder import FIXED_VECTORS

NOW = "2026-10-16T00:00:00Z"
ROLES = ["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def typed(value, key=""):
    if isinstance(value, dict):
        return {k: typed(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [typed(v) for v in value]
    if value is None:
        return None
    if key in {"effective_from", "effective_to", "business_date", "coverage_from", "coverage_to"}:
        return {"date": value}
    if key in {"observed_at", "generated_at"}:
        return {"datetime": datetime.fromisoformat(value).astimezone(UTC).isoformat()}
    if key in {"settled", "encumbered", "available", "amount"}:
        return {"decimal": value}
    return value


def fact_hash(fact, family):
    return digest(
        {
            "contract": "PortfolioFinancialSourceObservations:v1",
            "family": family,
            "observation": typed(fact),
        }
    )


def export_hash(result):
    evidence = deepcopy(result["source_evidence"])
    evidence.pop("selection_digest", None)
    pages = evidence.pop("pages")
    for page in pages:
        page["source_metadata"]["page"].pop("next_page_token", None)
    return digest(
        {
            "identity_version": "analytics-export-selection-v1",
            "rows": result["data"],
            "source_evidence": evidence,
            "pages": pages,
        }
    )


def fixture_products(portfolio, large=False):
    decoded = [json.loads(base64.b64decode(v["bytes_base64"])) for v in FIXED_VECTORS]
    cash, flow, valuation = [w["payload"] for w in decoded]
    for payload in (cash, flow):
        payload["receipt"]["tenant_id"] = "tenant"
    cash["fact"]["envelope"].update(tenant_id="tenant", portfolio_id=portfolio)
    cash["content_hash"] = cash["observation_id"] = fact_hash(cash["fact"], "cash_availability")
    readiness = deepcopy(cash)
    readiness["fact"] = {
        "envelope": deepcopy(cash["fact"]["envelope"]),
        "funded": False,
        "invested": None,
    }
    readiness["content_hash"] = readiness["observation_id"] = fact_hash(
        readiness["fact"], "funding_investment"
    )
    readiness["receipt"].update(
        endpoint="/ingest/portfolio-funding-investment-observations",
        entity_type="portfolio_funding_investment_observation",
        job_id="ready-receipt",
    )
    flow["cut"].update(tenant_id="tenant", portfolio_id=portfolio)
    event = flow["events"][0]
    event["fact"]["envelope"].update(tenant_id="tenant", portfolio_id=portfolio)
    event["receipt"]["tenant_id"] = "tenant"
    root = digest(
        {"contract": "PortfolioFlowEventObservation:v1", "observation": typed(event["fact"])}
    )
    flow["cut"]["event_pins"][0].update(observation_id=root, content_hash=root)
    flow_root = digest({"contract": "PortfolioFlowSourceCut:v1", "cut": typed(flow["cut"])})
    values = []
    for role, day, start in (
        ("PRIOR_ASSETS", "2024-12-31", "2024-12-30"),
        ("MONTH_END_ASSETS", "2025-01-31", "2025-01-30"),
    ):
        payload = deepcopy(valuation)
        job = portfolio + "-" + role
        payload["receipt"].update(job_id=job, portfolio_id=portfolio, result_row_count=2)
        payload["request"].update(portfolio_id=portfolio)
        scope = payload["request"]["portfolio_timeseries_request"]
        scope.update(window={"start_date": start, "end_date": day}, as_of_date=day)
        result = payload["result"]
        result.update(
            job_id=job,
            result_row_count=2,
            data=[
                {"valuation_date": start, "eod_market_value": "90.00"},
                {"valuation_date": day, "eod_market_value": "100.00"},
            ],
        )
        if large and role == "PRIOR_ASSETS":
            result["data"][0]["source_note"] = "α" * 100000
        page = result["source_evidence"]["pages"][0]
        page["requested_scope"] = deepcopy(scope)
        page["source_metadata"].update(
            tenant_id="tenant", portfolio_id=portfolio, resolved_window=deepcopy(scope["window"])
        )
        result["source_evidence"]["pages"] = [deepcopy(page), deepcopy(page)]
        result["source_evidence"]["pages"][0]["source_metadata"]["page"]["next_page_token"] = (
            "native-original-token"
        )
        result["source_evidence"]["pages"][1]["page_number"] = 2
        root = export_hash(result)
        result["source_evidence"]["selection_digest"] = "sha256:" + root
        selector = {
            "kind": "VALUATION",
            "as_of_date": day,
            "from_date": start,
            "to_date": day,
            "reporting_currency": "USD",
            "consumer_system": "lotus-manage",
            "export_job_id": job,
            "export_content_hash": root,
            "refresh_of_job_id": None,
        }
        values.append(
            (
                role,
                payload,
                selector,
                root,
                job,
                job,
                "portfolio-timeseries-export:retained-json:v1",
                2,
            )
        )
    for role, payload in (("CASH", cash), ("READINESS", readiness)):
        env = payload["fact"]["envelope"]
        selector = {
            "kind": role,
            "as_of_date": "2025-01-31",
            "producer_id": env["producer_id"],
            "source_record_id": env["source_record_id"],
            "observation_id": payload["content_hash"],
            "content_hash": payload["content_hash"],
            "source_cut_id": env["source_cut_id"],
            "source_version": 1,
        }
        serializer = (
            "portfolio-cash-availability:domain-json:v1"
            if role == "CASH"
            else "portfolio-funding-investment:domain-json:v1"
        )
        values.append(
            (
                role,
                payload,
                selector,
                payload["content_hash"],
                payload["receipt"]["job_id"],
                "1",
                serializer,
                1,
            )
        )
    selector = {
        "kind": "FLOWS",
        "source_system": "producer",
        "source_cut_id": "flow-cut",
        "cut_revision": 1,
        "manifest_hash": flow_root,
        "from_date": "2025-01-01",
        "to_date": "2025-01-31",
        "currency": "USD",
    }
    values.append(
        (
            "FLOWS",
            flow,
            selector,
            flow_root,
            "cut-receipt",
            "1",
            "portfolio-flow-source-cut:domain-json:v1",
            1,
        )
    )
    return values


def set_product_definition(payload, definition):
    """Rebind flow event pins too, so foreign families remain internally valid."""
    if "fact" in payload:
        payload["fact"]["envelope"]["definition_version"] = definition
        return
    payload["cut"]["definition_version"] = definition
    for name, pin_name in (("events", "event_pins"), ("dependencies", "dependency_pins")):
        for value, pin in zip(payload[name], payload["cut"][pin_name], strict=True):
            value["fact"]["envelope"]["definition_version"] = definition
            root = digest(
                {
                    "contract": "PortfolioFlowEventObservation:v1",
                    "observation": typed(value["fact"]),
                }
            )
            pin.update(content_hash=root, observation_id=root)


def artifact(
    raw,
    *,
    role,
    product,
    root,
    selector=None,
    job="terminal",
    revision="1",
    page=0,
    serializer,
    portfolio=None,
    count=None,
):
    selector_root = digest(selector) if selector else None
    acquired = role is not None
    raw_hash = hashlib.sha256(raw).hexdigest()
    identity = (
        {
            "contract": "NativeSourceCaptureRequest:v1",
            "tenant": "tenant",
            "portfolio": portfolio,
            "product": product,
            "version": "v1",
            "selector": selector_root,
            "content": root,
            "receipt": job,
            "revision": revision,
            "page_index": page,
        }
        if acquired
        else {
            "contract": "NeutralIngressSourceCapture:v1",
            "tenant_id": "tenant",
            "product_name": product,
            "source_system": "producer",
            "registry_scope_id": "scope",
            "source_cut_id": "registry",
            "revision": 1,
            "source_page_index": page,
            "raw_hash": raw_hash,
        }
    )
    valuation = role in ROLES[:2]
    commitment = {
        "capture_id": digest(identity),
        "role": role,
        "source_page_index": page,
        "source_product": product,
        "product_version": "v1",
        "selector_hash": selector_root,
        "typed_content_hash": root,
        "raw_hash": raw_hash,
        "byte_count": len(raw),
        "segment_count": (len(raw) + 524287) // 524288,
        "serializer_id": serializer,
        "schema_version": "v1",
        "mime_type": "application/json",
        "source_context": {
            "capture_origin": "ACQUIRED_NATIVE_DTO" if acquired else "INGRESS_JSON",
            "captured_at": NOW,
            "snapshot_epoch": "7" if valuation else None,
            "request_scope": "actual-scope" if valuation else None,
            "receipt_job_id": job,
            "source_revision": revision,
            "selector_json": encoded(selector).decode() if selector else None,
            "export_job_id": job if valuation else None,
            "refresh_of_job_id": None,
            "returned_count": count,
            "total_count": count,
            "next_page_token": None,
        },
        "original_supplier_digest": None,
        "original_supplier_reference": None,
    }
    segments = []
    for index in range(commitment["segment_count"]):
        chunk = raw[index * 524288 : (index + 1) * 524288]
        segments.append(
            {
                **deepcopy(commitment),
                "row_kind": "CAPTURE_SEGMENT",
                "segment_index": index,
                "segment_hash": hashlib.sha256(chunk).hexdigest(),
                "bytes_base64": base64.b64encode(chunk).decode(),
            }
        )
    return commitment, segments


def fixture():
    ids = ["P1", "P2", "P3"]
    identity = {
        "tenant_id": "tenant",
        "source_system": "producer",
        "scope_id": "scope",
        "source_cut_id": "registry",
        "revision": 1,
        "definition_version": "v1",
        "coverage_from": "2025-01-01",
        "coverage_to": "2025-01-31",
        "calendar": "TEST",
        "observed_at": NOW,
        "generated_at": NOW,
        "predecessor_hash": None,
        "expected_head_hash": None,
    }
    members, member_roots = [], []
    for portfolio in ids:
        member = {
            "source_member_id": "source-" + portfolio,
            "provider_namespace": "native",
            "core_portfolio_id": portfolio,
            "member_revision": 1,
            "declarations": [
                {
                    "effective_from": "2025-01-01",
                    "effective_to": None,
                    "definition_version": "v1",
                    "provenance_reference": "fixture",
                    "currency": "USD",
                    "discretionary": True,
                    "included": True,
                }
            ],
        }
        material = deepcopy(member)
        material["declarations"][0]["effective_from"] = {"date": "2025-01-01"}
        root = digest({"contract": "PortfolioHistoricalRegistryMember:v1", "member": material})
        members.append(
            {"row_kind": "REGISTRY_MEMBER", "member": member, "member_content_hash": root}
        )
        member_roots.append(root)
    chunkroot = digest({"contract": "PortfolioHistoricalRegistryChunk:v1", "members": member_roots})
    manifest = {
        "identity": identity,
        "expected_population": {
            "reference": "independent-population",
            "definition_version": "v1",
            "count": 3,
            "content_hash": "e" * 64,
        },
        "declared_coverage": "COMPLETE",
        "supplied_count": 3,
        "members_root": owner_root("PortfolioHistoricalRegistryMembers:v1", member_roots),
        "chunk_count": 1,
        "chunks_root": owner_root("PortfolioHistoricalRegistryChunks:v1", [chunkroot]),
    }
    registry_root = owner_domain_digest("PortfolioHistoricalRegistry:v1", "cut", manifest)
    body = deepcopy(manifest)
    body.pop("identity")
    flattened = {k: v for k, v in identity.items() if k not in {"tenant_id", "scope_id"}}
    flattened["registry_scope_id"] = "scope"
    headerbody = {**flattened, **body}
    chunkbody = {
        "source_system": "producer",
        "registry_scope_id": "scope",
        "source_cut_id": "registry",
        "revision": 1,
        "chunk_index": 0,
        "members": [m["member"] for m in members],
        "typed_content_hash": chunkroot,
    }
    registry_captures, registry_segments = [], []
    for page, rawbody, root, tag in (
        (0, headerbody, registry_root, "portfolio-historical-registry-cut:ingress-json:v1"),
        (1, chunkbody, chunkroot, "portfolio-historical-registry-chunk:ingress-json:v1"),
    ):
        commitment, segments = artifact(
            encoded(rawbody),
            role=None,
            product="PortfolioHistoricalRegistry",
            root=root,
            page=page,
            serializer=tag,
        )
        registry_captures.append(commitment)
        registry_segments.extend(segments)
    records = {
        (None, "CUT"): [
            {
                "row_kind": "REGISTRY_CUT",
                "manifest": manifest,
                "receipt_job_id": "terminal",
                "received_at": NOW,
                "completed_at": NOW,
            }
        ],
        (None, "MEMBERS"): members,
        (None, "CAPTURES"): registry_segments,
    }
    roots = {None: registry_root}
    inputs = []
    for portfolio in ids:
        values = fixture_products(portfolio, large=portfolio == "P1")
        selections, captures, segments = [], [], []
        for role, payload, selector, root, job, revision, serializer, count in values:
            selection = {
                "role": role,
                "product_name": payload["product_name"],
                "product_version": "v1",
                "selector": selector,
                "selector_hash": digest(selector),
                "content_hash": root,
                "receipt_job_id": job,
                "source_revision": revision,
            }
            selections.append(selection)
            commitment, parts = artifact(
                encoded({"serializer": serializer, "payload": payload}),
                role=role,
                product=payload["product_name"],
                root=root,
                selector=selector,
                job=job,
                revision=revision,
                serializer=serializer,
                portfolio=portfolio,
                count=count,
            )
            captures.append(commitment)
            segments.extend(parts)
        declaration = {
            "portfolio_id": portfolio,
            "currency": "USD",
            "prior_date": "2024-12-31",
            "month_end_date": "2025-01-31",
            "registry_root": registry_root,
            "member_revision": 1,
            "selections": selections,
            "settled_unencumbered": {
                "amount": "0.00",
                "currency": "USD",
                "business_date": "2025-01-31",
                "semantic_definition": "explicit-settled-unencumbered-v1",
                "producer_revision": "1",
            },
            "compatibility": None,
        }
        financial_identity = {**identity, "source_cut_id": "financial"}
        graph = {**deepcopy(declaration), "identity": financial_identity}
        for selection in graph["selections"]:
            selection.pop("selector")
        inputroot = digest(
            {"contract": "PortfolioFinancialSourceCutInput:v1", "selection": declaration}
        )
        graphroot = owner_domain_digest("PortfolioFinancialSourceCut:v1", "cut", graph)
        inputs.append(
            {
                "row_kind": "FINANCIAL_INPUT",
                "declaration": declaration,
                "input_content_hash": inputroot,
                "graph": graph,
                "graph_content_hash": graphroot,
            }
        )
        records[(portfolio, "INPUTS")] = [inputs[-1]]
        records[(portfolio, "CAPTURES")] = segments
    batch = {
        "identity": {**identity, "source_cut_id": "financial"},
        "selection_count": 3,
        "selections_root": owner_root(
            "PortfolioFinancialSourceCutInputs:v1", [i["input_content_hash"] for i in inputs]
        ),
        "chunk_count": 1,
        "chunks_root": "c" * 64,
    }
    financial_root = owner_domain_digest(
        "PortfolioFinancialSourceCutManifest:v1", "manifest", batch
    )
    for portfolio in ids:
        roots[portfolio] = financial_root
        records[(portfolio, "CUT")] = [
            {
                "row_kind": "FINANCIAL_CUT",
                "manifest": batch,
                "receipt_job_id": "terminal",
                "received_at": NOW,
                "completed_at": NOW,
            }
        ]

    def address(cut, root):
        return {
            "source_system": "producer",
            "registry_scope_id": "scope",
            "source_cut_id": cut,
            "revision": 1,
            "content_hash": "sha256:" + root,
        }

    config = CoreFinancialConfiguration.model_validate_json(
        encoded(
            {
                "tenant_id": "tenant",
                "composite_id": "composite",
                "definition_version": "v1",
                "strategy_code": "strategy",
                "month": "2025-01",
                "reporting_currency": "USD",
                "registry": address("registry", registry_root),
                "observation_cut_id": "normalized-cut",
                "observation_revision": "1",
                "members": [
                    {
                        "portfolio_id": p,
                        "provider_namespace": "native",
                        "source_member_id": "source-" + p,
                        "provider_id": "native-provider",
                        "financial_cut": address("financial", financial_root),
                    }
                    for p in ids
                ],
            }
        )
    )
    return config, records, roots


def rebind_financial_groups(config, records, roots, groups, *, committed=None, count_offset=0):
    """Produce exact pinned test batches without changing selected DTO/decoder validation."""
    document = config.model_dump(mode="json")
    bindings = {m["portfolio_id"]: m for m in document["members"]}
    for index, ids in enumerate(groups):
        cut = "financial-group-" + str(index)
        batch = deepcopy(records[(ids[0], "CUT")][0]["manifest"])
        batch["identity"]["source_cut_id"] = cut
        hashes = (
            committed[index]
            if committed is not None
            else [records[(pid, "INPUTS")][0]["input_content_hash"] for pid in ids]
        )
        batch.update(
            selection_count=len(hashes) + count_offset,
            selections_root=owner_root("PortfolioFinancialSourceCutInputs:v1", hashes),
        )
        root = owner_domain_digest("PortfolioFinancialSourceCutManifest:v1", "manifest", batch)
        for pid in ids:
            records[(pid, "CUT")][0]["manifest"] = deepcopy(batch)
            row = records[(pid, "INPUTS")][0]
            row["graph"]["identity"] = deepcopy(batch["identity"])
            row["graph_content_hash"] = owner_domain_digest(
                "PortfolioFinancialSourceCut:v1", "cut", row["graph"]
            )
            roots[pid] = root
            bindings[pid]["financial_cut"].update(source_cut_id=cut, content_hash="sha256:" + root)
    return CoreFinancialConfiguration.model_validate_json(encoded(document))


def response(request, records, roots):
    body = json.loads(request.content)
    portfolio, view = body.get("portfolio_id"), body["view"]
    rows = records[(portfolio, view)]
    offset = int(body["page"]["page_token"] or "0")
    size = min(body["page"]["page_size"], 2)
    page_rows = deepcopy(rows[offset : offset + size])
    if view == "CAPTURES":
        items = [
            digest(
                {
                    "contract": "PortfolioNeutralSourceCaptureArtifact:v1",
                    **{
                        k: v
                        for k, v in row.items()
                        if k not in {"row_kind", "segment_index", "segment_hash", "bytes_base64"}
                    },
                }
            )
            for row in rows
            if row["segment_index"] == 0
        ]
        kind, ordering, domain = (
            "CAPTURE_ARTIFACTS",
            "role,source_page_index,capture_id,segment_index",
            "PortfolioNeutralSourceCaptureArtifacts:v1",
        )
    elif view == "MEMBERS":
        items = [r["member_content_hash"] for r in rows]
        kind, ordering, domain = (
            "REGISTRY_MEMBERS",
            "provider_namespace,source_member_id",
            "PortfolioHistoricalRegistryMembers:v1",
        )
    elif view == "INPUTS":
        items = [r["input_content_hash"] for r in rows]
        kind, ordering, domain = (
            "SELECTED_FINANCIAL_INPUTS",
            "selected_portfolio",
            "PortfolioFinancialSourceCutInputs:v1",
        )
    else:
        items = [roots[portfolio]]
        kind, ordering, domain = "CUT_HEADERS", "single_cut", "NeutralSourceCutHeaders:v1"
    return {
        "product_name": "PortfolioHistoricalRegistry"
        if portfolio is None
        else "PortfolioFinancialSourceCut",
        "product_version": "v1",
        "tenant_id": "tenant",
        "generated_at": NOW,
        "as_of_date": "2025-01-31",
        "restatement_version": "R1",
        "reconciliation_status": "UNQUALIFIED",
        "data_quality_status": "COMPLETE",
        "latest_evidence_timestamp": None,
        "source_cut_id": body["source_cut_id"],
        "source_batch_fingerprint": None,
        "snapshot_id": None,
        "content_hash": "sha256:" + roots[portfolio],
        "source_digest": "sha256:" + roots[portfolio],
        "source_refs": [],
        "source_lineage": {},
        "degradation": {"status": "NONE", "reason_codes": [], "details": []},
        "source_evidence_current": True,
        "freshness_status": "CURRENT",
        "policy_version": None,
        "correlation_id": None,
        "source_address": {
            k: body[k] for k in ("source_system", "registry_scope_id", "source_cut_id", "revision")
        },
        "batch_manifest_hash": roots[portfolio],
        "portfolio_id": portfolio,
        "view": view,
        "receipt_job_id": "terminal",
        "received_at": NOW,
        "completed_at": NOW,
        "qualification": "UNQUALIFIED",
        "population_verification": "UNVERIFIED",
        "compatibility_posture": "UNAVAILABLE",
        "authoritative_use_available": False,
        "pagination": {
            "total_count": len(rows),
            "returned_count": len(page_rows),
            "next_page_token": str(offset + size) if offset + size < len(rows) else None,
            "ordered_set_hash": owner_root(domain, items),
            "root_item_count": len(items),
            "root_kind": kind,
            "ordering": ordering,
        },
        "rows": page_rows,
    }


class SyntheticReaderAuth(httpx.Auth):
    """Only injected-client transport evidence; this supplies no enterprise IAM signature."""

    def auth_flow(self, request):
        assert "Authorization" not in request.headers
        request.headers["X-Synthetic-Reader-Auth"] = "injected-test-auth"
        yield request


def make_reader(
    monkeypatch,
    mutate=None,
    *,
    authentication_mode="bearer",
    auth=None,
    default_headers=None,
    fixture_data=None,
):
    config, records, roots = fixture_data or fixture()
    calls = []
    monkeypatch.setenv("CORE_READER_TEST_TOKEN", "synthetic-only")

    def transport(request):
        body = json.loads(request.content)
        calls.append(body)
        if authentication_mode == "bearer":
            assert request.headers["authorization"] == "Bearer synthetic-only"
        else:
            assert "Authorization" not in request.headers
            assert request.headers["X-Synthetic-Reader-Auth"] == "injected-test-auth"
            assert "synthetic-only" not in str(request.headers)
        assert "tenant_id" not in body and "endpoint" not in body and "credential" not in body
        result = response(request, records, roots)
        if mutate:
            transport_response = mutate(result, body)
            if isinstance(transport_response, httpx.Response):
                return transport_response
        return httpx.Response(200, json=result)

    client = httpx.Client(
        transport=httpx.MockTransport(transport), auth=auth, headers=default_headers
    )
    reader = CoreHttpRetainedReader(
        CoreReaderConfiguration(
            tenant_id="tenant",
            endpoint="https://core.example",
            credential_env="CORE_READER_TEST_TOKEN",
            authentication_mode=authentication_mode,
            page_size=2,
        ),
        client,
        members=config.members,
    )
    return config, reader, calls


def source_request(config, observations):
    return MonthlyEligibilitySourceRequest(
        scope=MonthlyPolicyScope(
            tenant_id=config.tenant_id,
            composite_id=config.composite_id,
            definition_version=config.definition_version,
            strategy_code=config.strategy_code,
        ),
        month=config.month,
        reporting_currency=config.reporting_currency,
        source_cut_id=config.observation_cut_id,
        owner_service="lotus-manage",
        expected_source_revision=config.observation_revision,
        expected_content_hash=hash_canonical_payload(observations.model_dump(mode="json")),
        expected_portfolio_ids=tuple(m.portfolio_id for m in config.members),
    )


def test_real_http_retained_reader_multi_page_member_artifact_and_export(monkeypatch):
    config, reader, calls = make_reader(monkeypatch)
    registry = reader.registry(tenant_id="tenant", address=config.registry)
    assert len(registry.members) == 3
    retained = reader.portfolio(
        tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
    )
    assert retained.observations.prior_month_end_assets == "100.00"
    assert retained.observations.settled_unencumbered_cash == "0.00"
    assert retained.observations.funded is False and retained.observations.invested is None
    assert retained.observations.flows[0].amount == "-10.00"
    assert retained.observations.flows[0].received_at == "2026-10-16T00:00:00.000000Z"
    captures = retained.native_custody.captures
    assert len(captures) == 5 and sum(c.segment_count for c in captures) == 6
    assert max(c.byte_count for c in captures) > 524288
    assert any(c["page"]["page_token"] is not None for c in calls)
    assert all("synthetic-only" not in c.model_dump_json() for c in captures)


@pytest.mark.parametrize("role", ["CASH", "READINESS", "FLOWS"])
@pytest.mark.parametrize("definition", ["v1", "foreign-definition"])
def test_reader_product_definition_matches_graph_after_complete_rehash(
    monkeypatch, role, definition
):
    original_products = fixture_products

    def products(portfolio, large=False):
        values = original_products(portfolio, large)
        for index, value in enumerate(values):
            family, payload, selector, root, job, revision, serializer, count = value
            if family != role:
                continue
            set_product_definition(payload, definition)
            if role == "FLOWS":
                root = digest(
                    {"contract": "PortfolioFlowSourceCut:v1", "cut": typed(payload["cut"])}
                )
                selector["manifest_hash"] = root
            else:
                root = fact_hash(
                    payload["fact"], "cash_availability" if role == "CASH" else "funding_investment"
                )
                payload["content_hash"] = payload["observation_id"] = root
                selector.update(content_hash=root, observation_id=root)
            values[index] = (family, payload, selector, root, job, revision, serializer, count)
        return values

    monkeypatch.setattr(__name__ + ".fixture_products", products)
    config, reader, calls = make_reader(monkeypatch)
    if definition == "v1":
        retained = reader.portfolio(
            tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
        )
        assert retained.native_custody.graph.identity.definition_version == definition
        assert retained.observations.settled_unencumbered_cash == "0.00"
        assert retained.observations.funded is False
        assert retained.observations.flows[0].amount == "-10.00"
        assert len(retained.native_custody.captures) == 5
    else:
        error = "FLOW_SELECTION_SCOPE" if role == "FLOWS" else "FACT_SCOPE"
        with pytest.raises(ValueError, match=error):
            reader.portfolio(
                tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
            )
    assert {call["view"] for call in calls} == {"CUT", "INPUTS", "CAPTURES"}


def test_enterprise_auth_mode_preserves_full_retained_custody_without_any_bearer(monkeypatch):
    config, bearer, bearer_calls = make_reader(monkeypatch)
    _, enterprise, enterprise_calls = make_reader(
        monkeypatch, authentication_mode="core_enterprise_hmac_v1", auth=SyntheticReaderAuth()
    )
    assert enterprise.client is not bearer.client
    assert enterprise.registry(tenant_id="tenant", address=config.registry) == bearer.registry(
        tenant_id="tenant", address=config.registry
    )
    for member in config.members:
        observed = enterprise.portfolio(
            tenant_id="tenant", portfolio_id=member.portfolio_id, address=member.financial_cut
        )
        assert observed == bearer.portfolio(
            tenant_id="tenant", portfolio_id=member.portfolio_id, address=member.financial_cut
        )
        assert len(observed.native_custody.captures) == 5
        assert "synthetic-only" not in observed.model_dump_json()
    assert enterprise_calls == bearer_calls
    assert len(enterprise_calls) > 15
    assert any(call["page"]["page_token"] for call in enterprise_calls)


@pytest.mark.parametrize("credential", [None, "", "   "])
@pytest.mark.parametrize("with_auth", [False, True])
def test_enterprise_missing_real_credential_or_client_auth_is_unavailable_before_io(
    monkeypatch, credential, with_auth
):
    config, reader, calls = make_reader(
        monkeypatch,
        authentication_mode="core_enterprise_hmac_v1",
        auth=SyntheticReaderAuth() if with_auth else None,
    )
    if credential is None:
        monkeypatch.delenv("CORE_READER_TEST_TOKEN")
    else:
        monkeypatch.setenv("CORE_READER_TEST_TOKEN", credential)
    assert reader.registry(tenant_id="tenant", address=config.registry) is None
    assert calls == []


@pytest.mark.parametrize(
    "portfolio,view",
    [(None, "MEMBERS"), (None, "CAPTURES"), ("P1", "CUT"), ("P1", "INPUTS"), ("P1", "CAPTURES")],
)
def test_retained_reader_discards_partial_resolution_when_a_required_view_is_unavailable(
    monkeypatch, portfolio, view
):
    def unavailable(result, body):
        if body.get("portfolio_id") == portfolio and body["view"] == view:
            return httpx.Response(503)

    config, reader, calls = make_reader(monkeypatch, unavailable)
    if portfolio is None:
        assert reader.registry(tenant_id="tenant", address=config.registry) is None
    else:
        assert (
            reader.portfolio(
                tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
            )
            is None
        )
    assert any(call["view"] == view for call in calls)


def test_tenant_scope_is_checked_before_any_retained_http_read(monkeypatch):
    config, reader, calls = make_reader(monkeypatch)
    with pytest.raises(ValueError, match="TENANT_CONFIG"):
        reader.registry(tenant_id="foreign", address=config.registry)
    assert calls == []


@pytest.mark.parametrize(
    "boundary", ["page_address", "aggregate_count", "cross_view_receipt", "selected_identity"]
)
def test_retained_http_rejects_valid_wire_pages_that_disagree_across_reader_scope(
    monkeypatch, boundary
):
    def mutate(result, body):
        if boundary == "page_address" and body["view"] == "CAPTURES":
            result["source_address"]["revision"] = 2
        elif boundary == "aggregate_count" and body["view"] == "MEMBERS":
            result["pagination"]["total_count"] = 2
        elif boundary == "cross_view_receipt" and body["view"] == "MEMBERS":
            result["compatibility_posture"] = "DECLARED_UNVERIFIED"
        elif boundary == "selected_identity" and body["view"] == "INPUTS":
            row = result["rows"][0]
            row["graph"]["identity"]["calendar"] = "FOREIGN_CALENDAR"
            row["graph_content_hash"] = owner_domain_digest(
                "PortfolioFinancialSourceCut:v1", "cut", row["graph"]
            )

    config, reader, _ = make_reader(monkeypatch, mutate)
    error = {
        "page_address": "PAGE_ADDRESS",
        "aggregate_count": "ROW_COUNT",
        "cross_view_receipt": "CROSS_VIEW_RECEIPT",
        "selected_identity": "SELECTED_INPUT",
    }[boundary]
    with pytest.raises(ValueError, match=error):
        if boundary == "selected_identity":
            reader.portfolio(
                tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
            )
        else:
            reader.registry(tenant_id="tenant", address=config.registry)


@pytest.mark.parametrize(
    "boundary", ["first_segment_absent", "last_segment_absent", "whole_raw_digest"]
)
def test_reader_reconstructs_entire_artifact_before_decoding_or_accepting_partial_bytes(
    monkeypatch, boundary
):
    config, records, roots = fixture()
    captures = records[("P1", "CAPTURES")]
    assert captures[0]["segment_count"] == 2
    if boundary == "first_segment_absent":
        records[("P1", "CAPTURES")] = captures[1:]
        error = "ARTIFACT_SEQUENCE"
    elif boundary == "last_segment_absent":
        records[("P1", "CAPTURES")] = [captures[0], *captures[2:]]
        error = "ARTIFACT_INCOMPLETE"
    else:
        for row in captures[:2]:
            row["raw_hash"] = "f" * 64
        error = "ARTIFACT_RAW"
    _, reader, _ = make_reader(monkeypatch, fixture_data=(config, records, roots))
    with pytest.raises(ValueError, match=error):
        reader.portfolio(
            tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
        )


def test_reader_requires_explicit_registry_member_enrollment_after_custody_verification(
    monkeypatch,
):
    config, reader, _ = make_reader(monkeypatch)
    reader.members = config.members[1:]
    with pytest.raises(ValueError, match="MEMBER_MAPPING"):
        reader.registry(tenant_id="tenant", address=config.registry)


@pytest.mark.parametrize("boundary", ["ambiguous_date", "numeric_amount", "unknown_amount"])
def test_reader_projects_only_an_unambiguous_exact_asset_fact_after_native_decode(
    monkeypatch, boundary
):
    from tests.unit.dpm.infrastructure.test_core_source_decoder import rebound_native_product

    def change(payload):
        rows = payload["result"]["data"]
        if boundary == "ambiguous_date":
            rows[0]["valuation_date"] = rows[1]["valuation_date"]
        else:
            rows[1]["eod_market_value"] = 100 if boundary == "numeric_amount" else None

    capture, raw, selected = rebound_native_product("PRIOR_ASSETS", change)
    config, records, roots = fixture()
    selection = selected.declaration.selections[0]
    _, parts = artifact(
        raw,
        role=capture.role,
        product=capture.source_product,
        root=capture.typed_content_hash,
        selector=selection.selector.model_dump(mode="json"),
        job=capture.source_context.receipt_job_id,
        revision=capture.source_context.source_revision,
        serializer=capture.serializer_id,
        portfolio="P1",
        count=capture.source_context.total_count,
    )
    records[("P1", "INPUTS")] = [selected.model_dump(mode="json")]
    records[("P1", "CAPTURES")] = parts + [
        row for row in records[("P1", "CAPTURES")] if row["role"] != "PRIOR_ASSETS"
    ]
    _, reader, _ = make_reader(monkeypatch, fixture_data=(config, records, roots))
    if boundary == "unknown_amount":
        retained = reader.portfolio(
            tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
        )
        assert retained.observations.prior_month_end_assets is None
        assert retained.observations.month_end_assets == "100.00"
    else:
        with pytest.raises(
            ValueError,
            match="VALUATION_DATE_AMBIGUOUS"
            if boundary == "ambiguous_date"
            else "ASSET_EXACT_TEXT",
        ):
            reader.portfolio(
                tenant_id="tenant", portfolio_id="P1", address=config.members[0].financial_cut
            )


def test_enterprise_missing_client_auth_never_uses_configured_credential_as_bearer(monkeypatch):
    config, reader, calls = make_reader(monkeypatch, authentication_mode="core_enterprise_hmac_v1")
    assert reader.registry(tenant_id="tenant", address=config.registry) is None
    assert calls == []


@pytest.mark.parametrize("value", ["Bearer forbidden", "Basic forbidden", ""])
@pytest.mark.parametrize("with_auth", [False, True])
def test_enterprise_refuses_client_default_authorization_before_io(monkeypatch, value, with_auth):
    config, reader, calls = make_reader(
        monkeypatch,
        authentication_mode="core_enterprise_hmac_v1",
        auth=SyntheticReaderAuth() if with_auth else None,
        default_headers={"aUtHoRiZaTiOn": value},
    )
    with pytest.raises(ValueError, match="^CORE_READER_AUTHORIZATION_HEADER_FORBIDDEN$"):
        reader.registry(tenant_id="tenant", address=config.registry)
    assert calls == []
    assert reader.client.headers["Authorization"] == value


@pytest.mark.parametrize("construction", ["copy", "construct"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("authentication_mode", "unrecognized-mode"),
        ("authentication_mode", None),
        ("credential_env", ""),
        ("endpoint", "http://untrusted.example"),
    ],
)
def test_copied_or_constructed_reader_configuration_refuses_before_io(
    monkeypatch, construction, field, value
):
    config, reader, calls = make_reader(monkeypatch)
    if construction == "copy":
        reader.configuration = reader.configuration.model_copy(update={field: value})
    else:
        document = reader.configuration.model_dump()
        document[field] = value
        reader.configuration = CoreReaderConfiguration.model_construct(**document)
    with pytest.raises(ValueError, match="^CORE_READER_CONFIGURATION_INVALID$"):
        reader.registry(tenant_id="tenant", address=config.registry)
    assert calls == []


@pytest.mark.parametrize(
    "failure",
    [
        "address",
        "tenant",
        "receipt",
        "root",
        "token",
        "drop",
        "duplicate",
        "reorder",
        "member",
        "context",
        "segment",
        "portfolio",
    ],
)
def test_http_refusals_before_normalization(monkeypatch, failure):
    def mutate(result, body):
        if failure == "address":
            result["source_address"]["revision"] = 2
        elif failure == "tenant":
            result["tenant_id"] = "foreign"
        elif failure == "receipt" and body["page"]["page_token"]:
            result["receipt_job_id"] = "mixed"
        elif failure == "root":
            result["pagination"]["ordered_set_hash"] = "f" * 64
        elif failure == "token" and body["page"]["page_token"]:
            result["pagination"]["next_page_token"] = body["page"]["page_token"]
        elif failure == "drop" and body["view"] == "MEMBERS":
            result["rows"] = result["rows"][:1]
            result["pagination"]["returned_count"] = len(result["rows"])
        elif failure == "duplicate" and body["view"] == "MEMBERS" and len(result["rows"]) == 2:
            result["rows"][1] = deepcopy(result["rows"][0])
        elif failure == "reorder" and body["view"] == "MEMBERS":
            result["rows"].reverse()
        elif failure == "member" and body["view"] == "MEMBERS":
            result["rows"][0]["member"]["core_portfolio_id"] = "foreign"
        elif failure == "context" and body["view"] == "CAPTURES":
            result["rows"][0]["source_context"]["snapshot_epoch"] = "invented"
        elif failure == "segment" and body["view"] == "CAPTURES":
            result["rows"][0]["segment_hash"] = "f" * 64
        elif failure == "portfolio":
            result["portfolio_id"] = "foreign"

    config, reader, _ = make_reader(monkeypatch, mutate)
    with pytest.raises(ValueError):
        reader.registry(tenant_id="tenant", address=config.registry)


def test_native_v2_assembly_preserves_all_members_and_five_role_roots(monkeypatch):
    config, reader, _ = make_reader(monkeypatch)
    # Exact expected source facts are independent from the assembly's role hashes.
    from src.core.composite_eligibility.observations import MonthlyEligibilityObservations

    registry = reader.registry(tenant_id="tenant", address=config.registry)
    portfolios = [
        reader.portfolio(
            tenant_id="tenant", portfolio_id=m.portfolio_id, address=m.financial_cut
        ).observations.model_copy(update={"discretionary": True})
        for m in config.members
    ]
    expected = MonthlyEligibilityObservations(
        product_name="CompositeMonthlyEligibilityObservations",
        product_version="v1",
        evidence_class="SOURCE_UNVERIFIED",
        tenant_id="tenant",
        composite_id="composite",
        definition_version="v1",
        month="2025-01",
        source_cut_id="normalized-cut",
        source_revision="1",
        reporting_currency="USD",
        source_generated_at=registry.generated_at,
        expected_portfolio_ids=["P1", "P2", "P3"],
        portfolios=portfolios,
    )
    source = CoreMonthlyEligibilitySource(config, reader)
    assembly = source.assemble(source_request(config, expected))
    assert assembly.product_version == "v2"
    assert assembly.observations == expected
    assert [p.portfolio_id for p in assembly.native_custody.portfolios] == ["P1", "P2", "P3"]
    assert [b.kind for b in assembly.inputs] == sorted(ROLES)
    for binding in assembly.inputs:
        assert binding.evidence.digest == native_role_set_digest(
            assembly.native_custody, binding.kind
        )
    assert assembly.compatibility_posture == "SOURCE_UNVERIFIED"


def test_missing_reader_configuration_or_credentials_is_unavailable(monkeypatch):
    config, reader, calls = make_reader(monkeypatch)
    monkeypatch.delenv("CORE_READER_TEST_TOKEN")
    assert reader.registry(tenant_id="tenant", address=config.registry) is None
    assert calls == []
    reader.configuration = None
    assert reader.registry(tenant_id="tenant", address=config.registry) is None


@pytest.mark.parametrize(
    "failure", ["redirect", "duplicate_json", "oversize", "compression", "unavailable"]
)
def test_actual_bounded_transport_refuses_unusable_responses(monkeypatch, failure):
    config, records, roots = fixture()
    monkeypatch.setenv("CORE_READER_TEST_TOKEN", "synthetic-only")
    calls = []

    def transport(request):
        calls.append(request)
        if failure == "redirect":
            return httpx.Response(307, headers={"Location": "https://foreign.example"})
        if failure == "unavailable":
            return httpx.Response(503)
        payload = encoded(response(request, records, roots))
        if failure == "duplicate_json":
            payload = payload.replace(
                b'"tenant_id":"tenant"', b'"tenant_id":"tenant","tenant_id":"foreign"', 1
            )
        return httpx.Response(
            200,
            stream=httpx.ByteStream(payload),
            headers={"content-encoding": "gzip"} if failure == "compression" else {},
        )

    client = httpx.Client(transport=httpx.MockTransport(transport))
    reader = CoreHttpRetainedReader(
        CoreReaderConfiguration(
            tenant_id="tenant",
            endpoint="https://core.example",
            credential_env="CORE_READER_TEST_TOKEN",
            maximum_response_bytes=1024 if failure == "oversize" else 2000000,
        ),
        client,
        members=config.members,
    )
    if failure == "unavailable":
        assert reader.registry(tenant_id="tenant", address=config.registry) is None
    else:
        with pytest.raises(ValueError):
            reader.registry(tenant_id="tenant", address=config.registry)
    assert len(calls) == 1


def test_bad_raw_source_never_calls_the_paired_verifier(monkeypatch):
    def mutate(result, body):
        if body["view"] == "CAPTURES":
            result["rows"][0]["segment_hash"] = "f" * 64

    config, reader, _ = make_reader(monkeypatch, mutate)
    calls = []

    class Verifier:
        def verify_with_proof(self, request):
            calls.append(request)
            return None

    from src.core.composite_eligibility.observations import MonthlyEligibilityObservations

    expected = MonthlyEligibilityObservations(
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
    source = CoreMonthlyEligibilitySource(
        config, reader, verifier=Verifier(), controlled_synthetic=True
    )
    with pytest.raises(ValueError, match="CORE_READER_SEGMENT_HASH_OR_BASE64"):
        source.resolve(source_request(config, expected))
    assert calls == []
