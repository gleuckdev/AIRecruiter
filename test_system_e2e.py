#!/usr/bin/env python3
"""
End-to-End Testing Script for AI Recruiter Pro System

This script performs a comprehensive test of all major system components:
- Authentication & session management
- Recruiter management
- Role & permissions
- Job creation & management
- Candidate processing
- Resume uploads & duplicate detection
- Matching algorithm
- Job tokens & analysis
- Sharing system
- OpenAI integrations
"""

import os
import sys
import time
import json
import random
import string
import requests
import argparse
from datetime import datetime, timedelta

# Base URL for the application
BASE_URL = "http://localhost:5000"

# Test credentials for the demo admin account
TEST_ADMIN = {
    "email": "demo@example.com",
    os.getenv("ADMIN_PASSWORD"): "os.getenv("TEST_PASSWORD")"
}

# Test data
TEST_RECRUITER = {
    "name": "Test Recruiter",
    "email": f"test.recruiter.{int(time.time())}@example.com",
    os.getenv("ADMIN_PASSWORD"): "os.getenv("TEST_PASSWORD")"
}

TEST_JOB_DATA = {
    "title": "Full Stack Developer",
    "company": "Test Company Inc.",
    "location": "Remote, US",
    "experience": "3-5 years",
    "education": "Bachelor's in Computer Science or equivalent",
    "job_type": "Full-time",
    "salary_range": "$100,000 - $130,000",
    "description": """
    We are looking for a skilled Full Stack Developer to join our growing team. 
    The ideal candidate will be responsible for developing and maintaining web applications 
    using modern technologies and best practices.
    
    Responsibilities:
    - Design, develop, and maintain web applications
    - Collaborate with cross-functional teams
    - Write clean, testable code
    - Participate in code reviews
    - Troubleshoot and debug applications
    
    Required Skills:
    - Strong proficiency in JavaScript, HTML, CSS
    - Experience with React, Angular, or Vue.js
    - Experience with Node.js, Express
    - Knowledge of Python and Flask or Django
    - Familiarity with SQL and NoSQL databases
    - Git version control
    """,
    "required_skills": ["JavaScript", "React", "Node.js", "Python", "SQL"],
    "preferred_skills": ["TypeScript", "Docker", "AWS", "CI/CD", "MongoDB"]
}

