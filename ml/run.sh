#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Running checks for ml package...${NC}"

cd "$(dirname "$0")"
cd .. # Move to top level

echo "Linting ml..."
ruff check ml ml/tests
echo "Formatting ml..."
ruff format --check ml ml/tests
echo "Type checking ml..."
mypy ml --ignore-missing-imports
echo "Testing ml with 100% coverage..."
pytest --cov=ml --cov-fail-under=100 ml/tests/

echo -e "${GREEN}ML package checks passed!${NC}"
