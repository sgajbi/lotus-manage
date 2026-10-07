"""Closed SQL identifiers and retained content admission; no database certification."""

from typing import cast
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from psycopg import sql

from src.core.composite_eligibility.staged_controls import control_revision
from src.core.composite_eligibility.staged_controls import SubjectPolicyProposal
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_ports import ControlKind
from src.core.composite_eligibility.staged_subject import subject_key
from src.infrastructure.composites import staged_postgres
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from src.core.composite_eligibility.staged_publication import SubjectFinalizationReceipt
from tests.composite_staged_eligibility_helpers import finalization_material, lifecycle_material


class RetainedRowConnection:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, query, parameters):
        self.calls.append((query, parameters))
        return self

    def fetchone(self):
        return self.row


@pytest.mark.parametrize("index", range(4))
def test_each_control_uses_quoted_closed_identifiers_and_bound_scope(index):
    subject, controls, _ = finalization_material()
    control = controls[index]
    key = subject_key(subject)
    connection = RetainedRowConnection(
        {
            "payload_json": control.model_dump(mode="json"),
            "content_hash": control.content_hash,
            "subject_content_hash": subject.content_hash,
        }
    )
    assert (
        staged_postgres.get_control(
            connection, key, control.product_name, control_revision(control)
        )
        == control
    )
    query, parameters = connection.calls[0]
    assert isinstance(query, sql.Composed)
    table, revision_column = staged_postgres.CONTROL_TABLES[control.product_name]
    rendered = query.as_string()
    assert f'FROM "{table}"' in rendered
    assert f'AND "{revision_column}"=%s' in rendered
    assert rendered.count("%s") == 5
    assert "custody_mode='STAGED'" in rendered
    assert parameters == (*key, control_revision(control))
    hostile_revision = "revision'; DROP TABLE dpm_composite_definitions; --"
    absent = RetainedRowConnection(None)
    assert staged_postgres.get_control(absent, key, control.product_name, hostile_revision) is None
    assert hostile_revision not in absent.calls[0][0].as_string()
    assert absent.calls[0][1][-1] == hostile_revision


def test_unknown_control_kind_never_reaches_sql():
    connection = RetainedRowConnection(None)
    with pytest.raises(KeyError):
        staged_postgres.get_control(
            connection,
            ("tenant", "composite", "v2", "subject"),
            cast(ControlKind, "arbitrary_table"),
            "revision",
        )
    assert not connection.calls


@pytest.mark.parametrize("field", ["content_hash", "subject_content_hash"])
def test_retained_control_rejects_corrupt_storage_hash(field):
    subject, controls, _ = finalization_material()
    control = controls[-1]
    row = {
        "payload_json": control.model_dump(mode="json"),
        "content_hash": control.content_hash,
        "subject_content_hash": subject.content_hash,
    }
    row[field] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="CONTROL_INTEGRITY_CONFLICT"):
        staged_postgres.get_control(
            RetainedRowConnection(row),
            subject_key(subject),
            control.product_name,
            control_revision(control),
        )


class ExactReadConnection:
    """Strict scripted SQL boundary: not a PostgreSQL transaction emulator."""

    def __init__(self, reads):
        self.reads = list(reads)
        self.calls = []
        self.closed = False

    def execute(self, query, parameters=None):
        rendered = query.as_string() if isinstance(query, sql.Composable) else query
        self.calls.append((rendered, parameters))
        if rendered == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY":
            assert parameters is None
            return self
        table, expected, row = self.reads.pop(0)
        assert table in rendered
        assert parameters == expected
        assert rendered.lstrip().startswith("SELECT")
        self.row = row
        return self

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


def finalized_reads():
    subject, controls, finalization = finalization_material()
    _, _, _, _, _, _, member, universe = lifecycle_material()
    receipt = SubjectFinalizationReceipt(
        finalization=finalization,
        publication_sequence=7,
        membership_content_hash=member.content_hash,
        universe_content_hash=universe.content_hash,
    )
    key = subject_key(subject)

    def row(model):
        return {"payload_json": model.model_dump(mode="json"), "content_hash": model.content_hash}

    reads = [
        ("dpm_composite_eligibility_finalizations", key, row(receipt)),
        ("dpm_composite_definitions", key[:3], row(finalization.definition)),
        ("dpm_composite_membership_revisions", (*key[:3], member.membership_revision), row(member)),
        (
            "dpm_composite_universe_attestations",
            (*key[:3], member.membership_revision, universe.attestation_version),
            row(universe),
        ),
        (
            "dpm_composite_membership_publications",
            (key[0], 7),
            {
                "tenant_id": subject.tenant_id,
                "composite_id": subject.composite_id,
                "definition_version": subject.definition_version,
                "membership_revision": member.membership_revision,
                "membership_content_hash": member.content_hash,
                "sequence": 7,
                "published_at": datetime(2026, 10, 2, tzinfo=timezone.utc),
            },
        ),
        ("dpm_composite_eligibility_subjects", key, row(subject)),
        (
            "dpm_composite_monthly_evaluation_approvals",
            (*key, controls[-1].proposal.evaluation_revision),
            row(controls[-1]) | {"subject_content_hash": subject.content_hash},
        ),
    ]
    return key, receipt, reads


