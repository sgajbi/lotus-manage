"""PostgreSQL immutable monthly configuration custody; caller owns the transaction."""

from typing import Any

from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_definition_versions import decode_composite_definition
from src.infrastructure.mandates.serialization import dump_model_json, load_model_json


def proposal_key(proposal: MonthlyPolicyProposal) -> tuple[str, str, str, str, str]:
    scope = proposal.policy.scope
    return (
        scope.tenant_id,
        scope.composite_id,
        scope.definition_version,
        proposal.policy.month,
        proposal.proposal_revision,
    )


def save_proposal(connection: Any, proposal: MonthlyPolicyProposal) -> None:
    proposal = MonthlyPolicyProposal.model_validate(proposal.model_dump(mode="json"))
    key = proposal_key(proposal)
    definition = connection.execute(
        "SELECT payload_json FROM dpm_composite_definitions WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s",
        key[:3],
    ).fetchone()
    if definition is None:
        raise ValueError("COMPOSITE_DEFINITION_NOT_FOUND")
    stored = decode_composite_definition(definition["payload_json"])
    if (stored.eligibility_policy_version, stored.strategy_code) != (
        proposal.eligibility_policy_version,
        proposal.policy.scope.strategy_code,
    ):
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_DEFINITION_POLICY_MISMATCH")
    connection.execute(
        """INSERT INTO dpm_composite_monthly_policy_proposals
        (tenant_id, composite_id, definition_version, month, proposal_revision, content_hash, payload_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (tenant_id, composite_id, definition_version, month, proposal_revision) DO NOTHING""",
        (*key, proposal.content_hash, dump_model_json(proposal)),
    )
    retained = get_proposal(connection, key)
    if retained is None or retained.content_hash != proposal.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT")


def get_proposal(
    connection: Any, key: tuple[str, str, str, str, str]
) -> MonthlyPolicyProposal | None:
    row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_monthly_policy_proposals
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND month=%s AND proposal_revision=%s""",
        key,
    ).fetchone()
    if row is None:
        return None
    result = load_model_json(MonthlyPolicyProposal, row["payload_json"])
    if result.content_hash != row["content_hash"] or proposal_key(result) != key:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_PROPOSAL_INTEGRITY_CONFLICT")
    return result


def save_approval(connection: Any, approval: MonthlyPolicyApproval) -> None:
    approval = MonthlyPolicyApproval.model_validate(approval.model_dump(mode="json"))
    key = proposal_key(approval.proposal)
    proposal = get_proposal(connection, key)
    if proposal is None or proposal.content_hash != approval.proposal.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVAL_PROPOSAL_MISMATCH")
    connection.execute(
        """INSERT INTO dpm_composite_monthly_policy_approvals
        (tenant_id, composite_id, definition_version, month, proposal_revision,
        proposal_content_hash, content_hash, payload_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (tenant_id, composite_id, month) DO NOTHING""",
        (*key, proposal.content_hash, approval.content_hash, dump_model_json(approval)),
    )
    retained = get_approval(connection, key[:4])
    if retained is None or retained.content_hash != approval.content_hash:
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_ACTIVE_POLICY_CONFLICT")


def get_approval(connection: Any, key: tuple[str, str, str, str]) -> MonthlyPolicyApproval | None:
    row = connection.execute(
        """SELECT content_hash, proposal_content_hash, payload_json FROM dpm_composite_monthly_policy_approvals
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND month=%s""",
        key,
    ).fetchone()
    if row is None:
        return None
    result = load_model_json(MonthlyPolicyApproval, row["payload_json"])
    if (result.content_hash, result.proposal.content_hash, proposal_key(result.proposal)[:4]) != (
        row["content_hash"],
        row["proposal_content_hash"],
        key,
    ):
        raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_APPROVAL_INTEGRITY_CONFLICT")
    return result
