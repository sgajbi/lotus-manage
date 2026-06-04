from types import SimpleNamespace
from typing import cast

from src.api.services.construction_alternative_set_lineage import (
    alternative_set_lineage_fields,
    source_supportability_state,
)
from src.core.dpm_source_context import DpmResolvedSourceContext


def test_alternative_set_lineage_fields_mark_stateless_without_source_context() -> None:
    assert alternative_set_lineage_fields(
        request_hash="sha256:construction",
        source_context=None,
    ) == {
        "request_hash": "sha256:construction",
        "input_mode": "stateless",
        "source_supportability_state": None,
    }


def test_alternative_set_lineage_fields_preserve_stateful_supportability_state() -> None:
    source_context = cast(
        DpmResolvedSourceContext,
        SimpleNamespace(context=SimpleNamespace(supportability=SimpleNamespace(state="DEGRADED"))),
    )

    assert alternative_set_lineage_fields(
        request_hash="sha256:construction",
        source_context=source_context,
    ) == {
        "request_hash": "sha256:construction",
        "input_mode": "stateful",
        "source_supportability_state": "DEGRADED",
    }


def test_source_supportability_state_preserves_absent_and_stateful_posture() -> None:
    source_context = cast(
        DpmResolvedSourceContext,
        SimpleNamespace(context=SimpleNamespace(supportability=SimpleNamespace(state="READY"))),
    )

    assert source_supportability_state(None) is None
    assert source_supportability_state(source_context) == "READY"
