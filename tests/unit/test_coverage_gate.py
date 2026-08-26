from __future__ import annotations

from pathlib import Path

import coverage
from pytest import CaptureFixture

from scripts.coverage_gate import DEFAULT_COVERAGE_FILES, REPORT_PRECISION, enforce_coverage_gate
from coverage.results import should_fail_under


def test_coverage_gate_reports_missing_default_files(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    result = enforce_coverage_gate(coverage_dir=tmp_path, fail_under=99.0)

    assert result == 1
    output = capsys.readouterr().out
    for coverage_file in DEFAULT_COVERAGE_FILES:
        assert (tmp_path / coverage_file).as_posix() in output


def test_coverage_gate_reports_missing_custom_artifact_files(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    result = enforce_coverage_gate(
        coverage_dir=tmp_path,
        coverage_files=[".coverage.unit", ".coverage.integration"],
        fail_under=99.0,
    )

    assert result == 1
    output = capsys.readouterr().out
    assert (tmp_path / ".coverage.unit").as_posix() in output
    assert (tmp_path / ".coverage.integration").as_posix() in output
    assert (tmp_path / ".coverage.e2e").as_posix() not in output


def test_coverage_gate_loads_one_monolithic_file_without_consuming_it(
    tmp_path: Path, capsys: CaptureFixture[str]
) -> None:
    source_path = tmp_path / "covered_module.py"
    source_path.write_text("value = 1\n", encoding="utf-8")
    coverage_path = tmp_path / ".coverage"
    measured = coverage.Coverage(data_file=coverage_path.as_posix())
    measured.start()
    exec(compile(source_path.read_text(encoding="utf-8"), source_path.as_posix(), "exec"))
    measured.stop()
    measured.save()

    result = enforce_coverage_gate(
        coverage_dir=tmp_path,
        coverage_files=[coverage_path.name],
        fail_under=100.0,
    )

    assert result == 0
    assert coverage_path.exists()
    assert "Coverage gate passed: 100.00" in capsys.readouterr().out


def test_coverage_gate_uses_report_precision_for_threshold_boundary() -> None:
    assert not should_fail_under(98.999, 99.0, REPORT_PRECISION)


def test_coverage_gate_still_fails_materially_below_threshold() -> None:
    assert should_fail_under(98.994, 99.0, REPORT_PRECISION)
