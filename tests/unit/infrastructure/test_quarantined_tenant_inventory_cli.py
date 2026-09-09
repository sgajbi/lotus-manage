"""CLI behavior for the NULL-tenant quarantine inventory."""

from __future__ import annotations

import json

from scripts import quarantined_tenant_inventory


def test_cli_emits_success_report_to_stdout(monkeypatch, capsys) -> None:
    report = {
        "schemaVersion": "lotus-manage.quarantined-tenant-inventory.v1",
        "status": "success",
        "readOnly": True,
        "limitPerDataset": 5,
        "totalQuarantinedRows": 0,
        "datasets": [],
    }
    monkeypatch.setattr(quarantined_tenant_inventory, "_run_inventory", lambda **_kwargs: report)

    exit_code = quarantined_tenant_inventory.main(["--dsn", "postgresql://test", "--limit", "5"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == report
    assert captured.err == ""


def test_cli_failure_is_nonzero_and_does_not_leak_exception_or_dsn(monkeypatch, capsys) -> None:
    def fail(**_kwargs):
        raise RuntimeError("password=do-not-print host=private-db")

    monkeypatch.setattr(quarantined_tenant_inventory, "_run_inventory", fail)

    exit_code = quarantined_tenant_inventory.main(
        ["--dsn", "postgresql://operator:secret@private-db/manage"]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "schemaVersion": "lotus-manage.quarantined-tenant-inventory.v1",
        "status": "error",
        "errorCode": "QUARANTINE_INVENTORY_FAILED",
    }
    assert "secret" not in captured.err
    assert "private-db" not in captured.err
