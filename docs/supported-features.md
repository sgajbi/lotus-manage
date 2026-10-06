# Lotus Manage Supported Features

This file tracks implementation-backed and supported `lotus-manage` capabilities. Unsupported claims are
explicitly excluded.

## Supported

- Deterministic rebalance simulation and what-if alternatives.
- Asynchronous operations with supportability and lineage artifacts.
- Policy-pack and mandate context read/build surfaces.
- Construction alternative generation/selection for supported methods.
- Wave lifecycle preview/create/read/list item/simulate/approve flows.
- Portfolio-memory persistence search and bounded retrieval.
- Monitoring, exceptions, and command-center read/write for managed domains.
- PM operating quality policy, score-run, fairness-analysis, review-action, summary-invocation,
  and PM-quality-backed portfolio-memory reads with trusted-identity tenant isolation. PM-quality
  trust telemetry remains certification-blocked until linked certification evidence is merged to
  `main` and runtime trust evidence is regenerated.

## Explicitly unsupported in `lotus-manage`

- Composite v2 provider registration, institutional-attestation verification and official activation
  are unavailable by default. Typed authority schemas, immutable version decoding and controlled
  producer tests are implemented, not live cross-repository certification. See the
  [source-authority guide](guides/composite-source-authority.md).

- The `lotus-idea` management-review realization is not yet a supported feature. It durably creates
  scoped `PENDING_REVIEW` actions and records append-only, version-fenced Manage review outcomes.
  Production IdP claim binding and live consumer certification remain outstanding. A review
  `APPROVED` outcome does not prove rebalance or order execution, suitability, OMS state, or client
  publication.
- OMS execution instructions, best execution claims, and settlement lifecycle.
- Client-ready communication, consent collection, or messaging.
- External treasury advisory, order routing, or execution confirmation.
- Final trade approval or portfolio-CRM decisioning.

## Promotion requirements

- New features remain unsupported until:
  - source-code implementation is complete,
  - API contracts are validated,
  - governance gates pass, and
  - owning RFC/release evidence is present.
