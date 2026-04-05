# Robco Platform - Cloud Run Services
# Serverless deployment for all platform services
# Uses Cloud Run GA API (v1) consistently

locals {
  service_images = {
    gateway         = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/gateway:latest"
    core            = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/core:latest"
    privacy         = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/privacy:latest"
    orchestration   = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/orchestration:latest"
    bim_ingestion   = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/bim_ingestion:latest"
    billing         = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/billing:latest"
  }
  
  service_ports = {
    gateway       = 8000
    core          = 3000
    privacy       = 3010
    orchestration = 3020
    bim_ingestion = 8001
    billing       = 8003
  }
  
  common_env = [
    {
      name  = "APP_ENV"
      value = var.environment
    }
  ]
}

# Gateway Service (main entry point)
resource "google_cloud_run_service" "gateway" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-gateway"
  location = var.cloud_run_region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.runtime.email
      container_concurrency = 80
      timeout_seconds      = 300
      
      containers {
        image = local.service_images.gateway
        ports {
          container_port = 8000
        }
        
        env {
          name  = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }
        
        env {
          name  = "REDIS_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.redis_url.secret_id
              version = "latest"
            }
          }
        }
        
        env {
          name  = "SIGNING_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.signing_key.secret_id
              version = "latest"
            }
          }
        }
        
        # Privacy service URL - references actual deployed service
        env {
          name  = "PRIVACY_SERVICE_URL"
          value = var.enable_cloud_run ? "http://robco-privacy.${var.cloud_run_region}.run.app" : "http://localhost:3010"
        }
        
        env {
          name  = "PRIVACY_SERVICE_TOKEN"
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
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.cloud_run_min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.cloud_run_max_instances)
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.privacy_service_token
  ]
  
  labels = local.common_tags
}

# Core Service
resource "google_cloud_run_service" "core" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-core"
  location = var.cloud_run_region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.runtime.email
      container_concurrency = 80
      timeout_seconds      = 300
      
      containers {
        image = local.service_images.core
        ports {
          container_port = 3000
        }
        
        env {
          name  = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }
        
        env {
          name  = "REDIS_URL"
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
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.cloud_run_min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.cloud_run_max_instances)
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url
  ]
  
  labels = local.common_tags
}

# Privacy Service
resource "google_cloud_run_service" "privacy" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-privacy"
  location = var.cloud_run_region
  project  = var.project_id
  
  template {
    spec {
      service_account_name = google_service_account.runtime.email
      container_concurrency = 80
      timeout_seconds      = 300
      
      containers {
        image = local.service_images.privacy
        ports {
          container_port = 3010
        }
        
        env {
          name  = "SERVICE_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.privacy_service_token.secret_id
              version = "latest"
            }
          }
        }
        
        env {
          name  = "REDIS_URL"
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
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = tostring(var.cloud_run_min_instances)
        "autoscaling.knative.dev/maxScale" = tostring(var.cloud_run_max_instances)
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.privacy_service_token,
    google_secret_manager_secret_version.redis_url
  ]
  
  labels = local.common_tags
}

# Output service URLs
output "gateway_url" {
  description = "Gateway Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_service.gateway[0].status[0].url : null
}

output "core_url" {
  description = "Core Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_service.core[0].status[0].url : null
}

output "privacy_url" {
  description = "Privacy Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_service.privacy[0].status[0].url : null
}
