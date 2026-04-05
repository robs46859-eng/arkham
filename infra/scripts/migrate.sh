#!/bin/bash
# Robco Platform - Database Migration Script
# Runs Alembic migrations against Cloud SQL or local database

set -euo pipefail

echo "🗄️  Robco Platform Database Migration"
echo "====================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo "  $1"; }

# Get DATABASE_URL from environment or Secret Manager
get_database_url() {
    if [[ -n "${DATABASE_URL:-}" ]]; then
        info "Using DATABASE_URL from environment"
        echo "${DATABASE_URL}"
        return
    fi
    
    # Try to get from Secret Manager
    PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
    ENVIRONMENT=${APP_ENV:-development}
    
    if [[ -n "${PROJECT_ID}" && "${ENVIRONMENT}" != "development" ]]; then
        info "Attempting to retrieve from Secret Manager..."
        SECRET_NAME="${ENVIRONMENT}-database-url"
        
        if DATABASE_URL=$(gcloud secrets versions access latest \
            --secret="${SECRET_NAME}" \
            --project="${PROJECT_ID}" 2>/dev/null); then
            success "Retrieved DATABASE_URL from Secret Manager"
            echo "${DATABASE_URL}"
            return
        else
            warning "Could not retrieve from Secret Manager (secret may not exist yet)"
        fi
    fi
    
    # Fallback to local development
    info "Falling back to local development database"
    echo "postgresql://robco:password@localhost:5432/robco_db"
}

# Check if psql is available
check_psql() {
    if command -v psql &> /dev/null; then
        success "psql is installed"
        return 0
    else
        warning "psql is not installed. Cannot verify database connectivity."
        return 1
    fi
}

# Test database connection
test_connection() {
    local db_url="$1"
    
    info "Testing database connection..."
    
    if ! check_psql; then
        info "Skipping connection test (psql not available)"
        return 0
    fi
    
    # Extract connection details from URL
    # This is a simplified parser - works for standard PostgreSQL URLs
    if [[ "${db_url}" =~ postgresql://([^:]+):([^@]+)@([^:/]+)(:[0-9]+)?/([^?]+) ]]; then
        DB_USER="${BASH_REMATCH[1]}"
        DB_PASS="${BASH_REMATCH[2]}"
        DB_HOST="${BASH_REMATCH[3]}"
        DB_PORT="${BASH_REMATCH[4]:-5432}"
        DB_NAME="${BASH_REMATCH[5]}"
        
        # Remove colon from port
        DB_PORT="${DB_PORT#:}"
        
        info "Connecting to ${DB_HOST}:${DB_PORT}/${DB_NAME} as ${DB_USER}"
        
        if PGPASSWORD="${DB_PASS}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" &>/dev/null; then
            success "Database connection successful"
            return 0
        else
            error "Failed to connect to database"
        fi
    else
        warning "Could not parse DATABASE_URL for connection test"
    fi
}

# Run Alembic migrations
run_migrations() {
    local db_url="$1"
    local action="${1:-upgrade}"
    
    info "Running Alembic migrations..."
    
    # Export DATABASE_URL for Alembic
    export DATABASE_URL="${db_url}"
    
    # Check if alembic is installed
    if ! command -v alembic &> /dev/null; then
        error "Alembic is not installed. Install with: pip install alembic"
    fi
    
    # Navigate to workspace root
    cd "$(dirname "$0")/../.."
    
    # Show current migration status
    info "Current migration status:"
    alembic current 2>&1 | sed 's/^/  /' || true
    
    echo ""
    
    # Run upgrade
    info "Running: alembic upgrade head"
    if alembic upgrade head; then
        success "Migrations completed successfully"
    else
        error "Migration failed"
    fi
    
    # Show new status
    echo ""
    info "New migration status:"
    alembic current 2>&1 | sed 's/^/  /' || true
}

# Show migration history
show_history() {
    info "Migration history:"
    alembic history --verbose 2>&1 | sed 's/^/  /' || true
}

# Main execution
main() {
    ACTION="${1:-upgrade}"
    
    case "${ACTION}" in
        upgrade)
            DB_URL=$(get_database_url)
            test_connection "${DB_URL}"
            run_migrations "${DB_URL}"
            ;;
        downgrade)
            DB_URL=$(get_database_url)
            run_migrations "${DB_URL}" "downgrade"
            ;;
        history)
            show_history
            ;;
        status)
            DB_URL=$(get_database_url)
            export DATABASE_URL="${DB_URL}"
            alembic current
            ;;
        *)
            echo "Usage: $0 {upgrade|downgrade|history|status}"
            echo ""
            echo "Commands:"
            echo "  upgrade   - Run all pending migrations (default)"
            echo "  downgrade - Downgrade one migration"
            echo "  history   - Show migration history"
            echo "  status    - Show current migration version"
            echo ""
            echo "Environment variables:"
            echo "  DATABASE_URL     - Database connection string"
            echo "  PROJECT_ID       - GCP project ID (for Secret Manager)"
            echo "  APP_ENV          - Environment name (development/staging/production)"
            exit 1
            ;;
    esac
}

main "$@"
