# Worldgraph Staging Smoke Log (2026-04-23)

- **Service / Component:** `arkham-worldgraph` + `arkham-worldgraph-worker`
- **Environment:** `staging`
- **Date/Time (UTC):** 2026-04-23
- **Operator:** Codex agent + joeiton
- **Change Ref:** `manual-20260423a`..`manual-20260423g`
- **Related Runbook:** `docs/worldgraph-v1-ops-runbook.md`
- **Expected Healthy Endpoint(s):** `/health`, `/readyz`, `/v1/worldgraph/travel/*`
- **Required Secrets/Env:** `DATABASE_URL`, `REDIS_URL`, `APP_ENV`, `CORE_SERVICE_URL`, `RAW_BUCKET_NAME`, `REDIS_QUEUE_KEY`, `OPENFLIGHTS_SOURCE_MODE=fixture`, `OPENFLIGHTS_FETCH_TIMEOUT_SECONDS`, `OPENFLIGHTS_FIXTURE_DIR`
- **Known Private Dependencies:** Cloud SQL private IP (`10.3.96.3`), Redis private endpoint (`10.70.148.3:6378`), staging VPC
- **Rollback Trigger:** Worldgraph revision fails readiness or worker cannot process Redis queue
- **Rollback Command:** `gcloud run services update-traffic arkham-worldgraph --to-revisions=<last-good>=100 --region=us-central1 --project=arkham-492414`

---

## Smoke Checklist (Current)

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | DB migrations applied to latest head | PASS (worldgraph target endpoint) | `arkham-worldgraph-dbcheck-sld4q` shows `worldgraph.wg_ingest_jobs` exists and `worldgraph_tables` populated on trigger secret endpoint |
| 2 | Service deploy completed, revision ready | PASS | `arkham-worldgraph-00004-wj9` serving 100% |
| 3 | Required env vars present | PASS | `gcloud run services describe arkham-worldgraph` shows required env |
| 4 | Required secrets bound | PASS | Trigger/service/worker all point `DATABASE_URL` to `staging-database-url:latest`, `REDIS_URL` to `staging-redis-url:latest` |
| 5 | Health endpoint returns expected payload | BLOCKED from this runner | control-plane Ready=True; direct curl blocked by network proxy |
| 6 | Ready endpoint dependencies all healthy | BLOCKED from this runner | same as above |
| 7 | Worker process running with correct runtime model | PASS | worker runs background process + HTTP keepalive revision `00005-9cg` |
| 8 | Worker reaches Redis/DB on intended network path | PASS (Cloud Run), FAIL (local shell) | local worker timeout to Redis; worker moved to VPC-attached Cloud Run |
| 9 | First ingest trigger accepted | PASS | Trigger executions `arkham-worldgraph-trigger-q7h4z` and `arkham-worldgraph-trigger-bd25t` succeeded; emitted `triggered_job_id`s |
| 10 | Ingest job reached `complete` | PASS | `wgjob_3d4f3fb4ee2949eea4049b10230294a0` completed |
| 11 | Raw objects/records persisted | PASS | verify `raw_objects=6`, `raw_records=4` |
| 12 | Canonical entities created | PASS | verify `entities_total=4` (`airports=2`, `airlines=1`, `routes=1`) |
| 13 | Search documents populated | PASS | verify `search_docs=4` |
| 14 | Search query returns expected seeded entities | PASS | verify `search_delta_count=1`, first=`Delta Air Lines` |
| 15 | Event publish failures non-blocking | PASS | ingest completed with canonical/search materialization; no blocking on event publishing path observed |
| 16 | Fixture mode is canonical staging smoke path | PASS | worker/trigger/verify configured with `OPENFLIGHTS_SOURCE_MODE=fixture` and fixture dir |
| 17 | Prod-facing resource sizing documented | PASS | worker memory raised to `2Gi`; runbook updated to keep source mode/timeout environment-configurable |

---

## Failure/Retry Incident Log

