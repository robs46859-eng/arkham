# Staging Deploy Runbook

This runbook verifies Terraform and deploys the staging environment from this repo.

## Prerequisites

- `terraform` installed locally
- `gcloud` installed and authenticated
- Docker installed and running
- A GCS bucket for Terraform state
- A staging GCP project with billing enabled
- A local Python environment at `/Users/robert/arkham/.venv` or a working `python3`

## 1. Prepare the staging tfvars file

Copy [`staging.tfvars.example`](/Users/robert/arkham/infra/terraform/staging.tfvars.example) to a local file that is not committed.

Example:

```bash
cd /Users/robert/arkham/infra/terraform
cp staging.tfvars.example staging.tfvars
```

Fill in at minimum:

- `project_id`
- `database_password`
- `redis_auth_token`
- `signing_key`
- `privacy_service_token`
- `storage_bucket_name`

## 2. Initialize Terraform

From [`infra/terraform`](/Users/robert/arkham/infra/terraform):

```bash
terraform init \
  -backend-config="bucket=<your-tf-state-bucket>" \
  -backend-config="prefix=staging"
```

## 3. Verify Terraform locally

```bash
terraform fmt -check
terraform validate
terraform plan -var-file=staging.tfvars -out=tfplan
```

Review the plan and confirm:

- Cloud SQL instance, DB, and user are created
- Memorystore Redis is created with auth enabled
- Secret Manager secrets exist for DB URL, Redis URL, signing key, and privacy token
- Cloud Run uses `google_cloud_run_v2_service`
- `PRIVACY_SERVICE_URL` is sourced from the privacy service URI, not a hardcoded string

## 4. Apply Terraform

```bash
terraform apply tfplan
```

## 5. Run database migrations

Fetch the DB URL from Secret Manager and run Alembic:

```bash
cd /Users/robert/arkham
DATABASE_URL="$(gcloud secrets versions access latest \
  --secret=staging-database-url \
  --project <your-gcp-project-id>)" \
./infra/scripts/deploy.sh migrate
```

Expected result:

- Alembic reaches `head`
- the `tenant_api_keys` table exists

## 6. Build and deploy services

From repo root:

```bash
PROJECT_ID=<your-gcp-project-id> \
REGION=us-central1 \
./infra/scripts/deploy.sh all
```

Notes:

- Images default to the current git SHA, not `latest`
- `all` runs build, push, migrations, deploy, and smoke tests

## 7. Verify Cloud Run

Check each service:

```bash
gcloud run services describe robco-gateway --region us-central1 --project <your-gcp-project-id>
gcloud run services describe robco-core --region us-central1 --project <your-gcp-project-id>
gcloud run services describe robco-privacy --region us-central1 --project <your-gcp-project-id>
```

Confirm:

- the image references include a git SHA tag
- env secrets are wired through Secret Manager refs
- service URLs are populated

## 8. Verify runtime behavior

Hit the health endpoints:

- `/health`
- `/healthz`
- `/readyz`

`/readyz` should report `ready` and show successful DB and Redis dependency checks.

## 9. Verify gateway auth

Create a tenant and API key:

1. `POST /v1/tenants`
2. `POST /v1/tenants/{tenant_id}/api-keys`
3. `POST /v1/auth/token` with the returned API key
4. Use the bearer token against `POST /v1/infer`

Success criteria:

- token issuance fails for invalid API keys
- valid API keys mint JWTs
- bearer auth works on protected endpoints

## 10. Run smoke tests independently

```bash
cd /Users/robert/arkham
./infra/scripts/deploy.sh smoke
```

This should pass:

- service health/readiness smoke
- gateway auth roundtrip smoke
- core registry durability smoke

## 11. Troubleshooting

If `terraform validate` fails:

- ensure `terraform init` completed
- verify the `random` provider is installed

If migrations fail:

- verify `DATABASE_URL` resolves to the Cloud SQL private endpoint
- confirm the runtime environment can reach the database

If deploy fails on Docker build:

- ensure Docker is running
- confirm the repo root contains `pyproject.toml`
- confirm service Dockerfiles are being built with repo-root context

If `/readyz` returns `not_ready`:

- confirm the DB secret and Redis secret values are correct
- confirm Cloud Run VPC connector access is present
- confirm Cloud SQL and Memorystore are both live
