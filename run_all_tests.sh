#!/bin/bash
#
# Script to run all the test scripts for the AI Recruiter Pro system
#

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "\n${BOLD}===========================================${NC}"
echo -e "${BOLD}    AI RECRUITER PRO SYSTEM TEST SUITE    ${NC}"
echo -e "${BOLD}===========================================${NC}\n"

# Function to run test and check result
run_test() {
  local test_name="$1"
  local script="$2"
  local verbose="$3"
  
  echo -e "${BOLD}Running ${test_name}...${NC}"
  
  if [ "$verbose" = "true" ]; then
    python3 "$script" -v
  else
    python3 "$script"
  fi
  
  local result=$?
  
  if [ $result -eq 0 ]; then
    echo -e "\n${GREEN}✓ ${test_name} PASSED${NC}\n"
    return 0
  else
    echo -e "\n${RED}✗ ${test_name} FAILED${NC}\n"
    return 1
  fi
}

# Check if tests should be run in verbose mode
VERBOSE=false
if [ "$1" = "-v" ] || [ "$1" = "--verbose" ]; then
  VERBOSE=true
  echo -e "${YELLOW}Running tests in verbose mode${NC}"
fi

# Initialize test results
PASSED=0
FAILED=0
TOTAL=0

# Create directory for test results
mkdir -p test_results

# Run all test scripts
echo -e "${BOLD}Test 1: Complete System E2E Test${NC}"
if run_test "System E2E Test" "test_system_e2e.py" "$VERBOSE"; then
  PASSED=$((PASSED+1))
else
  FAILED=$((FAILED+1))
fi
TOTAL=$((TOTAL+1))

echo -e "${BOLD}Test 2: Resume Upload and Matching Test${NC}"
if run_test "Resume Upload Test" "test_resume_system.py" "$VERBOSE"; then
  PASSED=$((PASSED+1))
else
  FAILED=$((FAILED+1))
fi
TOTAL=$((TOTAL+1))

echo -e "${BOLD}Test 3: Phone Number Matching Test${NC}"
if run_test "Phone Matching Test" "test_phone_matching.py" "$VERBOSE"; then
  PASSED=$((PASSED+1))
else
  FAILED=$((FAILED+1))
fi
TOTAL=$((TOTAL+1))

echo -e "${BOLD}Test 4: OpenAI Integration Test${NC}"
if run_test "OpenAI Integration Test" "test_openai_integration.py" "$VERBOSE"; then
  PASSED=$((PASSED+1))
else
  FAILED=$((FAILED+1))
fi
TOTAL=$((TOTAL+1))

# Print summary
echo -e "\n${BOLD}===========================================${NC}"
echo -e "${BOLD}            TEST SUMMARY                 ${NC}"
echo -e "${BOLD}===========================================${NC}"
echo -e "${GREEN}PASSED: $PASSED${NC}"
echo -e "${RED}FAILED: $FAILED${NC}"
echo -e "${BOLD}TOTAL: $TOTAL${NC}"

# Calculate percentage
PERCENTAGE=$((PASSED * 100 / TOTAL))
echo -e "${BOLD}SUCCESS RATE: ${PERCENTAGE}%${NC}"

# Final verdict
if [ $PERCENTAGE -eq 100 ]; then
  echo -e "\n${GREEN}${BOLD}✓✓✓ ALL TESTS PASSED! SYSTEM IS FULLY OPERATIONAL ✓✓✓${NC}"
  exit 0
elif [ $PERCENTAGE -ge 75 ]; then
  echo -e "\n${YELLOW}${BOLD}⚠ MOST TESTS PASSED! SYSTEM IS MOSTLY OPERATIONAL ⚠${NC}"
  exit 1
else
  echo -e "\n${RED}${BOLD}✗✗✗ SEVERAL TESTS FAILED! SYSTEM NEEDS ATTENTION ✗✗✗${NC}"
  exit 2
fi