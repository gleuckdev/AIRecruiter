#!/usr/bin/env python3
"""
OpenAI Integration Test Script for AI Recruiter Pro

This script focuses on testing the OpenAI integration capabilities:
- Resume analysis and parsing
- Embedding generation
- Candidate persona generation
- Matching algorithm with semantic understanding
"""

import os
import sys
import time
import json
import requests
import argparse
from datetime import datetime

# Base URL for the application
BASE_URL = "http://localhost:5000"

# Test credentials - using the demo admin account
TEST_ADMIN = {
    "email": "demo@example.com",
    os.getenv("ADMIN_PASSWORD"): "os.getenv("TEST_PASSWORD")"
}

# Test job with specific skills and requirements
TEST_JOB = {
    "title": "Machine Learning Engineer",
    "company": "AI Solutions Inc.",
    "location": "Remote",
    "description": """
    We're looking for a Machine Learning Engineer to join our team. The ideal candidate will have 
    experience with NLP, computer vision, and deep learning frameworks.
    
    Responsibilities:
    - Design and implement machine learning models
    - Work with large datasets to train and optimize models
    - Deploy models to production environments
    - Collaborate with cross-functional teams
    
    Requirements:
    - 3+ years of experience in machine learning
    - Proficiency in Python and relevant ML libraries
    - Experience with TensorFlow or PyTorch
    - Background in NLP, computer vision, or recommendation systems
    """,
    "required_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "NLP"],
    "preferred_skills": ["Computer Vision", "AWS", "Docker", "Kubernetes", "MLOps"]
}

# Test candidates with varying degrees of matching to the job
TEST_CANDIDATES = [
    {
        "name": "Alex ML Expert",
        "email": "alex.ml@example.com",
        "phone": "555-111-2222",
        "resume_text": """
        Alex ML Expert
        Machine Learning Engineer
        alex.ml@example.com | 555-111-2222 | San Francisco, CA
        
        Summary:
        Experienced Machine Learning Engineer with 5 years of experience building and deploying ML models.
        Expert in NLP, computer vision, and deep learning with Python, TensorFlow, and PyTorch.
        
        Experience:
        Senior ML Engineer, AI Company, 2020-Present
        - Developed NLP models for sentiment analysis and text classification
        - Built computer vision models for object detection and segmentation
        - Deployed models to production using Docker and Kubernetes
        - Technologies: Python, TensorFlow, PyTorch, AWS, Docker
        
        ML Engineer, Tech Solutions, 2018-2020
        - Implemented recommendation systems for e-commerce
        - Created models for churn prediction and customer segmentation
        - Technologies: Python, Keras, Scikit-learn, SQL
        
        Education:
        Master of Science in Machine Learning, Stanford University, 2018
        Bachelor of Science in Computer Science, UC Berkeley, 2016
        
        Skills:
        - Languages: Python, R, SQL
        - ML Frameworks: TensorFlow, PyTorch, Keras, Scikit-learn
        - ML Areas: NLP, Computer Vision, Deep Learning
        - Tools: Docker, Kubernetes, AWS, Git
        """
    },
    {
        "name": "Taylor Data Scientist",
        "email": "taylor.data@example.com",
        "phone": "555-333-4444",
        "resume_text": """
        Taylor Data Scientist
        Data Scientist
        taylor.data@example.com | 555-333-4444 | Chicago, IL
        
        Summary:
        Data Scientist with 3 years of experience in statistical analysis and predictive modeling.
        Specialized in building machine learning models for business insights.
        
        Experience:
        Data Scientist, Analytics Corp, 2021-Present
        - Developed predictive models for customer behavior
        - Created dashboards and visualizations for business insights
        - Implemented basic ML pipelines
        - Technologies: Python, pandas, Scikit-learn, Tableau
        
        Junior Data Analyst, Data Solutions, 2019-2021
        - Performed data cleaning and preprocessing
        - Created statistical reports and analyses
        - Technologies: SQL, Excel, Python
        
        Education:
        Master of Science in Statistics, University of Chicago, 2019
        Bachelor of Science in Mathematics, University of Illinois, 2017
        
        Skills:
        - Languages: Python, R, SQL
        - Tools: pandas, NumPy, Scikit-learn, Tableau
        - Statistics: Regression, Clustering, Hypothesis Testing
        """
    },
    {
        "name": "Morgan Backend Dev",
        "email": "morgan.backend@example.com",
        "phone": "555-555-6666",
        "resume_text": """
        Morgan Backend Dev
        Backend Developer
        morgan.backend@example.com | 555-555-6666 | Seattle, WA
        
        Summary:
        Backend Developer with 4 years of experience building scalable web services and APIs.
        Focused on performance optimization and system architecture.
        
        Experience:
        Senior Backend Developer, Web Services Inc., 2020-Present
        - Developed RESTful APIs using Node.js and Express
        - Optimized database queries for improved performance
        - Implemented authentication and authorization systems
        - Technologies: Node.js, Express, MongoDB, Redis
        
        Backend Developer, Software Company, 2018-2020
        - Built microservices using Python and Flask
        - Integrated third-party APIs and services
        - Technologies: Python, Flask, PostgreSQL
        
        Education:
        Bachelor of Science in Computer Science, University of Washington, 2018
        
        Skills:
        - Languages: JavaScript, Python, SQL
        - Frameworks: Node.js, Express, Flask
        - Databases: MongoDB, PostgreSQL, Redis
        - Tools: Git, Docker, AWS
        """
    }
]


