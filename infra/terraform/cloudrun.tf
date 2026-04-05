# Robco Platform - Cloud Run Services
# Serverless deployment for all platform services

locals {
  service_images = {
    gateway       = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/gateway:latest"
    core          = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/core:latest"
    privacy       = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/privacy:latest"
    orchestration = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/orchestration:latest"
    bim_ingestion = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/bim_ingestion:latest"
    billing       = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/billing:latest"
  }
}

# Privacy Service
resource "google_cloud_run_v2_service" "privacy" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-privacy"
  location = var.cloud_run_region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.common_tags

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.service_images.privacy

      ports {
        container_port = 3010
      }

      env {
        name = "SERVICE_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.privacy_service_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "500m"
          memory = "256Mi"
        }
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector[0].id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.privacy_service_token,
    google_secret_manager_secret_version.redis_url,
  ]
}

# Gateway Service (main entry point)
resource "google_cloud_run_v2_service" "gateway" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-gateway"
  location = var.cloud_run_region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"
  labels   = local.common_tags

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.service_images.gateway

      ports {
        container_port = 8000
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SIGNING_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.signing_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "PRIVACY_SERVICE_URL"
        value = google_cloud_run_v2_service.privacy[0].uri
      }

      env {
        name = "PRIVACY_SERVICE_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.privacy_service_token.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector[0].id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.privacy_service_token,
  ]
}

# Core Service
resource "google_cloud_run_v2_service" "core" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-core"
  location = var.cloud_run_region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.common_tags

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.service_images.core

      ports {
        container_port = 3000
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.redis_url.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.connector[0].id
      egress    = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
  ]
}

output "gateway_url" {
  description = "Gateway Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_v2_service.gateway[0].uri : null
}

output "core_url" {
  description = "Core Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_v2_service.core[0].uri : null
}

output "privacy_url" {
  description = "Privacy Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_v2_service.privacy[0].uri : null
}
