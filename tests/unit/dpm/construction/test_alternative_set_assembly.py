from src.api.services.construction_alternative_set_assembly import (
    build_persistable_alternative_set,
)
from src.core.construction.vocabulary import ConstructionMethodStatus


def test_build_persistable_alternative_set_applies_deterministic_identity_and_lineage() -> None:
    alternative_set = build_persistable_alternative_set(
        alternative_set_id="cas_test_001",
        portfolio_id="pf_assembly",
        as_of="2026-06-01",
        alternatives=[],
        request_hash="sha256:construction",
        source_context=None,
    )

    assert alternative_set.alternative_set_id == "cas_test_001"
    assert alternative_set.portfolio_id == "pf_assembly"
    assert alternative_set.as_of == "2026-06-01"
    assert alternative_set.status == ConstructionMethodStatus.BLOCKED
    assert alternative_set.request_hash == "sha256:construction"
    assert alternative_set.input_mode == "stateless"
    assert alternative_set.source_supportability_state is None
