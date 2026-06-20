from src.api.services.wave_supportability_diagnostics import (
    _should_emit_supportability_issue,
    _supportability_reason_codes,
    operator_actions,
    supportability_issue,
    supportability_severity,
    supportability_source_owner,
)
from src.core.waves import DpmRebalanceWaveItem


def _item(
    *,
    state: str,
    reason_codes: list[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id="dwi_supportability",
        portfolio_id="PB_SG_CONFIDENTIAL",
        state=state,  # type: ignore[arg-type]
        reason_codes=reason_codes or [],
        diagnostics=diagnostics or {},
    )


def test_supportability_issue_excludes_completed_items_without_degraded_proof_pack() -> None:
    assert (
        supportability_issue(wave_id="dwv_1", item=_item(state="HANDOFF_READY"), item_index=1)
        is None
    )


def test_supportability_issue_includes_degraded_proof_pack_and_fallback_reason() -> None:
    item = _item(
        state="PROOF_PACK_READY",
        diagnostics={"proof_pack_state": "DEGRADED"},
    )

    issue = supportability_issue(wave_id="dwv_1", item=item, item_index=3)

    assert _should_emit_supportability_issue(item)
    assert _supportability_reason_codes(item) == ["PROOF_PACK_DEGRADED"]
    assert issue is not None
    assert issue["severity"] == "WARNING"
    assert issue["reason_codes"] == ["PROOF_PACK_DEGRADED"]
    assert issue["remediation_route"] == "REVIEW_DEGRADED_PROOF_PACK"


def test_supportability_issue_preserves_explicit_owner_and_action() -> None:
    issue = supportability_issue(
        wave_id="dwv_1",
        item=_item(
            state="SIMULATION_BLOCKED",
            reason_codes=["RISK_INPUT_STALE"],
            diagnostics={
                "source_owner": "lotus-risk",
                "required_action": "REFRESH_RISK_INPUTS",
            },
        ),
        item_index=2,
    )

    assert issue == {
        "support_ref": "wave:dwv_1:item:2",
        "item_state": "SIMULATION_BLOCKED",
        "severity": "CRITICAL",
        "source_owner": "lotus-risk",
        "reason_codes": ["RISK_INPUT_STALE"],
        "remediation_route": "REFRESH_RISK_INPUTS",
    }


def test_supportability_severity_maps_wave_item_states() -> None:
    expectations = {
        "SOURCE_BLOCKED": "CRITICAL",
        "SIMULATION_BLOCKED": "CRITICAL",
        "SOURCE_DEGRADED": "WARNING",
        "REVIEW_REQUIRED": "WARNING",
        "SELECTED": "WARNING",
        "CANDIDATE": "INFO",
        "SOURCE_READY": "INFO",
        "SIMULATED": None,
    }

    for state, expected in expectations.items():
        assert supportability_severity(_item(state=state)) == expected


def test_supportability_severity_warns_only_on_degraded_proof_pack_ready_item() -> None:
    assert (
        supportability_severity(
            _item(state="PROOF_PACK_READY", diagnostics={"proof_pack_state": "DEGRADED"})
        )
        == "WARNING"
    )
    assert supportability_severity(_item(state="PROOF_PACK_READY")) is None


def test_supportability_source_owner_maps_wave_item_states_and_explicit_owner() -> None:
    expectations = {
        "SOURCE_BLOCKED": "lotus-manage",
        "SOURCE_DEGRADED": "lotus-manage",
        "REVIEW_REQUIRED": "lotus-manage",
        "SIMULATION_BLOCKED": "lotus-manage-construction",
        "SELECTED": "lotus-manage-proof-pack",
        "PROOF_PACK_READY": "lotus-manage-proof-pack",
        "CANDIDATE": "lotus-manage",
    }

    for state, expected in expectations.items():
        assert supportability_source_owner(_item(state=state)) == expected

    assert (
        supportability_source_owner(
            _item(state="SIMULATION_BLOCKED", diagnostics={"source_owner": "lotus-risk"})
        )
        == "lotus-risk"
    )


def test_operator_actions_preserve_ready_and_sorted_remediation_routes() -> None:
    assert operator_actions(state="ready", issues=[]) == ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]
    assert operator_actions(
        state="blocked",
        issues=[
            {"remediation_route": "REPAIR_SOURCE_DATA"},
            {"remediation_route": "REFRESH_RISK_INPUTS"},
            {"remediation_route": "REPAIR_SOURCE_DATA"},
        ],
    ) == ["REFRESH_RISK_INPUTS", "REPAIR_SOURCE_DATA"]
