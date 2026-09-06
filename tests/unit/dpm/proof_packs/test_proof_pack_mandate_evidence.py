from src.api.services.proof_pack_mandate_evidence import resolve_mandate_evidence
from src.core.mandates import DpmMandateHealthInput, calculate_mandate_health
from src.infrastructure.mandates import InMemoryDpmMandateRepository
from tests.unit.dpm.proof_packs.test_proof_pack_builder import _mandate_twin


def _repository(*, mandate_id: str, portfolio_id: str) -> InMemoryDpmMandateRepository:
    repository = InMemoryDpmMandateRepository()
    twin = _mandate_twin().model_copy(
        update={
            "mandate_id": mandate_id,
            "portfolio_id": portfolio_id,
        }
    )
    repository.save_mandate_snapshot(twin, tenant_id="tenant-test")
    repository.save_health_snapshot(calculate_mandate_health(DpmMandateHealthInput(twin=twin)), tenant_id="tenant-test")
    return repository


def test_resolve_mandate_evidence_returns_empty_when_optional_inputs_are_missing() -> None:
    without_mandate_id = resolve_mandate_evidence(
        mandate_id=None,
        portfolio_id="pf_mandate_evidence_1",
        mandate_repository=_repository(
            mandate_id="mandate_evidence",
            portfolio_id="pf_mandate_evidence_1",
        ),
        tenant_id="tenant-test",
    )
    without_repository = resolve_mandate_evidence(
        mandate_id="mandate_evidence",
        portfolio_id="pf_mandate_evidence_1",
        mandate_repository=None,
        tenant_id="tenant-test",
    )

    assert without_mandate_id.twin is None
    assert without_mandate_id.health is None
    assert without_mandate_id.gap_codes == []
    assert without_repository.twin is None
    assert without_repository.health is None
    assert without_repository.gap_codes == []


def test_resolve_mandate_evidence_returns_empty_when_snapshot_is_missing() -> None:
    evidence = resolve_mandate_evidence(
        mandate_id="missing",
        portfolio_id="pf_mandate_evidence_1",
        mandate_repository=InMemoryDpmMandateRepository(),
        tenant_id="tenant-test",
    )

    assert evidence.twin is None
    assert evidence.health is None
    assert evidence.gap_codes == []


def test_resolve_mandate_evidence_rejects_portfolio_mismatched_twin() -> None:
    evidence = resolve_mandate_evidence(
        mandate_id="mandate_evidence",
        portfolio_id="pf_mandate_evidence_1",
        mandate_repository=_repository(
            mandate_id="mandate_evidence",
            portfolio_id="different_portfolio",
        ),
        tenant_id="tenant-test",
    )

    assert evidence.twin is None
    assert evidence.health is None
    assert evidence.gap_codes == ["DPM_MANDATE_TWIN_PORTFOLIO_MISMATCH"]


def test_resolve_mandate_evidence_returns_portfolio_matched_twin_and_health() -> None:
    evidence = resolve_mandate_evidence(
        mandate_id="mandate_evidence",
        portfolio_id="pf_mandate_evidence_1",
        mandate_repository=_repository(
            mandate_id="mandate_evidence",
            portfolio_id="pf_mandate_evidence_1",
        ),
        tenant_id="tenant-test",
    )

    assert evidence.twin is not None
    assert evidence.twin.portfolio_id == "pf_mandate_evidence_1"
    assert evidence.health is not None
    assert evidence.health.mandate_id == "mandate_evidence"
    assert evidence.gap_codes == []