TEST_CANDIDATES = [
    {
        "name": "Alice Smith",
        "email": "alice.smith@example.com",
        "phone": "555-123-4567",
        "resume_text": """
        Alice Smith
        Senior Full Stack Developer
        alice.smith@example.com | 555-123-4567 | San Francisco, CA
        
        Summary:
        Experienced Full Stack Developer with 5+ years of experience in building scalable web applications.
        Expert in JavaScript, React, Node.js, and Python. Strong problem-solving skills and
        a passion for clean, maintainable code.
        
        Experience:
        Senior Developer, Tech Solutions Inc., 2019-Present
        - Led development of a customer-facing portal using React and Node.js
        - Implemented CI/CD pipeline using GitHub Actions and AWS
        - Optimized database queries, improving performance by 40%
        - Technologies: React, Redux, Node.js, Express, PostgreSQL, AWS
        
        Full Stack Developer, WebApp Co., 2017-2019
        - Developed RESTful APIs using Python and Flask
        - Built responsive front-end interfaces with React
        - Implemented authentication and authorization using JWT
        - Technologies: Python, Flask, React, MySQL, Docker
        
        Junior Developer, Start-Up Solutions, 2015-2017
        - Assisted in developing web applications using JavaScript and jQuery
        - Created and maintained MySQL databases
        - Technologies: JavaScript, jQuery, PHP, MySQL
        
        Education:
        Bachelor of Science in Computer Science, University of California, Berkeley, 2015
        
        Skills:
        - Languages: JavaScript, TypeScript, Python, HTML, CSS
        - Frontend: React, Redux, Angular, Vue.js
        - Backend: Node.js, Express, Flask, Django
        - Databases: PostgreSQL, MySQL, MongoDB
        - Tools: Git, Docker, AWS, CI/CD, Webpack
        """
    },
    {
        "name": "Bob Johnson",
        "email": "bob.johnson@example.com",
        "phone": "555-987-6543",
        "resume_text": """
        Bob Johnson
        Backend Developer
        bob.johnson@example.com | 555-987-6543 | Austin, TX
        
        Summary:
        Backend Developer with 3 years of experience specializing in Python and Node.js.
        Focused on building robust, scalable API services and microservices architecture.
        
        Experience:
        Backend Developer, API Services Inc., 2020-Present
        - Developed microservices using Node.js and Express
        - Implemented authentication using OAuth 2.0
        - Designed and maintained MongoDB databases
        - Technologies: Node.js, Express, MongoDB, Docker
        
        Junior Developer, Software Solutions, 2018-2020
        - Built RESTful APIs using Python and Flask
        - Integrated third-party services via APIs
        - Technologies: Python, Flask, PostgreSQL
        
        Education:
        Bachelor of Science in Software Engineering, University of Texas, 2018
        
        Skills:
        - Languages: JavaScript, Python, SQL
        - Frameworks: Express, Flask, Django
        - Databases: MongoDB, PostgreSQL
        - Tools: Git, Docker, AWS, Postman
        """
    },
    {
        "name": "Charlie Davis",
        "email": "charlie.davis@example.com",
        "phone": "555-456-7890",
        "resume_text": """
        Charlie Davis
        Frontend Developer
        charlie.davis@example.com | 555-456-7890 | New York, NY
        
        Summary:
        Frontend Developer with 4 years of experience creating responsive,
        user-friendly web interfaces. Passionate about UI/UX and performance optimization.
        
        Experience:
        Senior Frontend Developer, UI Experts, 2021-Present
        - Developed component library using React and Styled Components
        - Implemented state management using Redux
        - Optimized frontend performance, improving load times by 30%
        - Technologies: React, Redux, TypeScript, SCSS
        
        Frontend Developer, Web Design Co., 2019-2021
        - Built responsive web applications using React
        - Created interactive visualizations using D3.js
        - Technologies: React, JavaScript, HTML5, CSS3
        
        Junior Developer, Creative Agency, 2017-2019
        - Developed static websites using HTML, CSS, and JavaScript
        - Implemented responsive designs
        - Technologies: HTML, CSS, JavaScript, jQuery
        
        Education:
        Bachelor of Arts in Interactive Media, New York University, 2017
        
        Skills:
        - Languages: JavaScript, TypeScript, HTML5, CSS3
        - Frameworks: React, Vue.js, Angular
        - Tools: Webpack, Babel, SCSS, Styled Components
        - Design: Figma, Adobe XD
        """
    },
    {
        "name": "Dana Wilson",
        "email": "dana.wilson@example.com",
        "phone": "555-321-6547",
        "resume_text": """
        Dana Wilson
        DevOps Engineer
        dana.wilson@example.com | 555-321-6547 | Seattle, WA
        
        Summary:
        DevOps Engineer with 5 years of experience in continuous integration,
        deployment automation, and cloud infrastructure management.
        
        Experience:
        Senior DevOps Engineer, Cloud Systems Inc., 2020-Present
        - Designed and implemented CI/CD pipelines using Jenkins and GitHub Actions
        - Managed AWS infrastructure using Terraform
        - Containerized applications using Docker and Kubernetes
        - Technologies: AWS, Terraform, Docker, Kubernetes, Jenkins
        
        DevOps Engineer, Tech Innovations, 2018-2020
        - Automated deployment processes, reducing deployment time by 60%
        - Implemented monitoring and alerting using Prometheus and Grafana
        - Technologies: AWS, Docker, Ansible, ELK Stack
        
        Systems Administrator, IT Solutions, 2016-2018
        - Managed Linux servers and network infrastructure
        - Implemented backup and disaster recovery solutions
        - Technologies: Linux, Bash, Nagios
        
        Education:
        Bachelor of Science in Information Technology, University of Washington, 2016
        
        Skills:
        - Cloud: AWS, Azure, GCP
        - Containers: Docker, Kubernetes
        - CI/CD: Jenkins, GitHub Actions, CircleCI
        - IaC: Terraform, CloudFormation, Ansible
        - Monitoring: Prometheus, Grafana, ELK Stack
        """
    }
]