@pytest.mark.parametrize(
    "corruption",
    [
        None,
        "receipt",
        "definition",
        "member",
        "universe",
        "publication",
        "missing-member",
        "missing-universe",
        "missing-publication",
    ],
)
def test_finalized_sql_reader_verifies_each_retained_hash_and_publication_join(corruption):
    key, receipt, reads = finalized_reads()
    if corruption:
        if corruption.startswith("missing-"):
            index = {"missing-member": 2, "missing-universe": 3, "missing-publication": 4}[
                corruption
            ]
            table, parameters, _ = reads[index]
            reads[index] = (table, parameters, None)
        else:
            index = {"receipt": 0, "definition": 1, "member": 2, "universe": 3, "publication": 4}[
                corruption
            ]
            field = "membership_content_hash" if corruption == "publication" else "content_hash"
            reads[index][2][field] = "sha256:" + "0" * 64
    before = deepcopy(reads)
    connection = ExactReadConnection(reads)
    if corruption:
        with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT$"):
            staged_postgres.get_finalization(connection, key)
    else:
        assert staged_postgres.get_finalization(connection, key) == receipt
        assert not connection.reads
    assert reads == before
    assert all(query.lstrip().startswith("SELECT") for query, _ in connection.calls)


@pytest.mark.parametrize("corruption", [None, "hash", "scope"])
def test_sql_subject_reader_rejects_stored_hash_or_cross_scope_row(corruption):
    subject, _, _ = finalization_material()
    key = subject_key(subject)
    row = {"payload_json": subject.model_dump(mode="json"), "content_hash": subject.content_hash}
    if corruption == "hash":
        row["content_hash"] = "sha256:" + "0" * 64
    elif corruption == "scope":
        key = ("other-tenant", *key[1:])
    connection = ExactReadConnection([("dpm_composite_eligibility_subjects", key, row)])
    if corruption:
        with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_INTEGRITY_CONFLICT$"):
            staged_postgres.get_subject(connection, key)
    else:
        assert staged_postgres.get_subject(connection, key) == subject
    assert not connection.reads


@pytest.mark.parametrize("case", ["valid", "absent", "wrong-digest"])
def test_sql_repository_exact_resolver_is_read_only_bound_and_closes_on_refusal(monkeypatch, case):
    key, receipt, reads = finalized_reads()
    approval = receipt.finalization.evaluation_approval
    selection = (*key[:3], approval.proposal.evaluation_revision)
    connection = ExactReadConnection(
        [
            (
                "dpm_composite_monthly_evaluation_approvals",
                selection,
                None if case == "absent" else {"subject_revision": key[-1]},
            ),
            *([] if case == "absent" else reads),
        ]
    )
    # Bypass initialization only: no database, migration, or durability assertion.
    monkeypatch.setattr(PostgresDpmCompositeRepository, "_init_db", lambda self: None)
    repository = PostgresDpmCompositeRepository(dsn="postgresql://unit-boundary/unused")
    monkeypatch.setattr(repository, "_connect", lambda: connection)
    arguments = dict(
        tenant_id=key[0],
        composite_id=key[1],
        definition_version=key[2],
        evaluation_revision=selection[-1],
        approval_content_hash=approval.content_hash,
    )
    if case == "wrong-digest":
        arguments["approval_content_hash"] = "sha256:" + "0" * 64
        with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH$"):
            repository.resolve_eligibility_evidence(**arguments)
    else:
        assert repository.resolve_eligibility_evidence(**arguments) == (
            None if case == "absent" else receipt
        )
    assert connection.calls[0] == (
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY",
        None,
    )
    assert "custody_mode='STAGED'" in connection.calls[1][0]
    assert connection.closed
    assert not connection.reads


def locked_read(tenant):
    return ("pg_advisory_xact_lock", (f"dpm-composite-publication:{tenant}",), None)


@pytest.mark.parametrize("missing", ["subject", "approval"])
def test_sql_finalization_requires_retained_subject_and_approval_before_first_write(missing):
    key, receipt, reads = finalized_reads()
    expected = [
        locked_read(key[0]),
        ("dpm_composite_eligibility_finalizations", key, None),
        ("dpm_composite_eligibility_subjects", key, None if missing == "subject" else reads[5][2]),
    ]
    if missing == "approval":
        expected.append((reads[6][0], reads[6][1], None))
    before = deepcopy(expected)
    connection = ExactReadConnection(expected)
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_RETAINED_CONTROL_MISMATCH$"):
        staged_postgres.finalize(connection, receipt.finalization)
    assert not connection.reads
    assert expected == before


