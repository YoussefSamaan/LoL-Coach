#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Running checks for backend package...${NC}"

cd "$(dirname "$0")"
cd .. # Go to project root

echo "Linting backend..."
ruff check backend backend/tests
echo "Formatting backend..."
ruff format --check backend backend/tests
echo "Type checking backend..."
mypy backend --ignore-missing-imports
echo "Testing backend with 100% coverage..."
pytest --cov=backend --cov-fail-under=100 backend/tests/

echo -e "${GREEN}Backend package checks passed!${NC}"
