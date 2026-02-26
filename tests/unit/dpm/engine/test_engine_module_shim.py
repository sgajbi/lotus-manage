import src.core.advisory_engine as advisory_engine
import src.core.dpm_engine as dpm_engine
import src.core.engine as engine


def test_engine_shim_exports_expected_entrypoints():
    assert engine.run_simulation is dpm_engine.run_simulation
    assert engine.run_proposal_simulation is advisory_engine.run_proposal_simulation
