#!/usr/bin/env python
"""
Script to promote a regular recruiter to a senior recruiter in the AI Recruiter Pro application.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app import create_app, db
from models import Recruiter

def promote_to_senior_role(email):
    """
    Promote a recruiter to senior recruiter.
    
    Args:
        email (str): The email address of the recruiter
        
    Returns:
        bool: True if promotion was successful, False otherwise
    """
    try:
        app = create_app()
        with app.app_context():
            # Find recruiter by email
            recruiter = Recruiter.query.filter_by(email=email).first()
            
            if not recruiter:
                print(f"No recruiter found with email: {email}")
                return False
                
            if recruiter.role_id == 'senior_recruiter':
                print(f"Recruiter {email} is already a senior recruiter.")
                return True
                
            # Promote to senior recruiter
            old_role = recruiter.role_id
            recruiter.role_id = 'senior_recruiter'
            db.session.commit()
            
            print(f"Promotion successful: {email} (ID: {recruiter.id}, Role: {old_role} -> senior_recruiter)")
            return True
            
    except Exception as e:
        print(f"Error promoting recruiter: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promote_to_senior.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    
    success = promote_to_senior_role(email)
    
    if success:
        print("\nPromotion completed. The user can now create jobs and has all senior recruiter permissions.")
    else:
        print("\nFailed to promote user. Please check the error messages above.")
        sys.exit(1)