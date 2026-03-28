#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Running checks for ingest package...${NC}"

cd "$(dirname "$0")"
cd .. # Go to project root

echo "Linting ingest..."
ruff check ingest ingest/tests
echo "Formatting ingest..."
ruff format --check ingest ingest/tests
echo "Type checking ingest..."
mypy ingest --ignore-missing-imports
echo "Testing ingest with 100% coverage..."
pytest --cov=ingest --cov-fail-under=100 ingest/tests/

echo -e "${GREEN}Ingest package checks passed!${NC}"