class OpenAiIntegrationTester:
    """Tests OpenAI integration in the AI Recruiter Pro system."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.session = requests.Session()
        self.access_token = None
        self.job_id = None
        self.candidate_ids = []
        self.match_scores = {}

    def log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def login(self):
        """Log in as admin."""
        self.log(f"Logging in as {TEST_ADMIN['email']}...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_ADMIN
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

    def create_test_job(self):
        """Create a test job for matching candidates."""
        self.log("Creating test machine learning job...")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/jobs",
                json=TEST_JOB
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                self.job_id = data.get("job_id")
                self.log(f"Job created with ID: {self.job_id}")
                return True
            else:
                self.log(f"Job creation failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Job creation error: {str(e)}")
            return False

    def upload_candidate(self, candidate):
        """Upload a candidate resume."""
        self.log(f"Uploading resume for {candidate['name']}...")
        
        try:
            payload = {
                "name": candidate["name"],
                "email": candidate["email"],
                "phone": candidate["phone"],
                "resume_text": candidate["resume_text"]
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/resume/text",
                json=payload
            )
            
            if response.status_code in (200, 201, 202):
                data = response.json()
                candidate_id = data.get("candidate_id")
                if candidate_id:
                    self.candidate_ids.append(candidate_id)
                    self.log(f"Resume upload successful with ID: {candidate_id}")
                    return True
                else:
                    self.log("No candidate ID returned.")
                    return False
            else:
                self.log(f"Resume upload failed with status code: {response.status_code}")
                self.log(f"Response: {response.text}")
                return False
        except Exception as e:
            self.log(f"Resume upload error: {str(e)}")
            return False

    def test_resume_analysis(self, candidate_id):
        """Test the resume analysis and parsed data."""
        self.log(f"Testing resume analysis for candidate ID: {candidate_id}")
        
        try:
            response = self.session.get(f"{BASE_URL}/api/candidate/{candidate_id}")
            
            if response.status_code == 200:
                data = response.json()
                candidate = data.get("candidate", {})
                parsed_data = candidate.get("parsed_data", {})
                
                if parsed_data:
                    skills = parsed_data.get("skills", [])
                    experience = parsed_data.get("experience", [])
                    education = parsed_data.get("education", [])
                    
                    self.log(f"- Skills extracted: {len(skills)}")
                    self.log(f"- Experience entries: {len(experience)}")
                    self.log(f"- Education entries: {len(education)}")
                    
                    if len(skills) > 0 and len(experience) > 0:
                        return True
                    else:
                        self.log("Insufficient data extracted from resume.")
                        return False
                else:
                    self.log("No parsed data found.")
                    return False
            else:
                self.log(f"Failed to get candidate data: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Resume analysis check error: {str(e)}")
            return False

    def test_persona_generation(self, candidate_id):
        """Test the persona generation capability."""
        self.log(f"Testing persona generation for candidate ID: {candidate_id}")
        
        try:
            response = self.session.post(
                f"{BASE_URL}/api/candidate/{candidate_id}/persona"
            )
            
            if response.status_code == 200:
                data = response.json()
                persona = data.get("persona", {})
                
                if persona:
                    # Check for key persona attributes
                    has_summary = "summary" in persona
                    has_strengths = "strengths" in persona
                    has_personality = "personality" in persona
                    
                    self.log(f"- Has summary: {has_summary}")
                    self.log(f"- Has strengths: {has_strengths}")
                    self.log(f"- Has personality: {has_personality}")
                    
                    # If there's content in the persona, it's a success
                    return any([has_summary, has_strengths, has_personality])
                else:
                    self.log("Empty persona returned.")
                    return False
            else:
                self.log(f"Persona generation failed: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Persona generation error: {str(e)}")
            return False

    def test_matching(self):
        """Test the semantic matching capability."""
        if not self.job_id or not self.candidate_ids:
            self.log("Missing job ID or candidate IDs for matching test.")
            return False
            
        self.log("Testing matching algorithm...")
        
        try:
            # First refresh matches
            refresh_response = self.session.post(f"{BASE_URL}/api/matches/refresh")
            if refresh_response.status_code != 200:
                self.log(f"Match refresh failed: {refresh_response.status_code}")
                return False
                
            # Get matches for the job
            response = self.session.get(f"{BASE_URL}/api/candidates/{self.job_id}")
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])
                
                if matches:
                    for match in matches:
                        candidate_id = match.get("id")
                        score = match.get("score", 0)
                        
                        if candidate_id in self.candidate_ids:
                            self.match_scores[candidate_id] = score
                            self.log(f"Candidate {candidate_id} match score: {score:.2f}")
                    
                    # Check if we got scores for all candidates
                    if len(self.match_scores) == len(self.candidate_ids):
                        return True
                    else:
                        missing = len(self.candidate_ids) - len(self.match_scores)
                        self.log(f"Missing match scores for {missing} candidates.")
                        return False
                else:
                    self.log("No matches found for the job.")
                    return False
            else:
                self.log(f"Failed to get matches: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"Matching test error: {str(e)}")
            return False

    def analyze_matching_results(self):
        """Analyze the semantic matching results."""
        if not self.match_scores:
            self.log("No match scores available for analysis.")
            return False
            
        self.log("Analyzing matching results...")
        
        try:
            # Get candidate details for analysis
            candidates = []
            for candidate_id in self.candidate_ids:
                response = self.session.get(f"{BASE_URL}/api/candidate/{candidate_id}")
                if response.status_code == 200:
                    data = response.json()
                    candidate = data.get("candidate", {})
                    name = candidate.get("name", "Unknown")
                    score = self.match_scores.get(candidate_id, 0)
                    candidates.append({"id": candidate_id, "name": name, "score": score})
            
            # Sort by score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            print("\n----- Match Score Analysis -----")
            for idx, candidate in enumerate(candidates, 1):
                print(f"{idx}. {candidate['name']}: {candidate['score']*100:.1f}%")
            
            # Verify the ML expert is ranked highest
            if candidates and "ML Expert" in candidates[0]["name"]:
                self.log("✅ ML Expert correctly ranked highest")
                return True
            else:
                for candidate in candidates:
                    if "ML Expert" in candidate["name"]:
                        self.log(f"❌ ML Expert not ranked highest, found at position: {candidates.index(candidate)+1}")
                        break
                return False
        except Exception as e:
            self.log(f"Match analysis error: {str(e)}")
            return False

    def run_tests(self):
        """Run all OpenAI integration tests."""
        print("\n===== OPENAI INTEGRATION TEST =====\n")
        
        # 1. Login
        if not self.login():
            print("❌ Login failed. Aborting tests.")
            return False
        print("✅ Login successful")
        
        # 2. Create test job
        if not self.create_test_job():
            print("❌ Job creation failed. Aborting tests.")
            return False
        print("✅ Test job created")
        
        # 3. Upload test candidates
        success_count = 0
        for idx, candidate in enumerate(TEST_CANDIDATES, 1):
            if self.upload_candidate(candidate):
                success_count += 1
                print(f"✅ Candidate #{idx} ({candidate['name']}) uploaded successfully")
            else:
                print(f"❌ Candidate #{idx} ({candidate['name']}) upload failed")
        
        if success_count == 0:
            print("❌ All candidate uploads failed. Aborting tests.")
            return False
        print(f"✅ {success_count}/{len(TEST_CANDIDATES)} candidates uploaded")
        
        # Wait for processing
        print("\nWaiting for background processing...")
        time.sleep(5)
        
        # 4. Test resume analysis
        print("\n----- Testing Resume Analysis -----")
        analysis_success = 0
        for idx, candidate_id in enumerate(self.candidate_ids, 1):
            if self.test_resume_analysis(candidate_id):
                analysis_success += 1
                print(f"✅ Resume analysis passed for candidate #{idx}")
            else:
                print(f"❌ Resume analysis failed for candidate #{idx}")
        
        if analysis_success > 0:
            print(f"✅ Resume analysis works for {analysis_success}/{len(self.candidate_ids)} candidates")
        else:
            print("❌ Resume analysis failed for all candidates")
        
        # 5. Test persona generation
        print("\n----- Testing Persona Generation -----")
        persona_success = 0
        for idx, candidate_id in enumerate(self.candidate_ids, 1):
            if self.test_persona_generation(candidate_id):
                persona_success += 1
                print(f"✅ Persona generation passed for candidate #{idx}")
            else:
                print(f"❌ Persona generation failed for candidate #{idx}")
        
        if persona_success > 0:
            print(f"✅ Persona generation works for {persona_success}/{len(self.candidate_ids)} candidates")
        else:
            print("❌ Persona generation failed for all candidates")
        
        # 6. Test matching
        print("\n----- Testing Semantic Matching -----")
        if self.test_matching():
            print("✅ Semantic matching functioning correctly")
        else:
            print("❌ Semantic matching test failed")
        
        # 7. Analyze matching results
        print("\n----- Analyzing Matching Quality -----")
        if self.analyze_matching_results():
            print("✅ Matching algorithm produces expected results")
        else:
            print("⚠️ Matching algorithm results need review")
        
        # Overall result
        success_count = sum([
            success_count > 0,
            analysis_success > 0,
            persona_success > 0,
            bool(self.match_scores)
        ])
        
        print("\n===== TEST RESULTS =====")
        print(f"OpenAI Integration Score: {success_count}/4")
        
        if success_count == 4:
            print("\n✅✅✅ OpenAI integration is fully functional! ✅✅✅")
        elif success_count >= 2:
            print(f"\n⚠️ OpenAI integration is partially working ({success_count}/4 tests passing)")
        else:
            print("\n❌❌❌ OpenAI integration has significant issues! ❌❌❌")
        
        return success_count >= 3  # Consider it a success if at least 3/4 tests pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test OpenAI integration in the AI Recruiter Pro system")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    tester = OpenAiIntegrationTester(verbose=args.verbose)
    tester.run_tests()