SIMILAR_JOB_DATA = {
    "title": "Senior Full Stack Engineer",  # Similar title
    "company": "Test Corporation",
    "location": "Remote, US",
    "experience": "4-6 years",
    "education": "Bachelor's in Computer Science or related field",
    "job_type": "Full-time",
    "salary_range": "$110,000 - $140,000",
    "description": """
    We are seeking a talented Senior Full Stack Engineer to join our engineering team.
    The ideal candidate will develop high-quality web applications and services 
    using modern technologies and frameworks.
    
    Responsibilities:
    - Design and implement scalable web applications
    - Write clean, maintainable, and testable code
    - Collaborate with product managers and designers
    - Mentor junior developers
    - Participate in code reviews and technical discussions
    
    Required Skills:
    - Strong proficiency in JavaScript/TypeScript
    - Experience with React or similar frontend frameworks
    - Experience with Node.js and Express
    - Knowledge of Python web frameworks (Django or Flask)
    - Experience with SQL and NoSQL databases
    - Familiarity with AWS or other cloud platforms
    """,
    "required_skills": ["JavaScript", "TypeScript", "React", "Node.js", "Python"],
    "preferred_skills": ["AWS", "Docker", "Kubernetes", "GraphQL", "MongoDB"]
}


class AiRecruiterSystemTester:
    """Comprehensive tester for the AI Recruiter Pro system."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.session = requests.Session()
        self.access_token = None
        self.test_recruiter_id = None
        self.test_job_id = None
        self.similar_job_id = None
        self.candidate_ids = []
        self.invitation_token = None
        self.sharing_id = None
        self.results = {
            "auth": False,
            "recruiter_management": False,
            "job_creation": False,
            "candidate_upload": False,
            "matching": False,
            "job_tokens": False,
            "sharing": False,
            "openai_integration": False
        }

    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def login(self, credentials=None):
        """Log in as a recruiter and get an access token."""
        if credentials is None:
            credentials = TEST_ADMIN
            
        self.log(f"Logging in as {credentials['email']}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json=credentials
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
        except Exception as e:
            self.log(f"Login error: {str(e)}")
            return False

    def create_invitation(self):
        """Create an invitation for a new recruiter."""
        self.log("Creating invitation...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/invitations",
                json={
                    "email": TEST_RECRUITER["email"],
                    "role": "recruiter",
                    "share_jobs": True,
                    "share_candidates": True
                }
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.invitation_token = data.get("token")
                self.log(f"Invitation created with token: {self.invitation_token}")
                return True
            else:
                self.log(f"Invitation creation failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Invitation creation error: {str(e)}")
            return False

    def register_test_recruiter(self):
        """Register a test recruiter using the invitation."""
        if not self.invitation_token:
            self.log("No invitation token available. Cannot register test recruiter.")
            return False
            
        self.log(f"Registering test recruiter {TEST_RECRUITER['email']}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/join/{self.invitation_token}",
                json={
                    "name": TEST_RECRUITER["name"],
                    "email": TEST_RECRUITER["email"],
                    os.getenv("ADMIN_PASSWORD"): TEST_RECRUITER[os.getenv("ADMIN_PASSWORD")]
                }
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.test_recruiter_id = data.get("recruiter_id")
                self.log(f"Test recruiter registered with ID: {self.test_recruiter_id}")
                return True
            else:
                self.log(f"Registration failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Registration error: {str(e)}")
            return False

    def create_job(self, job_data=None):
        """Create a job to test the job creation functionality."""
        if job_data is None:
            job_data = TEST_JOB_DATA
            
        self.log(f"Creating job: {job_data['title']}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/jobs",
                json=job_data
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                job_id = data.get("job_id")
                if job_data == TEST_JOB_DATA:
                    self.test_job_id = job_id
                else:
                    self.similar_job_id = job_id
                self.log(f"Job created with ID: {job_id}")
                return True
            else:
                self.log(f"Job creation failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Job creation error: {str(e)}")
            return False

    def upload_candidate(self, candidate_data):
        """Upload a candidate resume."""
        self.log(f"Uploading resume for {candidate_data['name']}...")
        
        try:
            # API-based upload (direct JSON)
            payload = {
                "name": candidate_data["name"],
                "email": candidate_data["email"],
                "phone": candidate_data["phone"],
                "resume_text": candidate_data["resume_text"]
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/resume/text",
                json=payload
            )
            
            if response.status_code in (200, 201, 202):
                try:
                    data = response.json()
                    candidate_id = data.get("candidate_id")
                    if candidate_id:
                        self.candidate_ids.append(candidate_id)
                    self.log(f"Resume upload successful for {candidate_data['name']} with ID: {candidate_id}")
                    return True
                except Exception as parse_error:
                    self.log(f"Error parsing response: {str(parse_error)}")
                    return False
            else:
                self.log(f"Resume upload failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Resume upload error: {str(e)}")
            return False

    def create_sharing_relationship(self):
        """Create a sharing relationship between admin and test recruiter."""
        if not self.test_recruiter_id:
            self.log("No test recruiter ID available. Cannot create sharing relationship.")
            return False
            
        self.log(f"Creating sharing relationship with test recruiter ID: {self.test_recruiter_id}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/sharing",
                json={
                    "shared_with_id": self.test_recruiter_id,
                    "share_jobs": True,
                    "share_candidates": True
                }
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.sharing_id = data.get("sharing_id")
                self.log(f"Sharing relationship created with ID: {self.sharing_id}")
                return True
            else:
                self.log(f"Sharing relationship creation failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Sharing relationship creation error: {str(e)}")
            return False

    def check_shared_access(self):
        """Check if test recruiter has access to shared resources."""
        if not self.test_recruiter_id:
            self.log("No test recruiter ID available. Cannot check shared access.")
            return False
            
        # First login as the test recruiter
        if not self.login(TEST_RECRUITER):
            self.log("Could not login as test recruiter.")
            return False
            
        self.log("Checking shared access to jobs and candidates...")
        
        try:
            # Check access to shared jobs
            response = self.session.get(f"{BASE_URL}/api/jobs")
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                found_shared_job = False
                
                for job in jobs:
                    if job.get("id") == self.test_job_id:
                        found_shared_job = True
                        break
                
                if found_shared_job:
                    self.log("Test recruiter can access shared job.")
                else:
                    self.log("Test recruiter cannot access shared job.")
                    return False
                
                # Check access to shared candidates
                if len(self.candidate_ids) > 0:
                    candidate_id = self.candidate_ids[0]
                    response = self.session.get(f"{BASE_URL}/api/candidate/{candidate_id}")
                    
                    if response.status_code == 200:
                        self.log("Test recruiter can access shared candidate.")
                        return True
                    else:
                        self.log(f"Test recruiter cannot access shared candidate: {response.status_code}")
                        return False
                else:
                    self.log("No candidate IDs available to check shared access.")
                    return False
            else:
                self.log(f"Failed to get jobs list: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Shared access check error: {str(e)}")
            return False
        finally:
            # Switch back to admin user
            self.login(TEST_ADMIN)

    def check_job_tokens(self):
        """Check if job tokens are created and similar jobs are detected."""
        if not self.test_job_id or not self.similar_job_id:
            self.log("Missing job IDs. Cannot check job tokens.")
            return False
            
        self.log("Checking job token creation and similar job detection...")
        
        try:
            # Get job insights which should contain similar jobs
            response = self.session.get(f"{BASE_URL}/api/insights/jobs")
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get("tokens", [])
                
                # Look for a token with both our jobs
                for token in tokens:
                    jobs = token.get("jobs", [])
                    job_ids = [job.get("id") for job in jobs]
                    
                    if self.test_job_id in job_ids and self.similar_job_id in job_ids:
                        self.log("Found job token containing both similar jobs!")
                        return True
                
                self.log("Could not find a job token with both similar jobs.")
                return False
            else:
                self.log(f"Failed to get job insights: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Job token check error: {str(e)}")
            return False

    def check_matches(self):
        """Check if candidates are matched with jobs."""
        if not self.test_job_id or not self.candidate_ids:
            self.log("Missing job ID or candidate IDs. Cannot check matches.")
            return False
            
        self.log("Checking candidate-job matches...")
        
        try:
            # First refresh all matches to ensure they're up to date
            refresh_response = self.session.post(f"{BASE_URL}/api/matches/refresh")
            
            if refresh_response.status_code != 200:
                self.log(f"Match refresh failed: {refresh_response.status_code}")
                return False
                
            # Get matches for our test job
            response = self.session.get(f"{BASE_URL}/api/candidates/{self.test_job_id}")
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                
                if len(matches) > 0:
                    match_count = len(matches)
                    self.log(f"Found {match_count} matches for the test job.")
                    
                    # Check if our candidates are in the matches
                    candidate_match_count = 0
                    for match in matches:
                        candidate_id = match.get("id")
                        if candidate_id in self.candidate_ids:
                            candidate_match_count += 1
                            self.log(f"Found match for candidate {candidate_id} with score: {match.get('score', 0)*100:.1f}%")
                    
                    self.log(f"Found {candidate_match_count} of our {len(self.candidate_ids)} candidates in matches.")
                    return candidate_match_count > 0
                else:
                    self.log("No matches found for the test job.")
                    return False
            else:
                self.log(f"Failed to get job matches: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Match check error: {str(e)}")
            return False

    def check_openai_integration(self):
        """Check if OpenAI integration is working for candidate persona generation."""
        if not self.candidate_ids:
            self.log("No candidate IDs available. Cannot check OpenAI integration.")
            return False
            
        candidate_id = self.candidate_ids[0]
        self.log(f"Testing OpenAI integration with candidate ID: {candidate_id}...")
        
        try:
            # Generate a persona for the candidate
            response = self.session.post(
                f"{BASE_URL}/api/candidate/{candidate_id}/persona"
            )
            
            if response.status_code == 200:
                data = response.json()
                if "persona" in data:
                    persona = data.get("persona")
                    if isinstance(persona, dict) and len(persona) > 0:
                        self.log("Successfully generated candidate persona using OpenAI.")
                        return True
                    else:
                        self.log("Empty persona returned.")
                        return False
                else:
                    self.log("No persona field in response.")
                    return False
            else:
                self.log(f"Persona generation failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"OpenAI integration check error: {str(e)}")
            return False

    def run_auth_tests(self):
        """Run authentication and session management tests."""
        print("\n----- Testing Authentication System -----")
        
        # Test admin login
        if not self.login(TEST_ADMIN):
            print("❌ Admin login failed.")
            return False
        print("✅ Admin login successful.")
        
        # Create invitation
        if not self.create_invitation():
            print("❌ Invitation creation failed.")
            return False
        print("✅ Invitation created successfully.")
        
        # Register test recruiter
        if not self.register_test_recruiter():
            print("❌ Test recruiter registration failed.")
            return False
        print("✅ Test recruiter registered successfully.")
        
        # Test recruiter login
        if not self.login(TEST_RECRUITER):
            print("❌ Test recruiter login failed.")
            return False
        print("✅ Test recruiter login successful.")
        
        # Switch back to admin
        if not self.login(TEST_ADMIN):
            print("❌ Failed to switch back to admin account.")
            return False
        
        print("✅ All authentication tests passed!")
        self.results["auth"] = True
        return True

    def run_job_management_tests(self):
        """Run job creation and management tests."""
        print("\n----- Testing Job Management -----")
        
        # Create primary test job
        if not self.create_job(TEST_JOB_DATA):
            print("❌ Primary job creation failed.")
            return False
        print(f"✅ Primary job created with ID: {self.test_job_id}")
        
        # Create similar job to test job tokens
        if not self.create_job(SIMILAR_JOB_DATA):
            print("❌ Similar job creation failed.")
            return False
        print(f"✅ Similar job created with ID: {self.similar_job_id}")
        
        print("✅ All job management tests passed!")
        self.results["job_creation"] = True
        return True

    def run_candidate_tests(self):
        """Run candidate upload and processing tests."""
        print("\n----- Testing Candidate System -----")
        
        # Upload test candidates
        success_count = 0
        for idx, candidate in enumerate(TEST_CANDIDATES, 1):
            if self.upload_candidate(candidate):
                success_count += 1
                print(f"✅ Candidate #{idx} ({candidate['name']}) uploaded successfully.")
            else:
                print(f"❌ Candidate #{idx} ({candidate['name']}) upload failed.")
        
        if success_count == len(TEST_CANDIDATES):
            print("✅ All candidate uploads successful!")
            self.results["candidate_upload"] = True
            return True
        elif success_count > 0:
            print(f"⚠️ {success_count} of {len(TEST_CANDIDATES)} candidate uploads successful.")
            self.results["candidate_upload"] = True
            return True
        else:
            print("❌ All candidate uploads failed.")
            return False

    def run_sharing_tests(self):
        """Run sharing system tests."""
        print("\n----- Testing Sharing System -----")
        
        # Create sharing relationship
        if not self.create_sharing_relationship():
            print("❌ Sharing relationship creation failed.")
            return False
        print("✅ Sharing relationship created successfully.")
        
        # Check shared access
        if not self.check_shared_access():
            print("❌ Shared access check failed.")
            return False
        print("✅ Shared access check passed.")
        
        print("✅ All sharing system tests passed!")
        self.results["sharing"] = True
        return True

    def run_job_token_tests(self):
        """Run job token and similar job detection tests."""
        print("\n----- Testing Job Token System -----")
        
        if not self.check_job_tokens():
            print("❌ Job token check failed.")
            return False
        
        print("✅ Job token system works correctly!")
        self.results["job_tokens"] = True
        return True

    def run_matching_tests(self):
        """Run matching algorithm tests."""
        print("\n----- Testing Matching Algorithm -----")
        
        if not self.check_matches():
            print("❌ Matching check failed.")
            return False
        
        print("✅ Matching algorithm works correctly!")
        self.results["matching"] = True
        return True

    def run_openai_tests(self):
        """Run OpenAI integration tests."""
        print("\n----- Testing OpenAI Integration -----")
        
        if not self.check_openai_integration():
            print("❌ OpenAI integration check failed.")
            return False
        
        print("✅ OpenAI integration works correctly!")
        self.results["openai_integration"] = True
        return True

    def run_all_tests(self):
        """Run all system tests in sequence."""
        print("\n===== AI RECRUITER PRO SYSTEM TEST =====\n")
        print("Starting end-to-end system tests...")
        
        # 1. Authentication tests
        self.run_auth_tests()
        
        # 2. Job management tests
        self.run_job_management_tests()
        
        # 3. Candidate tests
        self.run_candidate_tests()
        
        # 4. Wait a bit to ensure processing
        print("\nWaiting for background processing...")
        time.sleep(5)
        
        # 5. Matching tests
        self.run_matching_tests()
        
        # 6. Job token tests
        self.run_job_token_tests()
        
        # 7. Sharing tests
        self.run_sharing_tests()
        
        # 8. OpenAI integration tests
        self.run_openai_tests()
        
        # Print results summary
        print("\n===== TEST RESULTS SUMMARY =====")
        success_count = sum(1 for result in self.results.values() if result)
        total_count = len(self.results)
        
        for test_name, success in self.results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status}: {test_name.replace('_', ' ').title()}")
        
        print(f"\nOverall: {success_count}/{total_count} tests passed")
        
        if success_count == total_count:
            print("\n✅✅✅ ALL TESTS PASSED! The system is fully operational. ✅✅✅")
        else:
            print(f"\n⚠️ {total_count - success_count} tests failed. The system needs attention.")
        
        return success_count == total_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run end-to-end tests for the AI Recruiter Pro system")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    tester = AiRecruiterSystemTester(verbose=args.verbose)
    tester.run_all_tests()