"""Populated 0041 controls keep their exact payload/hash and legacy behavior after 0042."""

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

import src.infrastructure.postgres_migrations as migrations
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationProposal
from src.core.composite_eligibility.publication import build_monthly_publication
from src.infrastructure.composites import membership_store, universe_store
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_eligibility_helpers import retained_repository, source_snapshot
from tests.composite_staged_eligibility_helpers import lifecycle_material, CHECKER, OBSERVED
from tests.integration.dpm.network_runtime import disposable_database

CONTROL_TABLES = (
    "dpm_composite_monthly_policy_proposals",
    "dpm_composite_monthly_policy_approvals",
    "dpm_composite_monthly_evaluation_proposals",
    "dpm_composite_monthly_evaluation_approvals",
)
CANONICAL_TABLES = (
    "dpm_composite_definitions",
    "dpm_composite_membership_revisions",
    "dpm_composite_universe_attestations",
    "dpm_composite_membership_publications",
)


def legacy_material():
    snapshot = source_snapshot()
    seed, universe = retained_repository(snapshot)
    scope = dict(
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
    )
    parent = seed.get_membership_revision(**scope, membership_revision="synthetic-membership")
    _, _, policy, approval, _, _, _, _ = lifecycle_material()
    evaluated = evaluate_monthly_eligibility(
        policy.proposal.policy,
        snapshot,
        evaluated_at=OBSERVED,
        universe_content_hash=universe.content_hash,
    )
    proposal = MonthlyEvaluationProposal(
        evaluation_revision="synthetic-legacy-evaluation",
        target_membership_revision="synthetic-legacy-membership",
        parent_membership_revision=parent.membership_revision,
        parent_membership_content_hash=parent.content_hash,
        policy_approval=approval.approval,
        universe=universe,
        observations=snapshot,
        evaluation=evaluated,
        proposed_by=policy.proposal.proposed_by,
        proposed_at=OBSERVED,
        correlation_id="synthetic-legacy-upgrade",
    )
    checked, member, final_universe = build_monthly_publication(
        proposal, parent, approved_by=CHECKER, approved_at=OBSERVED
    )
    return (
        seed.get_definition(**scope),
        parent,
        universe,
        policy.proposal,
        approval.approval,
        proposal,
        checked,
        member,
        final_universe,
    )


def seed_0041(connection):
    definition, parent, universe, policy, approval, proposal, checked, member, final_universe = (
        legacy_material()
    )
    scope = (definition.tenant_id, definition.composite_id, definition.definition_version)
    connection.execute(
        "INSERT INTO dpm_composite_definitions (tenant_id,composite_id,definition_version,inception_date,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s::jsonb)",
        (*scope, definition.inception_date, definition.content_hash, definition.model_dump_json()),
    )
    membership_store.store_membership_revision(connection=connection, revision=parent)
    universe_store.store_universe_attestation(connection=connection, attestation=universe)
    connection.execute(
        "INSERT INTO dpm_composite_monthly_policy_proposals (tenant_id,composite_id,definition_version,month,proposal_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)",
        (
            *scope,
            policy.policy.month,
            policy.proposal_revision,
            policy.content_hash,
            policy.model_dump_json(),
        ),
    )
    connection.execute(
        "INSERT INTO dpm_composite_monthly_policy_approvals (tenant_id,composite_id,definition_version,month,proposal_revision,proposal_content_hash,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
        (
            *scope,
            policy.policy.month,
            policy.proposal_revision,
            policy.content_hash,
            approval.content_hash,
            approval.model_dump_json(),
        ),
    )
    connection.execute(
        "INSERT INTO dpm_composite_monthly_evaluation_proposals (tenant_id,composite_id,definition_version,month,evaluation_revision,parent_membership_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
        (
            *scope,
            policy.policy.month,
            proposal.evaluation_revision,
            parent.membership_revision,
            proposal.content_hash,
            proposal.model_dump_json(),
        ),
    )
    membership_store.store_membership_revision(connection=connection, revision=member)
    universe_store.store_universe_attestation(connection=connection, attestation=final_universe)
    connection.execute(
        "INSERT INTO dpm_composite_monthly_evaluation_approvals (tenant_id,composite_id,definition_version,month,evaluation_revision,membership_revision,content_hash,payload_json) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
        (
            *scope,
            policy.policy.month,
            proposal.evaluation_revision,
            member.membership_revision,
            checked.content_hash,
            checked.model_dump_json(),
        ),
    )
    return scope, policy, approval, proposal, checked


def payload_rows(connection):
    return {
        table: connection.execute(
            sql.SQL("SELECT content_hash,payload_json FROM {} ORDER BY content_hash").format(
                sql.Identifier(table)
            )
        ).fetchall()
        for table in (*CONTROL_TABLES, *CANONICAL_TABLES)
        if table != "dpm_composite_membership_publications"
    } | {
        "dpm_composite_membership_publications": connection.execute(
            "SELECT * FROM dpm_composite_membership_publications ORDER BY sequence"
        ).fetchall()
    }


def test_populated_0041_to_0042_is_repeatable_preserves_all_payloads_and_legacy_api_replay(
    monkeypatch,
):
    original_loader = migrations._load_migrations
    with monkeypatch.context() as prior_loader:
        prior_loader.setattr(
            migrations,
            "_load_migrations",
            lambda *, namespace: [
                item for item in original_loader(namespace=namespace) if item.version <= "0041"
            ],
        )
        with disposable_database() as dsn:
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                scope, policy, approval, proposal, checked = seed_0041(connection)
                prior = payload_rows(connection)
                assert all(prior.values())
                assert (
                    connection.execute(
                        "SELECT to_regclass('dpm_composite_eligibility_subjects') AS name"
                    ).fetchone()["name"]
                    is None
                )
            prior_loader.undo()
            for _ in range(2):
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    assert payload_rows(connection) == prior
                    for table in CONTROL_TABLES:
                        row = connection.execute(
                            sql.SQL(
                                "SELECT custody_mode,subject_revision,subject_content_hash FROM {}"
                            ).format(sql.Identifier(table))
                        ).fetchone()
                        assert row == {
                            "custody_mode": "LEGACY",
                            "subject_revision": None,
                            "subject_content_hash": None,
                        }
            fresh = PostgresDpmCompositeRepository(dsn=dsn)
            args = dict(zip(("tenant_id", "composite_id", "definition_version"), scope))
            assert (
                fresh.get_monthly_policy_proposal(
                    **args, month=policy.policy.month, proposal_revision=policy.proposal_revision
                )
                == policy
            )
            assert fresh.get_monthly_policy_approval(**args, month=policy.policy.month) == approval
            assert (
                fresh.get_monthly_evaluation_proposal(
                    **args, evaluation_revision=proposal.evaluation_revision
                )
                == proposal
            )
            assert (
                fresh.get_monthly_evaluation_approval(
                    **args, evaluation_revision=proposal.evaluation_revision
                )
                == checked
            )
            fresh.save_monthly_policy_proposal(proposal=policy)
            fresh.save_monthly_policy_approval(approval=approval)
            fresh.save_monthly_evaluation_approval(approval=checked)
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                assert payload_rows(connection) == prior
