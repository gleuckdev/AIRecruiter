# AI Recruiter Pro Testing Suite

This directory contains a comprehensive testing suite for the AI Recruiter Pro system. These tests validate all major components of the application, including authentication, job management, candidate processing, matching algorithms, and OpenAI integrations.

## Test Scripts Overview

1. **System E2E Test** (`test_system_e2e.py`): 
   - A complete end-to-end test of all system components
   - Tests authentication, job management, candidate processing, matching, job tokens, sharing system, and OpenAI integrations
   - Provides a detailed summary of test results

2. **Resume Upload Test** (`test_resume_system.py`):
   - Specifically tests the resume upload functionality
   - Validates duplicate detection and resume quality comparison
   - Tests both API-based and form-based uploads

3. **Phone Matching Test** (`test_phone_matching.py`):
   - Tests the phone number matching logic for duplicate detection
   - Validates that different phone formats are properly normalized and matched

4. **OpenAI Integration Test** (`test_openai_integration.py`):
   - Tests the OpenAI integration for resume analysis, persona generation, and matching
   - Validates that embeddings and semantic matching are working correctly

## Running the Tests

### Prerequisites

- The AI Recruiter Pro system must be running locally on port 5000
- The `DEMO_PASSWORD` environment variable should be set to the admin password
- The `OPENAI_API_KEY` environment variable must be configured correctly
- Python 3.10+ with requests package installed

### Run All Tests

To run all tests at once, use the provided shell script:

```bash
./run_all_tests.sh
```

This will execute all test scripts in sequence and provide a summary report.

### Verbose Mode

To run tests with detailed logging, use the `-v` or `--verbose` flag:

```bash
./run_all_tests.sh -v
```

### Run Individual Tests

You can also run individual test scripts directly:

```bash
# System E2E Test
python3 test_system_e2e.py

# Resume Upload Test
python3 test_resume_system.py

# Phone Matching Test
python3 test_phone_matching.py

# OpenAI Integration Test
python3 test_openai_integration.py
```

Add the `-v` flag for verbose output:

```bash
python3 test_system_e2e.py -v
```

## Test Results Interpretation

Each test script will output a detailed report of its findings. The key indicators are:

- ✅ **PASS**: The test was successful
- ⚠️ **WARNING**: The test passed with some concerns
- ❌ **FAIL**: The test failed

The run_all_tests.sh script will provide an overall success rate percentage at the end of all tests.

## Troubleshooting

If tests are failing, check the following:

1. **Server Not Running**: Ensure the AI Recruiter Pro server is running on port 5000
2. **Authentication Issues**: Verify the DEMO_PASSWORD environment variable is set correctly
3. **OpenAI API Issues**: Check that the OPENAI_API_KEY is valid and has sufficient credits
4. **Network Issues**: Make sure there are no network connectivity problems
5. **Response Format Changes**: If API response formats have changed, the tests may need to be updated

For detailed error information, run the tests in verbose mode with the `-v` flag.

## Extending the Tests

To add new tests or modify existing ones:

1. Follow the pattern in the existing test files
2. Add new test functions to the appropriate classes
3. Update the `run_tests()` function to include your new tests
4. If adding a completely new test file, update `run_all_tests.sh` to include it

## Contact

For questions or issues with the testing suite, contact the development team.