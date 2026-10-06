"""Frozen producer wires and independent authority refusal controls."""

import copy
import json
from pathlib import Path

import pytest

from src.core.composite_definition_versions import decode_composite_definition
from src.infrastructure.composites.postgres import _load_definition
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_authority_helpers import (
    ending_assets_example,
    institutional_reference_wire,
    rebind_definition,
)

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures/composites/source-authority.v2.json"


def test_frozen_v1_and_v2_wires_round_trip_without_digest_or_default_drift() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wires = [pack["v1_compatibility"]["raw_definition"]] + [
        item["definition"] for item in pack["external_versions"].values()
    ]
    for wire in wires:
        assert decode_composite_definition(wire).model_dump(mode="json") == wire
        assert _load_definition({"payload_json": json.dumps(wire)}).model_dump(mode="json") == wire


def test_profile_tamper_refuses_before_definition_admission() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wire = copy.deepcopy(pack["external_versions"]["original"]["definition"])
    wire["source_authority"]["payload"]["providers"][0]["provider_id"] = "tampered"
    with pytest.raises(ValueError):
        decode_composite_definition(wire)


def test_mutated_nested_profile_refuses_storage_without_losing_original() -> None:
    wire, _ = ending_assets_example()
    definition = decode_composite_definition(wire)
    repository = InMemoryDpmCompositeRepository()
    repository.save_definition(definition=definition)
    definition.source_authority.payload.selections[0].member_ids.pop()
    with pytest.raises(ValueError):
        repository.save_definition(definition=definition)
    original = repository.get_definition(
        tenant_id=wire["tenant_id"],
        composite_id=wire["composite_id"],
        definition_version=wire["definition_version"],
    )
    assert original is not None
    assert original.model_dump(mode="json") == wire


def test_optional_ending_assets_have_distinct_profile_source_and_definition_identity() -> None:
    original = json.loads(FIXTURES.read_text(encoding="utf-8"))["external_versions"]["original"][
        "definition"
    ]
    wire, _ = ending_assets_example()
    assert decode_composite_definition(wire).model_dump(mode="json") == wire
    for key in ("definition_version", "definition_payload_digest", "content_hash"):
        assert wire[key] != original[key]
    assert (
        wire["source_authority"]["profile_digest"] != original["source_authority"]["profile_digest"]
    )
    assert all(
        s["fact"] != "ENDING_ASSETS" for s in original["source_authority"]["payload"]["selections"]
    )


@pytest.mark.parametrize("case", ["member_gap", "horizon_gap", "overlap", "return_provider"])
def test_declared_ending_assets_require_full_independent_authority(case: str) -> None:
    wire, _ = ending_assets_example()
    profile = wire["source_authority"]["payload"]
    ending = next(s for s in profile["selections"] if s["fact"] == "ENDING_ASSETS")
    reason = "COMPOSITE_ECONOMIC_AUTHORITY_GAP"
    if case == "member_gap":
        ending["member_ids"].pop()
    elif case == "horizon_gap":
        ending["effective_from"] = "2026-09-02"
    elif case == "overlap":
        duplicate = dict(ending, selection_id="ending_assets_duplicate")
        profile["selections"].append(duplicate)
        profile["selections"].sort(key=lambda s: s["selection_id"])
        reason = "COMPOSITE_ECONOMIC_AUTHORITY_OVERLAP"
    else:
        provider = dict(
            profile["providers"][0],
            provider_id="lotus-performance",
            source_kind="LOTUS_PERFORMANCE",
        )
        profile["providers"].append(provider)
        profile["providers"].sort(key=lambda p: p["provider_id"])
        ending["provider_id"] = ending["economic_authority"] = "lotus-performance"
        reason = "COMPOSITE_AUTHORITY_FACT_KIND_MISMATCH"
    with pytest.raises(ValueError, match=reason):
        decode_composite_definition(rebind_definition(wire, refresh_approval=True))


@pytest.mark.parametrize("duplicate", ["product_version", "profile_revision"])
def test_v2_rejects_duplicate_raw_keys_even_when_values_and_hashes_agree(duplicate: str) -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    raw = json.dumps(pack["external_versions"]["original"]["definition"])
    value = "v2" if duplicate == "product_version" else "synthetic.original"
    token = json.dumps(duplicate) + ": " + json.dumps(value)
    raw = raw.replace(token, token + ", " + token, 1)
    with pytest.raises(ValueError, match="COMPOSITE_DEFINITION_DUPLICATE_JSON_KEY"):
        decode_composite_definition(raw)


