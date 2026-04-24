# Arkham Staging Smoke + Incident Log Template

Use this for any staging rollout where a smoke test may require iterative fixes.

---

## Header

- **Service / Component:**
- **Environment:** `staging`
- **Date/Time (UTC):**
- **Operator:**
- **Change Ref:** (commit SHA / build ID / PR)
- **Related Runbook:**
- **Expected Healthy Endpoint(s):**
- **Required Secrets/Env:**
- **Known Private Dependencies:**
- **Rollback Trigger:**
- **Rollback Command:**

---

## 1) Smoke Checklist (Compact)

Mark each item as `PASS`, `FAIL`, or `BLOCKED`.

| # | Check | Status | Evidence (command/output/log link) |
|---|---|---|---|
| 1 | DB migrations applied to latest head |  |  |
| 2 | Service deploy completed, revision ready |  |  |
| 3 | Required env vars present |  |  |
| 4 | Required secrets bound |  |  |
| 5 | Health endpoint returns expected payload |  |  |
| 6 | Ready endpoint dependencies all healthy |  |  |
| 7 | Worker process running with correct runtime model |  |  |
| 8 | Worker reaches Redis/DB on intended network path |  |  |
| 9 | First ingest trigger accepted |  |  |
| 10 | Ingest job reached `complete` |  |  |
| 11 | Raw objects/records persisted |  |  |
| 12 | Canonical entities created |  |  |
| 13 | Search documents populated |  |  |
| 14 | Search query returns expected seeded entities |  |  |
| 15 | Event publish failures (if any) are non-blocking |  |  |

---

## 2) Failure/Retry Incident Log

One row per attempted correction.

| Attempted Action | Failure Observed | Root Cause | Fix Applied | Next Verification Step | Result |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

### Example row

| Attempted Action | Failure Observed | Root Cause | Fix Applied | Next Verification Step | Result |
|---|---|---|---|---|---|
| Deploy service | Container failed startup | Hardcoded `8050`, Cloud Run expects `PORT` | Bind server to `${PORT}` | Redeploy and check `/health` + revision Ready | PASS |

---

## 3) Network Path Validation

- **Runtime path used:** (local shell / Cloud Run service / Cloud Run job / VPC connector path)
- **Expected private dependencies:** (DB host, Redis host, internal APIs)
- **Connectivity verdict:** `PASS` / `FAIL`
- **Notes:**

---

## 4) Final Outcome

- **Rollout Verdict:** `PASS` / `PARTIAL` / `FAIL`
- **Blocking Issues Remaining:**
- **Workarounds in place:**
- **Follow-up Tasks:**

---

## 5) Handoff Notes

- **Safe to continue to next phase?** `yes` / `no`
- **If yes, next action:**
- **If no, owner + unblock condition:**

