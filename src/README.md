# Manage Source Layout

`src/` contains implementation code only. Keep domain logic, HTTP boundaries, application wiring,
and infrastructure adapters separated so feature work does not leak ownership across layers.

| Folder | Responsibility |
| --- | --- |
| `api/` | FastAPI app, routers, schemas, and HTTP error mapping. |
| `app/` | Application configuration, startup wiring, and service assembly. |
| `core/` | Domain models, policies, calculations, source contracts, and use-case services. |
| `infrastructure/` | Persistence, external source adapters, and runtime integration support. |

Layering rule: domain behavior belongs in `core/`; HTTP request/response shape belongs in `api/`;
adapter-specific I/O belongs in `infrastructure/`; composition belongs in `app/`. If a change
touches a boundary, update OpenAPI/API vocabulary, contract docs, and tests in the same slice.

Use this boundary map when refactoring:

```text
External Consumer
  -> API / Controller / Route
  -> Request DTO Mapper
  -> Application Use Case
  -> Domain Model + Domain Service
  -> Port / Interface
  -> Infrastructure Adapter
  -> Database / Cache / Queue / External API
```

Do not skip layers by putting infrastructure calls in route handlers or HTTP concerns in domain
services. Keep DTO translation at the edge and keep ports/interfaces as the dependency boundary
between domain/application logic and infrastructure adapters.

Useful checks:

```powershell
make typecheck
make openapi-gate
make api-vocabulary-gate
make service-boundary-gate
```
