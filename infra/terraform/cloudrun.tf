# Robco Platform - Cloud Run Services
# Serverless deployment for all platform services
# Uses Direct VPC Egress (no VPC connector needed)

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
          cpu    = "1000m"
          memory = "256Mi"
        }
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.main.name
      }
      egress = "PRIVATE_RANGES_ONLY"
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
        name = "ADMIN_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.admin_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "PRIVACY_SERVICE_URL"
        value = google_cloud_run_v2_service.privacy[0].uri
      }

      env {
        name  = "CORE_SERVICE_URL"
        value = google_cloud_run_v2_service.core[0].uri
      }

      env {
        name  = "BILLING_SERVICE_URL"
        value = google_cloud_run_v2_service.billing[0].uri
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
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.main.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.admin_token,
    google_secret_manager_secret_version.privacy_service_token,
    google_cloud_run_v2_service.billing,
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
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.main.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
  ]
}

# Billing Service
resource "google_cloud_run_v2_service" "billing" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-billing"
  location = var.cloud_run_region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.common_tags

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "60s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = local.service_images.billing

      ports {
        container_port = 3020
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
        name = "STRIPE_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.stripe_secret_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "STRIPE_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.stripe_webhook_secret.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "STRIPE_PRICE_ID"
        value = var.stripe_price_id
      }

      env {
        name  = "STRIPE_SUCCESS_URL"
        value = var.stripe_success_url
      }

      env {
        name  = "STRIPE_CANCEL_URL"
        value = var.stripe_cancel_url
      }

      env {
        name  = "STRIPE_PORTAL_RETURN_URL"
        value = var.stripe_portal_return_url
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "256Mi"
        }
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.main.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.stripe_secret_key,
    google_secret_manager_secret_version.stripe_webhook_secret,
  ]
}

output "billing_url" {
  description = "Billing Cloud Run service URL"
  value       = var.enable_cloud_run ? google_cloud_run_v2_service.billing[0].uri : null
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

# ── Vertical Services (hub-and-spoke spokes) ─────────────────────────────────

variable "verticals" {
  description = "Map of vertical services to deploy. Key = service name, value = config."
  type = map(object({
    container_port = optional(number, 8000)
    cpu            = optional(string, "1000m")
    memory         = optional(string, "256Mi")
    min_instances  = optional(number, 0)
    max_instances  = optional(number, 5)
  }))
  default = {
    omniscale = {}
  }
}

resource "google_cloud_run_v2_service" "vertical" {
  for_each = var.enable_cloud_run ? var.verticals : {}

  name     = "robco-${replace(each.key, "_", "-")}"
  location = var.cloud_run_region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  labels   = local.common_tags

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = each.value.min_instances
      max_instance_count = each.value.max_instances
    }

    containers {
      image = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/${each.key}:latest"

      ports {
        container_port = each.value.container_port
      }

      env {
        name  = "CORE_SERVICE_URL"
        value = google_cloud_run_v2_service.core[0].uri
      }

      env {
        name  = "APP_ENV"
        value = var.environment
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
          cpu    = each.value.cpu
          memory = each.value.memory
        }
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.name
        subnetwork = google_compute_subnetwork.main.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_service.core,
    google_secret_manager_secret_version.redis_url,
  ]
}

output "vertical_urls" {
  description = "Cloud Run URLs for all deployed verticals"
  value = var.enable_cloud_run ? {
    for k, v in google_cloud_run_v2_service.vertical : k => v.uri
  } : {}
}
