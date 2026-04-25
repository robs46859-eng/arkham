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
    migrations    = "${google_artifact_registry_repository.containers.location}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_name}/migrations:latest"
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
        name  = "APP_ENV"
        value = "production"
      }

      env {
        name  = "PREFER_LOCAL_MODELS"
        value = "false"
      }

      env {
        name  = "EMBEDDING_PROVIDER"
        value = "openai"
      }

      env {
        name  = "EMBEDDING_MODEL"
        value = "text-embedding-3-small"
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
        network    = google_compute_network.arkham.name
        subnetwork = google_compute_subnetwork.arkham.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].resources[0].cpu_idle,
      template[0].containers[0].resources[0].startup_cpu_boost,
      template[0].scaling[0].max_instance_count,
    ]
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
        name  = "APP_ENV"
        value = "production"
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

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = var.stripe_webhook_secret != "" ? [1] : []
        content {
          name = "STRIPE_WEBHOOK_SECRET"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.stripe_webhook_secret.secret_id
              version = "latest"
            }
          }
        }
      }

      env {
        name  = "STRIPE_PRICE_PLAN_MAP"
        value = var.stripe_price_plan_map
      }

      env {
        name  = "STRIPE_PRICE_ENTITLEMENT_MAP"
        value = var.stripe_price_entitlement_map
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
        network    = google_compute_network.arkham.name
        subnetwork = google_compute_subnetwork.arkham.name
      }
      egress = "ALL_TRAFFIC"
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].resources[0].cpu_idle,
      template[0].containers[0].resources[0].startup_cpu_boost,
      template[0].scaling[0].max_instance_count,
    ]
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.admin_token,
    google_secret_manager_secret_version.privacy_service_token,
    google_cloud_run_v2_service.billing,
    google_secret_manager_secret_version.stripe_webhook_secret,
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
        network    = google_compute_network.arkham.name
        subnetwork = google_compute_subnetwork.arkham.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].resources[0].cpu_idle,
      template[0].containers[0].resources[0].startup_cpu_boost,
    ]
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
    timeout                          = "300s"
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
          memory = "512Mi"
        }
      }
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.arkham.name
        subnetwork = google_compute_subnetwork.arkham.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].resources[0].cpu_idle,
      template[0].containers[0].resources[0].startup_cpu_boost,
      template[0].scaling[0].max_instance_count,
    ]
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.signing_key,
    google_secret_manager_secret_version.stripe_webhook_secret,
    google_secret_manager_secret_version.stripe_secret_key,
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

# Database migration job. Runs inside the VPC so it can reach private Cloud SQL.
resource "google_cloud_run_v2_job" "migrate" {
  count    = var.enable_cloud_run ? 1 : 0
  name     = "robco-migrate"
  location = var.cloud_run_region
  project  = var.project_id
  labels   = local.common_tags

  template {
    template {
      service_account = google_service_account.runtime.email
      timeout         = "600s"
      max_retries     = 0

      containers {
        image = local.service_images.migrations

        command = ["python", "-m", "alembic", "upgrade", "head"]

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
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
          network    = google_compute_network.arkham.name
          subnetwork = google_compute_subnetwork.arkham.name
        }
        egress = "PRIVATE_RANGES_ONLY"
      }
    }
  }

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.database_url,
    google_project_iam_member.runtime_secret_accessor,
    google_project_iam_member.runtime_cloudsql_client,
  ]
}

output "migration_job_name" {
  description = "Cloud Run job used to run Alembic migrations"
  value       = var.enable_cloud_run ? google_cloud_run_v2_job.migrate[0].name : null
}

# ── Vertical Services (hub-and-spoke spokes) ─────────────────────────────────

variable "verticals" {
  description = "Map of vertical services to deploy. Key = service name, value = config."
  type = map(object({
    container_port = optional(number, 8000)
    cpu            = optional(string, "1000m")
    memory         = optional(string, "512Mi")
    min_instances  = optional(number, 0)
    max_instances  = optional(number, 3)
    vpc_egress     = optional(string, "ALL_TRAFFIC")
    redis_enabled  = optional(bool, false)
    service_endpoint = optional(
      string,
      "https://robco-omniscale-zth4qhgsda-uc.a.run.app",
    )
    event_callback_url = optional(
      string,
      "https://robco-omniscale-zth4qhgsda-uc.a.run.app/events/receive",
    )
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

      dynamic "env" {
        for_each = each.value.service_endpoint != null ? [each.value.service_endpoint] : []
        content {
          name  = "SERVICE_ENDPOINT"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = each.value.event_callback_url != null ? [each.value.event_callback_url] : []
        content {
          name  = "EVENT_CALLBACK_URL"
          value = env.value
        }
      }

      dynamic "env" {
        for_each = each.value.redis_enabled ? [1] : []
        content {
          name = "REDIS_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.redis_url.secret_id
              version = "latest"
            }
          }
        }
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.secret_id
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
        network    = google_compute_network.arkham.name
        subnetwork = google_compute_subnetwork.arkham.name
      }
      egress = each.value.vpc_egress
    }
  }

  lifecycle {
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].resources[0].cpu_idle,
      template[0].containers[0].resources[0].startup_cpu_boost,
    ]
  }

  depends_on = [
    google_project_service.required_apis,
    google_cloud_run_v2_service.core,
    google_secret_manager_secret_version.redis_url,
    google_secret_manager_secret_version.anthropic_api_key,
  ]
}

output "vertical_urls" {
  description = "Cloud Run URLs for all deployed verticals"
  value = var.enable_cloud_run ? {
    for k, v in google_cloud_run_v2_service.vertical : k => v.uri
  } : {}
}
