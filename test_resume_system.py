#!/usr/bin/env python3
"""
Comprehensive test script for the AI Recruiter Pro system.
This script tests resume upload, duplicate detection, and matching functionality
using real API calls to the running application.
"""

import os
import sys
import time
import json
import requests
import random
import argparse
from datetime import datetime

# Base URL for the application
BASE_URL = "http://localhost:5000"

# Test credentials for the demo admin account
TEST_RECRUITER = {
    "email": "demo@example.com",
    os.getenv("ADMIN_PASSWORD"): "os.getenv("TEST_PASSWORD")"
}

# Sample test resumes with varying qualities
SAMPLE_RESUMES = [
    {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "123-456-7890",
        "resume_text": """
        John Doe
        Software Engineer
        john.doe@example.com | 123-456-7890

        Experience:
        Senior Software Engineer, Tech Corp, 2018-2020
        - Led team of 5 developers
        - Implemented CI/CD pipeline
        - Used Python, JavaScript, Docker
        
        Software Engineer, StartupXYZ, 2015-2018
        - Developed backend services using Node.js
        - Improved database performance by 40%
        
        Education:
        Bachelor's in Computer Science, University of Technology, 2015
        """
    },
    {
        "name": "John Doe",  # Same name to test duplicate detection
        "email": "john.doe@example.com",  # Same email to test duplicate handling
        "phone": "123-456-7890",  # Same phone
        "resume_text": """
        John Doe
        Senior Software Engineer
        john.doe@example.com | 123-456-7890

        Experience:
        Principal Engineer, Tech Innovators, 2021-Present
        - Leading architecture for cloud migration
        - Managing team of 10 engineers
        - Technologies: Python, AWS, Kubernetes, Terraform
        
        Senior Software Engineer, Tech Corp, 2018-2020
        - Led team of 5 developers
        - Implemented CI/CD pipeline
        - Used Python, JavaScript, Docker
        
        Software Engineer, StartupXYZ, 2015-2018
        - Developed backend services using Node.js
        - Improved database performance by 40%
        
        Education:
        Bachelor's in Computer Science, University of Technology, 2015
        Master's in Software Engineering, Tech Institute, 2018
        """
    },
    {
        "name": "Jane Smith",
        "email": "jane.smith@example.com",
        "phone": "987-654-3210",
        "resume_text": """
        Jane Smith
        Data Scientist
        jane.smith@example.com | 987-654-3210

        Experience:
        Data Scientist, Analytics Inc, 2019-Present
        - Built machine learning models for customer segmentation
        - Reduced prediction error by 30%
        - Used Python, TensorFlow, scikit-learn
        
        Data Analyst, Data Corp, 2017-2019
        - Created dashboards and reports
        - Analyzed customer behavior
        
        Education:
        Master's in Data Science, State University, 2017
        Bachelor's in Statistics, State University, 2015
        """
    },
    {
        # No email to test matching by name/phone
        "name": "Michael Johnson",
        "phone": "555-123-4567",
        "resume_text": """
        Michael Johnson
        Product Manager
        555-123-4567

        Experience:
        Senior Product Manager, Product Co, 2018-Present
        - Led product development for SaaS platform
        - Increased user base by 200%
        
        Product Manager, Tech Solutions, 2015-2018
        - Managed agile development team
        - Conducted user research
        
        Education:
        MBA, Business School, 2015
        Bachelor's in Business, University, 2013
        """
    }
]

# Sample test jobs
SAMPLE_JOB = {
    "title": "Senior Software Engineer",
    "company": "Test Company",
    "location": "Remote",
    "description": """
    We're looking for a Senior Software Engineer with experience in Python and web development.
    The ideal candidate will have 3+ years of experience with modern web frameworks and cloud services.
    
    Requirements:
    - Strong experience with Python
    - Experience with web frameworks (Flask, Django)
    - Knowledge of cloud platforms (AWS, GCP, Azure)
    - Experience with databases and SQL
    - CI/CD experience
    
    Nice to have:
    - JavaScript/TypeScript experience
    - Docker and Kubernetes
    - Experience with machine learning
    """,
    "required_skills": ["Python", "Flask", "SQL", "AWS"],
    "preferred_skills": ["Docker", "Kubernetes", "Machine Learning", "TypeScript"]
}


