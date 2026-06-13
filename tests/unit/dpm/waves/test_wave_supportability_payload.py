from src.api.services.wave_supportability_payload import (
    _issue_counts_by_severity,
    _supportability_state_reason,
    _wave_supportability_issues,
    wave_supportability_payload,
)
from src.core.waves import DpmRebalanceWave, DpmRebalanceWaveItem


def _item(
    *,
    state: str,
    reason_codes: list[str] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> DpmRebalanceWaveItem:
    return DpmRebalanceWaveItem(
        wave_item_id=f"dwi_{state.lower()}",
        portfolio_id="PB_SG_SUPPORTABILITY",
        state=state,
        reason_codes=reason_codes or [],
        diagnostics=diagnostics or {},
    )


def _wave(items: list[DpmRebalanceWaveItem]) -> DpmRebalanceWave:
    return DpmRebalanceWave.model_construct(
        wave_id="dwv_supportability",
        state="SOURCE_CHECKED",
        items=items,
    )


def test_wave_supportability_payload_reports_ready_when_no_issues() -> None:
    payload = wave_supportability_payload(_wave([_item(state="SIMULATED")]))

    assert payload["supportability_state"] == "ready"
    assert payload["reason"] == "wave_supportability_ready"
    assert payload["issue_counts"] == {"critical": 0, "warning": 0, "info": 0}
    assert payload["operator_actions"] == ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]


def test_wave_supportability_payload_counts_blocked_degraded_and_info_issues() -> None:
    payload = wave_supportability_payload(
        _wave(
            [
                _item(state="SOURCE_BLOCKED", reason_codes=["MANDATE_MISSING"]),
                _item(state="SOURCE_DEGRADED", reason_codes=["SOURCE_STALE"]),
                _item(state="CANDIDATE", reason_codes=["SOURCE_CHECK_PENDING"]),
            ]
        )
    )

    assert payload["supportability_state"] == "blocked"
    assert payload["reason"] == "wave_blocked_items"
    assert payload["item_count"] == 3
    assert payload["issue_counts"] == {"critical": 1, "warning": 1, "info": 1}
    assert [issue["support_ref"] for issue in payload["issues"]] == [
        "wave:dwv_supportability:item:1",
        "wave:dwv_supportability:item:2",
        "wave:dwv_supportability:item:3",
    ]
    assert payload["operator_actions"] == [
        "REFRESH_SOURCE_EVIDENCE",
        "REPAIR_SOURCE_DATA",
        "RUN_SOURCE_CHECK",
    ]


def test_wave_supportability_payload_reports_degraded_without_blocked_issues() -> None:
    payload = wave_supportability_payload(_wave([_item(state="SELECTED")]))

    assert payload["supportability_state"] == "degraded"
    assert payload["reason"] == "wave_degraded_items"
    assert payload["issue_counts"] == {"critical": 0, "warning": 1, "info": 0}


def test_wave_supportability_helpers_collect_count_and_classify_issues() -> None:
    issues = _wave_supportability_issues(
        _wave(
            [
                _item(state="SOURCE_BLOCKED", reason_codes=["MANDATE_MISSING"]),
                _item(state="SELECTED"),
                _item(state="CANDIDATE", reason_codes=["SOURCE_CHECK_PENDING"]),
            ]
        )
    )

    counts = _issue_counts_by_severity(issues)

    assert [issue["severity"] for issue in issues] == ["CRITICAL", "WARNING", "INFO"]
    assert counts == {"critical": 1, "warning": 1, "info": 1}
    assert _supportability_state_reason(counts) == ("blocked", "wave_blocked_items")
    assert _supportability_state_reason({"critical": 0, "warning": 1, "info": 0}) == (
        "degraded",
        "wave_degraded_items",
    )
    assert _supportability_state_reason({"critical": 0, "warning": 0, "info": 1}) == (
        "ready",
        "wave_supportability_ready",
    )


def test_wave_supportability_payload_exports_only_payload_builder() -> None:
    from src.api.services import wave_supportability_payload as module

    assert module.__all__ == ["wave_supportability_payload"]
