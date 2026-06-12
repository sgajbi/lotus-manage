from src.core.rebalance.tenant_policy_packs import (
    build_tenant_policy_pack_resolver,
    _load_tenant_policy_pack_json_map,
    _tenant_policy_pack_mapping_row,
    parse_tenant_policy_pack_map,
)


def test_parse_tenant_policy_pack_map_invalid_inputs():
    assert parse_tenant_policy_pack_map(None) == {}
    assert parse_tenant_policy_pack_map("") == {}
    assert parse_tenant_policy_pack_map("{bad-json}") == {}
    assert parse_tenant_policy_pack_map("[]") == {}


def test_parse_tenant_policy_pack_map_skips_invalid_rows():
    mapping = parse_tenant_policy_pack_map('{"tenant_1":"pack_1"," ":"pack_2","tenant_3":3}')
    assert mapping == {"tenant_1": "pack_1"}


def test_load_tenant_policy_pack_json_map_returns_only_json_objects():
    assert _load_tenant_policy_pack_json_map(None) is None
    assert _load_tenant_policy_pack_json_map(" ") is None
    assert _load_tenant_policy_pack_json_map("{bad-json}") is None
    assert _load_tenant_policy_pack_json_map("[]") is None
    assert _load_tenant_policy_pack_json_map('{"tenant_1":"pack_1"}') == {"tenant_1": "pack_1"}


def test_tenant_policy_pack_mapping_row_normalizes_valid_string_pairs():
    assert _tenant_policy_pack_mapping_row(tenant_id=" tenant_1 ", policy_pack_id=" pack_1 ") == (
        "tenant_1",
        "pack_1",
    )


def test_tenant_policy_pack_mapping_row_rejects_invalid_values():
    assert _tenant_policy_pack_mapping_row(tenant_id=1, policy_pack_id="pack_1") is None
    assert _tenant_policy_pack_mapping_row(tenant_id="tenant_1", policy_pack_id=1) is None
    assert _tenant_policy_pack_mapping_row(tenant_id=" ", policy_pack_id="pack_1") is None
    assert _tenant_policy_pack_mapping_row(tenant_id="tenant_1", policy_pack_id=" ") is None


def test_build_resolver_disabled_returns_none():
    resolver = build_tenant_policy_pack_resolver(
        enabled=False,
        mapping_json='{"tenant_1":"pack_1"}',
    )
    assert resolver.resolve(tenant_id="tenant_1") is None


def test_build_resolver_enabled_uses_normalized_tenant_ids():
    resolver = build_tenant_policy_pack_resolver(
        enabled=True,
        mapping_json='{"tenant_1":"pack_1","tenant_2":" pack_2 "}',
    )
    assert resolver.resolve(tenant_id=None) is None
    assert resolver.resolve(tenant_id="tenant_1") == "pack_1"
    assert resolver.resolve(tenant_id=" tenant_2 ") == "pack_2"
    assert resolver.resolve(tenant_id="missing") is None
