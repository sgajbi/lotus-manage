"""Published monthly custody joins; caller owns one repeatable-read snapshot."""

from typing import Any

from src.core.composite_definition_versions import decode_composite_definition
from src.core.composite_eligibility.monthly_evidence import (
    MonthlyPublicationReceipt,
    published_monthly_receipt,
    require_monthly_receipt_lineage,
)
from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentApprovalContent as MonthlyAmendmentApproval,
)
from src.core.composite_repository import DpmCompositeConflictError
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.infrastructure.composites import evaluation_control, policy_control, publication
from src.infrastructure.mandates.serialization import load_model_json


def _conflict() -> DpmCompositeConflictError:
    return DpmCompositeConflictError("COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT")


def _membership(connection: Any, key: tuple[str, str, str, str]) -> DpmCompositeMembershipRevision:
    row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_membership_revisions
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s""",
        key,
    ).fetchone()
    if row is None:
        raise _conflict()
    result = load_model_json(DpmCompositeMembershipRevision, row["payload_json"])
    if (
        result.tenant_id,
        result.composite_id,
        result.definition_version,
        result.membership_revision,
    ) != key or result.content_hash != row["content_hash"]:
        raise _conflict()
    return result


def _universe(
    connection: Any, key: tuple[str, str, str, str, str]
) -> DpmCompositeUniverseAttestation:
    row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_universe_attestations
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s
        AND membership_revision=%s AND attestation_version=%s""",
        key,
    ).fetchone()
    if row is None:
        raise _conflict()
    result = load_model_json(DpmCompositeUniverseAttestation, row["payload_json"])
    if (
        result.tenant_id,
        result.composite_id,
        result.definition_version,
        result.membership_revision,
        result.attestation_version,
    ) != key or result.content_hash != row["content_hash"]:
        raise _conflict()
    return result


def resolve(
    connection: Any,
    key: tuple[str, str, str, str],
    approval_content_hash: str,
) -> MonthlyPublicationReceipt | None:
    receipt = _resolve_single(connection, key, approval_content_hash)
    if receipt is not None:
        try:
            require_monthly_receipt_lineage(
                receipt,
                lambda binding: _resolve_single(
                    connection, (*key[:3], binding.revision), binding.digest
                ),
            )
        except ValueError as error:
            raise _conflict() from error
    return receipt


def _resolve_single(
    connection: Any,
    key: tuple[str, str, str, str],
    approval_content_hash: str,
) -> MonthlyPublicationReceipt | None:
    approval = evaluation_control.get_approval(connection, key)
    if approval is None or approval.proposal.publication_evidence_version is None:
        return None
    if approval.content_hash != approval_content_hash:
        raise DpmCompositeConflictError("COMPOSITE_MONTHLY_EVIDENCE_BINDING_MISMATCH")
    proposal = evaluation_control.get_proposal(connection, key)
    policy_key = (*key[:3], approval.proposal.evaluation.month)
    policy = policy_control.get_approval(connection, policy_key)
    policy_proposal = policy_control.get_proposal(
        connection, (*policy_key, approval.proposal.policy_approval.proposal.proposal_revision)
    )
    definition_row = connection.execute(
        """SELECT content_hash, payload_json FROM dpm_composite_definitions
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s""",
        key[:3],
    ).fetchone()
    if proposal is None or policy is None or policy_proposal is None or definition_row is None:
        raise _conflict()
    definition = decode_composite_definition(definition_row["payload_json"])
    if (definition.tenant_id, definition.composite_id, definition.definition_version) != key[
        :3
    ] or definition.content_hash != definition_row["content_hash"]:
        raise _conflict()
    parent = _membership(connection, (*key[:3], proposal.parent_membership_revision))
    member_key = (*key[:3], proposal.target_membership_revision)
    member = _membership(connection, member_key)
    universe = _universe(connection, (*member_key, key[3]))
    retained_input = _universe(
        connection,
        (*key[:3], proposal.parent_membership_revision, proposal.universe.attestation_version),
    )
    if retained_input != proposal.universe:
        raise _conflict()
    publication_row = connection.execute(
        """SELECT sequence FROM dpm_composite_membership_publications
        WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s AND membership_revision=%s""",
        member_key,
    ).fetchone()
    if publication_row is None:
        raise _conflict()
    published = publication.get_publication(
        connection=connection, tenant_id=key[0], sequence=publication_row["sequence"]
    )
    if published is None:
        raise _conflict()
    parent_publication = None
    if isinstance(approval, MonthlyAmendmentApproval):
        parent_row = connection.execute(
            """SELECT sequence FROM dpm_composite_membership_publications
            WHERE tenant_id=%s AND composite_id=%s AND definition_version=%s
            AND membership_revision=%s""",
            (*key[:3], proposal.parent_membership_revision),
        ).fetchone()
        if parent_row is None:
            raise _conflict()
        parent_publication = publication.get_publication(
            connection=connection, tenant_id=key[0], sequence=parent_row["sequence"]
        )
    return published_monthly_receipt(
        definition=definition,
        approval=approval,
        retained_policy=policy,
        retained_policy_proposal=policy_proposal,
        retained_proposal=proposal,
        parent=parent,
        membership=member,
        universe=universe,
        publication=published,
        parent_publication=parent_publication,
    )
