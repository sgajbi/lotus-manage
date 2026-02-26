from decimal import Decimal

import src.core.dpm.policy_packs as policy_pack_module
from src.core.dpm.policy_packs import (
    apply_policy_pack_to_engine_options,
    parse_policy_pack_catalog,
    resolve_effective_policy_pack,
    resolve_policy_pack_definition,
    resolve_policy_pack_replay_enabled,
)
from src.core.models import EngineOptions


def test_policy_pack_resolution_disabled_ignores_all_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=False,
        request_policy_pack_id="req_pack",
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is False
    assert resolved.source == "DISABLED"
    assert resolved.selected_policy_pack_id is None


def test_policy_pack_resolution_request_precedence():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="req_pack",
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "REQUEST"
    assert resolved.selected_policy_pack_id == "req_pack"


def test_policy_pack_resolution_tenant_precedence_when_request_missing():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id="tenant_pack",
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "TENANT_DEFAULT"
    assert resolved.selected_policy_pack_id == "tenant_pack"


def test_policy_pack_resolution_global_precedence_when_request_and_tenant_missing():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id="global_pack",
    )
    assert resolved.enabled is True
    assert resolved.source == "GLOBAL_DEFAULT"
    assert resolved.selected_policy_pack_id == "global_pack"


def test_policy_pack_resolution_none_when_enabled_and_no_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolved.enabled is True
    assert resolved.source == "NONE"
    assert resolved.selected_policy_pack_id is None


def test_policy_pack_resolution_trims_policy_pack_ids():
    resolved = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="  req_pack  ",
        tenant_default_policy_pack_id="   ",
        global_default_policy_pack_id=" global_pack ",
    )
    assert resolved.source == "REQUEST"
    assert resolved.selected_policy_pack_id == "req_pack"


def test_policy_pack_catalog_parse_and_resolve():
    catalog = parse_policy_pack_catalog(
        '{"dpm_standard_v1":{"version":"2","turnover_policy":{"max_turnover_pct":"0.05"}}}'
    )
    assert "dpm_standard_v1" in catalog
    definition = catalog["dpm_standard_v1"]
    assert definition.version == "2"
    assert definition.turnover_policy.max_turnover_pct == Decimal("0.05")

    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    assert selected is not None
    assert selected.policy_pack_id == "dpm_standard_v1"


def test_policy_pack_apply_turnover_override():
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))
    catalog = parse_policy_pack_catalog(
        '{"dpm_standard_v1":{"turnover_policy":{"max_turnover_pct":"0.01"}}}'
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.max_turnover_pct == Decimal("0.01")


def test_policy_pack_apply_tax_overrides():
    options = EngineOptions(enable_tax_awareness=False, max_realized_capital_gains=None)
    catalog = parse_policy_pack_catalog(
        (
            '{"dpm_standard_v1":{"tax_policy":{"enable_tax_awareness":true,'
            '"max_realized_capital_gains":"75"}}}'
        )
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.enable_tax_awareness is True
    assert effective_options.max_realized_capital_gains == Decimal("75")


def test_policy_pack_apply_settlement_overrides():
    options = EngineOptions(enable_settlement_awareness=False, settlement_horizon_days=5)
    catalog = parse_policy_pack_catalog(
        (
            '{"dpm_standard_v1":{"settlement_policy":{"enable_settlement_awareness":true,'
            '"settlement_horizon_days":3}}}'
        )
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.enable_settlement_awareness is True
    assert effective_options.settlement_horizon_days == 3


def test_policy_pack_apply_constraint_overrides():
    options = EngineOptions(single_position_max_weight=None, group_constraints={})
    catalog = parse_policy_pack_catalog(
        (
            '{"dpm_standard_v1":{"constraint_policy":{"single_position_max_weight":"0.25",'
            '"group_constraints":{"sector:TECH":{"max_weight":"0.20"}}}}}'
        )
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.single_position_max_weight == Decimal("0.25")
    assert "sector:TECH" in effective_options.group_constraints
    assert effective_options.group_constraints["sector:TECH"].max_weight == Decimal("0.20")


def test_policy_pack_apply_workflow_overrides():
    options = EngineOptions(
        enable_workflow_gates=True,
        workflow_requires_client_consent=False,
        client_consent_already_obtained=False,
    )
    catalog = parse_policy_pack_catalog(
        (
            '{"dpm_standard_v1":{"workflow_policy":{"enable_workflow_gates":false,'
            '"workflow_requires_client_consent":true,'
            '"client_consent_already_obtained":true}}}'
        )
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.enable_workflow_gates is False
    assert effective_options.workflow_requires_client_consent is True
    assert effective_options.client_consent_already_obtained is True


def test_policy_pack_resolve_replay_enabled_override_and_fallback():
    catalog = parse_policy_pack_catalog(
        '{"dpm_standard_v1":{"idempotency_policy":{"replay_enabled":false}}}'
    )
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    assert (
        resolve_policy_pack_replay_enabled(default_replay_enabled=True, policy_pack=selected)
        is False
    )

    no_override_catalog = parse_policy_pack_catalog('{"dpm_standard_v1":{"version":"1"}}')
    selected_no_override = resolve_policy_pack_definition(
        resolution=resolution,
        catalog=no_override_catalog,
    )
    assert (
        resolve_policy_pack_replay_enabled(
            default_replay_enabled=True,
            policy_pack=selected_no_override,
        )
        is True
    )
    assert (
        resolve_policy_pack_replay_enabled(
            default_replay_enabled=False,
            policy_pack=None,
        )
        is False
    )


def test_policy_pack_catalog_parse_invalid_json_and_shape():
    assert parse_policy_pack_catalog("{bad-json}") == {}
    assert parse_policy_pack_catalog("[]") == {}


def test_policy_pack_catalog_parse_skips_invalid_rows():
    catalog = parse_policy_pack_catalog(
        '{"bad_row":"x"," ":"x","invalid_turnover":{"turnover_policy":{"max_turnover_pct":"bad"}}}'
    )
    assert catalog == {}


def test_policy_pack_catalog_parse_skips_non_string_and_blank_ids(monkeypatch):
    monkeypatch.setattr(
        policy_pack_module.json,
        "loads",
        lambda _raw: {123: {"version": "1"}, "  ": {"version": "1"}},
    )
    assert policy_pack_module.parse_policy_pack_catalog('{"ignored":"input"}') == {}


def test_policy_pack_resolve_definition_missing_or_none():
    resolution_none = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id=None,
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolve_policy_pack_definition(resolution=resolution_none, catalog={}) is None

    resolution_missing = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="missing_pack",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    assert resolve_policy_pack_definition(resolution=resolution_missing, catalog={}) is None


def test_policy_pack_apply_no_override_returns_original():
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))
    catalog = parse_policy_pack_catalog('{"dpm_standard_v1":{"version":"1"}}')
    resolution = resolve_effective_policy_pack(
        policy_packs_enabled=True,
        request_policy_pack_id="dpm_standard_v1",
        tenant_default_policy_pack_id=None,
        global_default_policy_pack_id=None,
    )
    selected = resolve_policy_pack_definition(resolution=resolution, catalog=catalog)
    assert selected is not None
    effective_options = apply_policy_pack_to_engine_options(options=options, policy_pack=selected)
    assert effective_options.max_turnover_pct == Decimal("0.15")
