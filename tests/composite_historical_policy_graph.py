"""Export controlled complete custody graphs through existing repository and registered reads."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.dependencies import get_composite_monthly_eligibility_service, get_composite_repository
from src.api.main import app
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
)
from src.core.common.canonical import hash_canonical_payload
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_contracts import check_contract_files
from tests.composite_historical_policy_helpers import (
    historical_approval_for,
    historical_contract_material,
)
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_monthly_eligibility_helpers import BASE, HEADERS


class ControlledPublicationClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 10, 5, tzinfo=timezone.utc).astimezone(tz)


def wire(model):
    return None if model is None else model.model_dump(mode="json")


def endpoint(client, method, path, body=None):
    response = client.request(method, path, headers=HEADERS, json=body)
    return dict(
        method=method,
        path=path,
        request=body,
        status=response.status_code,
        response=response.json(),
    )


def capture(repository, client, scope, proposal, parent, phase):
    approval = repository.get_monthly_evaluation_approval(
        **scope, evaluation_revision=proposal.evaluation_revision
    )
    binding = (
        None
        if approval is None
        else dict(
            product_name=approval.product_name,
            product_version=approval.product_version,
            revision=proposal.evaluation_revision,
            digest=approval.content_hash,
        )
    )
    target = repository.get_membership_revision(
        **scope, membership_revision=proposal.target_membership_revision
    )
    universe = None
    # The output attestation revision is producer-owned; derive it from the exact receipt.
    receipt = None
    if approval is not None:
        receipt = repository.resolve_monthly_eligibility_evidence(
            **scope,
            evaluation_revision=proposal.evaluation_revision,
            approval_content_hash=approval.content_hash,
        )
        universe = repository.get_universe_attestation(
            **scope,
            membership_revision=target.membership_revision,
            attestation_version=receipt.universe_binding.revision,
        )
        assert receipt.membership_binding.digest == target.content_hash
        assert receipt.universe_binding.digest == universe.content_hash
    evaluation_url = BASE + "/evaluations/" + proposal.evaluation_revision
    responses = [
        endpoint(client, "GET", evaluation_url),
        endpoint(client, "GET", evaluation_url + "/approval"),
    ]
    if binding is not None:
        resolved = endpoint(
            client,
            "POST",
            BASE.removesuffix("/monthly-eligibility") + "/eligibility-evidence/resolve",
            binding,
        )
        assert resolved["status"] == 200 and resolved["response"] == wire(receipt)
        responses.append(resolved)
    return dict(
        phase=phase,
        definition=wire(repository.get_definition(**scope)),
        policy_proposal=wire(proposal.policy_approval.proposal),
        policy_approval=wire(proposal.policy_approval),
        parent_membership=wire(parent),
        input_universe=wire(proposal.universe),
        evaluation_proposal=wire(proposal),
        evaluation_approval=wire(approval),
        published_membership=wire(target),
        published_universe=wire(universe),
        receipt=wire(receipt),
        publications=wire(
            repository.list_publications(tenant_id=scope["tenant_id"], after_sequence=0, limit=100)
        ),
        endpoint_responses=responses,
    )


def profile_graph(profile):
    port, policy, approved_policy, root, checked, _ = historical_contract_material(
        definition_product_version=profile
    )
    original = InMemoryDpmCompositeRepository()
    scope, _, _ = seed_complete_monthly_root(
        original,
        definition_product_version=profile,
        parent_decided_at="2026-08-01T00:00:00.000000Z",
    )
    repository = InMemoryDpmCompositeRepository()
    parent = original.get_membership_revision(
        **scope, membership_revision=root.parent_membership_revision
    )
    repository.save_definition(definition=original.get_definition(**scope))
    repository.save_membership_revision(revision=parent)
    repository.save_universe_attestation(attestation=root.universe)
    repository.save_monthly_policy_proposal(proposal=policy)
    repository.save_monthly_policy_approval(approval=approved_policy)
    prior_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_composite_repository] = lambda: repository
    app.dependency_overrides[get_composite_monthly_eligibility_service] = lambda: (
        CompositeMonthlyEligibilityApplicationService(repository)
    )
    stages = {}
    try:
        with TestClient(app) as client:
            repository.save_monthly_evaluation_proposal(proposal=root)
            stages["root-evaluated-only"] = capture(
                repository, client, scope, root, parent, "EVALUATED_ONLY"
            )
            repository.save_monthly_evaluation_approval(approval=checked)
            stages["root-published"] = capture(repository, client, scope, root, parent, "PUBLISHED")
            prior = repository.resolve_monthly_eligibility_evidence(
                **scope,
                evaluation_revision=root.evaluation_revision,
                approval_content_hash=checked.content_hash,
            )
            for revision, cash in ((2, "100"), (3, "50")):
                parent = repository.get_membership_revision(
                    **scope, membership_revision=prior.approval.proposal.target_membership_revision
                )
                proposal = corrected_monthly_proposal(
                    prior,
                    parent,
                    sequence=prior.publication_sequence,
                    historical_verifier=port,
                    revision=revision,
                    cash=cash,
                )
                repository.save_universe_attestation(attestation=proposal.universe)
                repository.save_monthly_evaluation_proposal(proposal=proposal)
                stages[f"correction-{revision}-evaluated-only"] = capture(
                    repository, client, scope, proposal, parent, "EVALUATED_ONLY"
                )
                approval = historical_approval_for(proposal, parent, port)[0]
                repository.save_monthly_evaluation_approval(approval=approval)
                stages[f"correction-{revision}-published"] = capture(
                    repository, client, scope, proposal, parent, "PUBLISHED"
                )
                prior = repository.resolve_monthly_eligibility_evidence(
                    **scope,
                    evaluation_revision=proposal.evaluation_revision,
                    approval_content_hash=approval.content_hash,
                )
        return stages
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(prior_overrides)


def graph_files():
    files = {}
    with patch("src.infrastructure.composites.in_memory.datetime", ControlledPublicationClock):
        for profile in ("v1", "v2"):
            for stage, value in profile_graph(profile).items():
                files[f"definition-{profile}.{stage}.json"] = value
    root = Path(__file__).resolve().parents[1]
    sources = [
        Path(__file__),
        root / "tests/composite_historical_policy_helpers.py",
        root / "tests/composite_monthly_amendment_helpers.py",
    ]
    sources.extend((root / "src/core/composite_eligibility").glob("*.py"))
    sources.extend((root / "src/infrastructure/composites").glob("*.py"))
    files["manifest.json"] = dict(
        posture="CONTROLLED_SYNTHETIC_GRAPH_UNCOMMITTED_DRAFT_NOT_RELEASE_QUALIFIED",
        production_adapter="UNAVAILABLE",
        consumer_enablement="NOT_ADMITTED",
        official_activation="UNAVAILABLE",
        baseline="9224d85664fb07e8074ef21681b88449d05193e8",
        provenance="python -m tests.composite_historical_policy_graph DIRECTORY; existing typed fixtures, real in-memory UOW and registered TestClient GET/resolver routes. Publication clock fixed only inside this generator at 2026-10-10T05:00:00Z; no production clock override or runtime proof.",
        source_file_encoding="UTF-8 source text with universal newline normalization to LF; source-code provenance only, not original artifact bytes",
        source_file_sha256_lf={
            str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(
                path.read_text(encoding="utf-8").encode("utf-8")
            ).hexdigest()
            for path in sorted(set(sources))
        },
        canonical_content_digests={
            name: hash_canonical_payload(value) for name, value in sorted(files.items())
        },
        raw_file_sha256={
            name: hashlib.sha256(
                (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            for name, value in sorted(files.items())
        },
    )
    return {
        name: json.dumps(value, indent=2, sort_keys=True) + "\n" for name, value in files.items()
    }


def main():
    logging.disable(logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = graph_files()
    if args.check:
        check_contract_files(args.directory, files)
    else:
        args.directory.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (args.directory / name).write_bytes(content.encode())
    print(f"{'Checked' if args.check else 'Generated'} {len(files)} controlled graph files")


if __name__ == "__main__":
    main()
