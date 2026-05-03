# lotus-manage wiki

`lotus-manage` is the discretionary mandate portfolio-management execution and operational
supportability service in Lotus.

## Start here

- Repo entrypoint: [README.md](../README.md)
- Repo context: [REPOSITORY-ENGINEERING-CONTEXT.md](../REPOSITORY-ENGINEERING-CONTEXT.md)
- Project overview: [docs/documentation/project-overview.md](../docs/documentation/project-overview.md)
- Upstream contract map:
  [docs/standards/RFC-0082-upstream-contract-family-map.md](../docs/standards/RFC-0082-upstream-contract-family-map.md)

## Repo role

This repo owns:

- deterministic rebalance simulation and what-if analysis
- management-side async execution and supportability workflows
- run artifacts, lineage, idempotency, and policy-pack supportability
- management capability publication for gateway and platform consumers

Strategic target-state RFCs now define the proposed revamp into a DPM operating system covering
mandate digital twins, health scoring, command-center workflows, advanced construction alternatives,
proof packs, rebalance waves, outcome feedback, and governed AI PM support. See
[Roadmap](Roadmap) for the business-facing plan and [Supported Features](Supported-Features) for
the separation between implementation-backed support and proposed target-state features.

This repo does not own:

- advisor-led proposal workflows
- canonical portfolio ledger and source-data authority
- risk methodology or performance analytics authority
- UI experience composition

## Navigation

- [Overview](Overview)
- [Architecture](Architecture)
- [API Surface](API-Surface)
- [Endpoint Certification](Endpoint-Certification)
- [Supported Features](Supported-Features)
- [Getting Started](Getting-Started)
- [Development Workflow](Development-Workflow)
- [Validation and CI](Validation-and-CI)
- [Operations Runbook](Operations-Runbook)
- [Integrations](Integrations)
- [Security and Governance](Security-and-Governance)
- [RFC Index](RFC-Index)
- [Roadmap](Roadmap)
- [Troubleshooting](Troubleshooting)
