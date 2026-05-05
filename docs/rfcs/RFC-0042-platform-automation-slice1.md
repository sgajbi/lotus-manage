# RFC-0042 Slice 1 - Platform Automation and Scaffolding Improvement

| Metadata | Details |
| --- | --- |
| **RFC** | RFC-0042 Post-Trade Outcome Feedback Loop |
| **Slice** | Slice 1 - Platform Automation and Scaffolding Improvement |
| **Status** | DONE - PLATFORM SCAFFOLD IMPROVEMENT MERGED |
| **Manage Branch** | `feat/rfc0042-implementation` |
| **Platform Branch** | `feat/rfc0042-platform-scaffold-api-certification` |
| **Platform PR** | `sgajbi/lotus-platform#297`, merged |
| **Platform Commit** | `1b9671e automation: scaffold source-degraded API certification guidance` |

---

## Slice Objective

RFC-0042 introduces expected-versus-realized and source-degraded reconciliation APIs. That pattern
is cross-cutting across Lotus services and should not be rediscovered locally in every app.

Slice 1 reviewed whether platform scaffolding already gives new backend services enough guidance
for:

1. API certification pattern,
2. Swagger/OpenAPI quality,
3. source-owner and lineage posture,
4. structured degraded-state examples,
5. tests for missing, stale, unavailable, partial, malformed, and conflicting upstream evidence,
6. documentation and supported-feature promotion rules.

---

## Finding

`lotus-platform` backend scaffolding already includes strong baseline coverage for health,
readiness, metrics, structured logging, product-safe errors, OpenAPI gate, CI lanes, no-sensitive
content guard, supported-features gate, and an API certification operations page.

The gap was narrower but real: the generated `docs/operations/api-certification.md` did not
explicitly seed source-degraded and reconciliation endpoint expectations. RFC-0042 outcome review
APIs depend on that pattern, and future Lotus apps that reconcile source-owned evidence should
start with the same rule.

---

## Platform Change

`lotus-platform` PR `#297` updates `automation/New-Lotus-Service.ps1` so newly scaffolded backend
services include a source-degraded and reconciliation endpoint section in generated API
certification guidance.

The scaffold now tells new services to include:

1. explicit source-owner fields in success and degraded responses,
2. source freshness, lineage, and supportability fields where exposed by the source owner,
3. `READY`, `DEGRADED`, `BLOCKED`, and `NOT_SUPPORTED` examples where applicable,
4. tests for missing, stale, unavailable, partial, malformed, and conflicting upstream evidence,
5. proof that the service does not clone calculations owned by another Lotus app,
6. README, wiki, supported-feature, and RFC evidence updates before any product support claim.

The platform test `tests/unit/test_repository_hygiene_scaffold_contract.py` now pins the generated
guidance so future scaffold changes do not regress it.

---

## Validation

Platform validation run locally:

```powershell
python -m pytest tests\unit\test_repository_hygiene_scaffold_contract.py -q
```

Result:

`2 passed`

Additional local check:

```powershell
git diff --check
```

Result:

`passed`

GitHub CI:

1. `lotus-platform` PR `#297` Pull Request Merge Gate: passed.
2. `lotus-platform` PR `#297` API Vocabulary Governance: passed.

Merge evidence:

`lotus-platform` PR `#297` merged as `1b9671e`.

---

## Manage Boundary Decision

No manage runtime code is added in Slice 1.

The platform change benefits RFC-0042 and future Lotus services. `lotus-manage` still owns the
RFC-0042 outcome-review implementation, but the repeatable source-degraded API certification
expectation now lives in platform scaffolding rather than in RFC-0042 local prose alone.

No supported feature is promoted by this slice.

Slice 1 closure:

`DONE`. The platform-scaffold gap was fixed in the owning platform app and validated before the
RFC-0042 manage implementation moved to Slice 2.
