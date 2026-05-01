import pytest

from scripts.run_demo_pack_live import DemoRunError, _assert_demo_status


def test_solver_demo_accepts_explicit_solver_unavailable_response() -> None:
    _assert_demo_status(
        name="08_solver_mode.json",
        body={"status": "BLOCKED", "diagnostics": {"warnings": ["SOLVER_ERROR"]}},
        expected="READY",
    )


def test_solver_demo_rejects_blocked_without_solver_warning() -> None:
    with pytest.raises(DemoRunError, match="08_solver_mode.json"):
        _assert_demo_status(
            name="08_solver_mode.json",
            body={"status": "BLOCKED", "diagnostics": {"warnings": []}},
            expected="READY",
        )


def test_non_solver_demo_requires_expected_status() -> None:
    with pytest.raises(DemoRunError, match="01_standard_drift.json"):
        _assert_demo_status(
            name="01_standard_drift.json",
            body={"status": "BLOCKED", "diagnostics": {"warnings": ["SOLVER_ERROR"]}},
            expected="READY",
        )


def test_live_demo_script_does_not_use_fixed_async_correlation_ids() -> None:
    import scripts.run_demo_pack_live as demo_pack

    source = demo_pack.Path(demo_pack.__file__).read_text(encoding="utf-8")

    assert '"demo-corr-26-async"' not in source
    assert '"demo-corr-28-async-inline"' not in source
