"""Temporal mandate reads proven on real PostgreSQL (issues #646, #647).

Both defects are engine-shaped and cannot be trusted to a fake:

  - #646 is lexicographic ordering of a TEXT column. `"9" > "10"` is true in
    Python and in SQL alike, so the wrong-row behaviour reproduces anywhere -
    but the FIX is a SQL expression, and only PostgreSQL can prove the
    expression parses, orders numerically, and survives a non-integer value
    without aborting the query.
  - #647 depends on migration 0020 having relaxed the uniqueness key to
    (mandate_id, mandate_version, as_of_date). Whether the database ACCEPTS a
    repeated version at a later date is a schema fact, so a repeated-version
    fixture is only meaningful against the real schema.

Skips without a DSN, in line with the other PostgreSQL integration tests. The
CI job that owns the database runs this file explicitly.
"""

from __future__ import annotations

import os
import uuid
from contextlib import closing
from datetime import date
from decimal import Decimal

import pytest

from src.api.services.mandate_diff import build_mandate_diff_for_versions
from src.api.services.mandate_errors import DpmMandateDiffUnavailableError
from src.core.mandates import (
    DpmMandateConstraintSet,
    DpmMandateDigitalTwin,
    DpmMandateReviewPolicy,
)
from src.infrastructure.mandates.postgres import PostgresDpmMandateRepository

_DSN = os.getenv("DPM_POSTGRES_INTEGRATION_DSN", "").strip()

pytestmark = pytest.mark.skipif(
    not _DSN, reason="DPM_POSTGRES_INTEGRATION_DSN is required for the temporal-read proof"
)

_AS_OF = date(2026, 5, 3)


def _twin(
    *,
    mandate_id: str,
    portfolio_id: str,
    version: str,
    as_of: date = _AS_OF,
    turnover: str = "0.15",
) -> DpmMandateDigitalTwin:
    return DpmMandateDigitalTwin(
        mandate_id=mandate_id,
        portfolio_id=portfolio_id,
        mandate_version=version,
        as_of_date=as_of,
        base_currency="SGD",
        reference_currency="SGD",
        risk_profile="BALANCED",
        investment_objective="LONG_TERM_TOTAL_RETURN",
        time_horizon="LONG_TERM",
        model_portfolio_id="MODEL_PB_SG_GLOBAL_BAL_DPM",
        constraints=DpmMandateConstraintSet(turnover_budget=Decimal(turnover)),
        review_policy=DpmMandateReviewPolicy(next_review_due_date=date(2026, 6, 30)),
    )


@pytest.fixture
def repository() -> PostgresDpmMandateRepository:
    return PostgresDpmMandateRepository(dsn=_DSN)


def _clear(repository: PostgresDpmMandateRepository, mandate_id: str) -> None:
    with closing(repository._connect()) as connection:
        connection.execute("DELETE FROM dpm_mandate_snapshots WHERE mandate_id = %s", (mandate_id,))
        connection.commit()


def test_version_ten_wins_over_version_nine_on_the_same_business_date(
    repository: PostgresDpmMandateRepository,
) -> None:
    """Issue #646. Lexicographically "9" sorts above "10", so before the fix
    every temporal read resolved to the older binding once a mandate reached
    version 10 - and migration 0020 is what makes two rows share a date."""

    mandate_id = f"MANDATE_ORDER_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_ORDER_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="9")
        )
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="10")
        )

        assert repository.get_latest_mandate(mandate_id=mandate_id).mandate_version == "10"
        assert (
            repository.get_latest_mandate_by_portfolio(portfolio_id=portfolio_id).mandate_version
            == "10"
        )
        assert (
            repository.get_mandate_by_portfolio_as_of(
                portfolio_id=portfolio_id, as_of_date=_AS_OF
            ).mandate_version
            == "10"
        )
        # The listing is newest-first, so the numeric order must hold there too.
        listed = [
            twin.mandate_version for twin in repository.list_mandate_versions(mandate_id=mandate_id)
        ]
        assert listed == ["10", "9"]
    finally:
        _clear(repository, mandate_id)


def test_version_ordering_survives_a_non_integer_version(
    repository: PostgresDpmMandateRepository,
) -> None:
    """The column is TEXT, so a non-integer value is representable. The
    ordering expression must sort it last rather than aborting the query for
    every caller - a cast without the guard raises 22P02 and takes the whole
    read down."""

    mandate_id = f"MANDATE_TEXTVER_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_TEXTVER_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="2024-R1")
        )
        repository.save_mandate_snapshot(
            _twin(mandate_id=mandate_id, portfolio_id=portfolio_id, version="7")
        )

        assert repository.get_latest_mandate(mandate_id=mandate_id).mandate_version == "7"
        listed = [
            twin.mandate_version for twin in repository.list_mandate_versions(mandate_id=mandate_id)
        ]
        assert listed == ["7", "2024-R1"]
    finally:
        _clear(repository, mandate_id)


