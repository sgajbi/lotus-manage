"""Forward 0046 custody: actual typed writes, populated upgrade and SQL refusals.

Requires the admitted PostgreSQL lane; no runtime prerequisite is synthesized here.
Frozen source-owned graph fixtures exercise custody, not native admission coverage.
The separate native HTTP test owns empty-scope admission and source-off recovery.
"""

import json
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

import src.infrastructure.postgres_migrations as migrations
from src.core.composite_eligibility.staged_controls import STAGED_CONTROL_ADAPTER
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_historical_policy_helpers import seed_historical_root
from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root
from tests.composite_staged_eligibility_helpers import finalization_material
from tests.integration.dpm.composites.test_composite_staged_upgrade_postgres import payload_rows
from tests.integration.dpm.network_runtime import disposable_database

CONTRACTS = Path(__file__).resolve().parents[4] / "docs/contracts/composite-historical-subject"
PRODUCTS = (
    "CompositeSubjectPolicyProposal",
    "CompositeSubjectPolicyApproval",
    "CompositeSubjectEvaluationProposal",
    "CompositeSubjectEvaluationApproval",
)


def historical_controls(profile="historical_v1"):
    if profile == "controlled_scenario":
        receipt = json.loads(
            (CONTRACTS.parent / "composite-controlled-scenario/valid-graph.json").read_bytes()
        )
        approval = receipt["finalization"]["evaluation_approval"]
        evaluation = approval["proposal"]
        policy = evaluation["policy_approval"]
        return [
            STAGED_CONTROL_ADAPTER.validate_python(wire)
            for wire in (policy["proposal"], policy, evaluation, approval)
        ]
    return [
        STAGED_CONTROL_ADAPTER.validate_python(
            json.loads((CONTRACTS / f"{product}.v2.controlled.json").read_text(encoding="utf-8"))
        )
        for product in PRODUCTS
    ]


@pytest.fixture(
    params=[
        ("fresh", "historical_v1"),
        ("upgrade_0045", "historical_v1"),
        ("fresh", "controlled_scenario"),
        ("upgrade_0046", "controlled_scenario"),
    ],
    ids=["fresh_legacy", "upgrade0045_legacy", "fresh_scenario", "upgrade0046_scenario"],
)
def retained_historical_controls(monkeypatch, request):
    loader = migrations._load_migrations
    mode, profile = request.param
    with monkeypatch.context() as previous:
        if mode.startswith("upgrade_"):
            previous.setattr(
                migrations,
                "_load_migrations",
                lambda *, namespace: [
                    m
                    for m in loader(namespace=namespace)
                    if m.version <= mode.removeprefix("upgrade_")
                ],
            )
        with disposable_database() as dsn:
            repository = PostgresDpmCompositeRepository(dsn=dsn)
            controls = historical_controls(profile)
            repository.save_eligibility_subject(subject=controls[0].subject)
            for control in controls[:2]:
                repository.save_subject_control(control=control)
            if mode.startswith("upgrade_"):
                with pytest.raises(psycopg.errors.CheckViolation) as refused:
                    repository.save_subject_control(control=controls[2])
                assert refused.value.diag.constraint_name == "monthly_evaluation_amendment_wire"
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    before = payload_rows(connection)
                    old_checksums = connection.execute(
                        "SELECT version,checksum FROM schema_migrations ORDER BY version"
                    ).fetchall()
                previous.undo()
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    assert payload_rows(connection) == before
                    assert (
                        connection.execute(
                            "SELECT version,checksum FROM schema_migrations WHERE version <= %s ORDER BY version",
                            ("dpm:" + mode.removeprefix("upgrade_"),),
                        ).fetchall()
                        == old_checksums
                    )
                    new_row = connection.execute(
                        "SELECT checksum FROM schema_migrations WHERE version=%s", ("dpm:0047",)
                    ).fetchall()
                    assert new_row == [
                        {
                            "checksum": next(
                                m.checksum for m in loader(namespace="dpm") if m.version == "0047"
                            )
                        }
                    ]
            for control in controls[2:]:
                repository.save_subject_control(control=control)
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                before = payload_rows(connection)
                migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                assert payload_rows(connection) == before
            yield dsn, controls


