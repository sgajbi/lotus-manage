"""Real storage corruption refuses custody; synthetic inputs do not qualify Core."""

import pytest
import psycopg
import json
from contextlib import closing
from psycopg import sql
from src.core.composite_repository import DpmCompositeConflictError
from src.api.services.composite_monthly_eligibility import MonthlyApprovalRequest
from src.core.composite_eligibility.approval import MonthlyPolicyProposal, MonthlyPolicyApproval
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationProposal,
    MonthlyEvaluationApproval,
    monthly_evaluation_approval_claims_hash,
)
from tests.integration.dpm.composites.test_composite_monthly_evaluation_postgres import (
    material as material,
    candidate,
)


@pytest.mark.parametrize(
    "case,code",
    [
        ("policy_identity", "COMPOSITE_ELIGIBILITY_DEFINITION_POLICY_MISMATCH"),
        ("policy_proposal", "COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT"),
        ("policy_approval", "COMPOSITE_ELIGIBILITY_APPROVAL_PROPOSAL_MISMATCH"),
        ("evaluation_proposal", "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT"),
        ("evaluation_approval", "COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT"),
    ],
)
def test_real_custody_rejects_valid_but_unowned_or_conflicting_material(material, case, code):
    _, repository, scope, _, service, _, parent = material
    proposal = candidate(material)
    policy_approval = proposal.policy_approval
    if case.startswith("policy"):
        wire = policy_approval.proposal.model_dump(mode="json")
        wire["content_hash"] = ""
        if case == "policy_identity":
            wire["eligibility_policy_version"] = "unowned-policy"
        elif case == "policy_proposal":
            wire["proposed_by"] = "other-maker"
        else:
            wire["proposal_revision"] = "unretained-proposal"
        changed = MonthlyPolicyProposal.model_validate(wire)
        if case == "policy_approval":
            altered_approval = MonthlyPolicyApproval(
                proposal=changed,
                approved_by=policy_approval.approved_by,
                approved_at=policy_approval.approved_at,
            )
            operation = repository.save_monthly_policy_approval
            command = {"approval": altered_approval}
        else:
            operation = repository.save_monthly_policy_proposal
            command = {"proposal": changed}
    elif case == "evaluation_proposal":
        wire = proposal.model_dump(mode="json")
        wire.update(content_hash="", proposed_by="other-maker")
        changed = MonthlyEvaluationProposal.model_validate(wire)
        operation = repository.save_monthly_evaluation_proposal
        command = {"proposal": changed}
    else:
        from src.core.composite_eligibility.publication import build_monthly_publication

        approved = service.approve(
            **scope,
            evaluation_revision=proposal.evaluation_revision,
            actor_id="synthetic-checker",
            command=MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash),
        )
        alternative = build_monthly_publication(
            proposal, parent, approved_by="other-checker", approved_at=approved.approved_at
        )[0]
        operation = repository.save_monthly_evaluation_approval
        command = {"approval": alternative}
    before = repository.list_publications(tenant_id=scope["tenant_id"], after_sequence=0, limit=10)
    with pytest.raises(DpmCompositeConflictError, match=code):
        operation(**command)
    assert (
        repository.list_publications(tenant_id=scope["tenant_id"], after_sequence=0, limit=10)
        == before
    )
    assert repository.get_monthly_policy_approval(**scope, month="2026-09") == policy_approval


@pytest.mark.parametrize(
    "stage", ["policy_proposal", "policy_approval", "evaluation_proposal", "evaluation_approval"]
)
@pytest.mark.parametrize("corruption", ["hash", "identity"])
def test_real_stored_monthly_hash_and_identity_corruption_refuses_without_publication(
    material, stage, corruption
):
    dsn, repository, scope, _, service, _, _ = material
    proposal = candidate(material)
    if stage == "evaluation_approval":
        service.approve(
            **scope,
            evaluation_revision=proposal.evaluation_revision,
            actor_id="synthetic-checker",
            command=MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash),
        )
    before = repository.list_publications(tenant_id=scope["tenant_id"], after_sequence=0, limit=10)
    table = "dpm_composite_monthly_" + stage + "s"
    protected_constraint = {
        ("policy_proposal", "hash"): "monthly_policy_approval_mode_fk",
        ("policy_proposal", "identity"): "monthly_policy_approval_mode_fk",
        ("policy_approval", "hash"): "monthly_evaluation_policy_mode_fk",
        ("policy_approval", "identity"): "monthly_evaluation_policy_mode_fk",
        ("evaluation_approval", "identity"): "monthly_evaluation_approval_mode_fk",
    }.get((stage, corruption))
    getter = getattr(repository, "get_monthly_" + stage)
    selectors = (
        {"month": "2026-09"}
        if stage.startswith("policy")
        else {"evaluation_revision": proposal.evaluation_revision}
    )
    if stage == "policy_proposal":
        selectors["proposal_revision"] = "synthetic-config-r1"
    retained = getter(**scope, **selectors)
    with closing(psycopg.connect(dsn)) as connection:
        prior_controls = _monthly_control_rows(connection, scope["tenant_id"])
        if protected_constraint is not None:
            with pytest.raises(psycopg.errors.ForeignKeyViolation) as failure:
                _corrupt_monthly_row(connection, table, stage, corruption, scope["tenant_id"])
            assert failure.value.diag.constraint_name == protected_constraint
            connection.rollback()
            assert _monthly_control_rows(connection, scope["tenant_id"]) == prior_controls
        else:
            _corrupt_monthly_row(connection, table, stage, corruption, scope["tenant_id"])
            connection.commit()
    if protected_constraint is not None:
        assert getter(**scope, **selectors) == retained
    else:
        prefix = "COMPOSITE_ELIGIBILITY_" + (
            "EVALUATION_" if stage.startswith("evaluation") else ""
        )
        code = (
            prefix
            + ("APPROVAL" if stage.endswith("approval") else "PROPOSAL")
            + "_INTEGRITY_CONFLICT"
        )
        with pytest.raises(DpmCompositeConflictError, match=code):
            getter(**scope, **selectors)
    assert (
        repository.list_publications(tenant_id=scope["tenant_id"], after_sequence=0, limit=10)
        == before
    )


