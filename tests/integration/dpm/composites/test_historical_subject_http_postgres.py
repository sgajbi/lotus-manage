"""Empty business scope → native historical first publication → source-off process restart.

Requires the independently admitted PostgreSQL test lane. No business history is seeded.
Source fixtures are explicit synthetic original history, never institutional approval.
"""

import psycopg
from psycopg.rows import dict_row

from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_controls import EVALUATION_APPROVAL_ADAPTER
from src.core.composite_eligibility.staged_publication import decode_subject_receipt
from tests.composite_historical_subject_helpers import empty_historical_subject_service
from tests.composite_monthly_source_helpers import assembly_material
from tests.composite_staged_eligibility_helpers import BASE, HEADERS, CHECKER, final_definition
from tests.integration.dpm.composites.historical_provider import historical_provider
from tests.integration.dpm.composites.test_composite_configured_sources_postgres import (
    synthetic_sources,
)
from tests.integration.dpm.network_runtime import disposable_database, native_api
from tests.unit.api.test_composite_subject_lifecycle_routes import subject_body, policy_body


def test_empty_native_historical_subject_publication_and_source_off_restart(tmp_path, monkeypatch):
    _, _, original, source_subject, source_policy, source_evaluation = (
        empty_historical_subject_service()
    )
    maker = HEADERS | {
        "X-Service-Identity": "synthetic-historical-subject-proof",
        "X-Capabilities": "manage.write",
        "X-Correlation-Id": "synthetic-historical-subject",
    }
    checker = maker | {"X-Actor-Id": CHECKER}
    with (
        disposable_database() as dsn,
        synthetic_sources(monkeypatch) as (sources, source_state),
        historical_provider(tmp_path, monkeypatch, original.mapping) as (
            history,
            provider_state,
            provider,
        ),
    ):
        with native_api(dsn, composite_config=sources, historical_config=history) as (client, _):
            publications = "/api/v1/rebalance/composites/publications"
            before = client.get(publications, headers=maker)
            assert before.status_code == 200 and before.json()["items"] == []
            created = client.put(BASE, headers=maker, json=subject_body(source_subject))
            assert created.status_code == 200, created.text
            subject = EligibilitySubject.model_validate(created.json())
            ordinary = client.put(
                BASE + "/policies/ordinary", headers=maker, json=policy_body(subject, source_policy)
            )
            assert ordinary.status_code == 403
            assert (
                ordinary.json()["detail"]["code"]
                == "COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN"
            )
            policy_url = BASE + "/policies/historical-first-policy"
            historical_body = {
                "expected_subject_content_hash": subject.content_hash,
                "reference": provider.mapping.reference.model_dump(mode="json"),
            }
            proposed = client.put(
                policy_url + "/historical-admission", headers=maker, json=historical_body
            )
            assert proposed.status_code == 200, proposed.text
            policy_hash = {"expected_proposal_content_hash": proposed.json()["content_hash"]}
            self_approval = client.put(policy_url + "/approval", headers=maker, json=policy_hash)
            assert self_approval.status_code == 403
            approved = client.put(policy_url + "/approval", headers=checker, json=policy_hash)
            assert approved.status_code == 200, approved.text
            binding = source_evaluation.observation_binding
            evaluation_url = BASE + "/evaluations/historical-first-evaluation"
            evaluation_body = {
                "policy_proposal_revision": "historical-first-policy",
                "policy_approval_content_hash": approved.json()["content_hash"],
                "target_membership_revision": "historical-first-membership",
                "source_cut_id": binding.source_cut_id,
                "source_revision": binding.source_watermark,
                "source_content_hash": binding.content_hash,
            }
            evaluated = client.put(evaluation_url, headers=maker, json=evaluation_body)
            assert evaluated.status_code == 200, evaluated.text
            assert (
                evaluated.json()["source_assembly_evidence"]["assembly"] == assembly_material()[1]
            )
            approval_body = {"expected_proposal_content_hash": evaluated.json()["content_hash"]}
            checked = client.put(evaluation_url + "/approval", headers=checker, json=approval_body)
            assert checked.status_code == 200, checked.text
            with psycopg.connect(dsn, row_factory=dict_row) as connection:
                for table, response in (
                    ("dpm_composite_monthly_evaluation_proposals", evaluated),
                    ("dpm_composite_monthly_evaluation_approvals", checked),
                ):
                    from psycopg import sql

                    row = connection.execute(
                        sql.SQL("SELECT custody_mode, content_hash, payload_json FROM {}").format(
                            sql.Identifier(table)
                        )
                    ).fetchone()
                    assert row["custody_mode"] == "STAGED"
                    assert row["content_hash"] == response.json()["content_hash"]
                    assert row["payload_json"] == response.json()
                    assert row["payload_json"]["product_version"] == "v2"
            approval = EVALUATION_APPROVAL_ADAPTER.validate_python(checked.json())
            definition = final_definition(subject, approval)
            finalization_body = {
                "evaluation_revision": "historical-first-evaluation",
                "expected_approval_content_hash": approval.content_hash,
                "definition": definition.model_dump(
                    mode="json",
                    exclude={
                        "product_name",
                        "tenant_id",
                        "composite_id",
                        "definition_version",
                        "created_by",
                    },
                ),
            }
            premature = final_definition(
                subject, approval, authority_approved_at=subject.created_at
            )
            refused = client.put(
                BASE + "/finalization",
                headers=checker,
                json=finalization_body
                | {
                    "definition": premature.model_dump(
                        mode="json",
                        exclude={
                            "product_name",
                            "tenant_id",
                            "composite_id",
                            "definition_version",
                            "created_by",
                        },
                    )
                },
            )
            assert refused.status_code == 422
            assert client.get(publications, headers=maker).json()["items"] == []
            published = client.put(BASE + "/finalization", headers=checker, json=finalization_body)
            assert published.status_code == 200, published.text
            receipt = published.json()
            assert receipt["product_version"] == "v3"
            assert decode_subject_receipt(receipt).model_dump(mode="json") == receipt
            assert len(client.get(publications, headers=maker).json()["items"]) == 1
            resolver = "/api/v1/rebalance/composites/synthetic-composite/definitions/synthetic-definition/eligibility-evidence/resolve"
            eligibility = (
                definition.source_authority.payload.eligibility_evaluation_binding.model_dump(
                    mode="json"
                )
            )
            assert client.post(resolver, headers=maker, json=eligibility).json() == receipt
            provider_count = len(provider_state["calls"])
        # No source configuration or seeded controls in the second actual process.
        with native_api(dsn) as (client, _):
            assert client.post(resolver, headers=maker, json=eligibility).json() == receipt
            assert client.get(BASE + "/finalization", headers=maker).json() == receipt
            assert (
                client.put(BASE + "/finalization", headers=checker, json=finalization_body).json()
                == receipt
            )
            assert (
                client.put(
                    policy_url + "/historical-admission", headers=maker, json=historical_body
                ).json()
                == proposed.json()
            )
            assert len(client.get(publications, headers=maker).json()["items"]) == 1
            assert len(provider_state["calls"]) == provider_count
