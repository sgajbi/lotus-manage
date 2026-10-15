# Historical first-subject engineering contract

Root approved the additive contract under Manage #778, coordinated with Performance #633.
This is controlled synthetic engineering history, not released support, bank identity or actual
historical approval. Historical first-subject PostgreSQL custody requires forward migration `0046`; no generic importer is introduced. Existing v1 staged controls,
v1 ordinary finalization and v2 institutional finalization retain their concrete wires and hashes.

## Version graph

| Product | Version | Fields and nested contracts |
| --- | --- | --- |
| CompositeSubjectPolicyProposal | v2 | subject (existing EligibilitySubject/v1), proposal (existing historical monthly policy proposal/v2), verification (existing CompositeEvidenceVerificationReceipt/v1), content_hash |
| CompositeSubjectPolicyApproval | v2 | proposal (subject policy proposal/v2), approval (existing historical monthly policy approval/v2), verification (existing receipt/v1), content_hash |
| CompositeSubjectEvaluationProposal | v2 | existing initial evaluation fields, policy_approval (subject policy approval/v2), operation_verification (existing HistoricalPolicyVerification/v1), content_hash |
| CompositeSubjectEvaluationApproval | v2 | existing approval fields, proposal (subject evaluation/v2), operation_verification (existing HistoricalPolicyVerification/v1), content_hash |
| CompositeEligibilityFinalization | v3 | existing finalization fields with evaluation_approval/v2 and existing synthetic verification receipts |
| CompositeEligibilityFinalizationReceipt | v3 | existing receipt fields with finalization/v3 |

Definition remains v2; membership, universe, subject and source assembly remain their current
versions. Only the definition's eligibility binding admits the dedicated
HistoricalSubjectApprovalBinding: product_name CompositeSubjectEvaluationApproval, product_version
v2, revision, digest. Generic EvidenceBinding remains v1. No historical/institutional mixed graph.
All new evidence is SYNTHETIC_NON_CERTIFYING, official activation UNAVAILABLE, publication
completeness UNVERIFIED; the declared synthetic universe may be structurally COMPLETE.

## Native command and immutable hashes

The new subject-scoped `PUT .../policies/{proposal_revision}/historical-admission` receives only
expected_subject_content_hash and the original HistoricalPolicyReference. Scope, actor, source,
trust and current time remain server owned. Existing independent approval/evaluation/finalization
commands select retained versions; callers do not select response versions.

Each graph content hash is SHA256 of canonical UTF-8 JSON (sorted keys, compact separators,
ensure_ascii=True), prefixed sha256:, excluding only its own top-level content_hash. All nested
hashes and proofs remain. Historical policy proposal/approval proofs use unchanged original
verification contracts. The outer policy proposal verification purpose is ELIGIBILITY_POLICY,
claims digest hashes {subject_content_hash, proposal_content_hash}. Outer approval verification
hashes {subject_content_hash, approval_content_hash}. Both require exact subject/month scope.

Evaluation operation_verification uses the existing historical purpose and original mapping.
EVALUATION_PROPOSAL intent hashes the complete serialized proposal excluding ONLY top-level
content_hash and operation_verification. EVALUATION_APPROVAL intent is the complete proposal's
content_hash. Each request signs current actor/revision/requested_at, original reference and exact
scope/month/currency/policy. Original policy approval predates its effective month; present
admission/checker timestamps are current. Original bytes/credential/timestamps are never rewritten.

Typed refusals retain existing historical admission/signature/trust/request/intent/mapping/window
codes and subject stale-content/immutable/self-approval/source/custody codes. New version mismatch
is COMPOSITE_SUBJECT_CONTROL_VERSION_MISMATCH; unsupported qualified historical first-subject
posture is COMPOSITE_SUBJECT_HISTORICAL_POLICY_POSTURE_UNAVAILABLE. Ordinary retrospective
proposal still refuses COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN.

## Contract vectors and qualification

Generated source-owned schemas, controlled examples and manifest will pin valid exact versions,
canonical digests and raw-file digests. Owning tests must reject changed nested hashes/proofs,
wrong subject/tenant/operation/intent, stale expected content and mixed v1/v2/v3 graphs. Retained
replay precedes fresh provider calls and preserves bytes even with providers unavailable.

Native proof starts empty: subject creation, verified original admission, independent approval,
configured-source evaluation, independent evaluation approval, atomic first finalization, exact
resolver and restart. Preseeding subject/policy/control history is not this proof. Unit/in-process
proof is distinct from Root-owned PostgreSQL/deployed source and Performance READY acceptance.
