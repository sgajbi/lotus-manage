"""Exact retained bytes and complete traversal, independent of future HTTP wire decoding."""

import hashlib

import pytest

from src.infrastructure.composites.core_source_custody import (
    CashFact,
    FlowCut,
    FlowFact,
    FlowPin,
    RetainedPortfolio,
    CaptureSegment,
    TraversalPage,
    core_digest,
    reconstruct_capture,
    validate_traversal,
)

SCOPE = "sha256:" + "1" * 64
ROOT = "sha256:" + "2" * 64
RAW = b'{"source":"native","amount":"0","unknown":null}'


def segments():
    raw_digest = "sha256:" + hashlib.sha256(RAW).hexdigest()
    return tuple(
        CaptureSegment(
            capture_id="capture/opaque",
            scope_digest=SCOPE,
            raw_digest=raw_digest,
            segment_index=index,
            segment_count=2,
            data=data,
        )
        for index, data in enumerate((RAW[:17], RAW[17:]))
    )


def pages():
    common = dict(scope_digest=SCOPE, source_root=ROOT, total_count=3)
    return (
        TraversalPage(**common, row_keys=("a", "b"), request_token=None, next_token="opaque/token"),
        TraversalPage(**common, row_keys=("c",), request_token="opaque/token", next_token=None),
    )


def test_exact_segment_bytes_and_producer_digest_are_preserved():
    assert reconstruct_capture(segments(), scope_digest=SCOPE) == RAW
    bare = hashlib.sha256(RAW).hexdigest()
    assert core_digest(bare) == "sha256:" + bare
    assert core_digest(bare) != "sha256:" + hashlib.sha256(bare.encode()).hexdigest()


@pytest.mark.parametrize("value", ["1" * 63, "G" * 64, "A" * 64, ROOT, " " + "1" * 64])
def test_digest_normalization_rejects_aliases_and_malformed_hashes(value):
    with pytest.raises(ValueError, match="DIGEST_INVALID"):
        core_digest(value)


@pytest.mark.parametrize(
    "mutation", ["missing", "order", "duplicate", "bytes", "scope", "root", "id"]
)
def test_raw_capture_never_accepts_partial_reordered_or_mixed_bytes(mutation):
    first, second = segments()
    if mutation == "missing":
        selected = (first,)
    elif mutation == "order":
        selected = (second, first)
    elif mutation == "duplicate":
        selected = (first, first)
    else:
        field, value = {
            "bytes": ("data", b"changed"),
            "scope": ("scope_digest", ROOT),
            "root": ("raw_digest", ROOT),
            "id": ("capture_id", "another"),
        }[mutation]
        selected = (first, second.model_copy(update={field: value}))
    with pytest.raises(ValueError, match="CORE_CUSTODY_CAPTURE"):
        reconstruct_capture(selected, scope_digest=SCOPE)


def test_complete_paged_and_explicit_empty_traversal():
    assert validate_traversal(pages(), scope_digest=SCOPE, source_root=ROOT) == ("a", "b", "c")
    empty = TraversalPage(
        scope_digest=SCOPE,
        source_root=ROOT,
        total_count=0,
        row_keys=(),
        request_token=None,
        next_token=None,
    )
    assert validate_traversal((empty,), scope_digest=SCOPE, source_root=ROOT) == ()
    with pytest.raises(ValueError, match="AFTER_TERMINAL"):
        validate_traversal((empty, empty), scope_digest=SCOPE, source_root=ROOT)


