"""Real HTTP/PostgreSQL/restart proof over explicitly supplied synthetic membership."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import psycopg
import pytest
from psycopg.rows import dict_row

from src.core.composite_membership import DpmCompositeMembershipRevision
from src.core.composite_repository import DpmCompositeConflictError
from src.infrastructure.composites import publication
from src.infrastructure.composites.postgres import PostgresDpmCompositeRepository
from src.infrastructure.mandates.serialization import dump_model_json

from tests.composite_correction_helpers import correction_body, definition_body, original_body
from tests.integration.dpm.network_runtime import disposable_database, native_api

BASE = "/api/v1/rebalance/composites/synthetic-correction/definitions/d1"
PUBLICATIONS = "/api/v1/rebalance/composites/publications"
HEADERS = {
    "X-Tenant-Id": "synthetic-correction-tenant",
    "X-Actor-Id": "synthetic-maker",
    "X-Role": "DPM_COMPOSITE_ADMIN",
    "X-Correlation-Id": "synthetic-correction-proof",
    "X-Service-Identity": "local-network-proof",
    "X-Capabilities": "manage.write",
}


def put(client, path, body):
    headers = HEADERS
    if "/universe-attestations/" in path:
        headers = HEADERS | {
            "X-Role": "DPM_COMPOSITE_UNIVERSE_ATTESTER",
            "X-Service-Identity": "lotus-manage",
        }
    response = client.put(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def get(client, path):
    response = client.get(path, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def statuses(client, revision, day):
    wire = get(client, f"{BASE}/membership/{revision}/as-of?as_of_date={day}")
    return {item["portfolio_id"]: item["status"] for item in wire["decisions"]}


def universe_body(membership, *, first="2026-01-01", last="2026-01-15", posture="COMPLETE"):
    return {
        "coverage_from": first,
        "coverage_to": last,
        "policy_version": membership["policy_version"],
        "source_cut_id": membership["source_cut_id"],
        "source_products": [
            {
                "owner_service": "lotus-manage",
                "product_name": "SyntheticSuppliedUniverse",
                "contract_version": "v1",
                "authority_scope": "AUTHORITATIVE_UNIVERSE",
                "source_cut_id": membership["source_cut_id"],
                "source_watermark": "synthetic-registry-r1",
                "content_hash": "sha256:" + "a" * 64,
            }
        ],
        "posture": posture,
        "expected_portfolio_ids": ["A", "B", "C"],
        "reason_code": "SYNTHETIC_MISSING_MEMBER" if posture == "INCOMPLETE" else None,
        "correlation_id": "synthetic-universe-proof",
    }


def test_native_correction_refusal_replay_restart_and_retained_three_member_history():
    with disposable_database() as dsn:
        with native_api(dsn) as (client, _):
            definition = put(client, BASE, definition_body())
            original = put(client, f"{BASE}/membership/m1", original_body())
            original_universe = put(
                client, f"{BASE}/membership/m1/universe-attestations/u1", universe_body(original)
            )
            bad = correction_body()
            bad["decisions"] = [bad["decisions"][1]]
            refused = client.put(f"{BASE}/membership/m2", headers=HEADERS, json=bad)
            assert refused.status_code == 409, refused.text
            assert (
                refused.json()["detail"]["code"] == "COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"
            )
            assert client.get(f"{BASE}/membership/m2", headers=HEADERS).status_code == 404
            assert len(get(client, PUBLICATIONS)["items"]) == 1
            assert (
                client.put(
                    f"{BASE}/membership/m2",
                    headers=HEADERS | {"X-Role": "DPM_VIEWER"},
                    json=correction_body(),
                ).status_code
                == 403
            )
        # New process with default dependencies: publication must survive response loss.
        with native_api(dsn) as (client, _):
            assert get(client, f"{BASE}/membership/m1") == original
            with ThreadPoolExecutor(max_workers=4) as workers:
                receipts = list(
                    workers.map(
                        lambda _: put(client, f"{BASE}/membership/m2", correction_body()), range(4)
                    )
                )
            corrected = receipts[0]
            assert all(item == corrected for item in receipts)
            corrected_universe = put(
                client, f"{BASE}/membership/m2/universe-attestations/u2", universe_body(corrected)
            )
            _check_boundaries(client)
            # A terminated historical member absent from February is missing if still expected.
            missing = universe_body(
                corrected, first="2026-02-01", last="2026-02-28", posture="INCOMPLETE"
            )
            incomplete = put(client, f"{BASE}/membership/m2/universe-attestations/u3", missing)
            assert incomplete["missing_portfolio_ids"] == ["C"]
            assert incomplete["observed_portfolio_count"] == 2
            assert incomplete["coverage_gap_portfolio_ids"] == []
            conflict = client.put(
                f"{BASE}/membership/m2",
                headers=HEADERS,
                json=correction_body() | {"correlation_id": "different-command"},
            )
            assert conflict.status_code == 409
            foreign = HEADERS | {"X-Tenant-Id": "other-tenant"}
            assert client.get(BASE, headers=foreign).status_code == 404
            assert client.get(f"{BASE}/membership/m2", headers=foreign).status_code == 404
            assert client.get(PUBLICATIONS, headers=foreign).json()["items"] == []
            publications = get(client, PUBLICATIONS)
            assert len(publications["items"]) == 2
            assert all(item["completeness"] == "UNVERIFIED" for item in publications["items"])
            corrected_publication = publications["items"][1]
            assert (
                corrected_publication["affected_from"],
                corrected_publication["affected_to"],
            ) == ("2026-01-05", "2026-01-05")
            assert corrected_publication["membership_content_hash"] == corrected["content_hash"]
        with native_api(dsn) as (client, _):
            assert get(client, BASE) == definition
            assert get(client, f"{BASE}/membership/m1") == original
            assert get(client, f"{BASE}/membership/m2") == corrected
            assert (
                get(client, f"{BASE}/membership/m1/universe-attestations/u1") == original_universe
            )
            assert (
                get(client, f"{BASE}/membership/m2/universe-attestations/u2") == corrected_universe
            )
            assert put(client, f"{BASE}/membership/m2", correction_body()) == corrected
            assert get(client, PUBLICATIONS) == publications


def _check_boundaries(client):
    assert statuses(client, "m1", "2026-01-05") == {
        "A": "INCLUDED",
        "B": "INCLUDED",
        "C": "INCLUDED",
    }
    assert statuses(client, "m2", "2026-01-05") == {
        "A": "EXCLUDED",
        "B": "INCLUDED",
        "C": "INCLUDED",
    }
    for day in ("2026-01-04", "2026-01-06"):
        assert statuses(client, "m1", day) == statuses(client, "m2", day)
    assert statuses(client, "m2", "2026-01-15")["C"] == "INCLUDED"
    assert "C" not in statuses(client, "m2", "2026-01-16")
    assert statuses(client, "m2", "2026-01-31")["B"] == "INCLUDED"
    assert statuses(client, "m2", "2026-02-01")["B"] == "EXCLUDED"


def test_retained_legacy_wrong_window_replays_without_certifying_a_new_correction():
    with disposable_database() as dsn:
        with native_api(dsn) as (client, _):
            put(client, BASE, definition_body())
            put(client, f"{BASE}/membership/m1", original_body())
        bad = correction_body()
        bad["decisions"] = [bad["decisions"][1]]
        legacy = DpmCompositeMembershipRevision(
            **bad,
            tenant_id=HEADERS["X-Tenant-Id"],
            composite_id="synthetic-correction",
            definition_version="d1",
            membership_revision="legacy",
            decided_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            decided_by=HEADERS["X-Actor-Id"],
        )
        # Explicit historical fixture representing pre-fix persisted state; no API bypass.
        with psycopg.connect(dsn, row_factory=dict_row) as connection:
            publication.lock_tenant_publication_order(
                connection=connection, tenant_id=legacy.tenant_id
            )
            connection.execute(
                """INSERT INTO dpm_composite_membership_revisions
                (tenant_id, composite_id, definition_version, membership_revision,
                 decided_at, content_hash, payload_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)""",
                (
                    legacy.tenant_id,
                    legacy.composite_id,
                    legacy.definition_version,
                    legacy.membership_revision,
                    legacy.decided_at,
                    legacy.content_hash,
                    dump_model_json(legacy),
                ),
            )
            publication.publish_revision(connection=connection, revision=legacy)
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        repository.save_membership_revision(revision=legacy)
        with native_api(dsn) as (client, _):
            retained = get(client, f"{BASE}/membership/legacy")
            publications = get(client, PUBLICATIONS)
            assert len(publications["items"]) == 2
            assert put(client, f"{BASE}/membership/legacy", bad) == retained
            refused = client.put(f"{BASE}/membership/new", headers=HEADERS, json=bad)
            assert refused.status_code == 409, refused.text
            assert (
                refused.json()["detail"]["code"] == "COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"
            )
            assert client.get(f"{BASE}/membership/new", headers=HEADERS).status_code == 404
            assert get(client, PUBLICATIONS) == publications
            assert get(client, f"{BASE}/membership/legacy") == retained


def test_postgres_correction_rollback_preserves_original_and_allows_a_valid_retry():
    with disposable_database() as dsn:
        with native_api(dsn) as (client, _):
            put(client, BASE, definition_body())
            original = put(client, f"{BASE}/membership/m1", original_body())
        repository = PostgresDpmCompositeRepository(dsn=dsn)
        key = {
            "tenant_id": HEADERS["X-Tenant-Id"],
            "composite_id": "synthetic-correction",
            "definition_version": "d1",
            "membership_revision": "m2",
        }
        bad = correction_body() | {"decisions": [correction_body()["decisions"][1]]}
        invalid = DpmCompositeMembershipRevision(**key, **bad, decided_by=HEADERS["X-Actor-Id"])
        before = repository.list_publications(
            tenant_id=key["tenant_id"], after_sequence=0, limit=10
        )
        with pytest.raises(
            DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_CORRECTION_OUTSIDE_WINDOW"
        ):
            repository.save_membership_revision(revision=invalid)
        assert repository.get_membership_revision(**key) is None
        assert (
            repository.list_publications(tenant_id=key["tenant_id"], after_sequence=0, limit=10)
            == before
        )
        corrected = DpmCompositeMembershipRevision(
            **key, **correction_body(), decided_by=HEADERS["X-Actor-Id"]
        )
        repository.save_membership_revision(revision=corrected)
        repository.save_membership_revision(revision=corrected)
        assert repository.get_membership_revision(**key) == corrected
        retained = repository.get_membership_revision(**(key | {"membership_revision": "m1"}))
        assert retained is not None
        assert retained.model_dump(mode="json") == original
        assert (
            len(
                repository.list_publications(
                    tenant_id=key["tenant_id"], after_sequence=0, limit=10
                ).items
            )
            == 2
        )

        # A deliberately corrupting storage trigger must not leave a partial publication.
        with psycopg.connect(dsn) as connection:
            connection.execute("""CREATE FUNCTION synthetic_corrupt_membership_hash()
                RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
                NEW.content_hash := 'sha256:deliberately-corrupted'; RETURN NEW; END $$""")
            connection.execute("""CREATE TRIGGER synthetic_membership_hash_fault
                BEFORE INSERT ON dpm_composite_membership_revisions
                FOR EACH ROW EXECUTE FUNCTION synthetic_corrupt_membership_hash()""")
        next_key = key | {"membership_revision": "m3"}
        next_revision = DpmCompositeMembershipRevision(
            **next_key, **correction_body(), decided_by=HEADERS["X-Actor-Id"]
        )
        with pytest.raises(
            DpmCompositeConflictError, match="COMPOSITE_MEMBERSHIP_REVISION_IMMUTABLE_CONFLICT"
        ):
            repository.save_membership_revision(revision=next_revision)
        assert repository.get_membership_revision(**next_key) is None
        assert (
            len(
                repository.list_publications(
                    tenant_id=key["tenant_id"], after_sequence=0, limit=10
                ).items
            )
            == 2
        )
