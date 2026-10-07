"""Real Core cohort consumption; not composite-universe, execution or capacity proof."""

from __future__ import annotations

import uuid

import psycopg
import pytest

from tests.integration.dpm.actual_core_runtime import actual_core
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.integration.dpm.waves.test_source_bound_wave_network import _call, _headers

pytestmark = pytest.mark.integration
_WAVES = "/api/v1/rebalance/waves"
_AS_OF = "2026-04-01"


def _binding(portfolio, mandate, client, model, version, status, *, effective="2026-01-01"):
    return {
        "portfolio_id": portfolio,
        "mandate_id": mandate,
        "client_id": client,
        "discretionary_authority_status": status,
        "booking_center_code": "Singapore",
        "jurisdiction_code": "SG",
        "model_portfolio_id": model,
        "risk_profile": "balanced",
        "investment_horizon": "long_term",
        "rebalance_frequency": "monthly",
        "rebalance_bands": {},
        "effective_from": effective,
        "binding_version": version,
        "source_system": "cohort-consumer-proof",
        "source_record_id": f"{mandate}:v{version}",
        "observed_at": f"2026-0{version}-01T00:00:00Z",
        "quality_status": "accepted",
    }


def _request(model, *, as_of=_AS_OF):
    return {
        "trigger_type": "CIO_MODEL_CHANGE",
        "trigger_id": uuid.uuid4().hex,
        "rationale": "Actual Core effective mandate cohort acceptance",
        "as_of_date": as_of,
        "actor_id": "wave-pm",
        "model_portfolio_id": model,
        "booking_center_code": "Singapore",
    }


def _cohort(core, model, tenant, *, as_of=_AS_OF, supplied_tenant=None):
    body = {
        "as_of_date": as_of,
        "booking_center_code": "Singapore",
        "include_inactive_mandates": False,
    }
    if supplied_tenant is not None:
        body["tenant_id"] = supplied_tenant
    return core.client.post(
        f"/integration/model-portfolios/{model}/affected-mandates",
        headers={"X-Tenant-Id": tenant},
        json=body,
    )


def _assert_lineage(wave, cohort, portfolio, mandate, version):
    assert wave["as_of_date"] == _AS_OF
    assert len(wave["items"]) == 1
    item = wave["items"][0]
    assert (item["portfolio_id"], item["mandate_id"]) == (portfolio, mandate)
    assert item["state"] == "CANDIDATE"  # Cohort membership is not execution readiness.
    refs = {ref["source_type"]: ref for ref in item["source_refs"]}
    assert set(refs) == {
        "CioModelChangeAffectedCohort",
        "CIO_MODEL_CHANGE_EVENT",
        "CIO_MODEL_CHANGE_AFFECTED_MANDATE",
    }
    source = refs["CioModelChangeAffectedCohort"]
    assert source["source_system"] == "lotus-core"
    assert source["source_id"] == cohort["snapshot_id"]
    assert source["source_version"] == cohort["product_version"]
    fingerprint = cohort["source_batch_fingerprint"]
    if fingerprint is None:
        assert source["content_hash"] is None
        # Core's registered cohort currently provides snapshot identity, not a batch digest.
        # This path proves binding/source identity preservation, not positive hash verification.
    else:
        assert isinstance(fingerprint, str) and fingerprint.strip()
        assert source["content_hash"] == fingerprint
    event = refs["CIO_MODEL_CHANGE_EVENT"]
    assert event["source_id"] == cohort["model_change_event_id"]
    assert event["source_version"] == cohort["model_portfolio_version"]
    binding = refs["CIO_MODEL_CHANGE_AFFECTED_MANDATE"]
    assert binding["source_id"] == f"{mandate}:v{version}"
    assert binding["source_version"] == str(version)
    assert source in wave["trigger"]["source_refs"]


def _admit(client, tenant, model, cohort, portfolio, mandate, version):
    body, headers = _request(model), _headers(tenant)
    preview = _call(client, "POST", f"{_WAVES}/preview", headers, body)
    assert preview["durable"] is False
    _assert_lineage(preview["wave"], cohort, portfolio, mandate, version)
    created = _call(client, "POST", _WAVES, headers, body, 201)
    assert created["durable"] is True and created["idempotent_replay"] is False
    _assert_lineage(created["wave"], cohort, portfolio, mandate, version)
    replay = _call(client, "POST", _WAVES, headers, body, 201)
    assert replay["idempotent_replay"] is True
    assert replay["wave"] == created["wave"]
    return created["wave"]


def _refuse(client, tenant, model, *, as_of=_AS_OF):
    for path in (f"{_WAVES}/preview", _WAVES):
        rejected = _call(client, "POST", path, _headers(tenant), _request(model, as_of=as_of), 424)
        assert rejected["detail"]["code"] == "DPM_CORE_CIO_MODEL_CHANGE_COHORT_INCOMPLETE"


