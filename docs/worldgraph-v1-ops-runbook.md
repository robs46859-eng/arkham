# Worldgraph v1 Ops Runbook

This runbook covers deployment readiness and first smoke for Worldgraph v1 on `arkham-492414`.

Scope is intentionally limited to v1 behavior:
- `travel` namespace only
- OpenFlights ingest only
- canonical airports/airlines/routes
- search/get-by-id APIs
- Redis worker for ingest/reindex pipeline

---

## 1. DB Migration

### Apply migration

```bash
cd /Users/joeiton/Arkham
alembic upgrade head
```

### Expected revision

Worldgraph migration revision id is:
- `20260423_0009` (file: `alembic/versions/20260423_0008_worldgraph_schema.py`)

Current full repo head (including workflow approval migration) is:
- `20260423_0010` (head)

Verify:

```bash
cd /Users/joeiton/Arkham
python3 -m alembic current
python3 -m alembic heads
```

After `python3 -m alembic upgrade head`, `alembic current` should include `20260423_0010`.

### Rollback note (if worldgraph migration fails)

If failure occurs during Worldgraph DDL:
1. capture error output
2. fix the migration/root cause
3. rerun `alembic upgrade head`

If you must roll back the worldgraph revision:

```bash
cd /Users/joeiton/Arkham
alembic downgrade 20260421_0007
```

Use downgrade only in non-production or controlled rollback windows.

---

## 2. Bucket + IAM

### Required bucket

- `arkham-worldgraph-raw` (or the value of `RAW_BUCKET_NAME`)

### Service account used by `arkham-worldgraph`

Identify runtime SA:

```bash
gcloud run services describe arkham-worldgraph \
  --region=us-central1 \
  --project=arkham-492414 \
  --format="value(spec.template.spec.serviceAccountName)"
```

### Required IAM permissions

Grant to the runtime service account:

- Raw bucket write:
  - `roles/storage.objectCreator` (minimum for create-only)
  - if overwrite/list/read needed later: `roles/storage.objectAdmin` or add targeted read roles
- Raw bucket read (if manifests are read back):
  - `roles/storage.objectViewer`
- Secret Manager access:
  - `roles/secretmanager.secretAccessor` for DB/Redis secrets
- Cloud SQL connection (if using Cloud SQL):
  - `roles/cloudsql.client`

### Auth model in Cloud Run

- Expected auth is **ADC (Application Default Credentials)** via attached Cloud Run service account.
- No explicit JSON key file should be mounted in Cloud Run for this service.

---

## 3. Cloud Run Deploy Contract

### Required env vars

- `APP_ENV=production`
- `CORE_SERVICE_URL=<core service URL>`
- `RAW_BUCKET_NAME=<raw bucket name>`
- `REDIS_QUEUE_KEY=worldgraph:jobs`
- `OPENFLIGHTS_SOURCE_MODE=<fixture|http|gcs>`
- `OPENFLIGHTS_FETCH_TIMEOUT_SECONDS=<seconds>`
- `OPENFLIGHTS_FIXTURE_DIR=<fixture directory>` (required when `OPENFLIGHTS_SOURCE_MODE=fixture`)
- `OPENFLIGHTS_GCS_PREFIX=<gs://bucket/prefix>` (required when `OPENFLIGHTS_SOURCE_MODE=gcs`)

### Required secrets

- `DATABASE_URL` (Secret Manager)
- `REDIS_URL` (Secret Manager)

### Health expectations

- `GET /health` -> `200` and status `ok`
- `GET /healthz` -> `200` and status `ok`
- `GET /readyz` -> `200` and:
  - `dependencies.database.ok=true`
  - `dependencies.redis.ok=true`

### Connectivity expectations

- Core unavailable must not block health endpoints.
- Event publish failures to Core must not fail ingest completion.
- Redis unavailability should fail worker processing and surface in logs.

---

## 4. First Ingest Smoke Sequence

### Canonical staging smoke source contract

- **Required default for staging smoke:** `OPENFLIGHTS_SOURCE_MODE=fixture`
- **Why:** deterministic smoke behavior independent of transient internet egress and upstream source volatility.
- **Higher-fidelity option:** `OPENFLIGHTS_SOURCE_MODE=http` (recommended for production validation only; non-deterministic in smoke).
- **Internalized high-fidelity option:** `OPENFLIGHTS_SOURCE_MODE=gcs` with versioned snapshots in GCS.

### A. Deploy API service

```bash
cd /Users/joeiton/Arkham
gcloud builds submit --config cloudbuild.worldgraph.yaml --project=arkham-492414
```

### B. Start worker process

Run worker in a separate runtime (recommended: separate Cloud Run service/job using same image), command:

```bash
python -m app.workers.normalize_worker
```

If running locally:
- ensure `DATABASE_URL`, `REDIS_URL`, `RAW_BUCKET_NAME`, `CORE_SERVICE_URL` are set
- ensure ADC can write to bucket
- for deterministic smoke, set:
  - `OPENFLIGHTS_SOURCE_MODE=fixture`
  - `OPENFLIGHTS_FIXTURE_DIR=/app/services/worldgraph/app/fixtures/openflights`

