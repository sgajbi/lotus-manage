from src.api.services.wave_portfolio_sources import (
    diagnostics_from_portfolio,
    optional_str,
    source_refs_from_portfolio,
    trigger_source_refs,
)


def _source_ref(source_id: str) -> dict[str, object]:
    return {
        "source_system": "lotus-core",
        "source_type": "PORTFOLIO_SNAPSHOT",
        "source_id": source_id,
        "source_version": "2026-05-03",
        "supportability_state": "READY",
    }


def test_source_refs_from_portfolio_validates_dict_refs_only() -> None:
    source_refs = source_refs_from_portfolio(
        {
            "portfolio_id": "PB_SG_SOURCE",
            "source_refs": [_source_ref("snap_001"), "not-a-ref", _source_ref("snap_002")],
        }
    )

    assert [ref.source_id for ref in source_refs] == ["snap_001", "snap_002"]
    assert [ref.supportability_state for ref in source_refs] == ["READY", "READY"]


def test_source_refs_from_portfolio_rejects_non_list_payload() -> None:
    assert source_refs_from_portfolio({"source_refs": "not-a-list"}) == []


def test_trigger_source_refs_flattens_portfolio_refs() -> None:
    refs = trigger_source_refs(
        [
            {"portfolio_id": "PB_SG_001", "source_refs": [_source_ref("snap_001")]},
            {"portfolio_id": "PB_SG_002", "source_refs": [_source_ref("snap_002")]},
        ]
    )

    assert [ref.source_id for ref in refs] == ["snap_001", "snap_002"]


def test_diagnostics_from_portfolio_preserves_string_keys_only() -> None:
    diagnostics = diagnostics_from_portfolio({"diagnostics": {"source": "ready", 1: "ignored"}})

    assert diagnostics == {"source": "ready"}


def test_diagnostics_from_portfolio_rejects_non_dict_payload() -> None:
    assert diagnostics_from_portfolio({"diagnostics": ["not", "a", "dict"]}) == {}


def test_optional_str_normalizes_blank_and_non_string_values() -> None:
    assert optional_str(None) is None
    assert optional_str("   ") is None
    assert optional_str(" MANDATE_001 ") == "MANDATE_001"
    assert optional_str(123) == "123"


def test_wave_portfolio_sources_exports_only_source_helpers() -> None:
    from src.api.services import wave_portfolio_sources

    assert wave_portfolio_sources.__all__ == [
        "diagnostics_from_portfolio",
        "optional_str",
        "source_refs_from_portfolio",
        "trigger_source_refs",
    ]
