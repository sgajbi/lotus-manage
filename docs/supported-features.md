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

## Explicitly unsupported in `lotus-manage`

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
