# Robco Platform Infrastructure

Production-grade infrastructure for the Robco multi-service AI platform on Google Cloud.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Google Cloud Platform                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    VPC Network                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ Cloud SQL   │  │ Memorystore │  │ Cloud Run    │  │  │
│  │  │ PostgreSQL  │  │ Redis       │  │ Services     │  │  │
│  │  │ (Private IP)│  │ (Private)   │  │ - Gateway    │  │  │
│  │  └─────────────┘  └─────────────┘  │ - Core       │  │  │
│  │                                      │ - Privacy    │  │  │
│  │  ┌─────────────────────────────┐    │ - Others     │  │  │
│  │  │ Secret Manager              │    └──────────────┘  │  │
│  │  │ - DATABASE_URL            │                        │  │
│  │  │ - REDIS_URL               │  ┌──────────────────┐ │  │
│  │  │ - SIGNING_KEY             │  │ Artifact Registry│ │  │
│  │  │ - Service Tokens          │  │ (Docker Images)  │ │  │
│  │  └─────────────────────────────┘  └──────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required Tools
- Terraform >= 1.5.0
- Google Cloud SDK (`gcloud`)
- kubectl (for Cloud Run debugging)

### Required GCP APIs
The following APIs will be automatically enabled by Terraform:
- compute.googleapis.com
- sqladmin.googleapis.com
- redis.googleapis.com
- secretmanager.googleapis.com
- artifactregistry.googleapis.com
- storage.googleapis.com
- run.googleapis.com
- cloudbuild.googleapis.com
- servicenetworking.googleapis.com
- iam.googleapis.com

## Quick Start

### 1. Authentication & Project Setup

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# Create a service account for Terraform (if not using user credentials)
gcloud iam service-accounts create terraform \
  --display-name "Terraform Service Account"

# Grant necessary roles to the service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:terraform@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/editor"

# If using service account, download key and authenticate
# gcloud iam service-accounts keys create terraform-key.json \
#   --iam-account=terraform@${PROJECT_ID}.iam.gserviceaccount.com
# export GOOGLE_APPLICATION_CREDENTIALS="terraform-key.json"
```

### 2. Create Terraform State Bucket

```bash
# Create GCS bucket for remote state
gsutil mb -p $PROJECT_ID -l us-central1 gs://${PROJECT_ID}-tf-state

# Enable versioning for state backup
gsutil versioning set on gs://${PROJECT_ID}-tf-state
```

### 3. Initialize Terraform

```bash
cd infra/terraform

# Initialize with GCS backend
terraform init \
  -backend-config="bucket=${PROJECT_ID}-tf-state" \
  -backend-config="prefix=production"
```

### 4. Configure Variables

Create a `terraform.tfvars` file:

```hcl
project_id          = "your-project-id"
region              = "us-central1"
environment         = "production"  # or "staging"

database_name       = "robco_db"
database_user       = "robco"
database_password   = "super-secure-password-min-16-chars"
database_tier       = "db-custom-2-4096"
enable_ha           = true

redis_tier          = "STANDARD"
redis_memory_size_gb = 2

signing_key         = "your-jwt-signing-key-min-32-characters-long"
privacy_service_token = "your-privacy-service-token"

storage_bucket_name = "${PROJECT_ID}-bim-storage"
enable_gcs          = true

enable_cloud_run    = true
cloud_run_region    = "us-central1"
cloud_run_min_instances = 1  # 0 for cost savings, 1+ for no cold starts
cloud_run_max_instances = 10

artifact_registry_name = "robco-containers"
```

**Security Note**: Never commit `terraform.tfvars` with real passwords to version control. Use environment variables or a secrets manager.

### 5. Plan and Apply

```bash
# Review the plan
terraform plan -out=tfplan

# Apply infrastructure
terraform apply tfplan
```

### 6. Retrieve Outputs

```bash
# Get all outputs
terraform output

# Get specific values
terraform output -raw gateway_url
terraform output -raw database_private_ip
```

## Deployment Workflow

### Build and Push Docker Images

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export REGISTRY_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/robco-containers"

# Authenticate Docker
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push each service
docker build -t ${REGISTRY_URL}/gateway:latest ./services/gateway
docker push ${REGISTRY_URL}/gateway:latest

docker build -t ${REGISTRY_URL}/core:latest ./services/core
docker push ${REGISTRY_URL}/core:latest

docker build -t ${REGISTRY_URL}/privacy:latest ./services/privacy
docker push ${REGISTRY_URL}/privacy:latest

# Repeat for other services...
```

### Run Database Migrations

```bash
# Get DATABASE_URL from Secret Manager
export DATABASE_URL=$(gcloud secrets versions access latest \
  --secret="production-database-url" \
  --project="${PROJECT_ID}")

# Run Alembic migrations
cd /workspace
alembic upgrade head
```

