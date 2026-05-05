# RFC-0042 Slice 2 - Cleanup and Structure

| Field | Value |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | Slice 2 - Cleanup and Structure |
| **Implementation Branch** | `feat/rfc0042-implementation` |
| **Date** | 2026-05-05 |
| **Status** | DONE |

---

## Review Scope

Slice 2 reviewed the existing `lotus-manage` post-trade, wave, proof-pack, construction, supportability,
documentation, and wiki surfaces before runtime RFC-0042 implementation begins.

The review searched for premature outcome-feedback implementation, dead or duplicated outcome-adjacent
code, unsupported supported-feature claims, and structural pressure points that should shape the
implementation.

## Findings

1. No runtime `outcomes` authority exists yet in `src/`; RFC-0042 implementation can introduce a
   clean module boundary instead of extending the already-large wave router or cloning logic from
   proof packs, construction, risk, performance, or core.
2. Existing wave, proof-pack, construction, repository, and dependency modules are active and should
   be reused through explicit services and repositories rather than copied.
3. `wiki/Supported-Features.md` contained one premature phrase that implied outcome events were
   already part of supported decision-timeline memory. That phrase was tightened so outcome events
   remain proposed until RFC-0042 implementation, proof, Gateway/Workbench realization where
   surfaced, wiki publication, and supported-feature promotion are complete.
4. Long-lived product posture remains in the wiki; detailed implementation evidence remains in RFC
   evidence documents. No additional doc sprawl was added outside the RFC evidence trail.

## Cleanup Completed

1. Corrected the supported-feature boundary for decision timeline and portfolio memory.
2. Added documentation regression coverage so RFC-0042 cannot accidentally promote outcome support
   before source-backed implementation and proof.
3. Recorded the structure decision for the runtime implementation: use a dedicated outcome domain,
   service, repository, API router, and source-adapter boundary rather than adding outcome behavior
   to the existing wave router.

## Runtime Structure Direction

RFC-0042 runtime implementation should use these module boundaries:

| Concern | Target Boundary |
| --- | --- |
| Domain model and deterministic comparison | `src/core/outcomes/` |
| Source snapshot and supportability adapters | `src/api/services/` and source-specific infrastructure modules |
| Persistence | `src/infrastructure/outcomes/` |
| API presentation and OpenAPI examples | `src/api/routers/outcomes.py` |
| Report and AI evidence inputs | dedicated outcome handoff builders, not report/AI-local clones |
| Observability | existing `src/api/observability.py` patterns extended with outcome counters/histograms |

This structure keeps RFC-0042 independent from monolithic wave endpoint growth and prevents
manage-local clones of source-owner methodology.

## Validation

Validation command:

```powershell
python -m pytest tests\unit\test_documentation_current_state.py -q
git diff --check
```

Expected result: documentation current-state tests pass and the diff has no whitespace errors.

## Supported-Feature Decision

No supported feature is promoted by Slice 2. Post-trade outcome feedback remains proposed until the
runtime implementation, source-backed proof, API certification, wiki publication, and
supported-feature promotion are complete.
