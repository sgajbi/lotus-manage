"""Actual configured HTTP sources, registered API, PostgreSQL and API-process restart.

The initial month is retained synthetic history. Source correction and approval
are actual HTTP requests; no bank identity, source qualification or activation.
"""

import pytest

from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS
from tests.integration.dpm.composites.test_composite_configured_sources_postgres import (
    synthetic_sources,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api


def amendment_command(proposal):
    return dict(
        month=proposal.evaluation.month,
        policy_approval_content_hash=proposal.policy_approval.content_hash,
        parent_membership_revision=proposal.parent_membership_revision,
        parent_membership_content_hash=proposal.parent_membership_content_hash,
        attestation_version=proposal.universe.attestation_version,
        universe_content_hash=proposal.universe.content_hash,
        target_membership_revision=proposal.target_membership_revision,
        correlation_id=proposal.correlation_id,
        amendment=proposal.amendment.model_dump(mode="json"),
    )


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_registered_source_correction_approval_restart_and_exact_receipt_versions(
    monkeypatch, profile
):
    headers = HEADERS | {
        "X-Service-Identity": "synthetic-native-amendment-proof",
        "X-Capabilities": "manage.write",
        "X-Actor-Id": "synthetic-native-amendment-maker",
        "X-Correlation-Id": "synthetic-native-amendment-proof",
    }
    checker = headers | {"X-Actor-Id": "synthetic-native-independent-checker"}
    with disposable_database() as dsn, synthetic_sources(monkeypatch) as (configuration, state):
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        scope, original, parent = seed_complete_monthly_root(
            repository, definition_product_version=profile
        )
        material = corrected_monthly_proposal(
            original, parent, sequence=original.publication_sequence
        )
        repository.save_universe_attestation(attestation=material.universe)
        state["assembly"] = material.source_assembly_evidence.assembly.model_dump(mode="json")
        url = BASE + "/evaluations/" + material.evaluation_revision
        command = amendment_command(material)
        resolver = BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve"
        with native_api(dsn, composite_config=configuration) as (client, _):
            malformed = client.put(
                url + "/source-amendment",
                headers=headers,
                json=command | {"observations": material.observations.model_dump(mode="json")},
            )
            assert malformed.status_code == 422, malformed.text
            assert state["calls"] == []
            state["deny"] = True
            unavailable = client.put(url + "/source-amendment", headers=headers, json=command)
            assert unavailable.status_code == 503, unavailable.text
            assert (
                repository.get_monthly_evaluation_proposal(
                    **scope, evaluation_revision=material.evaluation_revision
                )
                is None
            )
            assert (
                len(
                    repository.list_publications(
                        tenant_id=scope["tenant_id"], after_sequence=0, limit=10
                    ).items
                )
                == 2
            )
            assert state["calls"] == ["observations", "verification"]
            state["deny"] = False
            proposed = client.put(url + "/source-amendment", headers=headers, json=command)
            assert proposed.status_code == 200, proposed.text
            proposal = proposed.json()
            assert proposal["product_version"] == "v2"
            assert proposal["observations"] == material.observations.model_dump(mode="json")
            assert proposal["evaluation"]["included_count"] == 0
            assert state["calls"] == ["observations", "verification"] * 2
            approval_command = {"expected_proposal_content_hash": proposal["content_hash"]}
            refused = client.put(url + "/approval", headers=headers, json=approval_command)
            assert refused.status_code == 422, refused.text
            wrong_role = client.put(
                url + "/approval",
                headers=checker | {"X-Role": "DPM_REVIEWER"},
                json=approval_command,
            )
            assert wrong_role.status_code == 403, wrong_role.text
            approved = client.put(url + "/approval", headers=checker, json=approval_command)
            assert approved.status_code == 200, approved.text
            approval = approved.json()
            assert approval["product_version"] == "v2"
            binding = dict(
                product_name=approval["product_name"],
                product_version="v2",
                revision=material.evaluation_revision,
                digest=approval["content_hash"],
            )
            resolved = client.post(resolver, headers=headers, json=binding)
            assert resolved.status_code == 200, resolved.text
            amended = resolved.json()
            assert amended["lineage"] == command["amendment"]
            assert amended["definition"]["product_version"] == profile
            assert amended["completeness"] == "UNVERIFIED"
            wrong_version = client.post(
                resolver, headers=headers, json=binding | {"product_version": "v1"}
            )
            assert wrong_version.status_code == 422, wrong_version.text
        # New interpreter, new PostgreSQL read snapshot, same actual registered routes.
        with native_api(dsn, composite_config=configuration) as (client, _):
            for receipt in (original.model_dump(mode="json"), amended):
                retained = receipt["approval"]
                binding = dict(
                    product_name=retained["product_name"],
                    product_version=retained["product_version"],
                    revision=retained["proposal"]["evaluation_revision"],
                    digest=retained["content_hash"],
                )
                reopened = client.post(resolver, headers=headers, json=binding)
                assert reopened.status_code == 200, reopened.text
                assert reopened.json() == receipt
            for endpoint, body, identity, expected in (
                (url + "/source-amendment", command, headers, proposal),
                (url + "/approval", approval_command, checker, approval),
            ):
                replay = client.put(endpoint, headers=identity, json=body)
                assert replay.status_code == 200, replay.text
                assert replay.json() == expected
            publications = client.get("/api/v1/rebalance/composites/publications", headers=headers)
            assert publications.status_code == 200, publications.text
            assert len(publications.json()["items"]) == 3
        assert state["calls"] == ["observations", "verification"] * 2
        assert (
            repository.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=material.evaluation_revision,
                approval_content_hash=approval["content_hash"],
            ).model_dump(mode="json")
            == amended
        )
