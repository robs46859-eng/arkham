# Gateway OpenAPI

The canonical generated gateway spec lives at [gateway.openapi.json](/Users/robert/arkham/docs/openapi/gateway.openapi.json).
The human-friendly static docs page lives at [index.html](/Users/robert/arkham/docs/openapi/index.html).

## What It Covers

- Gateway health and readiness endpoints
- Bearer token issuance via `POST /v1/auth/token`
- Protected inference via `POST /v1/infer`
- Tenant and tenant API key management endpoints
- Workflow start and workflow status endpoints

## Auth Model

- Call `POST /v1/auth/token` with a tenant-scoped API key.
- Use the returned JWT as `Authorization: Bearer <token>` on protected endpoints.
- The generated spec documents bearer auth via the `HTTPBearer` security scheme.

## Regenerate

Run:

```bash
cd /Users/robert/arkham
make openapi-export
```

The exporter injects safe placeholder environment values so schema generation works without staging secrets.

## Preview Locally

Run:

```bash
cd /Users/robert/arkham
make openapi-serve
```

Then open `http://127.0.0.1:8080` in a browser.

## Notes

- This is a generated artifact. Prefer improving endpoint metadata and shared schemas in source code rather than editing the JSON by hand.
- Some gateway endpoints still reflect scaffolded runtime behavior; the OpenAPI is ready for internal integration and SDK generation, but endpoint behavior should stay aligned as implementation fills in.