def _monthly_control_rows(connection, tenant_id):
    return {
        stage: connection.execute(
            sql.SQL(
                "SELECT to_jsonb(t) FROM {} t WHERE tenant_id=%s ORDER BY to_jsonb(t)::text"
            ).format(sql.Identifier("dpm_composite_monthly_" + stage + "s")),
            (tenant_id,),
        ).fetchall()
        for stage in (
            "policy_proposal",
            "policy_approval",
            "evaluation_proposal",
            "evaluation_approval",
        )
    }


def _corrupt_monthly_row(connection, table, stage, corruption, tenant_id):
    if corruption == "hash":
        cursor = connection.execute(
            sql.SQL(
                "UPDATE {} SET content_hash=%s WHERE tenant_id=%s RETURNING content_hash"
            ).format(sql.Identifier(table)),
            ("sha256:" + "0" * 64, tenant_id),
        )
    else:
        field = "proposal_revision" if stage.startswith("policy") else "evaluation_revision"
        wire = connection.execute(
            sql.SQL("SELECT payload_json FROM {} WHERE tenant_id=%s").format(sql.Identifier(table)),
            (tenant_id,),
        ).fetchone()[0]
        proposal_wire = wire["proposal"] if stage.endswith("approval") else wire
        proposal_wire.update(content_hash="", **{field: "foreign-revision"})
        proposal_type = (
            MonthlyPolicyProposal if stage.startswith("policy") else MonthlyEvaluationProposal
        )
        rebound = proposal_type.model_validate(proposal_wire)
        if stage.endswith("approval"):
            wire.update(proposal=rebound.model_dump(mode="json"), content_hash="")
            if stage == "evaluation_approval":
                wire["claims_digest"] = monthly_evaluation_approval_claims_hash(
                    rebound, approved_by=wire["approved_by"], approved_at=wire["approved_at"]
                )
            approval_type = (
                MonthlyPolicyApproval if stage.startswith("policy") else MonthlyEvaluationApproval
            )
            rebound = approval_type.model_validate(wire)
        cursor = connection.execute(
            sql.SQL(
                "UPDATE {} SET payload_json=%s::jsonb, content_hash=%s WHERE tenant_id=%s RETURNING payload_json"
            ).format(sql.Identifier(table)),
            (
                json.dumps(rebound.model_dump(mode="json")),
                rebound.content_hash,
                tenant_id,
            ),
        )
    assert cursor.fetchone() is not None
    assert cursor.fetchone() is None


@pytest.mark.parametrize("lost", ["universe", "publication"])
def test_real_approved_membership_read_refuses_missing_publication_evidence(material, lost):
    dsn, repository, scope, _, service, _, _ = material
    proposal = candidate(material)
    approval = service.approve(
        **scope,
        evaluation_revision=proposal.evaluation_revision,
        actor_id="synthetic-checker",
        command=MonthlyApprovalRequest(expected_proposal_content_hash=proposal.content_hash),
    )
    table = (
        "dpm_composite_universe_attestations"
        if lost == "universe"
        else "dpm_composite_membership_publications"
    )
    with psycopg.connect(dsn) as connection:
        cursor = connection.execute(
            sql.SQL(
                "DELETE FROM {} WHERE tenant_id=%s AND membership_revision=%s RETURNING membership_revision"
            ).format(sql.Identifier(table)),
            (scope["tenant_id"], proposal.target_membership_revision),
        )
        assert cursor.fetchone() is not None
        assert cursor.fetchone() is None
    code = (
        "COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH"
        if lost == "universe"
        else "COMPOSITE_PUBLICATION_INTEGRITY_CONFLICT"
    )
    with pytest.raises(DpmCompositeConflictError, match=code):
        service.get_approval(**scope, evaluation_revision=proposal.evaluation_revision)
    retained = repository.get_membership_revision(
        **scope, membership_revision=proposal.target_membership_revision
    )
    assert retained.content_hash == approval.membership_content_hash
