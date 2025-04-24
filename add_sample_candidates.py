#!/usr/bin/env python
"""
Script to add sample candidates to the database.
Run this to populate the database with realistic candidates for testing.
"""

import os
from dotenv import load_dotenv
import json
import random

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app import db, create_app
from models import Candidate, Recruiter, Job, JobCandidateMatch

def add_sample_candidates():
    """Add sample candidates to the database"""
    app = create_app()
    
    with app.app_context():
        # Check if we already have a recruiter to assign the candidates to
        recruiter = Recruiter.query.first()
        
        if not recruiter:
            print("Error: No recruiter found in database. Please create a recruiter first.")
            return
        
        # Get a job to associate with some candidates
        job = Job.query.first()
        
        # Sample candidate data
        candidates_data = [
            {
                "name": "Emily Johnson",
                "email": "emily.johnson@example.com",
                "phone": "555-123-4567",
                "resume_file": "emily_johnson_resume.pdf",
                "gcs_url": "https://storage.example.com/resumes/emily_johnson_resume.pdf",
                "parsed_data": {
                    "skills": ["Python", "Django", "Flask", "PostgreSQL", "React", "Docker", "AWS"],
                    "experience": "6 years",
                    "education": "M.S. Computer Science, Stanford University",
                    "summary": "Experienced full-stack developer with a focus on Python web applications."
                }
            },
            {
                "name": "Michael Chen",
                "email": "michael.chen@example.com",
                "phone": "555-234-5678",
                "resume_file": "michael_chen_resume.pdf",
                "gcs_url": "https://storage.example.com/resumes/michael_chen_resume.pdf",
                "parsed_data": {
                    "skills": ["Python", "Django", "MongoDB", "JavaScript", "Angular", "Kubernetes", "GCP"],
                    "experience": "4 years",
                    "education": "B.S. Computer Engineering, MIT",
                    "summary": "Full-stack developer specializing in Python backends and modern JavaScript frameworks."
                }
            },
            {
                "name": "Sarah Williams",
                "email": "sarah.williams@example.com",
                "phone": "555-345-6789",
                "resume_file": "sarah_williams_resume.pdf",
                "gcs_url": "https://storage.example.com/resumes/sarah_williams_resume.pdf",
                "parsed_data": {
                    "skills": ["Python", "Flask", "FastAPI", "SQLAlchemy", "PostgreSQL", "Vue.js", "CI/CD", "Docker"],
                    "experience": "7 years",
                    "education": "Ph.D. Computer Science, Carnegie Mellon University",
                    "summary": "Senior backend developer focused on building scalable APIs and microservices."
                }
            },
            {
                "name": "David Rodriguez",
                "email": "david.rodriguez@example.com",
                "phone": "555-456-7890",
                "resume_file": "david_rodriguez_resume.pdf",
                "gcs_url": "https://storage.example.com/resumes/david_rodriguez_resume.pdf",
                "parsed_data": {
                    "skills": ["JavaScript", "React", "Node.js", "Express", "MongoDB", "AWS Lambda", "Serverless"],
                    "experience": "5 years",
                    "education": "B.S. Information Systems, UC Berkeley",
                    "summary": "Frontend specialist with full-stack capabilities and serverless experience."
                }
            },
            {
                "name": "Jennifer Kim",
                "email": "jennifer.kim@example.com",
                "phone": "555-567-8901",
                "resume_file": "jennifer_kim_resume.pdf",
                "gcs_url": "https://storage.example.com/resumes/jennifer_kim_resume.pdf",
                "parsed_data": {
                    "skills": ["Python", "Django", "Flask", "GraphQL", "React", "TypeScript", "PostgreSQL", "Redis"],
                    "experience": "8 years",
                    "education": "M.S. Software Engineering, University of Washington",
                    "summary": "Tech lead with expertise in Python web development and modern frontend technologies."
                }
            }
        ]
        
        added_candidates = []
        
        for candidate_data in candidates_data:
            # Check if this candidate already exists
            existing_candidate = Candidate.query.filter_by(email=candidate_data["email"]).first()
            
            if existing_candidate:
                print(f"Candidate {candidate_data['name']} already exists.")
                added_candidates.append(existing_candidate)
                continue
            
            # Add the recruiter ID
            candidate_data["uploaded_by"] = recruiter.id
            
            # Randomly assign some candidates to the job if one exists
            if job and random.choice([True, False]):
                candidate_data["job_id"] = job.id
            
            # Create a persona
            persona = {
                "strengths": ["Quick learner", "Team player", "Detail-oriented"],
                "weaknesses": ["Sometimes overcommits", "Could improve presentation skills"],
                "work_style": "Collaborative but can work independently",
                "personality": "Analytical, thorough, and adaptable",
                "ideal_work_environment": "Fast-paced, innovative team with clear objectives"
            }
            candidate_data["persona"] = persona
            
            # Create a dummy embedding (would normally be generated by OpenAI)
            embedding = [0.01] * 1536  # OpenAI embeddings are 1536 dimensions
            candidate_data["embedding"] = embedding
            
            # Create the candidate
            candidate = Candidate(**candidate_data)
            
            # Add to database
            db.session.add(candidate)
            db.session.flush()  # To get the ID
            
            # Create a match if the candidate is associated with a job
            if "job_id" in candidate_data and candidate_data["job_id"]:
                # Calculate a score between 0.3 and 0.95
                score = random.uniform(0.3, 0.95)
                
                match = JobCandidateMatch(
                    job_id=candidate_data["job_id"],
                    candidate_id=candidate.id,
                    score=score
                )
                db.session.add(match)
            
            added_candidates.append(candidate)
            print(f"Added sample candidate: {candidate_data['name']}")
        
        db.session.commit()
        print(f"Added {len(added_candidates)} sample candidates.")
        return added_candidates

if __name__ == "__main__":
    add_sample_candidates()