def test_v2_nonfinite_raw_json_refuses_before_model_projection() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    raw = json.dumps(pack["external_versions"]["original"]["definition"])
    with pytest.raises(ValueError, match="COMPOSITE_DEFINITION_NONFINITE_JSON_FORBIDDEN"):
        decode_composite_definition(raw[:-1] + ', "untrusted": NaN}')


def test_v1_retains_legacy_raw_duplicate_semantics() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wire = pack["v1_compatibility"]["raw_definition"]
    raw = '{"product_version":"v1",' + json.dumps(wire)[1:]
    assert decode_composite_definition(raw).model_dump(mode="json") == wire


@pytest.mark.parametrize(
    "case,reason",
    [
        ("overlap", "COMPOSITE_ECONOMIC_AUTHORITY_OVERLAP"),
        ("gap", "COMPOSITE_ECONOMIC_AUTHORITY_GAP"),
        ("mode", "COMPOSITE_AUTHORITY_MODE_MISMATCH"),
        ("provider", "COMPOSITE_AUTHORITY_PROVIDER_MISMATCH"),
        ("method", "COMPOSITE_AUTHORITY_METHOD_BINDING_MISMATCH"),
        ("window", "COMPOSITE_AUTHORITY_SELECTION_WINDOW_INVALID"),
        ("internal_owner", "COMPOSITE_AUTHORITY_INTERNAL_OWNER_MISMATCH"),
    ],
)
def test_economic_authority_refuses_contradictions_even_with_recomputed_hashes(
    case: str, reason: str
) -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wire = copy.deepcopy(pack["external_versions"]["original"]["definition"])
    profile = wire["source_authority"]["payload"]
    if case == "overlap":
        selection = copy.deepcopy(profile["selections"][0])
        selection["selection_id"] = "assets_duplicate"
        profile["selections"].append(selection)
        profile["selections"].sort(key=lambda item: item["selection_id"])
    elif case == "gap":
        profile["selections"][0]["member_ids"].pop()
    elif case == "mode":
        profile["mode"] = "INTERNAL"
    elif case == "provider":
        profile["selections"][0]["economic_authority"] = "lotus-core"
    elif case == "method":
        profile["selections"][1]["method_profile_binding"]["revision"] = "unapproved"
    elif case == "window":
        profile["selections"][0]["effective_to"] = "2026-10-01"
    else:
        profile["providers"][0]["source_kind"] = "LOTUS_CORE"
    with pytest.raises(ValueError, match=reason):
        decode_composite_definition(rebind_definition(wire, refresh_approval=True))


def test_rehashing_business_content_cannot_repair_the_existing_approval_binding() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    wire = copy.deepcopy(pack["external_versions"]["original"]["definition"])
    wire["display_name"] = "Changed without a new approval"
    with pytest.raises(ValueError, match="COMPOSITE_AUTHORITY_APPROVAL_BINDING_MISMATCH"):
        decode_composite_definition(rebind_definition(wire))


def test_institutional_reference_representation_preserves_business_hash_without_granting_activation() -> (
    None
):
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    original = pack["external_versions"]["original"]["definition"]
    wire = institutional_reference_wire(original)
    decoded = decode_composite_definition(wire)
    assert decoded.model_dump(mode="json") == wire
    assert decoded.definition_payload_digest == original["definition_payload_digest"]
    assert decoded.content_hash != original["content_hash"]
    assert decoded.authority_approval.official_activation == "UNAVAILABLE"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("scope", "COMPOSITE_AUTHORITY_SCOPE_MISMATCH"),
        ("inception", "COMPOSITE_AUTHORITY_DEFINITION_WINDOW_MISMATCH"),
        ("termination", "COMPOSITE_AUTHORITY_DEFINITION_WINDOW_MISMATCH"),
        ("approval_time", "COMPOSITE_AUTHORITY_APPROVAL_BEFORE_CREATION"),
        ("self_approval", "COMPOSITE_AUTHORITY_SELF_APPROVAL_FORBIDDEN"),
        ("business_digest", "COMPOSITE_DEFINITION_PAYLOAD_DIGEST_MISMATCH"),
        ("wire_digest", "COMPOSITE_DEFINITION_WIRE_DIGEST_MISMATCH"),
    ],
)
def test_definition_rejects_invalid_scope_window_and_immutable_approval_material(
    case: str, reason: str
) -> None:
    wire, _ = ending_assets_example()
    if case == "scope":
        wire["composite_id"] = "another-composite"
    elif case == "inception":
        wire["inception_date"] = "2026-09-02"
    elif case == "termination":
        wire["termination_date"] = "2026-09-29"
    elif case == "approval_time":
        wire["authority_approval"]["claims"]["approved_at"] = "2020-01-01T00:00:00.000000Z"
    elif case == "self_approval":
        wire["authority_approval"]["claims"]["approving_identity"] = wire["created_by"]
    elif case == "business_digest":
        wire["display_name"] = "Unapproved material change"
    else:
        wire["correlation_id"] = "changed-correlation"
        wire = rebind_definition(wire, refresh_approval=True)
        wire["content_hash"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match=reason):
        decode_composite_definition(wire)


