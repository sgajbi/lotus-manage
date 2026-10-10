"""Actual HTTP correction and process restart with explicit controlled admission injection."""

import pytest

from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_historical_policy_helpers import seed_historical_root
from tests.composite_monthly_amendment_helpers import corrected_monthly_proposal
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS
from tests.integration.dpm.composites.test_composite_configured_sources_postgres import (
    synthetic_sources,
)
from tests.integration.dpm.composites.test_composite_monthly_amendment_http_postgres import (
    amendment_command,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_native_v4_correction_and_fresh_default_process_exact_receipts(monkeypatch, profile):
    headers = HEADERS | {
        "X-Service-Identity": "synthetic-native-amendment-proof",
        "X-Capabilities": "manage.write",
        "X-Actor-Id": "controlled-native-maker",
        "X-Correlation-Id": "controlled-native-historical-proof",
    }
    checker = headers | {"X-Actor-Id": "controlled-native-checker"}
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        port, scope, original, parent = seed_historical_root(
            repository, definition_product_version=profile
        )
        material = corrected_monthly_proposal(
            original,
            parent,
            sequence=original.publication_sequence,
            historical_verifier=port,
        )
        repository.save_universe_attestation(attestation=material.universe)
        state["assembly"] = material.source_assembly_evidence.assembly.model_dump(mode="json")
        url = BASE + "/evaluations/" + material.evaluation_revision
        command = amendment_command(material)
        resolver = BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve"
        with native_api(dsn, composite_config=configuration, historical_test_admission=True) as (
            client,
            _,
        ):
            proposed = client.put(url + "/source-amendment", headers=headers, json=command)
            assert proposed.status_code == 200, proposed.text
            assert proposed.json()["product_version"] == "v4"
            approval_command = {"expected_proposal_content_hash": proposed.json()["content_hash"]}
            checked = client.put(url + "/approval", headers=checker, json=approval_command)
            assert checked.status_code == 200, checked.text
            assert checked.json()["product_version"] == "v4"
            binding = dict(
                product_name=checked.json()["product_name"],
                product_version="v4",
                revision=material.evaluation_revision,
                digest=checked.json()["content_hash"],
            )
            resolved = client.post(resolver, headers=headers, json=binding)
            assert resolved.status_code == 200, resolved.text
            receipt = resolved.json()
            assert receipt["lineage"] == proposed.json()["amendment"]
            assert receipt["approval"]["proposal"][
                "policy_approval"
            ] == original.approval.proposal.policy_approval.model_dump(mode="json")
        state["deny"] = True
        calls = list(state["calls"])
        # Default fresh process has neither source configuration nor historical test injection.
        with native_api(dsn) as (fresh, _):
            assert (
                fresh.put(url + "/source-amendment", headers=headers, json=command).json()
                == proposed.json()
            )
            assert (
                fresh.put(url + "/approval", headers=checker, json=approval_command).json()
                == checked.json()
            )
            replay = fresh.post(resolver, headers=headers, json=binding)
            assert replay.status_code == 200, replay.text
            assert replay.json() == receipt
            original_binding = dict(
                product_name=original.approval.product_name,
                product_version="v3",
                revision=original.approval.proposal.evaluation_revision,
                digest=original.approval.content_hash,
            )
            old = fresh.post(resolver, headers=headers, json=original_binding)
            assert old.status_code == 200, old.text
            assert old.json() == original.model_dump(mode="json")
        assert state["calls"] == calls