def test_actual_core_successors_replace_cohort_without_rewriting_admitted_waves():
    suffix = uuid.uuid4().hex
    tenant, foreign = f"cohort-{suffix}", f"foreign-{suffix}"
    portfolio, mandate, client_id = f"PB_{suffix}", f"MANDATE_{suffix}", f"CLIENT_{suffix}"
    model_a, model_b = f"MODEL_A_{suffix}", f"MODEL_B_{suffix}"
    with actual_core() as core:
        core.ingest(
            {
                "initialize": True,
                "tenant": tenant,
                "portfolio": portfolio,
                "client": client_id,
                "models": [model_a, model_b],
                "bindings": [_binding(portfolio, mandate, client_id, model_a, 1, "active")],
            }
        )
        with disposable_database() as dsn:
            with native_api(dsn, core_url=str(core.client.base_url)) as (api, _):
                first = _cohort(core, model_a, tenant)
                assert first.status_code == 200, first.text
                cohort_a = first.json()
                assert cohort_a["tenant_id"] == tenant and cohort_a["as_of_date"] == _AS_OF
                assert [row["binding_version"] for row in cohort_a["affected_mandates"]] == [1]
                wave_a = _admit(api, tenant, model_a, cohort_a, portfolio, mandate, 1)

                core.ingest(
                    {"bindings": [_binding(portfolio, mandate, client_id, model_a, 2, "suspended")]}
                )
                empty = _cohort(core, model_a, tenant)
                assert empty.status_code == 404
                assert empty.json()["metadata"]["reason"] == "empty_result"
                _refuse(api, tenant, model_a)

                core.ingest(
                    {"bindings": [_binding(portfolio, mandate, client_id, model_b, 3, "active")]}
                )
                assert _cohort(core, model_a, tenant).status_code == 404
                _refuse(api, tenant, model_a)
                third = _cohort(core, model_b, tenant)
                assert third.status_code == 200, third.text
                cohort_b = third.json()
                assert cohort_b["model_portfolio_id"] == model_b
                assert [row["binding_version"] for row in cohort_b["affected_mandates"]] == [3]
                wave_b = _admit(api, tenant, model_b, cohort_b, portfolio, mandate, 3)

                # Effective date, not observed_at, controls historical membership.
                core.ingest(
                    {
                        "bindings": [
                            _binding(
                                portfolio,
                                mandate,
                                client_id,
                                model_a,
                                4,
                                "active",
                                effective="2027-01-01",
                            )
                        ]
                    }
                )
                historical = _cohort(core, model_b, tenant)
                assert historical.status_code == 200, historical.text
                assert historical.json()["as_of_date"] == _AS_OF
                assert historical.json()["affected_mandates"] == cohort_b["affected_mandates"]
                assert historical.json()["snapshot_id"] == cohort_b["snapshot_id"]
                future = _cohort(core, model_a, tenant, as_of="2027-01-01")
                assert future.status_code == 200, future.text
                assert future.json()["as_of_date"] == "2027-01-01"
                assert [row["binding_version"] for row in future.json()["affected_mandates"]] == [4]
                _refuse(api, tenant, model_a)
                _refuse(api, tenant, model_b, as_of="2025-12-31")
                invalid = _call(
                    api,
                    "POST",
                    f"{_WAVES}/preview",
                    _headers(tenant),
                    _request(model_b, as_of="2026/04/01"),
                    422,
                )
                assert invalid["detail"]["code"] == "INVALID_AS_OF_DATE"
                assert _cohort(core, model_b, foreign).status_code == 404
                assert _cohort(core, model_b, foreign, supplied_tenant=tenant).status_code == 403
                _refuse(api, foreign, model_b)
                for wave in (wave_a, wave_b):
                    stored = _call(api, "GET", f"{_WAVES}/{wave['wave_id']}", _headers(tenant))
                    assert stored["wave"] == wave
                    _call(
                        api, "GET", f"{_WAVES}/{wave['wave_id']}", _headers(foreign), expected=404
                    )
                with psycopg.connect(dsn) as observer:
                    observer.execute("SET TRANSACTION READ ONLY")
                    assert observer.execute(
                        "SELECT count(*) FROM dpm_rebalance_waves"
                    ).fetchone() == (2,), "Rejected previews/creates must not persist a wave"

            # A new API process must rehydrate the original cohort/binding evidence.
            with native_api(dsn, core_url=str(core.client.base_url)) as (api, _):
                for wave in (wave_a, wave_b):
                    stored = _call(api, "GET", f"{_WAVES}/{wave['wave_id']}", _headers(tenant))
                    assert stored["wave"] == wave
