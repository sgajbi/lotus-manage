"""Closed SQL identifiers and retained content admission; no database certification."""

from typing import cast

import pytest
from psycopg import sql

from src.core.composite_eligibility.staged_controls import control_revision
from src.core.composite_eligibility.staged_ports import ControlKind
from src.core.composite_eligibility.staged_subject import subject_key
from src.infrastructure.composites import staged_postgres
from tests.composite_staged_eligibility_helpers import finalization_material


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