def test_exact_historical_controls_survive_repository_reopen(retained_historical_controls):
    dsn, controls = retained_historical_controls
    repository = PostgresDpmCompositeRepository(dsn=dsn)
    # Idempotent replay performs decoding and original-hash comparison from PostgreSQL.
    for control in controls:
        repository.save_subject_control(control=control)
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        for family, control in zip(("proposals", "approvals"), controls[2:], strict=True):
            row = connection.execute(
                sql.SQL("SELECT custody_mode, content_hash, payload_json FROM {}").format(
                    sql.Identifier("dpm_composite_monthly_evaluation_" + family)
                )
            ).fetchone()
            assert row["custody_mode"] == "STAGED"
            assert row["content_hash"] == control.content_hash
            assert row["payload_json"] == control.model_dump(mode="json")


@pytest.mark.parametrize("family", ["proposals", "approvals"])
@pytest.mark.parametrize(
    "mutation",
    [
        "mixed_version",
        "monthly_forgery",
        "null_proof",
        "missing_proof",
        "wrong_operation",
        "wrong_subject",
        "wrong_scope",
        "wrong_mapping",
        "amendment",
        "amendment_null",
    ],
)
def test_staged_historical_wire_refuses_mixed_or_forged_graph(
    retained_historical_controls, family, mutation
):
    dsn, controls = retained_historical_controls
    wire = deepcopy(controls[2 if family == "proposals" else 3].model_dump(mode="json"))
    proposal = wire if family == "proposals" else wire["proposal"]
    if mutation == "mixed_version":
        proposal["policy_approval"]["product_version"] = "v1"
    elif mutation == "monthly_forgery":
        proposal["product_name"] = "CompositeMonthlyEvaluationProposal"
    elif mutation == "null_proof":
        wire["operation_verification"] = None
    elif mutation == "missing_proof":
        wire.pop("operation_verification")
    elif mutation == "wrong_operation":
        wire["operation_verification"]["request"]["operation"] = "POLICY_PROPOSAL"
    elif mutation == "wrong_subject":
        proposal["policy_approval"]["proposal"]["subject"]["content_hash"] = "sha256:" + "0" * 64
    elif mutation == "wrong_scope":
        proposal["operation_verification"]["request"]["scope"]["tenant_id"] = "forged"
    elif mutation == "wrong_mapping":
        wire["operation_verification"]["mapping"]["content_hash"] = "sha256:" + "0" * 64
    else:
        proposal["amendment"] = (
            None if mutation == "amendment_null" else {"correction_kind": "SOURCE_CORRECTION"}
        )
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        before = payload_rows(connection)
    with pytest.raises(psycopg.errors.CheckViolation) as refused:
        with psycopg.connect(dsn) as connection:
            connection.execute(
                sql.SQL("UPDATE {} SET payload_json=%s::jsonb").format(
                    sql.Identifier("dpm_composite_monthly_evaluation_" + family)
                ),
                (json.dumps(wire),),
            )
    expected = (
        "monthly_evaluation_" + ("approval_" if family == "approvals" else "") + "amendment_wire"
    )
    assert refused.value.diag.constraint_name == expected
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        assert payload_rows(connection) == before


