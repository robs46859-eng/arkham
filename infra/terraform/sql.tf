# Robco Platform - Cloud SQL PostgreSQL
# Production-grade managed database with backups and PITR

resource "google_sql_database_instance" "main" {
  name             = "${var.project_id}-robco-db"
  project          = var.project_id
  region           = var.region
  database_version = "POSTGRES_15"
  
  deletion_protection = var.environment == "production" ? true : false
  
  settings {
    tier              = var.database_tier
    availability_type = var.enable_ha ? "REGIONAL" : "ZONAL"
    
    disk_size_gb       = 50
    disk_autoresize    = true
    disk_autoresize_limit = 500
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
    
    database_flags {
      name  = "log_lock_waits"
      value = "on"
    }
    
    database_flags {
      name  = "log_statement"
      value = "ddl"
    }
    
    maintenance_window {
      day          = 7
      hour         = 2
      update_track = "stable"
    }
    
    user_labels = local.common_tags
  }
  
  depends_on = [google_service_networking_connection.private_vpc]
}

resource "google_sql_database" "robco" {
  name      = var.database_name
  instance  = google_sql_database_instance.main.name
  project   = var.project_id
  charset   = "UTF8"
  collation = "en_US.UTF8"
}

resource "google_sql_user" "robco" {
  name     = var.database_user
  instance = google_sql_database_instance.main.name
  project  = var.project_id
  password = var.database_password
  
  deletion_policy = "ABANDON"
}

# Output: Database connection string (to be stored in Secret Manager)
output "database_connection_string" {
  description = "PostgreSQL connection string for Cloud SQL"
  value       = "postgresql://${var.database_user}:${var.database_password}@${google_sql_database_instance.main.private_ip_address}:5432/${var.database_name}?sslmode=require"
  sensitive   = true
}

output "database_private_ip" {
  description = "Cloud SQL private IP address"
  value       = google_sql_database_instance.main.private_ip_address
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = var.database_name
}
