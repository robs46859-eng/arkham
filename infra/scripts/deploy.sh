#!/bin/bash
# Robco Platform - Deployment Script
# Builds Docker images, pushes to Artifact Registry, and deploys to Cloud Run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="${PYTHON_FALLBACK:-python3}"
fi

echo "🚀 Robco Platform Deployment"
echo "============================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
warning() { echo -e "${YELLOW}⚠${NC} $1"; }
info() { echo "  $1"; }

# Configuration
SERVICES=("gateway" "core" "privacy" "orchestration" "bim_ingestion" "billing")
PROJECT_ID="${PROJECT_ID:-}"
REGION=${REGION:-us-central1}
REGISTRY_NAME=${REGISTRY_NAME:-robco-containers}
TAG=${TAG:-latest}
if [[ "${TAG}" == "latest" ]]; then
    TAG="$(git -C "${REPO_ROOT}" rev-parse --short=12 HEAD)"
fi

# Validate prerequisites
validate_prerequisites() {
    info "Validating prerequisites..."
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI is not installed"
    fi
    success "gcloud CLI found"
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
    fi
    success "Docker found"
    
    # Check project
    if [[ -z "${PROJECT_ID}" ]]; then
        PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
    fi
    if [[ -z "${PROJECT_ID}" ]]; then
        error "PROJECT_ID not set and no default project configured"
    fi
    success "Project: ${PROJECT_ID}"
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q .; then
        error "Not authenticated with gcloud"
    fi
    success "Authenticated with gcloud"
}

# Authenticate Docker with Artifact Registry
auth_docker() {
    info "Authenticating Docker with Artifact Registry..."
    
    if gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet 2>/dev/null; then
        success "Docker authenticated"
    else
        error "Failed to authenticate Docker"
    fi
}

run_migrations() {
    info "Running Alembic migrations..."

    if [[ -z "${DATABASE_URL:-}" ]]; then
        error "DATABASE_URL must be set to run migrations"
    fi

    (
        cd "${REPO_ROOT}"
        DATABASE_URL="${DATABASE_URL}" "${PYTHON_BIN}" -m alembic upgrade head
    )
    success "Migrations applied"
}

run_smoke_tests() {
    info "Running smoke tests..."
    (
        cd "${REPO_ROOT}"
        "${PYTHON_BIN}" -m pytest -m smoke
    )
    success "Smoke tests passed"
}

# Build a single service
build_service() {
    local service="$1"
    local service_dir="${REPO_ROOT}/services/${service}"
    local image_name="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_NAME}/${service}:${TAG}"
    
    if [[ ! -d "${service_dir}" ]]; then
        warning "Service directory not found: ${service_dir}"
        return 1
    fi
    
    info "Building ${service}..."
    
    if docker build -t "${image_name}" -f "${service_dir}/Dockerfile" "${REPO_ROOT}"; then
        success "Built ${service}"
        echo "${image_name}"
        return 0
    else
        error "Failed to build ${service}"
        return 1
    fi
}

# Push a single service
push_service() {
    local image_name="$1"
    local service=$(basename "$(dirname "${image_name}")")
    
    info "Pushing ${service}..."
    
    if docker push "${image_name}"; then
        success "Pushed ${service}"
        return 0
    else
        error "Failed to push ${service}"
        return 1
    fi
}

# Deploy service to Cloud Run
deploy_service() {
    local service="$1"
    local image_name="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REGISTRY_NAME}/${service}:${TAG}"
    
    info "Deploying ${service} to Cloud Run..."
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "robco-${service}" \
        --region "${REGION}" \
        --project "${PROJECT_ID}" \
        --format='value(status.url)' 2>/dev/null || echo "")
    
    if [[ -z "${SERVICE_URL}" ]]; then
        warning "Service robco-${service} not found. Skipping deployment."
        return 1
    fi
    
    # Update service with new image
    if gcloud run services update "robco-${service}" \
        --image "${image_name}" \
        --region "${REGION}" \
        --project "${PROJECT_ID}" \
        --quiet; then
        success "Deployed ${service}"
        info "URL: ${SERVICE_URL}"
        return 0
    else
        error "Failed to deploy ${service}"
        return 1
    fi
}

# Build all services
build_all() {
    local built_images=()
    
    echo ""
    info "Building all services..."
    echo ""
    
    for service in "${SERVICES[@]}"; do
        if image=$(build_service "${service}"); then
            built_images+=("${image}")
        fi
    done
    
    echo ""
    success "Build complete: ${#built_images[@]} services"
    
    # Return images as newline-separated string
    printf '%s\n' "${built_images[@]}"
}

# Push all services
push_all() {
    local images=("$@")
    
    echo ""
    info "Pushing all services..."
    echo ""
    
    for image in "${images[@]}"; do
        push_service "${image}"
    done
    
    echo ""
    success "Push complete: ${#images[@]} images"
}

# Deploy all services
deploy_all() {
    echo ""
    info "Deploying all services..."
    echo ""
    
    local deployed=0
    local failed=0
    
    for service in "${SERVICES[@]}"; do
        if deploy_service "${service}"; then
            ((deployed++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    success "Deployment complete: ${deployed} succeeded, ${failed} failed"
}

# Main execution
main() {
    ACTION="${1:-all}"
    
    case "${ACTION}" in
        build)
            validate_prerequisites
            build_all
            ;;
        push)
            validate_prerequisites
            auth_docker
            # Build first if no images provided
            if [[ $# -eq 1 ]]; then
                images=$(build_all)
                push_all ${images}
            else
                shift
                push_all "$@"
            fi
            ;;
        deploy)
            validate_prerequisites
            deploy_all
            ;;
        migrate)
            run_migrations
            ;;
        smoke)
            run_smoke_tests
            ;;
        all)
            validate_prerequisites
            auth_docker
            images=$(build_all)
            push_all ${images}
            run_migrations
            deploy_all
            run_smoke_tests
            ;;
        *)
            echo "Usage: $0 {build|push|deploy|migrate|smoke|all} [service...]"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker images for all services"
            echo "  push    - Build and push images to Artifact Registry"
            echo "  deploy  - Deploy services to Cloud Run"
            echo "  migrate - Run Alembic migrations against DATABASE_URL"
            echo "  smoke   - Run pytest smoke tests"
            echo "  all     - Build, push, and deploy (default)"
            echo ""
            echo "Environment variables:"
            echo "  PROJECT_ID     - GCP project ID (required)"
            echo "  REGION         - GCP region (default: us-central1)"
            echo "  REGISTRY_NAME  - Artifact Registry name (default: robco-containers)"
            echo "  TAG            - Docker image tag (default: current git SHA)"
            echo "  DATABASE_URL   - Required for migrate/all"
            echo ""
            echo "Examples:"
            echo "  $0 all                          # Full deployment"
            echo "  $0 build                        # Build only"
            echo "  $0 push gateway core privacy    # Push specific services"
            echo "  $0 deploy                       # Deploy only"
            exit 1
            ;;
    esac
}

main "$@"
