# Robco Platform - Terraform Variables

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region (e.g., us-central1)"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production", "development"], var.environment)
    error_message = "Environment must be staging, production, or development."
  }
}

# Database Configuration
variable "database_name" {
  description = "Cloud SQL PostgreSQL database name"
  type        = string
  default     = "robco_db"
}

variable "database_user" {
  description = "Cloud SQL PostgreSQL master username"
  type        = string
  default     = "robco"
}

variable "database_password" {
  description = "Cloud SQL PostgreSQL master password"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.database_password) >= 16
    error_message = "Database password must be at least 16 characters for security."
  }
}

variable "database_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-custom-2-4096" # 2 vCPU, 4GB RAM
  
  validation {
    condition     = can(regex("^db-", var.database_tier))
    error_message = "Database tier must start with 'db-'."
  }
}

variable "enable_ha" {
  description = "Enable high availability for Cloud SQL"
  type        = bool
  default     = false
}

# Redis Configuration
variable "redis_tier" {
  description = "Memorystore Redis tier (BASIC, STANDARD)"
  type        = string
  default     = "BASIC"
  
  validation {
    condition     = contains(["BASIC", "STANDARD"], var.redis_tier)
    error_message = "Redis tier must be BASIC or STANDARD."
  }
}

variable "redis_memory_size_gb" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 1
  
  validation {
    condition     = var.redis_memory_size_gb >= 1 && var.redis_memory_size_gb <= 50
    error_message = "Redis memory size must be between 1 and 50 GB."
  }
}

# Secrets
variable "signing_key" {
  description = "JWT signing key for gateway authentication"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.signing_key) >= 32
    error_message = "Signing key must be at least 32 characters."
  }
}

variable "privacy_service_token" {
  description = "Service token for privacy service authentication"
  type        = string
  sensitive   = true
  default     = ""
}

variable "admin_token" {
  description = "Static admin token for /v1/tenants/* routes"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.admin_token) >= 32
    error_message = "Admin token must be at least 32 characters."
  }
}

# Stripe
variable "stripe_secret_key" {
  description = "Stripe secret key (sk_live_... or sk_test_...)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_webhook_secret" {
  description = "Stripe webhook signing secret (whsec_...)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_price_id" {
  description = "Stripe Price ID for the subscription product (price_...)"
  type        = string
  default     = ""
}

variable "stripe_success_url" {
  description = "URL Stripe redirects to after successful checkout"
  type        = string
  default     = "https://your-app.example.com/billing/success"
}

variable "stripe_cancel_url" {
  description = "URL Stripe redirects to on checkout cancellation"
  type        = string
  default     = "https://your-app.example.com/billing/cancel"
}

variable "stripe_portal_return_url" {
  description = "URL Stripe redirects to after customer portal session"
  type        = string
  default     = "https://your-app.example.com/billing"
}

variable "redis_auth_token" {
  description = "Auth token for Memorystore Redis"
  type        = string
  sensitive   = true
  default     = ""
}

# Storage Configuration
variable "storage_bucket_name" {
  description = "GCS bucket name for BIM files and artifacts"
  type        = string
  default     = ""
}

variable "enable_gcs" {
  description = "Enable GCS for object storage"
  type        = bool
  default     = true
}

# Cloud Run Configuration
variable "enable_cloud_run" {
  description = "Enable Cloud Run deployment"
  type        = bool
  default     = true
}

variable "cloud_run_region" {
  description = "Cloud Run region"
  type        = string
  default     = "us-central1"
}

variable "cloud_run_min_instances" {
  description = "Minimum instances for Cloud Run services (0 for cold start allowed)"
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum instances for Cloud Run services"
  type        = number
  default     = 10
}

# Artifact Registry
variable "artifact_registry_name" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "robco-containers"
}

# Networking
variable "vpc_name" {
  description = "VPC network name"
  type        = string
  default     = "robco-vpc"
}

variable "private_services_access_cidr" {
  description = "CIDR range for private services access"
  type        = string
  default     = "192.168.0.0/24"
}
