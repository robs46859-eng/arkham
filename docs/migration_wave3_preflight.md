# Final Pre-Flight Gate: Wave 3 Database Migration

## 1. Window & Ownership
- **Execution Window:** April 24, 2026, 02:00 - 03:30 UTC.
- **Maintenance Start:** 02:00 UTC.
- **Target Cutover:** 02:45 UTC.
- **Migration Lead:** CTO Agent (Control Plane).
- **Approval/Validation Lead:** Platform Owner (User).

## 2. Readiness Check
- [x] **Latest Backup:** 2026-04-23T03:00 (Status: SUCCESSFUL).
- [x] **PITR State:** Verified ACTIVE on `arkham-492414-robco-db`.
- [x] **Incident Log:** `docs/migration_wave3_exec.log` initialized.
- [x] **Rollback Workspace:** Inverse commands open in secure terminal.

## 3. Execution Commands (Verified)

### **Step 1: Freeze (02:00 UTC)**
```bash
gcloud sql connect arkham-492414-robco-db --user=postgres --quiet \
  --command="REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM robco;"
```

### **Step 2: Clone (02:05 UTC)**
```bash
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
gcloud sql instances clone arkham-492414-robco-db arkham-492414-arkham-db \
  --point-in-time "${TIMESTAMP}" --project arkham-492414
```

### **Step 3: Update Secret (Approx. 02:35 UTC)**
```bash
NEW_DB_IP=$(gcloud sql instances describe arkham-492414-arkham-db --format='value(ipAddresses[0].ipAddress)')
gcloud secrets versions add staging-database-url --data="postgresql://robco:<DB_PASS>@${NEW_DB_IP}:5432/robco_db?sslmode=require"
```

### **Step 4: Update Cloud Run Bindings (Approx. 02:40 UTC)**
```bash
# Wave A: Foundation
gcloud run services update robco-core --add-cloudsql-instances=arkham-492414:us-central1:arkham-492414-arkham-db
gcloud run services update robco-privacy --add-cloudsql-instances=arkham-492414:us-central1:arkham-492414-arkham-db
gcloud run services update robco-orchestration --add-cloudsql-instances=arkham-492414:us-central1:arkham-492414-arkham-db

# Wave B: Edge/Product
gcloud run services update robco-gateway --add-cloudsql-instances=arkham-492414:us-central1:arkham-492414-arkham-db
gcloud run services update arkham-worldgraph --add-cloudsql-instances=arkham-492414:us-central1:arkham-492414-arkham-db
```

## 4. Validation (02:50 UTC)
- **Smoke Wave A:** `curl -f https://robco-core-zth4qhgsda-uc.a.run.app/healthz`
- **Smoke Wave B:** `curl -f https://robco-gateway-zth4qhgsda-uc.a.run.app/v1/health`
- **Data Parity:** `gcloud sql connect arkham-492414-arkham-db --user=postgres --command="SELECT count(*) FROM workflow_runs;"`

## 5. Rollback Thresholds
- **Critical Fail:** Step 2 (Clone) fails to provision after 40 mins.
- **Critical Fail:** Wave A services fail smoke tests after cutover.
- **Rollback Lead Time:** 5 minutes (Secret + Binding Reversal).
