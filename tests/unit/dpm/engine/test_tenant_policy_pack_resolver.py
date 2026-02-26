from src.core.dpm.tenant_policy_packs import (
    build_tenant_policy_pack_resolver,
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
