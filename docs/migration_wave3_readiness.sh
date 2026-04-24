#!/bin/bash
# Wave 3 Database Migration - Operator Readiness Script
# DO NOT RUN UNTIL 2026-04-24 02:00 UTC

PROJECT_ID="arkham-492414"
SOURCE_INSTANCE="arkham-492414-robco-db"
TARGET_INSTANCE="arkham-492414-arkham-db"
REGION="us-central1"

echo "Step 1: Freeze Writes (02:00 UTC)"
echo "Command:"
echo "gcloud sql connect ${SOURCE_INSTANCE} --user=postgres --quiet --command=\"REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM robco;\""

echo ""
echo "Step 2: Trigger Clone (02:05 UTC)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "Command:"
echo "gcloud sql instances clone ${SOURCE_INSTANCE} ${TARGET_INSTANCE} --point-in-time \"${TIMESTAMP}\" --project ${PROJECT_ID}"

echo ""
echo "Step 3: Update Secret Manager (Approx 02:35 UTC)"
echo "Command (Run after clone is complete):"
echo "NEW_DB_IP=\$(gcloud sql instances describe ${TARGET_INSTANCE} --format='value(ipAddresses[0].ipAddress)')"
echo "DB_PASS=\$(gcloud secrets versions access latest --secret=staging-database-password)" # Verify secret name
echo "NEW_URL=\"postgresql://robco:\${DB_PASS}@\${NEW_DB_IP}:5432/robco_db?sslmode=require\""
echo "gcloud secrets versions add staging-database-url --data=\"\${NEW_URL}\""

echo ""
echo "Step 4: Update Cloud Run Bindings (Approx 02:40 UTC)"
echo "Commands:"
echo "gcloud run services update robco-core --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${TARGET_INSTANCE}"
echo "gcloud run services update robco-privacy --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${TARGET_INSTANCE}"
echo "gcloud run services update robco-orchestration --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${TARGET_INSTANCE}"
echo "gcloud run services update robco-gateway --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${TARGET_INSTANCE}"
echo "gcloud run services update arkham-worldgraph --add-cloudsql-instances=${PROJECT_ID}:${REGION}:${TARGET_INSTANCE}"

echo ""
echo "Step 5: Validation"
echo "Command:"
echo "gcloud sql connect ${TARGET_INSTANCE} --user=postgres --command=\"SELECT count(*) FROM workflow_runs;\""
