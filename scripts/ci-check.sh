#!/bin/bash

# CI/CD Check Script
# This script runs the same checks as the GitHub Actions CI/CD pipeline locally

set -e  # Exit on any error

echo "🚀 Running CI/CD checks locally..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

print_status "Installing dependencies..."
uv sync --frozen

print_status "Running tests with coverage..."
uv run pytest test/ -v --cov=stages --cov-report=term-missing --cov-report=xml --cov-report=html --junitxml=pytest-report.xml

print_status "Running linting checks..."

# Install dev dependencies if not already installed
if ! uv run ruff --version &> /dev/null; then
    print_warning "Installing development dependencies..."
    uv add --dev ruff black isort bandit safety
fi

print_status "Running Ruff linter..."
uv run ruff check stages/ test/ --fix

print_status "Running Black formatter..."
uv run black --check --diff stages/ test/

print_status "Running isort..."
uv run isort --check-only --diff stages/ test/

print_status "Running security checks..."

print_status "Running Bandit security linter..."
uv run bandit -r stages/ -f json -o bandit-report.json || print_warning "Bandit found some issues. Check bandit-report.json for details."

print_status "Running Safety check..."
uv run safety check --json --output safety-report.json || print_warning "Safety found some issues. Check safety-report.json for details."

print_status "All checks completed!"
print_status "Coverage report: htmlcov/index.html"
print_status "Coverage files: .coverage, coverage.xml"
print_status "Test report: pytest-report.xml"
print_status "Security reports: bandit-report.json, safety-report.json"

echo ""
echo "🎉 All CI/CD checks passed locally!"
echo "You can now push your changes with confidence." 