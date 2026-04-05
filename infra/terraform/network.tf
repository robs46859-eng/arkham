# Robco Platform - Network Configuration
# VPC with private services access for Cloud SQL and Memorystore

resource "google_compute_network" "vpc" {
  name                            = var.vpc_name
  auto_create_subnetworks         = false
  routing_mode                    = "REGIONAL"
  project                         = var.project_id
  
  tags = ["robco-services"]
}

resource "google_compute_subnetwork" "main" {
  name                     = "${var.vpc_name}-subnet"
  ip_cidr_range            = "10.0.0.0/20"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Private Services Access for Cloud SQL and Memorystore
resource "google_compute_global_address" "private_services" {
  name          = "${var.vpc_name}-psa"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = google_compute_network.vpc.id
  ip_version    = "IPV4"
  
  labels = local.common_tags
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
  
  depends_on = [google_project_service.required_apis]
}

# Serverless VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  count         = var.enable_cloud_run ? 1 : 0
  name          = "${var.vpc_name}-connector"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.8.0.0/28"
  
  min_instances = 2
  max_instances = 10
  
  depends_on = [google_project_service.required_apis]
}

# Firewall rules for internal service communication
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.vpc_name}-allow-internal"
  network = google_compute_network.vpc.name
  project = var.project_id
  
  allow {
    protocol = "tcp"
    ports    = ["3000", "3010", "8000", "8001", "8002", "8003"]
  }
  
  allow {
    protocol = "icmp"
  }
  
  source_ranges = ["10.0.0.0/20"]
  
  target_tags = ["robco-services"]
}

# Firewall rule for Cloud SQL private IP access
resource "google_compute_firewall" "allow_sql" {
  name    = "${var.vpc_name}-allow-sql"
  network = google_compute_network.vpc.name
  project = var.project_id
  
  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }
  
  direction     = "INGRESS"
  source_ranges = ["10.0.0.0/20"]
  
  target_tags = ["robco-services"]
}