### Deploy Services

After pushing new images, Cloud Run automatically deploys the latest version if configured for continuous deployment, or you can force a revision:

```bash
gcloud run services update robco-gateway \
  --image ${REGISTRY_URL}/gateway:latest \
  --region us-central1 \
  --project ${PROJECT_ID}
```

## Secret Management

All sensitive configuration is stored in Google Secret Manager. Services access secrets via environment variables injected at runtime.

### Accessing Secrets Manually

```bash
# List secrets
gcloud secrets list --project=${PROJECT_ID}

# Access a secret value
gcloud secrets versions access latest \
  --secret="production-signing-key" \
  --project="${PROJECT_ID}"
```

### Creating Additional Secrets

```bash
# Create a new secret
echo -n "my-secret-value" | gcloud secrets create my-new-secret \
  --data-file=- \
  --project=${PROJECT_ID}

# Add a new version to existing secret
echo -n "updated-value" | gcloud secrets versions add my-secret \
  --data-file=- \
  --project=${PROJECT_ID}
```

## Monitoring & Observability

### Cloud Logging
All services write logs to Cloud Logging automatically. View logs:

```bash
# Gateway logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=robco-gateway" \
  --limit=50 \
  --format="table(timestamp,textPayload)"
```

### Cloud Monitoring
Metrics are automatically collected. Create dashboards at:
https://console.cloud.google.com/monitoring/dashboards

### Health Checks
Each service exposes health endpoints:
- `/health` - Basic liveness check
- `/readyz` - Readiness check (includes Redis/DB connectivity)

Test health:
```bash
curl https://$(gcloud run services describe robco-gateway --format='value(status.url)')/health
```

## Cost Optimization

### Development/Staging
```hcl
cloud_run_min_instances = 0  # Allow cold starts
database_tier = "db-f1-micro"
redis_tier = "BASIC"
redis_memory_size_gb = 1
enable_ha = false
```

### Production
```hcl
cloud_run_min_instances = 1  # No cold starts for critical services
database_tier = "db-custom-4-8192"
redis_tier = "STANDARD"  # High availability
redis_memory_size_gb = 4
enable_ha = true
```

## Disaster Recovery

### Database Backups
- Automated daily backups retained for 30 days
- Point-in-time recovery enabled (7-day window)
- Manual backups before major migrations

### Restore Procedure
```bash
# List available backups
gcloud sql backups list --instance=${INSTANCE_NAME}

# Restore from backup
gcloud sql instances restore-backup ${INSTANCE_NAME} \
  --backup-id=${BACKUP_ID}
```

## Security Considerations

1. **Private IPs Only**: Cloud SQL and Redis use private IPs only
2. **VPC Service Controls**: All traffic stays within VPC
3. **Secret Manager**: No secrets in environment variables or code
4. **Service Accounts**: Minimal permissions principle
5. **SSL/TLS**: Required for all database connections
6. **IAM**: Fine-grained access control for all resources

## Troubleshooting

### Common Issues

**Cloud Run fails to start:**
```bash
# Check logs
gcloud run services logs read robco-gateway --limit=50

# Verify secrets exist
gcloud secrets list --filter="name:production"
```

**Database connection failures:**
```bash
# Verify VPC peering
gcloud services vpc-peerings list --network=${VPC_NAME}

# Test connectivity from Cloud Run
gcloud run services exec robco-core --command="ping" --args="${DB_PRIVATE_IP}"
```

**Redis connection issues:**
```bash
# Check Redis instance status
gcloud redis instances describe ${INSTANCE_NAME} --region=${REGION}

# Verify network connectivity
gcloud redis instances test-authorization ${INSTANCE_NAME} --region=${REGION}
```

## Environment Matrix

| Feature | Development | Staging | Production |
|---------|-------------|---------|------------|
| Cloud SQL Tier | db-f1-micro | db-custom-2-4096 | db-custom-4-8192 |
| HA Enabled | No | No | Yes |
| Redis Tier | BASIC | BASIC | STANDARD |
| Redis Memory | 1 GB | 1 GB | 4 GB |
| Min Instances | 0 | 0 | 1 |
| Max Instances | 5 | 10 | 20 |
| Backups | 7 days | 15 days | 30 days |
| Deletion Protection | No | No | Yes |

## Next Steps

After infrastructure is deployed:
1. Build and push Docker images
2. Run database migrations
3. Deploy services to Cloud Run
4. Configure custom domains (optional)
5. Set up monitoring alerts
6. Configure CI/CD pipeline

## Support

For issues or questions:
- Check Cloud Logging for error details
- Review Terraform state: `terraform show`
- Consult architecture diagrams in `/docs`
