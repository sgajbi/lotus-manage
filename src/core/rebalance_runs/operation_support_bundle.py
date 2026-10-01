"""Attempt-aware operation evidence projection; never infer membership from correlation text."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmLineageEdgeRecord,
    DpmOperationHistoricalRun,
    DpmOperationScenarioEvidence,
    DpmOperationSupportBundleResponse,
    DpmRunSupportBundleResponse,
)
from src.core.rebalance_runs.repository import DpmRunRepository
from src.core.rebalance_runs.serializers import to_async_status


class OperationEvidenceInvalidError(ValueError):
    pass


@dataclass
class OperationSupportBundleBuilder:
    repository: DpmRunRepository
    operation: DpmAsyncOperationRecord
    bundle_for_run: Callable[[str], DpmRunSupportBundleResponse]
    include_async_operation: bool

    def build(self) -> DpmOperationSupportBundleResponse:
        requested = self._requested_scenarios()
        result = self.operation.result_json or {}
        results = result.get("results", {}) if self.operation.status == "SUCCEEDED" else {}
        failures = (
            result.get("failed_scenarios", {}) if self.operation.status == "SUCCEEDED" else {}
        )
        if not isinstance(results, dict) or not isinstance(failures, dict):
            raise OperationEvidenceInvalidError("DPM_ASYNC_OPERATION_EVIDENCE_INVALID")
        if not set(results).issubset(requested) or not set(failures).issubset(requested):
            raise OperationEvidenceInvalidError("DPM_ASYNC_OPERATION_EVIDENCE_INVALID")

        edges = self._membership_edges()
        memberships: dict[tuple[str, str], list[DpmLineageEdgeRecord]] = defaultdict(list)
        for edge in edges:
            scenario_key = edge.metadata_json.get("scenario_key")
            if isinstance(scenario_key, str):
                memberships[(scenario_key, edge.target_entity_id)].append(edge)

        scenarios, selected_ids = self._scenario_outcomes(
            requested=requested,
            results=results,
            failures=failures,
            memberships=memberships,
        )

        return DpmOperationSupportBundleResponse(
            operation_id=self.operation.operation_id,
            status=self.operation.status,
            async_operation=to_async_status(self.operation)
            if self.include_async_operation
            else None,
            scenarios=scenarios,
            historical_runs=self._historical_runs(
                edges=edges, selected_ids=selected_ids, requested=requested
            ),
        )

    def _scenario_outcomes(
        self,
        *,
        requested: dict[str, Any],
        results: dict[str, Any],
        failures: dict[str, Any],
        memberships: dict[tuple[str, str], list[DpmLineageEdgeRecord]],
    ) -> tuple[dict[str, DpmOperationScenarioEvidence], set[str]]:
        scenarios: dict[str, DpmOperationScenarioEvidence] = {}
        selected_ids: set[str] = set()
        result_ids = Counter(
            run_id
            for outcome in results.values()
            if isinstance(outcome, dict)
            if isinstance(run_id := outcome.get("rebalance_run_id"), str)
        )
        for scenario_key in sorted(requested):
            outcome = results.get(scenario_key)
            run_id = outcome.get("rebalance_run_id") if isinstance(outcome, dict) else None
            matching = (
                memberships.get((scenario_key, run_id), []) if isinstance(run_id, str) else []
            )
            if (
                isinstance(run_id, str)
                and result_ids[run_id] == 1
                and self._is_authoritative(run_id=run_id, matching=matching)
            ):
                assert isinstance(run_id, str)
                selected_ids.add(run_id)
                scenarios[scenario_key] = DpmOperationScenarioEvidence(
                    status="succeeded", bundle=self.bundle_for_run(run_id)
                )
                continue
            failure = failures.get(scenario_key)
            scenarios[scenario_key] = DpmOperationScenarioEvidence(
                status="failed" if isinstance(failure, str) else "missing",
                error=failure if isinstance(failure, str) else None,
            )
        return scenarios, selected_ids

    def _requested_scenarios(self) -> dict[str, Any]:
        request = self.operation.request_json or {}
        batch_request = request.get("batch_request", request)
        requested = batch_request.get("scenarios", {}) if isinstance(batch_request, dict) else {}
        if not isinstance(requested, dict) or any(not isinstance(key, str) for key in requested):
            raise OperationEvidenceInvalidError("DPM_ASYNC_OPERATION_EVIDENCE_INVALID")
        return requested

    def _membership_edges(self) -> list[DpmLineageEdgeRecord]:
        return [
            edge
            for edge in self.repository.list_lineage_edges(entity_id=self.operation.operation_id)
            if edge.edge_type == "OPERATION_TO_RUN"
            and edge.source_entity_id == self.operation.operation_id
            and edge.tenant_id == self.operation.tenant_id
        ]

    def _is_authoritative(self, *, run_id: Any, matching: list[DpmLineageEdgeRecord]) -> bool:
        if not isinstance(run_id, str) or len(matching) != 1:
            return False
        if matching[0].metadata_json.get("execution_attempt") != self.operation.execution_attempt:
            return False
        run = self.repository.get_run(rebalance_run_id=run_id)
        return run is not None and run.tenant_id == self.operation.tenant_id

    def _historical_runs(
        self,
        *,
        edges: list[DpmLineageEdgeRecord],
        selected_ids: set[str],
        requested: dict[str, Any],
    ) -> list[DpmOperationHistoricalRun]:
        historical: list[DpmOperationHistoricalRun] = []
        seen_ids = set(selected_ids)
        for edge in sorted(edges, key=lambda item: (item.created_at, item.target_entity_id)):
            if edge.target_entity_id in seen_ids:
                continue
            run = self.repository.get_run(rebalance_run_id=edge.target_entity_id)
            if run is None or run.tenant_id != self.operation.tenant_id:
                continue
            scenario_key = edge.metadata_json.get("scenario_key")
            attempt = edge.metadata_json.get("execution_attempt")
            if (
                not isinstance(scenario_key, str)
                or scenario_key not in requested
                or not isinstance(attempt, int)
                or attempt < 1
                or attempt > self.operation.execution_attempt
            ):
                continue
            seen_ids.add(edge.target_entity_id)
            historical.append(
                DpmOperationHistoricalRun(
                    scenario_key=scenario_key,
                    execution_attempt=attempt,
                    bundle=self.bundle_for_run(run.rebalance_run_id),
                )
            )
        return historical
