# Robco Platform - Artifact Registry
# Container registry for Docker images

resource "google_artifact_registry_repository" "containers" {
  repository_id = var.artifact_registry_name
  project       = var.project_id
  location      = var.region
  description   = "Docker container registry for Robco platform services"
  format        = "DOCKER"
  
  mode = "STANDARD_REPOSITORY"
  
  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
  
  labels = local.common_tags
  
  depends_on = [google_project_service.required_apis]
}

# Output registry URL for docker push/pull
output "artifact_registry_url" {
  description = "Artifact Registry Docker repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}"
}

output "artifact_registry_name" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.containers.name
}
