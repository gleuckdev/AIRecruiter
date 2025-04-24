#!/usr/bin/env python3
"""
Test script specifically for phone number matching in the AI Recruiter Pro system.
This script tests various phone number formats to ensure the matching logic works correctly.
"""

import os
import sys
import time
import json
import requests
import random
from datetime import datetime

# Base URL for the application
BASE_URL = "http://localhost:5000"

# Test credentials for the demo admin account
TEST_RECRUITER = {
    "email": "demo@example.com",
    os.getenv("ADMIN_PASSWORD"): "os.getenv("TEST_PASSWORD")"
}

# Test phone number variations
PHONE_TEST_CASES = [
    {
        "case": "Original Format",
        "name": "Phone Test User",
        "email": "",
        "phone": "555-123-4567",
        "resume_text": """
        Phone Test User
        Software Engineer
        555-123-4567
        
        Experience:
        Software Engineer, Test Company, 2020-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2020
        """
    },
    {
        "case": "Different Format (dots)",
        "name": "Different Format User",
        "email": "",
        "phone": "555.123.4567",
        "resume_text": """
        Different Format User
        Software Engineer
        555.123.4567
        
        Experience:
        Software Engineer, Test Company, 2020-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2020
        """
    },
    {
        "case": "No Separators",
        "name": "No Separators User",
        "email": "",
        "phone": "5551234567",
        "resume_text": """
        No Separators User
        Software Engineer
        5551234567
        
        Experience:
        Software Engineer, Test Company, 2021-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2021
        """
    },
    {
        "case": "With Parentheses",
        "name": "Parentheses User",
        "email": "",
        "phone": "(555) 123-4567",
        "resume_text": """
        Parentheses User
        Software Engineer
        (555) 123-4567
        
        Experience:
        Software Engineer, Test Company, 2022-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2022
        """
    },
    {
        "case": "With Country Code",
        "name": "Country Code User",
        "email": "",
        "phone": "+1 555-123-4567",
        "resume_text": """
        Country Code User
        Software Engineer
        +1 555-123-4567
        
        Experience:
        Software Engineer, Test Company, 2022-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2022
        """
    },
    {
        "case": "Different Phone Number",
        "name": "Different Phone User",
        "email": "",
        "phone": "999-888-7777",
        "resume_text": """
        Different Phone User
        Software Engineer
        999-888-7777
        
        Experience:
        Software Engineer, Test Company, 2021-2023
        
        Education:
        Bachelor's in Computer Science, Test University, 2021
        """
    }
]


class PhoneMatchingTester:
    """Test phone number matching in the AI Recruiter Pro system."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.session = requests.Session()
        self.access_token = None
        self.upload_results = []
        self.candidate_ids = []

    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def login(self):
        """Log in as a recruiter and get an access token."""
        self.log(f"Logging in as {TEST_RECRUITER['email']}...")
        
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_RECRUITER
        )
        
        if response.status_code == 200:
            # The session cookies are automatically handled by the requests.Session object
            # No need to manually set the cookie as it's done by the server
            self.log("Login successful!")
            return True
        else:
            self.log(f"Login failed with status code: {response.status_code}")
            self.log(f"Response: {response.text}")
            return False

    def upload_resume(self, resume_data):
        """Upload a resume to test phone matching."""
        self.log(f"Uploading resume for {resume_data['case']}: {resume_data['phone']}...")
        
        payload = {
            "name": resume_data["name"],
            "email": resume_data.get("email", ""),
            "phone": resume_data.get("phone", ""),
            "resume_text": resume_data["resume_text"],
            "is_direct_upload": "true"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/resume/text",
            json=payload
        )
        
        result = {
            "case": resume_data["case"],
            "name": resume_data["name"],
            "phone": resume_data["phone"],
            "status_code": response.status_code,
            "response": None
        }
        
        try:
            result["response"] = response.json()
            if "candidate_id" in result["response"]:
                self.candidate_ids.append(result["response"]["candidate_id"])
        except:
            result["response"] = response.text
        
        self.upload_results.append(result)
        
        if response.status_code in (200, 201, 202):
            self.log(f"Resume upload successful!")
            if "is_update" in result["response"]:
                if result["response"]["is_update"]:
                    self.log(f"Resume was an update to an existing record.")
                else:
                    self.log(f"Resume was a new record.")
            return True
        else:
            self.log(f"Resume upload failed with status code: {response.status_code}")
            return False

    def run_tests(self):
        """Run the phone number matching tests."""
        print("\n===== PHONE NUMBER MATCHING TEST =====\n")
        
        # Step 1: Login
        if not self.login():
            print("❌ Login failed. Aborting tests.")
            return False
        print("✅ Login successful")
        
        # Step 2: Upload the first phone number
        first_case = PHONE_TEST_CASES[0]
        if self.upload_resume(first_case):
            print(f"✅ First phone number ({first_case['phone']}) uploaded successfully")
        else:
            print(f"❌ First phone number upload failed")
            return False
        
        # Wait a bit to ensure processing
        time.sleep(2)
        
        # Step 3: Upload the variations to test matching
        print("\n----- Testing Phone Number Variations -----")
        
        matched_count = 0
        for idx, test_case in enumerate(PHONE_TEST_CASES[1:], 2):
            print(f"\nTesting Case #{idx}: {test_case['case']}")
            if self.upload_resume(test_case):
                result = self.upload_results[-1]
                is_update = result["response"].get("is_update", False)
                
                # For the different phone number, it should be a new record
                if test_case["case"] == "Different Phone Number":
                    if not is_update:
                        print(f"✅ Different phone number correctly created as a new record")
                    else:
                        print(f"❌ Different phone number incorrectly matched as an update")
                else:
                    # For variations of the same phone number, it should match
                    if is_update:
                        matched_count += 1
                        print(f"✅ {test_case['case']} correctly matched with original")
                    else:
                        print(f"❌ {test_case['case']} incorrectly created as a new record")
            else:
                print(f"❌ Upload failed for {test_case['case']}")
            
            # Wait a bit between uploads
            time.sleep(1)
        
        # Analysis of results
        print("\n----- Test Results Analysis -----")
        expected_matches = len(PHONE_TEST_CASES) - 2  # All except first and different phone
        print(f"Successfully matched: {matched_count} out of {expected_matches} expected matches")
        
        if matched_count == expected_matches:
            print("\n✅ All phone number variations were correctly matched!")
        else:
            print(f"\n❌ Some phone number variations were not matched correctly.")
        
        print("\n===== TEST COMPLETE =====")
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test phone number matching in the AI Recruiter Pro system")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    tester = PhoneMatchingTester(verbose=args.verbose)
    tester.run_tests()