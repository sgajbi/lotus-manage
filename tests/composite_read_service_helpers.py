"""Controlled enrollment and real-HTTP read/mutation boundary for published months."""

import json

READ_GRANTS = json.dumps(
    [
        {
            "service_identity": "synthetic-report-read-service",
            "actor_id": "synthetic-report-read-actor",
            "tenant_id": "synthetic-tenant",
        }
    ]
)
READ_HEADERS = {
    "X-Service-Identity": "synthetic-report-read-service",
    "X-Actor-Id": "synthetic-report-read-actor",
    "X-Tenant-Id": "synthetic-tenant",
    "X-Role": "REPORT_COMPOSITE_READER",
    "X-Capabilities": "manage.read",
    "X-Correlation-Id": "synthetic-report-read-proof",
}


def assert_evaluated_read_service(client, url, proposal):
    response = client.get(url, headers=READ_HEADERS)
    assert response.status_code == 200, response.text
    assert response.json() == proposal
    for name in READ_HEADERS:
        for value in (None, "foreign-value"):
            if name == "X-Correlation-Id" and value is not None:
                continue  # Correlation is required tracing, not an enrolled authority claim.
            headers = dict(READ_HEADERS)
            if value is None:
                del headers[name]
            else:
                headers[name] = value
            denied = client.get(url, headers=headers)
            assert denied.status_code == 403, (name, denied.text)
    for method, path in (("PUT", url), ("GET", url + "/approval"), ("GET", url + "/extra")):
        refused = client.request(method, path, headers=READ_HEADERS, json={})
        assert refused.status_code == 403, refused.text


def read_operations(receipt):
    proposal = receipt["approval"]["proposal"]
    root = "/api/v1/rebalance/composites/" + proposal["evaluation"]["composite_id"]
    root += "/definitions/" + proposal["evaluation"]["definition_version"]
    membership = root + "/membership/" + proposal["target_membership_revision"]
    binding = {
        "product_name": "CompositeMonthlyEvaluationApproval",
        "product_version": "v1",
        "revision": proposal["evaluation_revision"],
        "digest": receipt["approval"]["content_hash"],
    }
    return [
        ("membership", "GET", membership, None),
        (
            "universe",
            "GET",
            membership + "/universe-attestations/" + proposal["evaluation_revision"],
            None,
        ),
        ("receipt", "POST", root + "/eligibility-evidence/resolve", binding),
        (
            "parent_membership",
            "GET",
            root + "/membership/" + proposal["parent_membership_revision"],
            None,
        ),
        (
            "publication",
            "GET",
            "/api/v1/rebalance/composites/publications/" + str(receipt["publication_sequence"]),
            None,
        ),
    ]


def assert_read_service_capture(client, receipt, captured):
    """HTTP grant controls; real Report client composition is separately joined proof."""
    responses = {}
    for meaning, method, path, body in read_operations(receipt):
        response = client.request(method, path, headers=READ_HEADERS, json=body)
        assert response.status_code == 200, response.text
        responses[meaning] = response.json()
    assert responses["receipt"] == receipt
    assert responses["membership"] == captured["canonical_membership"]
    assert responses["universe"] == captured["canonical_universe"]
    assert (
        responses["parent_membership"]["content_hash"]
        == receipt["approval"]["proposal"]["parent_membership_content_hash"]
    )
    assert (
        responses["publication"]["membership_content_hash"]
        == responses["membership"]["content_hash"]
    )
    assert responses["publication"]["sequence"] == receipt["publication_sequence"]
    before = client.get(
        "/api/v1/rebalance/composites/publications", headers=captured["writer_headers"]
    ).json()
    for name in ("X-Service-Identity", "X-Actor-Id", "X-Tenant-Id", "X-Role", "X-Capabilities"):
        for value in (None, "foreign-value"):
            headers = dict(READ_HEADERS)
            if value is None:
                del headers[name]
            else:
                headers[name] = value
            for meaning, method, path, body in read_operations(receipt):
                refused = client.request(method, path, headers=headers, json=body)
                assert refused.status_code == 403, (name, value, meaning, refused.text)
    root = read_operations(receipt)[2][2].removesuffix("/eligibility-evidence/resolve")
    for method, path in (
        ("PUT", root),
        ("PUT", root + "/membership/forbidden"),
        ("PUT", root + "/monthly-eligibility/policies/forbidden"),
        ("PUT", root + "/monthly-eligibility/policies/forbidden/approval"),
        ("PUT", root + "/monthly-eligibility/evaluations/forbidden"),
        ("PUT", root + "/monthly-eligibility/evaluations/forbidden/approval"),
        ("POST", "/api/v1/rebalance/simulate"),
    ):
        denied = client.request(method, path, headers=READ_HEADERS, json={})
        assert denied.status_code == 403, denied.text
    after = client.get(
        "/api/v1/rebalance/composites/publications", headers=captured["writer_headers"]
    ).json()
    assert before == after
    return responses
