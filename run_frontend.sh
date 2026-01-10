#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

MODE=$1

setup_and_test() {
    echo -e "${GREEN}Starting Frontend Setup...${NC}"
    
    cd frontend

    # 1. Install dependencies
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies..."
        npm install
    fi

    # 2. Read configuration from root config.yml (using python as helper like backend script)
    local CONFIG_PATH="../config.yml"
    if [ -f "$CONFIG_PATH" ]; then
        COVERAGE_THRESHOLD=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH')).get('frontend', {}).get('coverage_threshold', 100))" 2>/dev/null || echo "100")
        RUN_LINT=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH')).get('frontend', {}).get('checks', {}).get('lint', True))" 2>/dev/null || echo "True")
        RUN_TYPE=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH')).get('frontend', {}).get('checks', {}).get('type_check', True))" 2>/dev/null || echo "True")
        RUN_TEST=$(python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_PATH')).get('frontend', {}).get('checks', {}).get('test', True))" 2>/dev/null || echo "True")
    else
        COVERAGE_THRESHOLD="100"
        RUN_LINT="True"
        RUN_TYPE="True"
        RUN_TEST="True"
    fi

    # 3. Type Checking (TSC)
    if [ "$RUN_TYPE" == "True" ]; then
        echo "Running Type Check (tsc)..."
        if ! npm run build; then
            echo -e "${RED}Type checking failed (via build).${NC}"
            exit 1
        fi
    else
        echo "Skipping Type Check..."
    fi

    # 4. Linting (ESLint)
    if [ "$RUN_LINT" == "True" ]; then
        echo "Running Lint Check..."
        if ! npm run lint; then
            echo -e "${RED}Linting failed. Run './run_frontend.sh fix' to attempt automatic fixes.${NC}"
            exit 1
        fi
    else
        echo "Skipping Lint Check..."
    fi
 
    # 5. Tests (Vitest) - Only if test script exists
    if [ "$RUN_TEST" == "True" ]; then
        if npm run | grep -q "test"; then
             echo "Running tests (Threshold: ${COVERAGE_THRESHOLD}%)..."
             # Execute test:coverage if available, otherwise fallback to test but we want coverage
             # Assuming we added test:coverage as per plan
             if ! npm run test:coverage -- --coverage.thresholds.global.lines=${COVERAGE_THRESHOLD} --coverage.thresholds.global.functions=${COVERAGE_THRESHOLD} --coverage.thresholds.global.branches=${COVERAGE_THRESHOLD} --coverage.thresholds.global.statements=${COVERAGE_THRESHOLD}; then
                 echo -e "${RED}Frontend tests or coverage check failed.${NC}"
                 exit 1
             fi
        else
            echo "No test script found in package.json. Skipping Integration Tests."
        fi
    else
        echo "Skipping Tests..."
    fi

    cd ..
}

fix_code() {
    echo -e "${BLUE}Running Auto-Fixers...${NC}"
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    
    echo "Fixing linting issues..."
    npm run lint -- --fix || true
    echo -e "${GREEN}Lint fixes applied!${NC}"
    cd ..
}


run_server() {
    echo -e "${BLUE}Starting Frontend Code...${NC}"
    
    cd frontend 2>/dev/null || true
    if [ ! -d "node_modules" ]; then
        echo "Dependencies not found. Running setup..."
        cd ..
        setup_and_test
        cd frontend
    fi

    # Read port from config.yml
    if [ -f "../config.yml" ]; then
        PORT=$(python3 -c "import yaml; print(yaml.safe_load(open('../config.yml')).get('frontend', {}).get('port', 3000))" 2>/dev/null || echo "3000")
    else
        PORT="3000"
    fi

    echo -e "${GREEN}Frontend running on http://localhost:${PORT}${NC}"
    npm run dev -- --port ${PORT}
}


if [ "$MODE" == "test" ]; then
    setup_and_test
elif [ "$MODE" == "fix" ]; then
    fix_code
elif [ "$MODE" == "run" ]; then
    run_server
else
    setup_and_test
    run_server
fi