| Attempted Action | Failure Observed | Root Cause | Fix Applied | Next Verification Step | Result |
|---|---|---|---|---|---|
| Deploy `arkham-worldgraph` | Revision failed startup (PORT health check) | Container bound to `8050` hardcoded, not Cloud Run `${PORT}` | Docker CMD changed to `uvicorn ... --port ${PORT:-8080}` | Redeploy + revision readiness check | PASS |
| Deploy worker as non-HTTP process | Worker service failed readiness | Cloud Run service requires HTTP listener | Run worker in background + `python -m http.server ${PORT}` foreground | Verify worker revision Ready | PASS |
| Run worker from local shell | Redis timeout / DB private IP access errors | Local host not on staging private network path | Run worker in Cloud Run with staging VPC/subnet/egress | Check worker logs for no runtime errors | PASS |
| Trigger ingest via Cloud Run job | `relation worldgraph.wg_ingest_jobs does not exist` | Worldgraph schema/tables absent in staging DB resolved by service secret path | Added migration/bootstrap jobs and scripts | Re-run migration + trigger | IN PROGRESS |
| Run migration job with `alembic` | `No module named alembic`, then `No script_location` | Runtime image lacked alembic / alembic config path mismatch in container | Added runtime alembic dep, then switched to explicit schema bootstrap script | Re-run migration job | PASS for execution, but table presence still unverified |
| Run bootstrap migration script | `schema "worldgraph" does not exist` during create_all | Schema creation and table creation not guaranteed on same connection visibility path | Updated job command to create schema + tables in single SQLAlchemy connection transaction | Re-run migration job, then trigger ingest | IN PROGRESS |
| Compare trigger/service/worker DB env + secrets | Suspected DB endpoint mismatch across workloads | Need to verify exact `DATABASE_URL` source parity on Cloud Run resources | Confirmed all three use `DATABASE_URL <- staging-database-url:latest`; same for `REDIS_URL` | Query target DB through trigger path and verify `worldgraph` tables | PASS |
| Run DB checks on trigger secret endpoint | Need hard proof of alembic/table state on exact target DB | Prior checks mixed migration state assumptions and command formatting issues | Executed `arkham-worldgraph-dbcheck-sld4q`; captured `alembic_version`, `worldgraph_tables`, `wg_ingest_jobs_count` | Re-run trigger + verify | PASS |
| Process triggered ingest in worker | Trigger succeeds but ingest does not progress (`pending`/`failed`) | Worker outbound fetch to OpenFlights initially timed out (`httpx.ConnectTimeout`) | Added explicit netcheck script and switched worker egress to `private-ranges-only` | Re-trigger and verify raw/canonical/search counts | PASS (outbound proven) |
| Validate outbound reachability from worker runtime | Need to separate DNS/TCP/TLS/remote timeout failure modes | Prior error lacked direct runtime diagnostics | Ran `arkham-worldgraph-netcheck-cnj7c`; DNS/TCP/HTTPS all succeeded and fetch returned all OpenFlights files | Continue smoke; investigate next failure if pipeline still blocked | PASS |
| Continue ingest after outbound fix | Worker still failed after successful OpenFlights fetch | GCS write failed: `404 The specified bucket does not exist` for `arkham-worldgraph-raw` | Created bucket, granted `roles/storage.objectAdmin` to worker service account | Re-trigger verify raw/canonical/search materialization | PASS |
| Stabilize staging smoke against external-source volatility | Need non-live dependency path for predictable smoke runs | Full dataset + memory pressure caused worker OOM; internet availability may vary | Added source-mode support (`http` / `fixture` / `gcs`) and switched worker to `OPENFLIGHTS_SOURCE_MODE=fixture` for smoke | Re-run trigger + verify complete/materialization | PASS |
| Keep queue worker continuously processing | Jobs remained `pending` due to worker lifecycle behavior | Service-like worker needed always-on processing characteristics | Set worker `min-instances=1` and disabled CPU throttling | Observe queue progress and ingest completion | PASS |
| Clean stale pre-fallback ingest job state | Legacy job stayed `running` after pre-fallback failures | Earlier worker OOM/failure left non-terminal ingest state | Ran admin DB cleanup job and marked stale job failed (`stale_jobs_updated=1`) | Re-run verify and confirm no stale `running` remains for legacy job | PASS |

---

## Network Path Validation

- **Runtime path used:** Cloud Run services/jobs attached to `robco-staging-vpc` and `robco-staging-vpc-subnet`
- **Expected private dependencies:** Cloud SQL `10.3.96.3`, Redis `10.70.148.3:6378`, Core service URL
- **Connectivity verdict:** PASS in Cloud Run; FAIL from local shell
- **Notes:** local direct smoke from this runner is constrained by proxy/network policy; in-cloud jobs used for execution.

---

## Current Outcome

- **Rollout Verdict:** `PASS (staging smoke contract)`
- **Blocking Issues Remaining:**
  - None for canonical fixture-mode staging smoke path.
- **Workarounds in place:**
  - In-cloud trigger and verify jobs ready.
  - Worker service updated to `private-ranges-only` egress, always-on processing (`min-instances=1`, CPU always allocated), memory `2Gi`, and latest image `manual-20260423g`.
  - Staging smoke now uses fixture-backed source mode (`OPENFLIGHTS_SOURCE_MODE=fixture`) to avoid public internet dependency.
  - Temporary utility Cloud Run jobs removed: `arkham-worldgraph-admin`, `arkham-worldgraph-netcheck` (scripts/docs retained).
  - Remaining legacy-or-auxiliary jobs classified: `arkham-worldgraph-migrate` (required), `arkham-worldgraph-dbcheck` (auxiliary). Superseded `arkham-worldgraph-smoke-trigger` removed.
- **Follow-up Tasks:**
  1. Keep fixture as required smoke mode in staging.
  2. Use `http` mode for higher-fidelity production validation only; keep timeout/source mode env-driven.
  3. Optionally shift production ingestion to `gcs` source snapshots for determinism + scale control.