class TestRunner:
    """Test runner for the AI Recruiter Pro system."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.session = requests.Session()
        self.access_token = None
        self.upload_results = []
        self.job_id = None
        self.candidates = []

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

    def create_test_job(self):
        """Create a test job for matching candidates."""
        self.log("Creating a test job...")
        
        response = self.session.post(
            f"{BASE_URL}/api/jobs",
            json=SAMPLE_JOB
        )
        
        if response.status_code in (200, 201):
            data = response.json()
            self.job_id = data.get("job_id")
            self.log(f"Job created successfully with ID: {self.job_id}")
            return True
        else:
            self.log(f"Job creation failed with status code: {response.status_code}")
            self.log(f"Response: {response.text}")
            return False

    def upload_resume(self, resume_data, is_api=True):
        """Upload a resume using either the API or form upload."""
        self.log(f"Uploading resume for {resume_data['name']}...")

        if is_api:
            # API-based upload (direct JSON)
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
        else:
            # Form-based upload (multipart/form-data)
            # Create a temporary file with the resume text
            timestamp = int(time.time())
            filename = f"test_resume_{timestamp}.txt"
            
            with open(filename, "w") as f:
                f.write(resume_data["resume_text"])
            
            with open(filename, "rb") as f:
                files = {"resume": (filename, f, "text/plain")}
                data = {
                    "name": resume_data["name"],
                    "email": resume_data.get("email", ""),
                    "phone": resume_data.get("phone", ""),
                    "is_direct_upload": "true"
                }
                
                response = self.session.post(
                    f"{BASE_URL}/api/resume/upload",
                    files=files,
                    data=data
                )
            
            # Clean up the temporary file
            try:
                os.remove(filename)
            except:
                pass
        
        result = {
            "name": resume_data["name"],
            "email": resume_data.get("email", ""),
            "status_code": response.status_code,
            "response": None
        }
        
        try:
            result["response"] = response.json()
            if "candidate_id" in result["response"]:
                self.candidates.append(result["response"]["candidate_id"])
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

    def check_candidates(self):
        """Check the candidates list to verify uploads."""
        self.log("Checking candidates list...")
        
        response = self.session.get(f"{BASE_URL}/api/candidates")
        
        if response.status_code == 200:
            try:
                data = response.json()
                candidates = data.get("candidates", [])
                self.log(f"Found {len(candidates)} candidates in the system.")
                
                # Check if our uploaded candidates are in the list
                found_count = 0
                for candidate_id in self.candidates:
                    for candidate in candidates:
                        if candidate.get("id") == candidate_id:
                            found_count += 1
                            break
                
                self.log(f"Found {found_count} of our {len(self.candidates)} uploaded candidates.")
                return True
            except:
                self.log(f"Failed to parse candidates response: {response.text}")
                return False
        else:
            self.log(f"Candidates check failed with status code: {response.status_code}")
            return False

    def check_matches(self):
        """Check job-candidate matches."""
        if not self.job_id:
            self.log("No job ID available to check matches.")
            return False
        
        self.log(f"Checking matches for job ID: {self.job_id}...")
        
        response = self.session.get(f"{BASE_URL}/api/candidates/{self.job_id}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                matches = data.get("matches", [])
                self.log(f"Found {len(matches)} matches for the job.")
                
                # Print top matches
                for idx, match in enumerate(matches[:3], 1):
                    self.log(f"Match #{idx}: {match.get('name')} ({match.get('score', 0)*100:.1f}%)")
                
                return True
            except:
                self.log(f"Failed to parse matches response: {response.text}")
                return False
        else:
            self.log(f"Matches check failed with status code: {response.status_code}")
            return False

    def refresh_matches(self):
        """Trigger a refresh of all job-candidate matches."""
        self.log("Refreshing all matches...")
        
        response = self.session.post(f"{BASE_URL}/api/matches/refresh")
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.log(f"Match refresh successful: {data.get('message', '')}")
                return True
            except:
                self.log(f"Failed to parse refresh response: {response.text}")
                return False
        else:
            self.log(f"Match refresh failed with status code: {response.status_code}")
            return False

    def run_tests(self):
        """Run all tests in sequence."""
        print("\n===== AI RECRUITER PRO SYSTEM TEST =====\n")
        
        # Step 1: Login
        if not self.login():
            print("❌ Login failed. Aborting tests.")
            return False
        print("✅ Login successful")
        
        # Step 2: Create a test job
        if not self.create_test_job():
            print("❌ Job creation failed. Continuing with tests...")
        else:
            print("✅ Test job created successfully")
        
        # Step 3: Upload resumes
        print("\n----- Testing Resume Uploads -----")
        
        # Upload the first resume using API
        if self.upload_resume(SAMPLE_RESUMES[0], is_api=True):
            print(f"✅ First resume uploaded successfully (API)")
        else:
            print(f"❌ First resume upload failed (API)")
        
        # Wait a bit to ensure processing
        time.sleep(1)
        
        # Upload the second resume (duplicate with better quality) using form upload
        if self.upload_resume(SAMPLE_RESUMES[1], is_api=False):
            print(f"✅ Second resume (duplicate with better quality) uploaded successfully (Form)")
        else:
            print(f"❌ Second resume upload failed (Form)")
        
        # Upload the third resume (different person)
        if self.upload_resume(SAMPLE_RESUMES[2], is_api=True):
            print(f"✅ Third resume (different person) uploaded successfully")
        else:
            print(f"❌ Third resume upload failed")
        
        # Upload the fourth resume (no email)
        if self.upload_resume(SAMPLE_RESUMES[3], is_api=True):
            print(f"✅ Fourth resume (no email) uploaded successfully")
        else:
            print(f"❌ Fourth resume upload failed")
        
        # Step 4: Check candidates
        print("\n----- Checking Candidates -----")
        if self.check_candidates():
            print("✅ Candidates check successful")
        else:
            print("❌ Candidates check failed")
        
        # Step 5: Check matches
        if self.job_id:
            print("\n----- Checking Matches -----")
            if self.check_matches():
                print("✅ Matches check successful")
            else:
                print("❌ Matches check failed")
            
            # Step 6: Refresh matches
            print("\n----- Refreshing All Matches -----")
            if self.refresh_matches():
                print("✅ Match refresh successful")
            else:
                print("❌ Match refresh failed")
        
        # Analysis of upload results
        print("\n----- Upload Results Analysis -----")
        for idx, result in enumerate(self.upload_results, 1):
            print(f"Resume #{idx} ({result['name']}):")
            print(f"  - Status: {result['status_code']}")
            if result['status_code'] in (200, 201, 202):
                print(f"  - Message: {result['response'].get('message', 'No message')}")
                if result['response'].get('is_update') is True:
                    print(f"  - Type: UPDATE (existing candidate)")
                elif result['response'].get('is_update') is False:
                    print(f"  - Type: NEW (new candidate)")
        
        print("\n===== TEST COMPLETE =====")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the AI Recruiter Pro system")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    runner.run_tests()