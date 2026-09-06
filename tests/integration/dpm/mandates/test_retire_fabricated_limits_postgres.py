"""The fabricated-limit retirement reaches already-persisted twins (#664).

Removing the invented limits from the compiler only governs twins written
after the change. Rows persisted before it still carry the derived cash band
and the 0.15 turnover budget inside payload_json, and because those fields are
now nullable rather than absent from the model, the old values deserialize
cleanly and every read keeps publishing them.

This proves the data migration against a real database, because that is the
only place the JSON rewrite and its guards actually run.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import closing

import pytest

from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()

pytestmark = pytest.mark.skipif(
    not _DSN, reason="DPM_POSTGRES_INTEGRATION_DSN is required for the retirement proof"
)


def _legacy_payload(*, mandate_id: str, portfolio_id: str) -> str:
    """A twin exactly as the pre-correction compiler wrote it: the cash reserve
    reinterpreted as a band minimum, a 0.10 ceiling, a 0.15 turnover budget,
    no cash_reserve_weight, and neither gap code."""

    return json.dumps(
        {
            "mandate_id": mandate_id,
            "portfolio_id": portfolio_id,
            "mandate_version": "3",
            "as_of_date": "2026-05-03",
            "source_system": "lotus-core",
            "base_currency": "SGD",
            "reference_currency": "SGD",
            "risk_profile": "BALANCED",
            "investment_objective": "LONG_TERM_TOTAL_RETURN",
            "time_horizon": "LONG_TERM",
            "model_portfolio_id": "MODEL_PB_SG_GLOBAL_BAL_DPM",
            "constraints": {
                "cash_band_min_weight": "0.0200000000",
                "cash_band_max_weight": "0.10",
                "turnover_budget": "0.15",
                "allowed_product_types": [],
                "restricted_instruments": [],
                "restricted_issuers": [],
                "restricted_sectors": [],
                "sustainability_exclusions": [],
            },
            "preferences": {"bespoke_notes": []},
            "review_policy": {"review_frequency": "QUARTERLY"},
            "source_lineage": [],
            "field_gap_codes": ["MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED"],
        }
    )


def _insert_legacy_row(repository: PostgresDpmMandateRepository, mandate_id: str) -> None:
    portfolio_id = f"PF_LEGACY_{uuid.uuid4().hex[:8]}"
    with closing(repository._connect()) as connection:
        connection.execute(
            """
            INSERT INTO dpm_mandate_snapshots (
                mandate_snapshot_id, mandate_id, portfolio_id, mandate_version,
                as_of_date, source_hash, source_lineage_json, payload_json,
                created_at, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                f"ms_{uuid.uuid4().hex[:12]}",
                mandate_id,
                portfolio_id,
                "3",
                "2026-05-03",
                f"sha256:{uuid.uuid4().hex}",
                "[]",
                _legacy_payload(mandate_id=mandate_id, portfolio_id=portfolio_id),
                "2026-05-03T01:00:00+00:00",
                "lotus-manage",
            ),
        )
        connection.commit()


def _apply_retirement(repository: PostgresDpmMandateRepository) -> None:
    """Run the migration's statements directly.

    The repository applies migrations on connect and records them, so by the
    time this test runs 0023 is already recorded and will not re-run. Executing
    the same statements against the row inserted afterwards is what proves the
    rewrite and its guards behave, which is the part that could be wrong.
    """

    from pathlib import Path

    from src.infrastructure.postgres_migrations import _split_sql_statements

    sql_path = (
        Path("src/infrastructure/postgres_migrations/dpm")
        / "0023_retire_fabricated_mandate_limits.sql"
    )
    with closing(repository._connect()) as connection:
        for statement in _split_sql_statements(sql_path.read_text(encoding="utf-8")):
            if statement.strip():
                connection.execute(statement)
        connection.commit()


@pytest.fixture
def repository() -> PostgresDpmMandateRepository:
    return PostgresDpmMandateRepository(dsn=_DSN)


def test_a_legacy_twin_loses_its_fabricated_limits_and_keeps_its_reserve(
    repository: PostgresDpmMandateRepository,
) -> None:
    mandate_id = f"MANDATE_LEGACY_{uuid.uuid4().hex[:8]}"
    try:
        _insert_legacy_row(repository, mandate_id)

        # Before the rewrite the fabricated limits load cleanly, which is
        # exactly why the compiler fix alone was not enough.
        stale = repository.get_latest_mandate(mandate_id=mandate_id)
        assert stale is not None
        assert stale.constraints.cash_band_max_weight is not None
        assert stale.constraints.turnover_budget is not None

        _apply_retirement(repository)

        migrated = repository.get_latest_mandate(mandate_id=mandate_id)
        assert migrated is not None
        # The fabricated limits are gone...
        assert migrated.constraints.cash_band_min_weight is None
        assert migrated.constraints.cash_band_max_weight is None
        assert migrated.constraints.turnover_budget is None
        # ...the source-owned reserve is recovered from the old band minimum,
        # which is where the pre-correction compiler put it...
        assert migrated.constraints.cash_reserve_weight is not None
        assert str(migrated.constraints.cash_reserve_weight) == "0.0200000000"
        # ...and the persisted twin now names the gaps like a fresh one.
        assert "MANDATE_CASH_BAND_NOT_YET_SOURCED" in migrated.field_gap_codes
        assert "MANDATE_TURNOVER_BUDGET_NOT_YET_SOURCED" in migrated.field_gap_codes
        # Unrelated evidence survives.
        assert "MANDATE_OBJECTIVE_PROFILE_NOT_YET_SOURCED" in migrated.field_gap_codes
    finally:
        _clear(repository, mandate_id)


def test_rerunning_the_retirement_is_idempotent(
    repository: PostgresDpmMandateRepository,
) -> None:
    """A migration that duplicates gap codes or wipes a recovered reserve on a
    second pass would corrupt exactly the rows it just repaired."""

    mandate_id = f"MANDATE_REPLAY_{uuid.uuid4().hex[:8]}"
    try:
        _insert_legacy_row(repository, mandate_id)
        _apply_retirement(repository)
        first = repository.get_latest_mandate(mandate_id=mandate_id)
        _apply_retirement(repository)
        second = repository.get_latest_mandate(mandate_id=mandate_id)

        assert first is not None and second is not None
        assert second.constraints.cash_reserve_weight == first.constraints.cash_reserve_weight
        assert second.field_gap_codes == first.field_gap_codes
        assert second.field_gap_codes.count("MANDATE_CASH_BAND_NOT_YET_SOURCED") == 1
    finally:
        _clear(repository, mandate_id)


def _clear(repository: PostgresDpmMandateRepository, mandate_id: str) -> None:
    with closing(repository._connect()) as connection:
        connection.execute("DELETE FROM dpm_mandate_snapshots WHERE mandate_id = %s", (mandate_id,))
        connection.commit()
