# Robco Platform - IAM Configuration
# Service accounts and permissions for secure service-to-service communication

# Runtime service account for all services
resource "google_service_account" "runtime" {
  account_id   = "robco-runtime"
  display_name = "Robco Platform Runtime Service Account"
  description  = "Service account for running Robco platform services on Cloud Run"
  project      = var.project_id
}

# Grant Secret Manager access
resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant Cloud SQL Client role
resource "google_project_iam_member" "runtime_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant Redis access (via network, but add monitoring role)
resource "google_project_iam_member" "runtime_redis_monitoring" {
  project = var.project_id
  role    = "roles/redis.viewer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant Storage access if GCS enabled
resource "google_project_iam_member" "runtime_storage_access" {
  count   = var.enable_gcs ? 1 : 0
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant Cloud Run invocation permissions between services
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant Artifact Registry pull permissions
resource "google_project_iam_member" "artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Grant logging and monitoring permissions
resource "google_project_iam_member" "runtime_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Output service account email for reference
output "runtime_service_account_email" {
  description = "Runtime service account email"
  value       = google_service_account.runtime.email
}

output "runtime_service_account_name" {
  description = "Runtime service account name"
  value       = google_service_account.runtime.name
}