def test_a_repeated_version_is_not_diffed_against_itself(
    repository: PostgresDpmMandateRepository,
) -> None:
    """Issue #647. Migration 0020 lets one version be re-observed on a later
    date. Diffing the two newest rows blindly compares that version against
    itself and reports "no changes", which a reader cannot distinguish from a
    mandate that genuinely did not change."""

    mandate_id = f"MANDATE_REOBS_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_REOBS_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(
                mandate_id=mandate_id,
                portfolio_id=portfolio_id,
                version="3",
                as_of=date(2026, 4, 30),
                turnover="0.10",
            )
        )
        # Version 4 changes the turnover budget...
        repository.save_mandate_snapshot(
            _twin(
                mandate_id=mandate_id,
                portfolio_id=portfolio_id,
                version="4",
                as_of=date(2026, 5, 1),
                turnover="0.20",
            )
        )
        # ...and is then re-observed unchanged on a later business date. The
        # database accepts this only because 0020 relaxed the uniqueness key.
        repository.save_mandate_snapshot(
            _twin(
                mandate_id=mandate_id,
                portfolio_id=portfolio_id,
                version="4",
                as_of=date(2026, 5, 3),
                turnover="0.20",
            )
        )

        versions = repository.list_mandate_versions(mandate_id=mandate_id)
        assert [twin.mandate_version for twin in versions] == ["4", "4", "3"]

        diff = build_mandate_diff_for_versions(
            mandate_id=mandate_id, versions=versions, from_version=None, to_version=None
        )

        # The comparison crosses a real version boundary...
        assert (diff.from_version, diff.to_version) == ("3", "4")
        # ...and names WHICH observations it used, so a same-version
        # re-observation is distinguishable from a version change.
        assert diff.from_as_of_date == date(2026, 4, 30)
        assert diff.to_as_of_date == date(2026, 5, 3)
        # The turnover change is real and must survive.
        assert any(
            change.field_path == "constraints.turnover_budget" for change in diff.changed_fields
        )
    finally:
        _clear(repository, mandate_id)


def test_repeated_observations_of_one_version_refuse_rather_than_report_no_changes(
    repository: PostgresDpmMandateRepository,
) -> None:
    """When every stored observation is of the same version there is no
    version change to describe. Refusing is more truthful than an empty
    change list, which reads as "compared, and nothing moved"."""

    mandate_id = f"MANDATE_SAMEVER_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_SAMEVER_{uuid.uuid4().hex[:8]}"
    try:
        for observed in (date(2026, 5, 1), date(2026, 5, 3)):
            repository.save_mandate_snapshot(
                _twin(
                    mandate_id=mandate_id,
                    portfolio_id=portfolio_id,
                    version="5",
                    as_of=observed,
                )
            )
        versions = repository.list_mandate_versions(mandate_id=mandate_id)
        assert len(versions) == 2

        with pytest.raises(DpmMandateDiffUnavailableError):
            build_mandate_diff_for_versions(
                mandate_id=mandate_id, versions=versions, from_version=None, to_version=None
            )
    finally:
        _clear(repository, mandate_id)


def test_a_requested_version_resolves_to_its_latest_observation(
    repository: PostgresDpmMandateRepository,
) -> None:
    """A caller naming a version gets its most recent observation. The old
    dict comprehension let the last list entry win, and the list is
    newest-first, so callers silently received the OLDEST observation."""

    mandate_id = f"MANDATE_PICK_{uuid.uuid4().hex[:8]}"
    portfolio_id = f"PF_PICK_{uuid.uuid4().hex[:8]}"
    try:
        repository.save_mandate_snapshot(
            _twin(
                mandate_id=mandate_id,
                portfolio_id=portfolio_id,
                version="1",
                as_of=date(2026, 4, 1),
                turnover="0.10",
            )
        )
        for observed in (date(2026, 4, 30), date(2026, 5, 3)):
            repository.save_mandate_snapshot(
                _twin(
                    mandate_id=mandate_id,
                    portfolio_id=portfolio_id,
                    version="2",
                    as_of=observed,
                    turnover="0.20",
                )
            )

        versions = repository.list_mandate_versions(mandate_id=mandate_id)
        diff = build_mandate_diff_for_versions(
            mandate_id=mandate_id, versions=versions, from_version="1", to_version="2"
        )

        assert (diff.from_version, diff.to_version) == ("1", "2")
        assert diff.to_as_of_date == date(2026, 5, 3)
    finally:
        _clear(repository, mandate_id)
