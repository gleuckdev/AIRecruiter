#!/usr/bin/env python
"""
Script to reset a recruiter's password in the AI Recruiter Pro application.
"""

import os
import sys
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app import create_app, db
from models import Recruiter

def reset_recruiter_password(email, new_password):
    """
    Reset a recruiter's password with the given email.
    
    Args:
        email (str): The email address of the recruiter
        new_password (str): The new password to set
        
    Returns:
        bool: True if password was reset, False otherwise
    """
    try:
        app = create_app()
        with app.app_context():
            # Find recruiter by email
            recruiter = Recruiter.query.filter_by(email=email).first()
            
            if not recruiter:
                print(f"No recruiter found with email: {email}")
                return False
                
            # Set new password
            recruiter.set_password(new_password)
            db.session.commit()
            
            print(f"Password reset successful for {email} (ID: {recruiter.id}, Role: {recruiter.role})")
            return True
            
    except Exception as e:
        print(f"Error resetting password: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)
        
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    success = reset_recruiter_password(email, new_password)
    
    if success:
        print("\nPassword has been reset. You can now log in with the new password.")
    else:
        print("\nFailed to reset password. Please check the error messages above.")
        sys.exit(1)