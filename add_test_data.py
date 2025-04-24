#!/usr/bin/env python
"""
Script to add sample test data to the database.
This combines add_sample_job.py and add_sample_candidates.py into a single script.
"""

import os
import sys
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app import db, create_app
from models import Recruiter, Role, Job, Candidate, JobCandidateMatch

# Import the individual functions
from add_sample_job import add_sample_job
from add_sample_candidates import add_sample_candidates
from create_admin import create_admin_user

def add_test_data():
    """
    Add test data to the database including:
    - A demo admin user (if none exists)
    - Sample job
    - Sample candidates with various skills
    - Job-candidate matches
    """
    app = create_app()
    
    with app.app_context():
        # Step 1: Make sure we have a recruiter (admin)
        recruiter = Recruiter.query.first()
        
        if not recruiter:
            print("No users found, creating a demo admin user...")
            # Use environment variable for demo password or a secure default
            demo_password = os.environ.get('DEMO_PASSWORD', os.urandom(12).hex())
            recruiter = create_admin_user(
                email="demo@example.com",
                password=demo_password,
                name="Demo Admin"
            )
            print(f"Created demo admin user: {recruiter.email}")
            if not os.environ.get('DEMO_PASSWORD'):
                print(f"Auto-generated password: {demo_password}")
                print("Set DEMO_PASSWORD environment variable to make this consistent across runs.")
        else:
            print(f"Using existing user: {recruiter.email}")
        
        # Step 2: Add a sample job
        job = add_sample_job()
        if job:
            print(f"Added job: {job.title}")
        
        # Step 3: Add sample candidates
        candidates = add_sample_candidates()
        if candidates:
            print(f"Added {len(candidates)} sample candidates")
        
        print("\nTest data setup complete!")
        print("\nLogin with:")
        print("Email: demo@example.com")
        password_msg = f"Password: {os.environ.get('DEMO_PASSWORD', 'Check app logs for auto-generated password')}"
        print(password_msg)

if __name__ == "__main__":
    add_test_data()