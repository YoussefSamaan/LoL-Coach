#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Running checks for core package...${NC}"

cd "$(dirname "$0")"
cd .. # Go to project root

echo "Linting core..."
ruff check core core/tests
echo "Formatting core..."
ruff format --check core core/tests
echo "Type checking core..."
mypy core --ignore-missing-imports
echo "Testing core with 100% coverage..."
pytest --cov=core --cov-fail-under=100 core/tests/

echo -e "${GREEN}Core package checks passed!${NC}"
