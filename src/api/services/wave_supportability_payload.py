from src.api.services.wave_supportability_diagnostics import (
    operator_actions,
    supportability_issue,
)
from src.core.waves import DpmRebalanceWave

_ISSUE_SEVERITIES = ("CRITICAL", "WARNING", "INFO")


def _wave_supportability_issues(wave: DpmRebalanceWave) -> list[dict[str, object]]:
    return [
        issue
        for index, item in enumerate(wave.items, start=1)
        if (issue := supportability_issue(wave_id=wave.wave_id, item=item, item_index=index))
        is not None
    ]


def _issue_counts_by_severity(issues: list[dict[str, object]]) -> dict[str, int]:
    return {
        severity.lower(): sum(1 for issue in issues if issue["severity"] == severity)
        for severity in _ISSUE_SEVERITIES
    }


def _supportability_state_reason(issue_counts: dict[str, int]) -> tuple[str, str]:
    if issue_counts["critical"]:
        return "blocked", "wave_blocked_items"
    if issue_counts["warning"]:
        return "degraded", "wave_degraded_items"
    return "ready", "wave_supportability_ready"


def wave_supportability_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    issues = _wave_supportability_issues(wave)
    issue_counts = _issue_counts_by_severity(issues)
    state, reason = _supportability_state_reason(issue_counts)
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "supportability_state": state,
        "reason": reason,
        "item_count": len(wave.items),
        "issue_counts": issue_counts,
        "issues": issues,
        "operator_actions": operator_actions(state=state, issues=issues),
    }


__all__ = ["wave_supportability_payload"]
