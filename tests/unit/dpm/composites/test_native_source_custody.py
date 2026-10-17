"""Independent fixed native-domain, ordered-root and Manage role commitments."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.native_source_custody import (
    MonthlyNativeCustody,
    NativeCashDeclaration,
    NativeFinancialGraph,
    NativeCompatibilityDeclaration,
    NativeRegistryManifest,
    native_domain_hash,
    native_ordered_root,
    native_role_set_digest,
    require_native_observation_scope,
)
from src.core.composite_eligibility.source_assembly import NativeMonthlySourceAssembly
from tests.composite_monthly_source_helpers import assembly_material

ROLES = ["PRIOR_ASSETS", "MONTH_END_ASSETS", "CASH", "READINESS", "FLOWS"]
PRODUCTS = [
    "PortfolioTimeseriesInput",
    "PortfolioTimeseriesInput",
    "PortfolioFinancialSourceObservations",
    "PortfolioFinancialSourceObservations",
    "PortfolioFinancialFlowObservations",
]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def owner_domain_digest(contract, field, value):
    """Fixture recipe from Core: explicit known typed fields, independent of consumer code."""
    value = deepcopy(value)
    identity = value["identity"]
    for key in ("coverage_from", "coverage_to"):
        identity[key] = {"date": identity[key]}
    for key in ("observed_at", "generated_at"):
        identity[key] = {
            "datetime": datetime.fromisoformat(identity[key]).astimezone(UTC).isoformat()
        }
    if "prior_date" in value:
        for key in ("prior_date", "month_end_date"):
            value[key] = {"date": value[key]}
        cash = value["settled_unencumbered"]
        if cash is not None:
            cash["business_date"] = {"date": cash["business_date"]}
            if cash["amount"] is not None:
                cash["amount"] = {"decimal": cash["amount"]}
    return digest({"contract": contract, field: value})


def owner_root(domain, items):
    state = hashlib.sha256(domain.encode() + b"\0").digest()
    for item in items:
        state = hashlib.sha256(state + bytes.fromhex(item)).digest()
    return hashlib.sha256(state + b"\0" + str(len(items)).encode()).hexdigest()


def view(name, kind, ordering, items, domain, total=None):
    return {
        "view": name,
        "root_kind": kind,
        "ordering": ordering,
        "total_count": len(items) if total is None else total,
        "root_item_count": len(items),
        "ordered_set_hash": owner_root(domain, items),
    }


def capture_view(captures):
    return view(
        "CAPTURES",
        "CAPTURE_ARTIFACTS",
        "role,source_page_index,capture_id,segment_index",
        [digest({"contract": "PortfolioNeutralSourceCaptureArtifact:v1", **c}) for c in captures],
        "PortfolioNeutralSourceCaptureArtifacts:v1",
        sum(c["segment_count"] for c in captures),
    )


def pin_financial_group(portfolios, cut, committed=None):
    """Commit a test-owned complete population using the independent producer recipe."""
    hashes = committed if committed is not None else [p["input_content_hash"] for p in portfolios]
    manifest = deepcopy(portfolios[0]["manifest"])
    manifest["identity"]["source_cut_id"] = cut
    manifest.update(
        selection_count=len(hashes),
        selections_root=owner_root("PortfolioFinancialSourceCutInputs:v1", hashes),
    )
    root = owner_domain_digest("PortfolioFinancialSourceCutManifest:v1", "manifest", manifest)
    for portfolio in portfolios:
        portfolio["manifest"] = deepcopy(manifest)
        portfolio["locator"]["source_address"]["source_cut_id"] = cut
        portfolio["locator"]["batch_manifest_hash"] = root
        portfolio["graph"]["identity"] = deepcopy(manifest["identity"])
        portfolio["graph_content_hash"] = owner_domain_digest(
            "PortfolioFinancialSourceCut:v1", "cut", portfolio["graph"]
        )
        portfolio["view_roots"][0] = view(
            "CUT", "CUT_HEADERS", "single_cut", [root], "NeutralSourceCutHeaders:v1"
        )


def custody_material(ids=None):
    """Synthetic compact source facts only; no bytes, source acquisition or financial proof."""
    ids = ids or ["synthetic-member"]
    identity = {
        "tenant_id": "synthetic-tenant",
        "source_system": "native:fixture:α",
        "scope_id": "registry-scope",
        "source_cut_id": "registry-cut",
        "revision": 2,
        "definition_version": "synthetic-definition",
        "coverage_from": "2026-08-31",
        "coverage_to": "2026-09-30",
        "calendar": "TEST_CALENDAR",
        "observed_at": "2026-10-01T08:00:00+08:00",
        "generated_at": "2026-10-01T08:01:00+08:00",
        "predecessor_hash": "d" * 64,
        "expected_head_hash": "d" * 64,
    }
    receipt = {
        "receipt_job_id": "retained-job",
        "received_at": "2026-10-01T00:00:00Z",
        "completed_at": "2026-10-01T00:01:00Z",
        "generated_at": identity["generated_at"],
    }
    members = [
        {
            "portfolio_id": p,
            "provider_id": "native-provider",
            "provider_namespace": "native",
            "source_member_id": "source-" + p,
            "member_revision": 1,
            "member_content_hash": hashlib.sha256(p.encode()).hexdigest(),
        }
        for p in ids
    ]
    registry_manifest = {
        "identity": deepcopy(identity),
        "expected_population": {
            "reference": "independent-population",
            "definition_version": "expected-v1",
            "count": len(ids),
            "content_hash": "e" * 64,
        },
        "declared_coverage": "COMPLETE",
        "supplied_count": len(ids),
        "members_root": owner_root(
            "PortfolioHistoricalRegistryMembers:v1", [m["member_content_hash"] for m in members]
        ),
        "chunk_count": 1,
        "chunks_root": "c" * 64,
    }
    registry_hash = owner_domain_digest("PortfolioHistoricalRegistry:v1", "cut", registry_manifest)

    def locator(product, cut, root):
        return {
            "product_name": product,
            "product_version": "v1",
            "batch_manifest_hash": root,
            "source_address": {
                "source_system": identity["source_system"],
                "registry_scope_id": identity["scope_id"],
                "source_cut_id": cut,
                "revision": 2,
            },
        }

    def captured(role, product, index):
        acquired = role is not None
        return {
            "capture_id": hashlib.sha256((str(role) + str(index)).encode()).hexdigest(),
            "role": role,
            "source_page_index": 0,
            "source_product": product,
            "product_version": "v1",
            "selector_hash": "1" * 64 if acquired else None,
            "typed_content_hash": "2" * 64,
            "raw_hash": "3" * 64,
            "byte_count": 524289,
            "segment_count": 2,
            "serializer_id": "fixed-synthetic-commitment:v1",
            "schema_version": "v1",
            "mime_type": "application/json",
            "source_context": {
                "capture_origin": "ACQUIRED_NATIVE_DTO" if acquired else "INGRESS_JSON",
                "captured_at": "2026-10-01T00:00:00Z",
                "snapshot_epoch": "retained-epoch" if role in ROLES[:2] else None,
                "request_scope": "native-scope" if role in ROLES[:2] else None,
                "receipt_job_id": receipt["receipt_job_id"],
                "source_revision": "native-r2" if acquired else None,
                "selector_json": None,
                "export_job_id": "retained-job" if role in ROLES[:2] else None,
                "refresh_of_job_id": None,
                "returned_count": 1 if acquired else None,
                "total_count": 1 if acquired else None,
                "next_page_token": None,
            },
            "original_supplier_digest": None,
            "original_supplier_reference": None,
        }

    registry_captures = [captured(None, "PortfolioHistoricalRegistry", 0)]
    registry = {
        "locator": locator("PortfolioHistoricalRegistry", "registry-cut", registry_hash),
        "manifest": registry_manifest,
        "receipt": deepcopy(receipt),
        "member_bindings": members,
        "captures": registry_captures,
        "view_roots": [
            view("CUT", "CUT_HEADERS", "single_cut", [registry_hash], "NeutralSourceCutHeaders:v1"),
            view(
                "MEMBERS",
                "REGISTRY_MEMBERS",
                "provider_namespace,source_member_id",
                [m["member_content_hash"] for m in members],
                "PortfolioHistoricalRegistryMembers:v1",
            ),
            capture_view(registry_captures),
        ],
    }
    portfolios = []
    for index, portfolio_id in enumerate(ids):
        financial_identity = {**identity, "source_cut_id": "financial-cut"}
        selections = [
            {
                "role": role,
                "product_name": product,
                "product_version": "v1",
                "selector_hash": "1" * 64,
                "content_hash": "2" * 64,
                "receipt_job_id": receipt["receipt_job_id"],
                "source_revision": "native-r2",
            }
            for role, product in zip(ROLES, PRODUCTS, strict=True)
        ]
        graph = {
            "identity": financial_identity,
            "portfolio_id": portfolio_id,
            "currency": "USD",
            "prior_date": "2026-08-31",
            "month_end_date": "2026-09-30",
            "registry_root": registry_hash,
            "member_revision": 1,
            "selections": selections,
            "compatibility": None,
            "settled_unencumbered": {
                "amount": "50",
                "currency": "USD",
                "business_date": "2026-09-30",
                "semantic_definition": "explicit-supplied-cash",
                "producer_revision": "native-r2",
            },
        }
        manifest = {
            "identity": deepcopy(financial_identity),
            "selection_count": 17,
            "selections_root": "4" * 64,
            "chunk_count": 2,
            "chunks_root": "5" * 64,
        }
        manifest_hash = owner_domain_digest(
            "PortfolioFinancialSourceCutManifest:v1", "manifest", manifest
        )
        graph_hash = owner_domain_digest("PortfolioFinancialSourceCut:v1", "cut", graph)
        input_hash = hashlib.sha256(("selected-input-" + str(index)).encode()).hexdigest()
        captures = [
            captured(role, product, index) for role, product in zip(ROLES, PRODUCTS, strict=True)
        ]
        portfolios.append(
            {
                "portfolio_id": portfolio_id,
                "locator": locator("PortfolioFinancialSourceCut", "financial-cut", manifest_hash),
                "manifest": manifest,
                "receipt": deepcopy(receipt),
                "graph": graph,
                "graph_content_hash": graph_hash,
                "input_content_hash": input_hash,
                "captures": captures,
                "view_roots": [
                    view(
                        "CUT",
                        "CUT_HEADERS",
                        "single_cut",
                        [manifest_hash],
                        "NeutralSourceCutHeaders:v1",
                    ),
                    view(
                        "INPUTS",
                        "SELECTED_FINANCIAL_INPUTS",
                        "selected_portfolio",
                        [input_hash],
                        "PortfolioFinancialSourceCutInputs:v1",
                    ),
                    capture_view(captures),
                ],
            }
        )
    pin_financial_group(portfolios, "financial-cut")
    return {
        "product_name": "CompositeMonthlyNativeCustody",
        "product_version": "v1",
        "registry": registry,
        "portfolios": portfolios,
    }


@pytest.mark.parametrize("groups", [[[0, 1, 2]], [[0], [1], [2]], [[0, 1], [2]]])
def test_financial_manifest_accepts_complete_single_or_disjoint_populations(groups):
    material = custody_material(["P1", "P2", "P3"])
    for index, group in enumerate(groups):
        pin_financial_group([material["portfolios"][i] for i in group], "financial-" + str(index))
    custody = MonthlyNativeCustody.model_validate(material)
    assert len(custody.portfolios) == 3
    assert len({p.locator for p in custody.portfolios}) == len(groups)


@pytest.mark.parametrize(
    "boundary",
    [
        "substituted",
        "count",
        "root_order",
        "duplicate_hash",
        "superset",
        "mixed_address",
        "overlap",
    ],
)
def test_financial_manifest_refuses_rehashed_incomplete_or_mismatching_groups(boundary):
    material = custody_material(["P1", "P2", "P3"])
    portfolios = material["portfolios"]
    hashes = [p["input_content_hash"] for p in portfolios]
    if boundary == "substituted":
        p = portfolios[0]
        p["input_content_hash"] = "a" * 64
        p["view_roots"][1] = view(
            "INPUTS",
            "SELECTED_FINANCIAL_INPUTS",
            "selected_portfolio",
            [p["input_content_hash"]],
            "PortfolioFinancialSourceCutInputs:v1",
        )
    elif boundary in ("root_order", "duplicate_hash", "superset"):
        committed = (
            list(reversed(hashes))
            if boundary == "root_order"
            else (
                [hashes[0], hashes[0], hashes[2]]
                if boundary == "duplicate_hash"
                else hashes + ["a" * 64]
            )
        )
        pin_financial_group(portfolios, "financial-cut", committed)
    elif boundary == "count":
        pin_financial_group(portfolios, "financial-cut", hashes[:2])
    elif boundary == "mixed_address":
        pin_financial_group(portfolios[:1], "other-financial", hashes)
    else:
        pin_financial_group(portfolios[:2], "financial-A", hashes[:2])
        pin_financial_group(portfolios[2:], "financial-B", hashes[1:])
    with pytest.raises(ValidationError, match="FINANCIAL_MEMBERSHIP"):
        MonthlyNativeCustody.model_validate(material)


@pytest.mark.parametrize("boundary", ["missing", "duplicate", "order"])
def test_financial_manifest_keeps_canonical_complete_monthly_portfolio_set(boundary):
    material = custody_material(["P1", "P2", "P3"])
    if boundary == "missing":
        material["portfolios"].pop()
    elif boundary == "duplicate":
        material["portfolios"].append(deepcopy(material["portfolios"][0]))
    else:
        material["portfolios"].reverse()
    with pytest.raises(ValidationError, match="PORTFOLIO_SET_MISMATCH"):
        MonthlyNativeCustody.model_validate(material)


def native_assembly_material(ids=None):
    material = assembly_material()[1]
    custody = MonthlyNativeCustody.model_validate(custody_material(ids))
    if ids:
        snapshot = material["observations"]
        snapshot["expected_portfolio_ids"] = ids
        snapshot["portfolios"] = [
            {**deepcopy(snapshot["portfolios"][0]), "portfolio_id": p} for p in ids
        ]
    snapshot = material["observations"]
    material["product_version"] = "v2"
    material["native_custody"] = custody.model_dump(mode="json")
    material["inputs"] = [
        {
            "kind": kind,
            "owner_service": "lotus-manage",
            "source_cut_id": snapshot["source_cut_id"],
            "evidence": {
                "product_name": "CompositeMonthlyRoleSet",
                "product_version": "v1",
                "revision": snapshot["source_revision"],
                "digest": native_role_set_digest(custody, kind),
            },
        }
        for kind in sorted(ROLES)
    ]
    material["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": snapshot, "inputs": material["inputs"]}
    )
    return material


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
def test_core_published_independent_ordered_root_vectors(domain, empty, one):
    assert native_ordered_root(domain, []) == empty
    assert native_ordered_root(domain, ["a" * 64]) == one
    with pytest.raises(ValueError, match="ROOT_ITEM_INVALID"):
        native_ordered_root(domain, ["sha256:" + "a" * 64])


def test_exact_retained_shapes_and_distinct_native_roots():
    custody = MonthlyNativeCustody.model_validate(custody_material())
    portfolio = custody.portfolios[0]
    assert custody.registry.manifest.identity.source_system == "native:fixture:α"
    assert portfolio.manifest.selection_count == 1
    assert portfolio.view_roots[1].root_item_count == 1
    assert portfolio.view_roots[2].total_count == 10
    assert portfolio.view_roots[2].root_item_count == 5
    assert (
        len(
            {
                portfolio.locator.batch_manifest_hash,
                portfolio.graph_content_hash,
                portfolio.input_content_hash,
                portfolio.view_roots[1].ordered_set_hash,
                portfolio.view_roots[2].ordered_set_hash,
            }
        )
        == 5
    )
    assert (
        "roles" not in portfolio.model_dump()
        and "bytes_base64" not in portfolio.captures[0].model_dump()
    )
    assert MonthlyNativeCustody.model_validate(custody.model_dump(mode="json")) == custody


def test_independent_fixed_custody_and_five_role_vectors():
    custody = MonthlyNativeCustody.model_validate(custody_material())
    assert (
        custody.content_hash
        == "sha256:5f403fce2a453eb5eaac8bbeb2d57fc64251ebf1e3cb5756f3b78dd5e579c02f"
    )
    assert (
        custody.registry.locator.batch_manifest_hash
        == "e7b0978ccf51de99398081c57e34c98ce378639ea3a1d37caedbfe6b4444d8c4"
    )
    assert (
        custody.portfolios[0].locator.batch_manifest_hash
        == "59c4d5e7c4e1f2b67559ecc93b02eeac8e78c58eaa47e7aa25c4e9ee7e7c7b2d"
    )
    assert (
        custody.portfolios[0].graph_content_hash
        == "66394b26f664c99a5d2d1e735e74da71aa137b3718cecfceedffdd76b0a4f0ca"
    )
    expected = {
        "PRIOR_ASSETS": "sha256:ea1210ce66cce6bf09ab5a44b4de63b663b9ee1d8af694f8e9cdc0ea75610c39",
        "MONTH_END_ASSETS": "sha256:753f75a835d3339a8cf1f40823496e132764c68e8ca5f501676c38058e62ceaa",
        "CASH": "sha256:1eb1bbc4231cbfa01b4a0512b9e37f7093da1f7c5ea566ceac632d0c2e5e9b53",
        "READINESS": "sha256:f36d2241dc1076cc2ca5d3212f43deed59641188ea6f4aba1fa85828a430282f",
        "FLOWS": "sha256:e3db80232a053cd03312e3cd20a94e1ce8c3fc91ad2d83f227780cc219fdea5d",
    }
    assert {role: native_role_set_digest(custody, role) for role in ROLES} == expected


def test_opaque_member_mapping_refuses_in_existing_manage_identity_instead_of_sanitizing():
    raw = native_assembly_material()
    raw["native_custody"]["registry"]["member_bindings"][0]["provider_namespace"] = (
        "native namespace"
    )
    raw["native_custody"].pop("content_hash")
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        NativeMonthlySourceAssembly.model_validate(raw)


@pytest.mark.parametrize(
    "mutation",
    [
        "batch_graph",
        "input_graph",
        "artifact_raw",
        "segment_artifact",
        "member_registry",
        "address",
        "graph_member",
        "graph_hash",
        "missing_role",
        "capture_order",
        "raw_bytes",
        "wrong_context",
        "naive_time",
        "opaque_portfolio",
        "false_revision",
        "wrong_segments",
    ],
)
def test_substituted_roots_and_incomplete_closed_custody_refuse(mutation):
    material = custody_material()
    p = material["portfolios"][0]
    if mutation == "batch_graph":
        p["locator"]["batch_manifest_hash"] = p["graph_content_hash"]
    elif mutation == "input_graph":
        p["input_content_hash"] = p["graph_content_hash"]
    elif mutation == "artifact_raw":
        p["view_roots"][2]["ordered_set_hash"] = p["captures"][0]["raw_hash"]
    elif mutation == "segment_artifact":
        p["view_roots"][2]["root_item_count"] = 10
    elif mutation == "member_registry":
        material["registry"]["member_bindings"][0]["member_content_hash"] = material["registry"][
            "locator"
        ]["batch_manifest_hash"]
    elif mutation == "address":
        p["locator"]["source_address"]["registry_scope_id"] = "foreign"
    elif mutation == "graph_member":
        p["graph"]["member_revision"] = 2
    elif mutation == "graph_hash":
        p["graph_content_hash"] = "9" * 64
    elif mutation == "missing_role":
        p["captures"].pop()
    elif mutation == "capture_order":
        p["captures"].reverse()
    elif mutation == "raw_bytes":
        p["captures"][0]["bytes_base64"] = "YQ=="
    elif mutation == "wrong_context":
        p["captures"][0]["source_context"]["receipt_job_id"] = "foreign"
    elif mutation == "naive_time":
        p["receipt"]["completed_at"] = "2026-10-01T00:01:00"
    elif mutation == "opaque_portfolio":
        p["portfolio_id"] = "a b"
    elif mutation == "false_revision":
        p["graph"]["member_revision"] = True
    else:
        p["captures"][0]["segment_count"] = 1
    with pytest.raises(ValidationError):
        MonthlyNativeCustody.model_validate(material)


def test_all_member_manage_role_sets_bind_every_member_and_receipt():
    ids = ["synthetic-member", "synthetic-member-2", "synthetic-member-3"]
    assembly = NativeMonthlySourceAssembly.model_validate(native_assembly_material(ids))
    custody = assembly.native_custody
    for binding in assembly.inputs:
        assert binding.owner_service == "lotus-manage"
        assert binding.evidence.digest != "sha256:" + custody.portfolios[0].graph_content_hash
        p = custody.model_dump(mode="json")
        p.pop("content_hash")
        p["portfolios"][2]["receipt"]["receipt_job_id"] = "changed-original-receipt"
        changed = MonthlyNativeCustody.model_validate(p)
        assert native_role_set_digest(changed, binding.kind) != binding.evidence.digest
    changed = assembly.model_dump(mode="json")
    changed["inputs"][0]["evidence"]["digest"] = (
        "sha256:" + custody.portfolios[0].graph_content_hash
    )
    changed["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": changed["observations"], "inputs": changed["inputs"]}
    )
    with pytest.raises(ValidationError, match="ROLE_SET_MISMATCH"):
        NativeMonthlySourceAssembly.model_validate(changed)


@pytest.mark.parametrize(
    "field,value", [("amount", "-0.00"), ("amount", "NaN"), ("amount", "1E+2"), ("amount", "01")]
)
def test_core_cash_canonicalization_refuses_noncanonical_wire(field, value):
    cash = custody_material()["portfolios"][0]["graph"]["settled_unencumbered"]
    cash[field] = value
    with pytest.raises(ValidationError):
        NativeCashDeclaration.model_validate(cash)


def test_native_domain_dates_offsets_decimal_scale_and_null_are_not_manage_hashes():
    material = custody_material()
    manifest = NativeRegistryManifest.model_validate(material["registry"]["manifest"])
    actual = native_domain_hash("PortfolioHistoricalRegistry:v1", "cut", manifest)
    assert actual == owner_domain_digest(
        "PortfolioHistoricalRegistry:v1", "cut", material["registry"]["manifest"]
    )
    assert actual != hash_canonical_payload(
        {"contract": "PortfolioHistoricalRegistry:v1", "cut": manifest.model_dump(mode="json")}
    ).removeprefix("sha256:")
    graph = material["portfolios"][0]["graph"]
    hashes = []
    for amount in (None, "0", "0.00", "50.00"):
        graph["settled_unencumbered"]["amount"] = amount
        typed = NativeFinancialGraph.model_validate(graph)
        result = native_domain_hash("PortfolioFinancialSourceCut:v1", "cut", typed)
        assert result == owner_domain_digest("PortfolioFinancialSourceCut:v1", "cut", graph)
        hashes.append(result)
    assert len(set(hashes)) == 4


@pytest.mark.parametrize(
    "path",
    [
        ("portfolios",),
        ("registry", "view_roots"),
        ("registry", "member_bindings"),
        ("registry", "captures"),
        ("portfolios", 0, "view_roots"),
        ("portfolios", 0, "captures"),
        ("portfolios", 0, "graph", "selections"),
    ],
)
def test_native_custody_arrays_cannot_mutate_retained_wire_or_roots(path):
    material = custody_material()
    custody = MonthlyNativeCustody.model_validate(material)
    before = custody.model_dump_json()
    collection = custody
    for key in path:
        collection = collection[key] if isinstance(key, int) else getattr(collection, key)
    assert isinstance(collection, tuple)
    with pytest.raises(AttributeError):
        collection.clear()
    with pytest.raises(TypeError):
        collection[0] = collection[0]
    material["portfolios"].clear()
    assert custody.model_dump_json() == before
    assert MonthlyNativeCustody.model_validate_json(before) == custody


def test_native_compatibility_inventory_and_each_pair_are_frozen_json_arrays():
    graph = custody_material()["portfolios"][0]["graph"]
    declaration = dict(
        source_system=graph["identity"]["source_system"],
        scope_id=graph["identity"]["scope_id"],
        definition_version=graph["identity"]["definition_version"],
        registry_root=graph["registry_root"],
        role_roots=[[s["role"], s["content_hash"]] for s in graph["selections"]],
        coverage_from=graph["identity"]["coverage_from"],
        coverage_to=graph["identity"]["coverage_to"],
        currency=graph["currency"],
        basis_reference="native-declared-basis",
        original_evidence_digest="6" * 64,
    )
    frozen = NativeCompatibilityDeclaration.model_validate(declaration)
    assert frozen.model_dump(mode="json") == declaration
    with pytest.raises(TypeError):
        frozen.role_roots[0][0] = "CASH"
    declaration["role_roots"][0][0] = "CASH"
    assert frozen.role_roots[0][0] == "PRIOR_ASSETS"


@pytest.mark.parametrize("construction", ["copy", "construct"])
def test_copied_or_constructed_native_arrays_are_revalidated_before_assembly_retention(
    construction,
):
    wire = native_assembly_material()
    custody = MonthlyNativeCustody.model_validate(wire["native_custody"])
    aliased = list(custody.portfolios)
    copied = (
        custody.model_copy(update={"portfolios": aliased})
        if construction == "copy"
        else MonthlyNativeCustody.model_construct(**{**custody.__dict__, "portfolios": aliased})
    )
    wire["native_custody"] = copied
    retained = NativeMonthlySourceAssembly.model_validate(wire)
    before = retained.native_custody.model_dump_json()
    aliased.clear()
    assert retained.native_custody.model_dump_json() == before
    assert isinstance(retained.native_custody.portfolios, tuple)


def paginated_cash_material():
    material = custody_material()
    portfolio = material["portfolios"][0]
    first = portfolio["captures"][2]
    first["source_context"].update(total_count=2, next_page_token="cash-page-2")
    second = deepcopy(first)
    second["capture_id"] = "f" * 64
    second["source_page_index"] = 1
    second["source_context"]["next_page_token"] = None
    portfolio["captures"].insert(3, second)
    return material, first, second


def test_retained_role_pagination_accepts_complete_contiguous_pages():
    material, _, _ = paginated_cash_material()
    portfolio = material["portfolios"][0]
    portfolio["view_roots"][2] = capture_view(portfolio["captures"])
    custody = MonthlyNativeCustody.model_validate(material)
    pages = [c for c in custody.portfolios[0].captures if c.role == "CASH"]
    assert [c.source_page_index for c in pages] == [0, 1]
    assert [c.source_context.returned_count for c in pages] == [1, 1]
    assert pages[-1].source_context.next_page_token is None


@pytest.mark.parametrize(
    "page,field,value,error",
    [
        (1, "total_count", 3, "ROLE_PAGINATION_INCOMPLETE"),
        (1, "returned_count", 0, "ROLE_PAGINATION_INCOMPLETE"),
        (1, "next_page_token", "unexpected-page-3", "ROLE_PAGINATION_INCOMPLETE"),
        (0, "next_page_token", None, "ROLE_PAGINATION_INCOMPLETE"),
        (0, "returned_count", 0, "ROLE_PAGINATION_INCOMPLETE"),
        (1, "receipt_job_id", "different-receipt", "SELECTION_CAPTURE_MISMATCH"),
    ],
)
def test_retained_role_pagination_refuses_incomplete_or_mixed_context(page, field, value, error):
    material, first, second = paginated_cash_material()
    (first, second)[page]["source_context"][field] = value
    if page == 0 and field == "returned_count":
        second["source_context"]["returned_count"] = 2
    portfolio = material["portfolios"][0]
    portfolio["view_roots"][2] = capture_view(portfolio["captures"])
    with pytest.raises(ValidationError, match=error):
        MonthlyNativeCustody.model_validate(material)


def test_role_page_gap_refuses_before_selection_and_pagination_mismatches():
    material, _, second = paginated_cash_material()
    second["source_page_index"] = 2
    second["source_context"].update(receipt_job_id="different-receipt", total_count=3)
    portfolio = material["portfolios"][0]
    portfolio["view_roots"][2] = capture_view(portfolio["captures"])
    with pytest.raises(ValidationError, match="ROLE_CAPTURE_INCOMPLETE"):
        MonthlyNativeCustody.model_validate(material)


@pytest.mark.parametrize(
    "field,value",
    [
        ("registry_root", "9" * 64),
        ("currency", "SGD"),
        ("coverage_from", "2026-09-01"),
        ("coverage_to", "2026-10-01"),
        ("source_system", "foreign-source"),
        ("scope_id", "foreign-scope"),
        ("role_roots", [[role, "9" * 64] for role in ROLES]),
    ],
)
def test_graph_compatibility_refuses_each_foreign_binding(field, value):
    graph = custody_material()["portfolios"][0]["graph"]
    graph["compatibility"] = {
        "source_system": graph["identity"]["source_system"],
        "scope_id": graph["identity"]["scope_id"],
        "definition_version": graph["identity"]["definition_version"],
        "registry_root": graph["registry_root"],
        "role_roots": [[s["role"], s["content_hash"]] for s in graph["selections"]],
        "coverage_from": graph["identity"]["coverage_from"],
        "coverage_to": graph["identity"]["coverage_to"],
        "currency": graph["currency"],
        "basis_reference": "native-declared-basis",
        "original_evidence_digest": "6" * 64,
    }
    assert NativeFinancialGraph.model_validate(graph).compatibility is not None
    graph["compatibility"][field] = value
    with pytest.raises(ValidationError, match="COMPATIBILITY_MISMATCH"):
        NativeFinancialGraph.model_validate(graph)


@pytest.mark.parametrize(
    "path,value,error",
    [
        (("registry", "manifest", "identity", "scope_id"), " scope", "IDENTITY_INVALID"),
        (("registry", "manifest", "identity", "coverage_from"), "20260831", "DATE_INVALID"),
        (("registry", "manifest", "identity", "coverage_to"), "2026-08-01", "COVERAGE_INVALID"),
        (("registry", "manifest", "identity", "expected_head_hash"), None, "CORRECTION_INVALID"),
        (("registry", "manifest", "chunk_count"), 0, "CHUNKS_REQUIRED"),
        (("portfolios", 0, "manifest", "chunk_count"), 0, "CHUNKS_REQUIRED"),
        (
            ("portfolios", 0, "graph", "selections", 2, "product_name"),
            "PortfolioTimeseriesInput",
            "PRODUCT_FAMILY_MISMATCH",
        ),
        (
            ("portfolios", 0, "graph", "settled_unencumbered", "amount"),
            "0." + "0" * 16383 + "1",
            "CASH_INVALID",
        ),
        (("portfolios", 0, "graph", "prior_date"), "2026-09-30", "GRAPH_SHAPE_INVALID"),
        (
            ("portfolios", 0, "graph", "settled_unencumbered", "currency"),
            "SGD",
            "CASH_BINDING_MISMATCH",
        ),
        (
            ("portfolios", 0, "receipt", "completed_at"),
            "2026-09-30T23:59:59Z",
            "RECEIPT_WINDOW_INVALID",
        ),
        (
            ("portfolios", 0, "captures", 0, "original_supplier_digest"),
            "1" * 64,
            "SUPPLIER_PAIR_INVALID",
        ),
        (
            ("portfolios", 0, "captures", 2, "source_context", "refresh_of_job_id"),
            "prior-export",
            "EXPORT_REFERENCE_INVALID",
        ),
        (
            ("portfolios", 0, "captures", 2, "source_context", "returned_count"),
            None,
            "ACQUIRED_CONTEXT_INVALID",
        ),
        (("portfolios", 0, "graph", "portfolio_id"), "foreign-member", "GRAPH_IDENTITY_MISMATCH"),
        (("content_hash",), "sha256:" + "1" * 64, "CUSTODY_CONTENT_MISMATCH"),
    ],
)
def test_retained_custody_rejects_invalid_declared_facts_at_ingestion(path, value, error):
    material = custody_material()
    assert (
        MonthlyNativeCustody.model_validate(material).portfolios[0].portfolio_id
        == "synthetic-member"
    )
    target = material
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError, match=error):
        MonthlyNativeCustody.model_validate(material)


@pytest.mark.parametrize(
    "boundary",
    ["members", "registry_capture", "financial_capture", "portfolio_set", "registry_graph"],
)
def test_retained_custody_rejects_rebound_cross_record_substitution(boundary):
    material = custody_material()
    portfolio = material["portfolios"][0]
    if boundary == "members":
        material["registry"]["member_bindings"].append(
            deepcopy(material["registry"]["member_bindings"][0])
        )
        error = "MEMBERS_NONCANONICAL"
    elif boundary == "registry_capture":
        registry = material["registry"]
        registry["captures"][0]["source_context"]["receipt_job_id"] = "foreign-receipt"
        registry["view_roots"][2] = capture_view(registry["captures"])
        error = "REGISTRY_CAPTURE_MISMATCH"
    elif boundary == "financial_capture":
        portfolio["captures"][0]["role"] = None
        portfolio["captures"][0]["source_context"]["capture_origin"] = "INGRESS_JSON"
        portfolio["view_roots"][2] = capture_view(portfolio["captures"])
        error = "FINANCIAL_CAPTURE_MISMATCH"
    elif boundary == "portfolio_set":
        material["portfolios"].append(deepcopy(portfolio))
        error = "PORTFOLIO_SET_MISMATCH"
    else:
        portfolio["graph"]["registry_root"] = "1" * 64
        portfolio["graph_content_hash"] = owner_domain_digest(
            "PortfolioFinancialSourceCut:v1", "cut", portfolio["graph"]
        )
        error = "REGISTRY_GRAPH_BINDING_MISMATCH"
    with pytest.raises(ValidationError, match=error):
        MonthlyNativeCustody.model_validate(material)


@pytest.mark.parametrize(
    "boundary", ["tenant", "missing_member", "duplicate_member", "window", "currency", "cash"]
)
def test_native_observation_projection_requires_complete_matching_scope(boundary):
    from src.core.composite_eligibility.observations import MonthlyEligibilityObservations

    assembly = NativeMonthlySourceAssembly.model_validate(native_assembly_material())
    custody = assembly.native_custody
    observations = assembly.observations.model_dump(mode="json")
    require_native_observation_scope(custody, assembly.observations)
    if boundary == "tenant":
        observations["tenant_id"] = "foreign-tenant"
        error = "OBSERVATION_SCOPE_MISMATCH"
    elif boundary in ("missing_member", "duplicate_member"):
        observations["portfolios"] = (
            [] if boundary == "missing_member" else observations["portfolios"] * 2
        )
        error = "NORMALIZED_PORTFOLIOS_MISMATCH"
    elif boundary == "window":
        observations["month"] = "2026-10"
        error = "OBSERVATION_WINDOW_MISMATCH"
    elif boundary == "currency":
        observations["reporting_currency"] = "SGD"
        error = "OBSERVATION_WINDOW_MISMATCH"
    else:
        observations["portfolios"][0]["settled_unencumbered_cash"] = "999"
        error = "NORMALIZED_CASH_MISMATCH"
    with pytest.raises(ValueError, match=error):
        require_native_observation_scope(
            custody, MonthlyEligibilityObservations.model_validate(observations)
        )


def test_role_set_api_rejects_unknown_role_without_substituting_a_known_commitment():
    custody = MonthlyNativeCustody.model_validate(custody_material())
    with pytest.raises(ValueError, match="ROLE_INVALID"):
        native_role_set_digest(custody, "UNKNOWN")
    assert native_role_set_digest(custody, "CASH") != native_role_set_digest(custody, "READINESS")
