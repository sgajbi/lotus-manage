import importlib

import pytest

import src.core.advisory_engine as advisory_engine
import src.core.rebalance.engine as dpm_engine_impl


def test_engine_shim_exports_expected_entrypoints():
    with pytest.warns(DeprecationWarning):
        dpm_engine = importlib.import_module("src.core.dpm_engine")
    with pytest.warns(DeprecationWarning):
        engine = importlib.import_module("src.core.engine")

    assert engine.run_simulation is dpm_engine_impl.run_simulation
    assert dpm_engine.run_simulation is dpm_engine_impl.run_simulation
    assert engine.run_proposal_simulation is advisory_engine.run_proposal_simulation
