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

Useful checks:

```powershell
make typecheck
make openapi-gate
make api-vocabulary-gate
make service-boundary-gate
```