@pytest.mark.parametrize(
    "mutation",
    [
        "absent",
        "partial",
        "scope",
        "root",
        "count",
        "token",
        "loop",
        "order",
        "duplicate",
        "terminal",
    ],
)
def test_traversal_refuses_changed_scope_roots_counts_or_continuation(mutation):
    first, second = pages()
    selected = (first, second)
    if mutation == "absent":
        selected = ()
    elif mutation == "partial":
        selected = (first,)
    elif mutation == "terminal":
        selected = (
            first,
            second,
            second.model_copy(update={"request_token": None, "row_keys": ()}),
        )
    else:
        field, value = {
            "scope": ("scope_digest", ROOT),
            "root": ("source_root", SCOPE),
            "count": ("total_count", 4),
            "token": ("request_token", "substitution"),
            "loop": ("next_token", "opaque/token"),
            "order": ("row_keys", ("0",)),
            "duplicate": ("row_keys", ("b",)),
        }[mutation]
        selected = (first, second.model_copy(update={field: value}))
    with pytest.raises(ValueError, match="CORE_CUSTODY_TRAVERSAL"):
        validate_traversal(selected, scope_digest=SCOPE, source_root=ROOT)


def test_absent_capture_never_becomes_an_empty_valid_source():
    with pytest.raises(ValueError, match="CAPTURE_MISSING"):
        reconstruct_capture((), scope_digest=SCOPE)
    assert reconstruct_capture(segments(), scope_digest=SCOPE) == RAW


@pytest.mark.parametrize("boundary", ["interval", "clock", "correction"])
def test_observation_envelope_rejects_invalid_effectivity_chronology_and_revision(boundary):
    from tests.unit.dpm.infrastructure.test_core_source_reader import fixture_products, encoded

    fact = fixture_products("P1")[2][1]["fact"]
    assert CashFact.model_validate_json(encoded(fact)).settled == "0.00"
    envelope = fact["envelope"]
    if boundary == "interval":
        envelope["effective_to"] = envelope["effective_from"]
    elif boundary == "clock":
        envelope["generated_at"] = "2025-01-01T00:00:00Z"
    else:
        envelope["source_revision"] = 2
    with pytest.raises(
        ValueError,
        match="OBSERVATION_"
        + {"interval": "INTERVAL", "clock": "CHRONOLOGY", "correction": "CORRECTION"}[boundary],
    ):
        CashFact.model_validate_json(encoded(fact))


@pytest.mark.parametrize("boundary", ["pin", "effective", "reversal", "target", "cut"])
def test_flow_admission_rejects_inconsistent_pins_effectivity_and_reversal_target(boundary):
    from tests.unit.dpm.infrastructure.test_core_source_reader import fixture_products, encoded

    payload = fixture_products("P1")[4][1]
    fact = payload["events"][0]["fact"]
    assert FlowFact.model_validate_json(encoded(fact)).amount == "-10.00"
    pin = payload["cut"]["event_pins"][0]
    if boundary == "pin":
        pin["content_hash"] = "f" * 64
        model, value, error = FlowPin, pin, "FLOW_PIN"
    elif boundary == "cut":
        payload["cut"]["cut_revision"] = 2
        model, value, error = FlowCut, payload["cut"], "FLOW_CUT"
    else:
        if boundary == "effective":
            fact["envelope"]["effective_to"] = fact["business_date"]
            error = "FLOW_EFFECTIVE_DATE"
        elif boundary == "reversal":
            fact["classification"] = "REVERSAL"
            error = "FLOW_REVERSAL"
        else:
            fact.update(
                classification="REVERSAL",
                reversal_state="REVERSES",
                reverses_source_record_id="another-record",
                reversal_target=pin,
            )
            error = "FLOW_TARGET"
        model, value = FlowFact, fact
    with pytest.raises(ValueError, match=error):
        model.model_validate_json(encoded(value))


def test_retained_role_descriptors_cannot_relabel_a_cash_product_as_valuation():
    from tests.unit.dpm.infrastructure.test_core_financial_sources import Reader

    retained = Reader().portfolios["P1"].model_dump(mode="python")
    retained["roles"][2]["product_name"] = "PortfolioTimeseriesInput"
    with pytest.raises(ValueError, match="ROLE_FAMILY"):
        RetainedPortfolio.model_validate(retained)