### C. Trigger ingest

Through gateway:

```bash
curl -X POST "https://robco-gateway-zth4qhgsda-uc.a.run.app/v1/worldgraph/travel/ingest/jobs" \
  -H "Authorization: Bearer <admin_token_or_valid_auth_path>" \
  -H "Content-Type: application/json" \
  -d '{"source_name":"openflights"}'
```

Or direct to worldgraph service:

```bash
curl -X POST "https://arkham-worldgraph-<hash>-uc.a.run.app/v1/worldgraph/travel/ingest/jobs" \
  -H "Content-Type: application/json" \
  -d '{"source_name":"openflights"}'
```

### D. Confirm ingest job row

```sql
select job_id, namespace, source_name, status, manifest_uri, started_at, finished_at
from worldgraph.wg_ingest_jobs
order by started_at desc
limit 5;
```

Expected: status transitions `pending -> running -> complete`.

### E. Confirm canonical entities

```sql
select entity_type, count(*)
from worldgraph.wg_entities
where namespace = 'travel'
group by entity_type
order by entity_type;
```

Expected: non-zero rows for `airport`, `airline`, `route`.

### F. Confirm search docs were reindexed

```sql
select count(*) as search_docs
from worldgraph.wg_search_documents;
```

Expected: count > 0 and roughly aligned with travel entity count.

### G. Confirm search endpoint returns seeded entities

```bash
curl "https://robco-gateway-zth4qhgsda-uc.a.run.app/v1/worldgraph/travel/search?q=delta&limit=10" \
  -H "Authorization: Bearer <tenant_token>"
```

Expected: array includes matching airlines/routes/airports.

### H. Confirm Core event publish failures do not block ingest

If Core is intentionally unreachable:
- ingest job should still complete
- logs may show event publish warnings
- canonical and search rows should still be present

---

## 5. Known v1 Behavior

- OpenFlights ingest is treated as **trusted Layer 2 seed**.
- Proposal pipeline is **not** the promotion control path for OpenFlights seeding.
- Collision/ambiguous identifier situations create review proposals.
- No admin UI in v1.
- No property namespace in v1.
- No OSM/Wikidata/GeoNames in v1.

---

## 6. Failure Checks

### Missing bucket permissions

Symptoms:
- ingest job fails
- worker logs show GCS permission denied

Check:
- runtime SA on `arkham-worldgraph`
- bucket IAM for object create/read

### Worker memory too small for live OpenFlights snapshot

Symptoms:
- worker logs show OOM kill or restart during ingest
- job remains `running`/`failed` after fetch

Check:
- Cloud Run worker memory limit
- full live OpenFlights mode (`OPENFLIGHTS_SOURCE_MODE=http`) uses larger in-memory payload

Recommendation:
- keep staging smoke on `fixture`
- size production worker memory for live source ingest (>= `2Gi` currently configured)

### Optional outbound diagnostic probe

- Retained script for future debugging: `services/worldgraph/app/scripts/openflights_netcheck.py`
- This script can be run in a one-off runtime to classify DNS/TCP/HTTPS/fetch failures without changing standing service topology.

---

## 7. Auxiliary Job Classification

Primary v1 staging operating path remains:
- services: `arkham-worldgraph`, `arkham-worldgraph-worker`
- jobs: `arkham-worldgraph-trigger`, `arkham-worldgraph-verify`

Remaining worldgraph jobs are classified as follows:

- `arkham-worldgraph-migrate`
  - **Classification:** still required (operational support)
  - **Why:** bootstrap/repair schema path in the exact Cloud Run runtime/secret/network context.
  - **Removal status:** not safe to remove yet.

- `arkham-worldgraph-dbcheck`
  - **Classification:** legacy-or-auxiliary
  - **Why:** useful on-demand DB/revision/table verification probe during incidents.
  - **Removal status:** safe to remove later once equivalent documented manual SQL/health checks are standardized in ops workflow.

- `arkham-worldgraph-smoke-trigger`
  - **Classification:** superseded (removed)
  - **Why:** older ad hoc trigger path; canonical trigger is `arkham-worldgraph-trigger` with current image/env contract.
  - **Removal status:** removed from staging to reduce ops surface.

### Missing Redis secret / bad Redis URL

Symptoms:
- worker cannot pop jobs
- `/readyz` shows `redis.ok=false`

Check:
- secret binding for `REDIS_URL`
- network path from service to Redis

### Migration not applied

Symptoms:
- runtime errors for missing `worldgraph.*` tables

Check:
- `alembic current`
- table existence under `worldgraph` schema

### Core unreachable

Symptoms:
- event publish warnings in logs

Expected:
- ingest and reindex still complete

### Duplicate ingest replay

Expected v1:
- raw ingest uses idempotency keys (`namespace/source/source_primary_key/payload_hash`)
- replay should not multiply identical raw rows
- identifier collisions should generate pending review proposals, not ownership mutation

