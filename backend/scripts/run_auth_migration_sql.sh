#!/bin/bash

# Simple SQL migration runner for authentication tables
# This script runs the SQL migration directly without Python dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if database URL is provided
if [ -z "$1" ]; then
    print_error "Usage: $0 <database_url>"
    print_status "Example: $0 postgresql://user:pass@host:port/database"
    exit 1
fi

DATABASE_URL="$1"
MIGRATION_FILE="migrations/001_add_authentication_tables.sql"

print_status "🚀 Starting authentication tables migration"
print_status "Database: ${DATABASE_URL}"

# Check if migration file exists
if [ ! -f "$MIGRATION_FILE" ]; then
    print_error "Migration file not found: $MIGRATION_FILE"
    exit 1
fi

print_status "📝 Running migration: $MIGRATION_FILE"

# Run the SQL migration
if psql "$DATABASE_URL" -f "$MIGRATION_FILE"; then
    print_success "✅ Migration completed successfully!"
    print_status "Authentication tables have been created:"
    print_status "  - users"
    print_status "  - refresh_tokens"
    print_status "  - api_keys"
    print_status "  - audit_logs"
    print_status "  - pipeline_jobs (updated with user_id columns)"
else
    print_error "❌ Migration failed!"
    exit 1
fi

print_success "🎉 Authentication system is ready for deployment!"
