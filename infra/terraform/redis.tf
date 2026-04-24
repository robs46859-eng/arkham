# Robco Platform - Memorystore Redis
# Managed Redis for caching, session storage, and event bus

resource "google_redis_instance" "arkham" {
  name                           = "${var.project_id}-robco-redis"
  project                        = var.project_id
  region                         = var.region
  tier                           = var.redis_tier
  memory_size_gb                 = var.redis_memory_size_gb
  display_name                   = "Robco Platform Redis"
  authorized_network             = google_compute_network.arkham.name
  connect_mode                   = "PRIVATE_SERVICE_ACCESS"
  transit_encryption_mode        = "SERVER_AUTHENTICATION"
  
  redis_version                  = "REDIS_7_0"
  
  # Maintenance window (Sunday 2-3 AM)
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 2
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }
  
  # Persistence configuration
  persistence_config {
    persistence_mode = "DISABLED"
  }
  
  # Authentication
  auth_enabled = true
  
  labels = local.common_tags
  
  depends_on = [google_service_networking_connection.private_vpc]
}

# Output: Redis connection string (to be stored in Secret Manager)
output "redis_host" {
  description = "Memorystore Redis host"
  value       = google_redis_instance.arkham.host
  sensitive   = true
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = google_redis_instance.arkham.port
}

output "redis_connection_string" {
  description = "Redis connection string (auth token to be added separately)"
  value       = "redis://${google_redis_instance.arkham.host}:${google_redis_instance.arkham.port}"
  sensitive   = true
}
