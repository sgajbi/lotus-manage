"""Controlled consumer graphs retain actual products for every referenced authority edge."""

import pytest

from tests.composite_historical_policy_graph import profile_graph


@pytest.mark.parametrize("profile", ["v1", "v2"])
def test_graph_has_exact_pending_and_published_products_for_every_successor(profile):
    stages = profile_graph(profile)
    prior = None
    for name in ("root", "correction-2", "correction-3"):
        pending = stages[name + "-evaluated-only"]
        published = stages[name + "-published"]
        assert pending["definition"]["product_version"] == profile
        assert pending["evaluation_approval"] is None
        assert pending["published_membership"] is None
        assert pending["published_universe"] is None
        assert pending["receipt"] is None
        assert pending["endpoint_responses"][1]["status"] == 404
        assert published["evaluation_proposal"] == pending["evaluation_proposal"]
        receipt = published["receipt"]
        assert (
            receipt["membership_binding"]["digest"]
            == published["published_membership"]["content_hash"]
        )
        assert (
            receipt["universe_binding"]["digest"] == published["published_universe"]["content_hash"]
        )
        publication = next(
            item
            for item in published["publications"]["items"]
            if item["sequence"] == receipt["publication_sequence"]
        )
        assert (
            publication["membership_content_hash"]
            == published["published_membership"]["content_hash"]
        )
        assert published["endpoint_responses"][-1]["response"] == receipt
        if prior is not None:
            assert published["parent_membership"] == prior["published_membership"]
            lineage = receipt["lineage"]
            assert (
                lineage["predecessor_approval_binding"]["digest"]
                == prior["evaluation_approval"]["content_hash"]
            )
            assert (
                lineage["predecessor_receipt_binding"]["digest"] == prior["receipt"]["content_hash"]
            )
        prior = published