@pytest.mark.parametrize("profile", ["ordinary_v1", "ordinary_v2", "staged", "historical"])
def test_populated_0045_upgrade_preserves_exact_rows_checksums_and_receipts(monkeypatch, profile):
    loader = migrations._load_migrations
    with monkeypatch.context() as previous:
        previous.setattr(
            migrations,
            "_load_migrations",
            lambda *, namespace: [m for m in loader(namespace=namespace) if m.version <= "0045"],
        )
        with disposable_database() as dsn:
            repository = PostgresDpmCompositeRepository(dsn=dsn)
            if profile == "staged":
                subject, controls, finalization = finalization_material()
                repository.save_eligibility_subject(subject=subject)
                for control in controls:
                    repository.save_subject_control(control=control)
                issued = repository.finalize_eligibility_subject(finalization=finalization)
            elif profile == "historical":
                _, scope, issued, _ = seed_historical_root(
                    repository, definition_product_version="v1"
                )
            else:
                scope, issued, _ = seed_complete_monthly_root(
                    repository, definition_product_version=profile.removeprefix("ordinary_")
                )
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                before = payload_rows(connection)
                checksums = connection.execute(
                    "SELECT version, checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            previous.undo()
            for _ in range(2):
                with psycopg.connect(dsn, row_factory=dict_row) as connection:
                    migrations.apply_postgres_migrations(connection=connection, namespace="dpm")
                    assert payload_rows(connection) == before
                    assert (
                        connection.execute(
                            "SELECT version, checksum FROM schema_migrations WHERE version <= 'dpm:0045' ORDER BY version"
                        ).fetchall()
                        == checksums
                    )
                    actual = connection.execute(
                        "SELECT checksum FROM schema_migrations WHERE version='dpm:0046'"
                    ).fetchall()
                    expected = next(
                        m.checksum for m in loader(namespace="dpm") if m.version == "0046"
                    )
                    assert actual == [{"checksum": expected}]
                fresh = PostgresDpmCompositeRepository(dsn=dsn)
                reopened = (
                    fresh.finalize_eligibility_subject(finalization=finalization)
                    if profile == "staged"
                    else fresh.resolve_monthly_eligibility_evidence(
                        **scope,
                        evaluation_revision=issued.approval.proposal.evaluation_revision,
                        approval_content_hash=issued.approval.content_hash,
                    )
                )
                assert reopened.model_dump(mode="json") == issued.model_dump(mode="json")


@pytest.mark.parametrize(
    "retained_historical_controls",
    [("fresh", "controlled_scenario"), ("upgrade_0046", "controlled_scenario")],
    indirect=True,
    ids=["fresh_scenario", "upgrade0046_scenario"],
)
@pytest.mark.parametrize("family", ["proposals", "approvals"])
@pytest.mark.parametrize(
    "mutation",
    [
        "old-purpose",
        "old-status",
        "qualified",
        "scenario-clock",
        "issued-clock",
        "nested-proof",
        "mixed-monthly",
        "old-alias",
        "missing-scenario",
        "key-collision",
    ],
)
def test_controlled_scenario_storage_refuses_false_temporal_or_mixed_authority(
    retained_historical_controls, family, mutation
):
    dsn, controls = retained_historical_controls
    wire = deepcopy(controls[2 if family == "proposals" else 3].model_dump(mode="json"))
    proposal = wire if family == "proposals" else wire["proposal"]
    proof = wire["operation_verification"]
    if mutation == "old-purpose":
        proof["request"]["purpose"] = "COMPOSITE_HISTORICAL_MONTHLY_POLICY_ADMISSION"
    elif mutation == "old-status":
        proof["original_signature_status"] = "VERIFIED_AT_ORIGINAL_APPROVAL"
    elif mutation == "qualified":
        proof["posture"] = "QUALIFIED_RECEIPT"
    elif mutation == "scenario-clock":
        proof["mapping"]["scenario_approved_at"] = "2099-01-01T00:00:00.000000Z"
    elif mutation == "issued-clock":
        proof["mapping"]["actual_issued_at"] = "2099-01-01T00:00:00.000000Z"
    elif mutation == "nested-proof":
        proposal["policy_approval"]["approval"]["verification"]["product_version"] = "v1"
    elif mutation == "mixed-monthly":
        proposal["policy_approval"]["approval"]["proposal"]["product_version"] = "v2"
    elif mutation == "old-alias":
        proof["mapping"]["original_approved_at"] = proof["mapping"]["scenario_approved_at"]
    elif mutation == "missing-scenario":
        proof["mapping"].pop("scenario_approved_at")
    else:
        proof["verifier_key_digest"] = proof["signer_key_digest"]
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        before = payload_rows(connection)
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(dsn) as connection:
        connection.execute(
            sql.SQL("UPDATE {} SET payload_json=%s::jsonb").format(
                sql.Identifier("dpm_composite_monthly_evaluation_" + family)
            ),
            (json.dumps(wire),),
        )
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        assert payload_rows(connection) == before
