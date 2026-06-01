from src.api.services.wave_supportability_diagnostics import (
    operator_actions,
    supportability_issue,
)
from src.core.waves import DpmRebalanceWave


def wave_supportability_payload(wave: DpmRebalanceWave) -> dict[str, object]:
    issues = [
        issue
        for index, item in enumerate(wave.items, start=1)
        if (issue := supportability_issue(wave_id=wave.wave_id, item=item, item_index=index))
        is not None
    ]
    blocked_count = sum(1 for issue in issues if issue["severity"] == "CRITICAL")
    degraded_count = sum(1 for issue in issues if issue["severity"] == "WARNING")
    if blocked_count:
        state = "blocked"
        reason = "wave_blocked_items"
    elif degraded_count:
        state = "degraded"
        reason = "wave_degraded_items"
    else:
        state = "ready"
        reason = "wave_supportability_ready"
    return {
        "wave_id": wave.wave_id,
        "wave_state": wave.state,
        "supportability_state": state,
        "reason": reason,
        "item_count": len(wave.items),
        "issue_counts": {
            "critical": blocked_count,
            "warning": degraded_count,
            "info": sum(1 for issue in issues if issue["severity"] == "INFO"),
        },
        "issues": issues,
        "operator_actions": operator_actions(state=state, issues=issues),
    }


__all__ = ["wave_supportability_payload"]
