# Robco Platform - Secret Manager
# Secure storage for all sensitive configuration values

# Database connection string
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.environment}-database-url"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql://${var.database_user}:${var.database_password}@${google_sql_database_instance.main.private_ip_address}:5432/${var.database_name}?sslmode=require"
  enabled     = true
}

# Redis connection string with auth
resource "google_secret_manager_secret" "redis_url" {
  secret_id = "${var.environment}-redis-url"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

# Note: Using rediss:// for SSL support if enabled
resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "rediss://:${google_redis_instance.main.auth_string}@${google_redis_instance.main.host}:${google_redis_instance.main.port}?ssl_cert_reqs=none"
  enabled     = true
}

# JWT Signing Key
resource "google_secret_manager_secret" "signing_key" {
  secret_id = "${var.environment}-signing-key"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "signing_key" {
  secret      = google_secret_manager_secret.signing_key.id
  secret_data = var.signing_key

  enabled = true
}

# Privacy Service Token
resource "google_secret_manager_secret" "privacy_service_token" {
  secret_id = "${var.environment}-privacy-service-token"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "privacy_service_token" {
  secret      = google_secret_manager_secret.privacy_service_token.id
  secret_data = var.privacy_service_token != "" ? var.privacy_service_token : random_password.privacy_token.result

  enabled = true
}

resource "random_password" "privacy_token" {
  length  = 32
  special = false
}

resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

# Storage credentials (if using GCS, service account keys)
resource "google_secret_manager_secret" "storage_credentials" {
  count     = var.enable_gcs ? 1 : 0
  secret_id = "${var.environment}-storage-credentials"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

# Admin token — guards /v1/tenants/* routes
resource "google_secret_manager_secret" "admin_token" {
  secret_id = "${var.environment}-admin-token"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_token" {
  secret      = google_secret_manager_secret.admin_token.id
  secret_data = var.admin_token

  enabled = true
}

# Stripe secrets (for billing service)
resource "google_secret_manager_secret" "stripe_secret_key" {
  secret_id = "${var.environment}-stripe-secret-key"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "stripe_secret_key" {
  count       = var.stripe_secret_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.stripe_secret_key.id
  secret_data = var.stripe_secret_key
  enabled     = true
}

resource "google_secret_manager_secret" "stripe_webhook_secret" {
  secret_id = "${var.environment}-stripe-webhook-secret"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "stripe_webhook_secret" {
  count       = var.stripe_webhook_secret != "" ? 1 : 0
  secret      = google_secret_manager_secret.stripe_webhook_secret.id
  secret_data = var.stripe_webhook_secret
  enabled     = true
}

# API Keys (OpenAI, Anthropic, etc.)
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "${var.environment}-openai-api-key"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "${var.environment}-anthropic-api-key"
  project   = var.project_id

  labels = local.common_tags

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "anthropic_api_key" {
  count       = var.anthropic_api_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.anthropic_api_key.id
  secret_data = var.anthropic_api_key
  enabled     = true
}

# Output secret IDs for reference
output "secret_ids" {
  description = "Map of secret IDs for use in deployments"
  value = {
    database_url          = google_secret_manager_secret.database_url.secret_id
    redis_url             = google_secret_manager_secret.redis_url.secret_id
    signing_key           = google_secret_manager_secret.signing_key.secret_id
    admin_token           = google_secret_manager_secret.admin_token.secret_id
    privacy_service_token = google_secret_manager_secret.privacy_service_token.secret_id
    stripe_secret_key     = google_secret_manager_secret.stripe_secret_key.secret_id
    stripe_webhook_secret = google_secret_manager_secret.stripe_webhook_secret.secret_id
    openai_api_key        = google_secret_manager_secret.openai_api_key.secret_id
    anthropic_api_key     = google_secret_manager_secret.anthropic_api_key.secret_id
  }
}

locals {
  redis_auth_token = var.redis_auth_token != "" ? var.redis_auth_token : random_password.redis_auth_token.result
}
