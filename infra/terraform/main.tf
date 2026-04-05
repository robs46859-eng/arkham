# Robco Platform - Google Cloud Infrastructure
# Production-ready infrastructure for multi-service AI platform

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "gcs" {
    # Bucket will be specified via CLI or variables
    # terraform init -backend-config="bucket=robco-tf-state" -backend-config="prefix=prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Common locals for tagging and organization
locals {
  common_tags = {
    environment = var.environment
    project     = var.project_id
    managed_by  = "terraform"
    application = "robco-platform"
  }
  
  service_accounts = [
    "gateway",
    "core",
    "privacy",
    "orchestration",
    "bim_ingestion",
    "billing"
  ]
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "servicenetworking.googleapis.com",
    "iam.googleapis.com"
  ])
  
  service            = each.value
  disable_on_destroy = false
}
