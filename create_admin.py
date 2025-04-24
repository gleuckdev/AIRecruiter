#!/usr/bin/env python
"""
Script to create an admin user for the AI Recruiter Pro application.
"""

import os
import argparse
import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Import after environment variables are loaded
from app import db, create_app
from models import Recruiter, Role

def create_admin_user(email, password, name=None):
    """
    Create an admin user with the given email and password.
    
    Args:
        email (str): The email address for the admin user
        password (str): The password for the admin user
        name (str, optional): The name for the admin user. Defaults to "Admin".
        
    Returns:
        Recruiter: The created admin user
    """
    app = create_app()
    
    with app.app_context():
        # Check if the user already exists
        existing_user = Recruiter.query.filter_by(email=email).first()
        if existing_user:
            print(f"User with email {email} already exists.")
            return existing_user
            
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create the admin user
        admin = Recruiter(
            name=name or "Admin",
            email=email,
            password_hash=password_hash,
            role="admin",
            role_id="admin"
        )
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user {email} created successfully!")
        return admin

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an admin user for AI Recruiter Pro")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--name", help="Admin name (default: Admin)")
    
    args = parser.parse_args()
    
    create_admin_user(args.email, args.password, args.name)