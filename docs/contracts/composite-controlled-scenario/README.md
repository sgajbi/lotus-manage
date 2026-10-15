# Controlled-scenario eligibility graph

This additive family declares a historical synthetic scenario at actual current issuance. It never
claims a signature physically existed at scenario approval. Defaults remain unavailable.
The preserved historical proof v1 continues to mean VERIFIED_AT_ORIGINAL_APPROVAL.

| Product | Version | Existing operation / location |
| --- | --- | --- |
| CompositeHistoricalPolicyVerificationRequest | v2 | Internal independent admission; purpose COMPOSITE_CONTROLLED_SCENARIO_POLICY_ADMISSION |
| CompositeHistoricalPolicyVerification | v2 | Policy verification and evaluation operation_verification |
| CompositeMonthlyPolicyProposal / Approval | v3 | Nested subject policy controls |
| CompositeSubjectPolicyProposal / Approval | v3 | policies/{revision}/historical-admission and /approval |
| CompositeSubjectEvaluationProposal / Approval | v3 | evaluations/{revision} and /approval |
| CompositeDefinition / CompositeSourceAuthority payload | v3 | Dedicated scenario definition and authority with only binding v3; old v2 remains strict |
| CompositeEligibilityFinalization / Receipt | v4 | finalization and published eligibility-evidence/resolve |
| CompositeSubjectEvaluationApproval binding | v3 | Dedicated eligibility_evaluation_binding; generic EvidenceBinding stays v1 |

All route paths are under the existing /api/v1/rebalance/composites scope. Bodies do not select
server time, member facts, key files or private trust. Current admitted maker/checker remain separate.

The mapping retains reference, raw_original_base64, original_credential, policy, policy version,
currency and attachments. It adds actual_issued_at and uses scenario_proposed_by/at and
scenario_approved_by/at, without original proposal/approval aliases. Proof status is exactly
VERIFIED_AT_ACTUAL_ISSUANCE, semantics SCENARIO_DECLARATION_AT_ACTUAL_ISSUANCE, and posture
SYNTHETIC_NON_CERTIFYING. Source-key validity covers actual issuance; scenario chronology is
separately ordered before the policy month. Current independent admission/revocation remain current.
Neither the source declaration nor the verifier asserts bank approval.

Content hashes canonicalize complete model serialization excluding only top-level content_hash.
Verifier signatures canonicalize complete proofs excluding only top-level content_hash and
verifier_credential. Evaluation proposal intent excludes only top-level content_hash and
operation_verification, retaining nested proofs/hashes/defaults. Approval intent equals the full
proposal content hash. Policy proposal intent binds {reference, proposal_revision}; policy approval
intent equals the monthly proposal hash. Outer subject-bound verifications remain required.

valid-graph.json is one complete normal in-process admission/publication/retained replay graph with
ephemeral independent test authors. No private key is exported. schemas.json contains the complete
receipt schema including nested definitions. manifest.json seals raw bytes, canonical JSON digests
and content hashes. Exact CompositeMembership.v1 and CompositeUniverseAttestation.v1 companion
products are extracted by the same source-owned native projection and match the receipt commitments.
Read them through existing GET definitions/{definition_version}/membership/{membership_revision}
and its /universe-attestations/{attestation_version} route under the composite scope.
refusal-vectors.json supplies pointer mutations which must refuse. This is
contract evidence, not deployed trust, institutional qualification or consumer admission.
The graph keeps official_activation UNAVAILABLE and completeness UNVERIFIED.

Run from a lotus-manage checkout with its declared Python environment (PowerShell or Bash):

```text
make test-unit UNIT_TESTS="tests/unit/dpm/composites/test_controlled_scenario_contracts.py tests/unit/dpm/infrastructure/test_historical_policy_verifier.py tests/unit/api/test_composite_historical_subject_routes.py"
```

Real PostgreSQL/native-process acceptance uses the existing owning integration modules and
requires DPM_POSTGRES_INTEGRATION_DSN with DPM_POSTGRES_INTEGRATION_REQUIRED=1. Offline
collection does not execute PostgreSQL. Migration0047 preserves every prior migration checksum,
retains old CHECK predicates, and adds only typed controlled-scenario STAGED branches.
