from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_observability_contracts import (
    CONTRACT_PATH,
    implemented_metric_contract,
    validate_observability_contract,
)


def _load_contract() -> dict:
    return json.loads(Path(CONTRACT_PATH).read_text(encoding="utf-8"))


def test_observability_monitoring_contract_validates() -> None:
    assert validate_observability_contract() == []


def test_monitoring_contract_references_only_implemented_metrics() -> None:
    payload = _load_contract()
    implemented_metrics = implemented_metric_contract()
    declared_metrics = {metric["name"] for metric in payload["metrics"]}

    assert declared_metrics == set(implemented_metrics)
    for dashboard in payload["dashboards"]:
        for panel in dashboard["panels"]:
            assert panel["metric"] in declared_metrics
    for alert in payload["alerts"]:
        assert alert["metric"] in declared_metrics


def test_monitoring_contract_keeps_sensitive_identifiers_out_of_labels() -> None:
    payload = _load_contract()
    forbidden = set(payload["no_sensitive_telemetry_policy"]["forbidden_label_values"])

    for metric in payload["metrics"]:
        for label_name, allowed_values in metric["labels"].items():
            assert label_name not in forbidden
            assert not any(forbidden_value in allowed_values for forbidden_value in forbidden)
