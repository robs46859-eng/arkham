#!/bin/bash
# Robco Platform - Infrastructure Setup Script
# Verifies prerequisites and prepares environment for Terraform deployment

set -euo pipefail

echo "🔧 Robco Platform Infrastructure Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
success() { echo -e "${GREEN}✓${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
info() { echo "  $1"; }

# Check if gcloud is installed
check_gcloud() {
    info "Checking Google Cloud SDK..."
    if command -v gcloud &> /dev/null; then
        success "gcloud CLI is installed"
        GCLOUD_VERSION=$(gcloud version --format='value(core)' 2>/dev/null | head -1)
        info "Version: ${GCLOUD_VERSION:-unknown}"
    else
        error "gcloud CLI is not installed. Install from: https://cloud.google.com/sdk/docs/install"
    fi
}

# Check if terraform is installed
check_terraform() {
    info "Checking Terraform..."
    if command -v terraform &> /dev/null; then
        success "Terraform is installed"
        TF_VERSION=$(terraform version -json 2>/dev/null | jq -r '.terraform_version' || terraform version | head -1)
        info "Version: ${TF_VERSION}"
        
        # Check minimum version
        MIN_VERSION="1.5.0"
        if [[ "$(printf '%s\n' "$MIN_VERSION" "${TF_VERSION#v}")" | sort -V | head -n1 != "$MIN_VERSION" ]]; then
            warning "Terraform version should be >= ${MIN_VERSION}"
        fi
    else
        error "Terraform is not installed. Install from: https://developer.hashicorp.com/terraform/install"
    fi
}

# Check if jq is installed (needed for parsing gcloud output)
check_jq() {
    info "Checking jq..."
    if command -v jq &> /dev/null; then
        success "jq is installed"
    else
        warning "jq is not installed. Some features may not work properly."
        info "Install with: sudo apt-get install jq (Ubuntu/Debian) or brew install jq (macOS)"
    fi
}

# Check gcloud authentication
check_auth() {
    info "Checking Google Cloud authentication..."
    if gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | grep -q .; then
        ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')
        success "Authenticated as: ${ACCOUNT}"
    else
        error "Not authenticated with Google Cloud. Run: gcloud auth login"
    fi
}

# Check project configuration
check_project() {
    info "Checking project configuration..."
    PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
    
    if [[ -z "${PROJECT_ID}" ]]; then
        error "No project configured. Set with: gcloud config set project YOUR_PROJECT_ID"
    fi
    
    success "Project: ${PROJECT_ID}"
    
    # Verify project exists
    if ! gcloud projects describe "${PROJECT_ID}" &>/dev/null; then
        error "Project '${PROJECT_ID}' does not exist or you don't have access"
    fi
    success "Project is accessible"
}

# Check required APIs
check_apis() {
    info "Checking required APIs..."
    
    APIS=(
        "compute.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "secretmanager.googleapis.com"
        "artifactregistry.googleapis.com"
        "storage.googleapis.com"
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "servicenetworking.googleapis.com"
        "iam.googleapis.com"
    )
    
    MISSING_APIS=()
    
    for api in "${APIS[@]}"; do
        if ! gcloud services list --enabled --filter="name:${api}" --format='value(name)' | grep -q "${api}"; then
            MISSING_APIS+=("${api}")
        fi
    done
    
    if [[ ${#MISSING_APIS[@]} -eq 0 ]]; then
        success "All required APIs are enabled"
    else
        warning "Missing APIs (will be enabled by Terraform):"
        for api in "${MISSING_APIS[@]}"; do
            info "  - ${api}"
        done
        info "To enable manually, run:"
        info "  gcloud services enable ${MISSING_APIS[*]}"
    fi
}

# Check service account (optional)
check_service_account() {
    info "Checking service account..."
    
    SA_EMAIL=$(gcloud config get-value account 2>/dev/null)
    
    if [[ "${SA_EMAIL}" == *"iam.gserviceaccount.com"* ]]; then
        success "Using service account: ${SA_EMAIL}"
    else
        info "Using user account: ${SA_EMAIL}"
        warning "For production, consider using a dedicated service account"
    fi
}

# Check bucket for state
check_state_bucket() {
    info "Checking Terraform state bucket..."
    
    BUCKET_NAME="${PROJECT_ID}-tf-state"
    
    if gsutil ls "gs://${BUCKET_NAME}" &>/dev/null; then
        success "State bucket exists: gs://${BUCKET_NAME}"
    else
        warning "State bucket does not exist: gs://${BUCKET_NAME}"
        info "Create it with:"
        info "  gsutil mb -p ${PROJECT_ID} -l us-central1 gs://${BUCKET_NAME}"
        info "  gsutil versioning set on gs://${BUCKET_NAME}"
    fi
}

# Main execution
main() {
    echo ""
    check_gcloud
    check_terraform
    check_jq
    echo ""
    check_auth
    check_project
    check_service_account
    echo ""
    check_apis
    echo ""
    check_state_bucket
    echo ""
    
    echo "======================================"
    success "Setup verification complete!"
    echo ""
    echo "Next steps:"
    echo "1. If needed, create state bucket (see above)"
    echo "2. Navigate to infra/terraform directory"
    echo "3. Create terraform.tfvars with your configuration"
    echo "4. Run: terraform init -backend-config=\"bucket=${PROJECT_ID}-tf-state\""
    echo "5. Run: terraform plan -out=tfplan"
    echo "6. Run: terraform apply tfplan"
    echo ""
}

# Run main function
main "$@"
