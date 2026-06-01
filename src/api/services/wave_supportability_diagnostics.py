from src.core.waves import DpmRebalanceWaveItem


def supportability_issue(
    *,
    wave_id: str,
    item: DpmRebalanceWaveItem,
    item_index: int,
) -> dict[str, object] | None:
    if item.state in {"APPROVED", "STAGED", "HANDOFF_READY", "PROOF_PACK_READY", "SIMULATED"}:
        if (
            item.state != "PROOF_PACK_READY"
            or item.diagnostics.get("proof_pack_state") != "DEGRADED"
        ):
            return None
    severity = supportability_severity(item)
    if severity is None:
        return None
    reason_codes = item.reason_codes or [supportability_reason(item)]
    return {
        "support_ref": f"wave:{wave_id}:item:{item_index}",
        "item_state": item.state,
        "severity": severity,
        "source_owner": supportability_source_owner(item),
        "reason_codes": reason_codes,
        "remediation_route": supportability_remediation(item),
    }


def supportability_severity(item: DpmRebalanceWaveItem) -> str | None:
    if item.state in {"SOURCE_BLOCKED", "SIMULATION_BLOCKED"}:
        return "CRITICAL"
    if item.state in {"SOURCE_DEGRADED", "REVIEW_REQUIRED", "SELECTED"}:
        return "WARNING"
    if item.state == "PROOF_PACK_READY" and item.diagnostics.get("proof_pack_state") == "DEGRADED":
        return "WARNING"
    if item.state in {"CANDIDATE", "SOURCE_READY"}:
        return "INFO"
    return None


def supportability_reason(item: DpmRebalanceWaveItem) -> str:
    reason_by_state = {
        "CANDIDATE": "SOURCE_CHECK_PENDING",
        "SOURCE_READY": "SIMULATION_PENDING",
        "SOURCE_DEGRADED": "SOURCE_DEGRADED",
        "REVIEW_REQUIRED": "REVIEW_REQUIRED",
        "SOURCE_BLOCKED": "SOURCE_BLOCKED",
        "SIMULATION_BLOCKED": "SIMULATION_BLOCKED",
        "SELECTED": "PROOF_PACK_PENDING_OR_DEGRADED",
        "PROOF_PACK_READY": "PROOF_PACK_DEGRADED",
    }
    return reason_by_state.get(item.state, "WAVE_ITEM_SUPPORTABILITY_REVIEW")


def supportability_source_owner(item: DpmRebalanceWaveItem) -> str:
    owner = item.diagnostics.get("source_owner")
    if isinstance(owner, str) and owner:
        return owner
    if item.state in {"SOURCE_BLOCKED", "SOURCE_DEGRADED", "REVIEW_REQUIRED"}:
        return "lotus-manage"
    if item.state == "SIMULATION_BLOCKED":
        return "lotus-manage-construction"
    if item.state in {"SELECTED", "PROOF_PACK_READY"}:
        return "lotus-manage-proof-pack"
    return "lotus-manage"


def supportability_remediation(item: DpmRebalanceWaveItem) -> str:
    explicit = item.diagnostics.get("required_action")
    if isinstance(explicit, str) and explicit:
        return explicit
    remediation_by_state = {
        "CANDIDATE": "RUN_SOURCE_CHECK",
        "SOURCE_READY": "RUN_WAVE_SIMULATION",
        "SOURCE_DEGRADED": "REFRESH_SOURCE_EVIDENCE",
        "REVIEW_REQUIRED": "PERFORM_HUMAN_REVIEW",
        "SOURCE_BLOCKED": "REPAIR_SOURCE_DATA",
        "SIMULATION_BLOCKED": "SUPPLY_VALID_RFC0039_CONSTRUCTION_INPUT",
        "SELECTED": "GENERATE_OR_REVIEW_PROOF_PACK",
        "PROOF_PACK_READY": "REVIEW_DEGRADED_PROOF_PACK",
    }
    return remediation_by_state.get(item.state, "REVIEW_WAVE_ITEM_SUPPORTABILITY")


def operator_actions(*, state: str, issues: list[dict[str, object]]) -> list[str]:
    if state == "ready":
        return ["CONTINUE_GOVERNED_WAVE_WORKFLOW"]
    routes = {
        str(issue["remediation_route"])
        for issue in issues
        if isinstance(issue.get("remediation_route"), str)
    }
    return sorted(routes)


__all__ = [
    "operator_actions",
    "supportability_issue",
    "supportability_reason",
    "supportability_remediation",
    "supportability_severity",
    "supportability_source_owner",
]