@pytest.mark.parametrize(
    "case", ["replay", "changed-content", "reserved-subject", "reserved-definition"]
)
def test_sql_subject_reservation_refusals_and_replay_do_not_issue_writes(case):
    subject, _, _ = finalization_material()
    key = subject_key(subject)
    command = subject
    retained = {
        "payload_json": subject.model_dump(mode="json"),
        "content_hash": subject.content_hash,
    }
    reads = [
        locked_read(key[0]),
        (
            "dpm_composite_eligibility_subjects",
            key,
            retained if case in {"replay", "changed-content"} else None,
        ),
    ]
    if case == "changed-content":
        command = EligibilitySubject.model_validate(
            subject.model_dump(mode="json") | {"display_name": "changed", "content_hash": ""}
        )
    if case.startswith("reserved-"):
        reads.extend(
            [
                (
                    "dpm_composite_eligibility_subjects",
                    key[:3],
                    {"exists": 1} if case == "reserved-subject" else None,
                ),
                (
                    "dpm_composite_definitions",
                    key[:3],
                    {"exists": 1} if case == "reserved-definition" else None,
                ),
            ]
        )
    before = deepcopy(reads)
    connection = ExactReadConnection(reads)
    if case == "replay":
        staged_postgres.save_subject(connection, command)
    else:
        code = (
            "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT"
            if case == "changed-content"
            else "COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT"
        )
        with pytest.raises(ValueError, match=f"^{code}$"):
            staged_postgres.save_subject(connection, command)
    assert not connection.reads
    assert reads == before


@pytest.mark.parametrize("case", ["replay", "changed-content", "missing-subject", "finalized"])
def test_sql_policy_custody_refuses_before_any_control_write(case):
    subject, controls, _ = finalization_material()
    key = subject_key(subject)
    policy = controls[0]
    wire = policy.model_dump(mode="json")
    if case == "changed-content":
        wire["proposal"].update(proposed_at="2026-08-21T00:00:00.000000Z", content_hash="")
    if case == "finalized":
        wire["proposal"].update(proposal_revision="new-revision", content_hash="")
    wire["content_hash"] = ""
    command = SubjectPolicyProposal.model_validate(wire)
    reads = [
        locked_read(key[0]),
        (
            "dpm_composite_eligibility_subjects",
            key,
            None
            if case == "missing-subject"
            else {
                "payload_json": subject.model_dump(mode="json"),
                "content_hash": subject.content_hash,
            },
        ),
    ]
    if case != "missing-subject":
        reads.append(
            (
                "dpm_composite_monthly_policy_proposals",
                (*key, control_revision(command)),
                None
                if case == "finalized"
                else {
                    "payload_json": policy.model_dump(mode="json"),
                    "content_hash": policy.content_hash,
                    "subject_content_hash": subject.content_hash,
                },
            )
        )
    if case == "finalized":
        reads.append(finalized_reads()[2][0])
    before = deepcopy(reads)
    connection = ExactReadConnection(reads)
    if case == "replay":
        staged_postgres.save_control(connection, command)
    else:
        code = {
            "changed-content": "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT",
            "missing-subject": "COMPOSITE_SUBJECT_NOT_FOUND",
            "finalized": "COMPOSITE_SUBJECT_ALREADY_FINALIZED_CONFLICT",
        }[case]
        with pytest.raises(ValueError, match=f"^{code}$"):
            staged_postgres.save_control(connection, command)
    assert not connection.reads
    assert reads == before


@pytest.mark.parametrize("case", ["unfinalized", "replay"])
def test_sql_repository_reserved_definition_cannot_bypass_subject_publication(monkeypatch, case):
    key, receipt, reads = finalized_reads()
    connection = ExactReadConnection(
        [
            locked_read(key[0]),
            ("dpm_composite_eligibility_subjects", key[:3], {"subject_revision": key[-1]}),
            *(reads if case == "replay" else [(reads[0][0], key, None)]),
        ]
    )
    monkeypatch.setattr(PostgresDpmCompositeRepository, "_init_db", lambda self: None)
    repository = PostgresDpmCompositeRepository(dsn="postgresql://unit-boundary/unused")
    monkeypatch.setattr(repository, "_connect", lambda: connection)
    if case == "replay":
        repository.save_definition(definition=receipt.finalization.definition)
    else:
        with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT$"):
            repository.save_definition(definition=receipt.finalization.definition)
    assert not connection.reads
    assert connection.closed


def test_sql_repository_get_control_keeps_exact_binding_and_closes_connection(monkeypatch):
    subject, controls, _ = finalization_material()
    key = subject_key(subject)
    policy = controls[0]
    connection = ExactReadConnection(
        [
            (
                "dpm_composite_monthly_policy_proposals",
                (*key, control_revision(policy)),
                {
                    "payload_json": policy.model_dump(mode="json"),
                    "content_hash": policy.content_hash,
                    "subject_content_hash": subject.content_hash,
                },
            )
        ]
    )
    monkeypatch.setattr(PostgresDpmCompositeRepository, "_init_db", lambda self: None)
    repository = PostgresDpmCompositeRepository(dsn="postgresql://unit-boundary/unused")
    monkeypatch.setattr(repository, "_connect", lambda: connection)
    assert (
        repository.get_subject_control(
            key=key, kind=policy.product_name, revision=control_revision(policy)
        )
        == policy
    )
    assert not connection.reads
    assert connection.closed