def test_valid_closed_definition_window_round_trips_but_invalid_calendar_date_refuses() -> None:
    wire, _ = ending_assets_example()
    wire["termination_date"] = "2026-09-30"
    wire = rebind_definition(wire, refresh_approval=True)
    assert decode_composite_definition(wire).model_dump(mode="json") == wire
    wire["termination_date"] = "2026-09-31"
    with pytest.raises(ValueError, match="day is out of range"):
        decode_composite_definition(rebind_definition(wire, refresh_approval=True))


@pytest.mark.parametrize(
    "case,reason",
    [
        ("reversed_window", "COMPOSITE_AUTHORITY_WINDOW_INVALID"),
        ("duplicate_member", "COMPOSITE_AUTHORITY_MEMBERS_NONCANONICAL"),
        ("unknown_member_provider", "COMPOSITE_AUTHORITY_MEMBER_PROVIDER_UNKNOWN"),
        ("member_kind", "COMPOSITE_AUTHORITY_MEMBER_KIND_MISMATCH"),
        ("unknown_selected_member", "COMPOSITE_AUTHORITY_MEMBER_UNKNOWN"),
        ("nonreturn_method", "COMPOSITE_AUTHORITY_METHOD_BINDING_UNEXPECTED"),
    ],
)
def test_recomputed_digests_do_not_admit_ambiguous_identity_or_fact_authority(
    case: str, reason: str
) -> None:
    wire, _ = ending_assets_example()
    profile = wire["source_authority"]["payload"]
    if case == "reversed_window":
        profile["effective_to"] = "2026-08-31"
    elif case == "duplicate_member":
        profile["member_identities"].append(copy.deepcopy(profile["member_identities"][0]))
    elif case == "unknown_member_provider":
        profile["member_identities"][0]["provider_id"] = "unregistered-provider"
    elif case == "member_kind":
        profile["member_identities"][0]["identity_kind"] = "CORE_PORTFOLIO"
    elif case == "unknown_selected_member":
        profile["selections"][0]["member_ids"] = ["unknown-member"]
    else:
        profile["selections"][0]["method_profile_binding"] = copy.deepcopy(
            profile["return_method_binding"]
        )
    with pytest.raises(ValueError, match=reason):
        decode_composite_definition(rebind_definition(wire, refresh_approval=True))


@pytest.mark.parametrize(
    "raw,reason",
    [
        ("[]", "COMPOSITE_DEFINITION_JSON_OBJECT_REQUIRED"),
        ("null", "COMPOSITE_DEFINITION_JSON_OBJECT_REQUIRED"),
        ('{"product_version":', "COMPOSITE_DEFINITION_RAW_JSON_INVALID"),
        ('{"product_version":"v3"}', "COMPOSITE_DEFINITION_PRODUCT_VERSION_UNSUPPORTED"),
    ],
)
def test_version_dispatch_refuses_nonobjects_malformed_json_and_unknown_versions(
    raw: str, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        decode_composite_definition(raw)


def test_absent_version_preserves_the_legacy_v1_default_and_wire() -> None:
    pack = json.loads(FIXTURES.read_text(encoding="utf-8"))
    expected = pack["v1_compatibility"]["raw_definition"]
    wire = copy.deepcopy(expected)
    del wire["product_version"]
    assert decode_composite_definition(json.dumps(wire)).model_dump(mode="json") == expected


def test_valid_authority_payload_with_a_substituted_profile_digest_refuses() -> None:
    wire, _ = ending_assets_example()
    assert decode_composite_definition(wire).model_dump(mode="json") == wire
    wire["source_authority"]["profile_digest"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="COMPOSITE_PROFILE_DIGEST_MISMATCH"):
        decode_composite_definition(wire)
