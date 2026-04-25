# Full Deploy Checklist

This checklist is for getting `robs46859-eng/arkham` all the way to a live deploy in `arkham-492414`, not just proving a build or checking health after the fact.

## 1. Pre-Deploy Code State

- Confirm the target branch and commit:
  - `git status --short --branch`
  - `git rev-parse HEAD`
- Confirm the remote branch contains the intended work:
  - `git fetch origin`
  - `git rev-parse origin/main`
  - `git log --oneline origin/main -n 5`
- Verify there are no uncommitted production changes left only on the local machine.
- If the deploy depends on repo-controlled startup or pipeline fixes, commit those first so Cloud Build and production use the same source of truth.

## 2. Deploy Pipeline Preconditions

- Confirm the Cloud Build config points at a real Artifact Registry repository.
- Confirm the Cloud Run service name, region, and image path match the build config:
  - service: `arkham`
  - region: `us-central1`
  - image repo: `us-central1-docker.pkg.dev/arkham-492414/arkham/arkham`
- Confirm secrets referenced by the deploy exist and are readable by the runtime service account:
  - `fs-ai-database-url`
  - `arkham-vault-key`
  - `arkham-sidecar-api-token`
- Confirm the runtime service still has the required Cloud SQL attachment:
  - `arkham-492414:us-central1:arkham-db`

## 3. Schema / Migration Posture

- Do not assume `alembic upgrade head` is safe on the production database without checking the current branch of history.
- Confirm the startup path does not hard-fail the container before it binds `PORT`.
- Review migrations added since the currently deployed revision and check for:
  - references to tables that may not exist on legacy databases
  - unconditional `add_column` or `create_table` operations against optional subsystems
  - foreign keys to tables that were never introduced in the current migration chain
- If the database is on a legacy track, make new migrations idempotent or schema-aware before deploying.

## 4. Build and Push

- Submit the build with the intended commit SHA:
  - `gcloud builds submit /Users/joeiton/Arkham --config /Users/joeiton/Arkham/cloudbuild.yaml --project=arkham-492414 --substitutions=COMMIT_SHA=<sha>`
- Watch the build until:
  - image build succeeds
  - image push succeeds
  - deploy step starts
- If the build wrapper is slow or stalls after a successful image push, verify the image exists in Artifact Registry before switching to a direct Cloud Run deploy.

## 5. Deploy

- Preferred path:
  - let `cloudbuild.yaml` finish the deploy for the committed SHA
- Recovery path when the image is already pushed but the wrapper stalls:
  - `gcloud run deploy arkham --image=us-central1-docker.pkg.dev/arkham-492414/arkham/arkham:<sha> --region=us-central1 --project=arkham-492414 --quiet --no-allow-unauthenticated --add-cloudsql-instances=arkham-492414:us-central1:arkham-db --vpc-egress=private-ranges-only --network=default --subnet=default --memory=512Mi --cpu=1 --max-instances=3 --set-secrets=DATABASE_URL=fs-ai-database-url:latest,BLOODS_VAULT_KEY=arkham-vault-key:latest,SIDECAR_SERVICE_TOKEN=arkham-sidecar-api-token:latest --set-env-vars=APP_ENV=production,SIDECAR_SHADOW_MODE=true,BLOODS_ENABLED=true`

## 6. Rollout Confirmation

- Confirm the service spec now points at the intended image:
  - `gcloud run services describe arkham --region us-central1 --project=arkham-492414`
- Confirm:
  - `latestCreatedRevisionName` is the new revision
  - `latestReadyRevisionName` is the same new revision
  - `Ready=True`
  - traffic is `100%` on the new revision

## 7. Runtime Validation

- Read revision logs for the new revision if rollout is slow or fails:
  - `gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="arkham" AND resource.labels.revision_name="<revision>"' --project=arkham-492414 --limit=100`
- Specifically check for:
  - migration failures before server startup
  - Cloud SQL connectivity failures
  - secret access failures
  - startup probe failures
  - port bind failures

## 8. Post-Deploy Product Checks

- Verify the new revision is actually serving the routes you care about, not just `/health`.
- Confirm any domain or upstream caller that depends on `arkham` still works after the revision cutover.
- If the deploy required a temporary recovery change, decide immediately whether:
  - it should remain as the normal behavior
  - it should be replaced by a cleaner migration strategy
  - it should be removed after the schema is repaired

## 9. Closeout

- Push any deploy-recovery or migration-fix commits back to GitHub so production is not ahead of version control.
- Record:
  - commit SHA deployed
  - Cloud Build ID
  - Cloud Run revision
  - any warnings or fallback behavior still present
- If startup succeeded only because a migration was skipped or tolerated, open the next cleanup task before treating the deploy path as fully healthy.
