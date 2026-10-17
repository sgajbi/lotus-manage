"""Original retained valuation export identity and dense native page checks."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.composite_eligibility.native_source_custody import NativeCaptureCommitment
from src.infrastructure.composites.core_source_products import require_fields
from src.infrastructure.composites.core_source_wire import InputRow, ValuationSelector


def validate_valuation(
    payload: dict[str, Any],
    capture: NativeCaptureCommitment,
    selector: ValuationSelector,
    selected: InputRow,
) -> int:
    receipt, request, result = payload["receipt"], payload["request"], payload["result"]
    if not isinstance(request, dict):
        raise ValueError("CORE_READER_EXPORT_REQUEST")
    _require_export_identity(receipt, capture, selector, selected)
    _require_original_export_request(request, result, capture, selector, selected)
    evidence = result["source_evidence"]
    if (
        evidence.get("availability") != "RETAINED"
        or not evidence.get("pages")
        or not isinstance(result["data"], list)
    ):
        raise ValueError("CORE_READER_EXPORT_RETAINED_REQUIRED")
    count = _valuation_traversal(evidence["pages"], request, selector, selected, capture)
    _require_export_row_count(result, receipt, count)
    return count


def _require_export_identity(
    receipt: dict[str, Any],
    capture: NativeCaptureCommitment,
    selector: ValuationSelector,
    selected: InputRow,
) -> None:
    require_fields(
        receipt,
        ("job_id", "status", "dataset_type", "portfolio_id", "completed_at", "result_row_count"),
    )
    if datetime.fromisoformat(receipt["completed_at"]).utcoffset() is None:
        raise ValueError("CORE_READER_EXPORT_RECEIPT")
    context = capture.source_context
    if selector.export_job_id is None or (
        receipt["job_id"],
        receipt["status"],
        receipt["dataset_type"],
        receipt["portfolio_id"],
        context.receipt_job_id,
        context.export_job_id,
        context.source_revision,
        selector.export_content_hash,
    ) != (
        selector.export_job_id,
        "completed",
        "portfolio_timeseries",
        selected.graph.portfolio_id,
        selector.export_job_id,
        selector.export_job_id,
        selector.export_job_id,
        capture.typed_content_hash,
    ):
        raise ValueError("CORE_READER_EXPORT_IDENTITY")


def _require_original_export_request(
    request: dict[str, Any],
    result: dict[str, Any],
    capture: NativeCaptureCommitment,
    selector: ValuationSelector,
    selected: InputRow,
) -> None:
    if (
        request.get("refresh_of_job_id"),
        capture.source_context.refresh_of_job_id,
        request.get("portfolio_id"),
        request.get("dataset_type"),
        result.get("job_id"),
        result.get("dataset_type"),
    ) != (
        selector.refresh_of_job_id,
        selector.refresh_of_job_id,
        selected.graph.portfolio_id,
        "portfolio_timeseries",
        selector.export_job_id,
        "portfolio_timeseries",
    ):
        raise ValueError("CORE_READER_EXPORT_REQUEST")


def _valuation_traversal(
    pages: list[dict[str, Any]],
    request: dict[str, Any],
    selector: ValuationSelector,
    selected: InputRow,
    capture: NativeCaptureCommitment,
) -> int:
    count, tokens = 0, set()
    for index, page in enumerate(pages):
        _valuation_page(page, index, request, selector, selected, capture)
        count += page["row_count"]
        token = page["source_metadata"]["page"].get("next_page_token")
        if index == len(pages) - 1:
            if token is not None:
                raise ValueError("CORE_READER_EXPORT_INCOMPLETE")
        elif not isinstance(token, str) or not token or token in tokens or not page["row_count"]:
            raise ValueError("CORE_READER_EXPORT_PROGRESS")
        else:
            tokens.add(token)
    return count


def _require_export_row_count(result: dict[str, Any], receipt: dict[str, Any], count: int) -> None:
    if (
        type(result.get("result_row_count")) is not int
        or type(receipt["result_row_count"]) is not int
        or (len(result["data"]), result["result_row_count"], receipt["result_row_count"])
        != (count, count, count)
    ):
        raise ValueError("CORE_READER_EXPORT_COUNT")


def _valuation_page(
    page: dict[str, Any],
    index: int,
    request: dict[str, Any],
    selector: ValuationSelector,
    selected: InputRow,
    capture: NativeCaptureCommitment,
) -> None:
    meta, scope = page["source_metadata"], page["requested_scope"]
    paging = meta["page"]
    window = {"start_date": selector.from_date, "end_date": selector.to_date}
    epoch, fingerprint = paging.get("snapshot_epoch"), paging.get("request_scope_fingerprint")
    _require_valuation_page_count(page, index, paging)
    _require_valuation_epoch(epoch, fingerprint, capture)
    _require_valuation_scope(meta, scope, request, selector, selected, window)


def _require_valuation_page_count(page: dict[str, Any], index: int, paging: dict[str, Any]) -> None:
    if (
        type(page["page_number"]) is not int
        or page["page_number"] != index + 1
        or type(page["row_count"]) is not int
        or page["row_count"] < 0
        or type(paging.get("returned_row_count")) is not int
        or page["row_count"] != paging["returned_row_count"]
    ):
        raise ValueError("CORE_READER_EXPORT_PAGE_COUNT")


def _require_valuation_epoch(
    epoch: Any, fingerprint: Any, capture: NativeCaptureCommitment
) -> None:
    if (
        type(epoch) is not int
        or epoch < 0
        or not isinstance(fingerprint, str)
        or not fingerprint.strip()
        or (str(epoch), fingerprint)
        != (capture.source_context.snapshot_epoch, capture.source_context.request_scope)
    ):
        raise ValueError("CORE_READER_EXPORT_EPOCH_SCOPE")


def _require_valuation_scope(
    meta: dict[str, Any],
    scope: dict[str, Any],
    request: dict[str, Any],
    selector: ValuationSelector,
    selected: InputRow,
    window: dict[str, str],
) -> None:
    requested = request["portfolio_timeseries_request"]
    if not isinstance(requested, dict):
        raise ValueError("CORE_READER_EXPORT_REQUEST")
    if meta.get("source_evidence_current") is not True:
        raise ValueError("CORE_READER_EXPORT_PAGE_SCOPE")
    if (
        meta.get("tenant_id"),
        meta.get("portfolio_id"),
        meta.get("reporting_currency"),
        meta.get("resolved_window"),
        scope.get("window"),
        scope.get("as_of_date"),
        scope.get("reporting_currency"),
        scope.get("consumer_system"),
        {k: v for k, v in requested.items() if k != "page"},
        meta.get("data_quality_status"),
        meta.get("freshness_status"),
        meta.get("source_evidence_current"),
        scope.get("period"),
    ) != (
        selected.graph.identity.tenant_id,
        selected.graph.portfolio_id,
        selected.graph.currency,
        window,
        window,
        selector.as_of_date,
        selected.graph.currency,
        selector.consumer_system,
        scope,
        "COMPLETE",
        "CURRENT",
        True,
        None,
    ):
        raise ValueError("CORE_READER_EXPORT_PAGE_SCOPE")
