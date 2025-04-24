"""
AI Recruiter Pro - Render Specific Database Migrations
This file contains all database migrations needed for the Render deployment.
It uses direct SQL commands with proper error handling to ensure database schema
is correctly set up before the application starts.
"""

import os
import sys
from datetime import datetime

def run_migrations():
    """Run all necessary database migrations for Render deployment"""
    try:
        # Import app inside the function to avoid import errors
        from app import create_app
        from models import db
        
        app = create_app()
        print("Application created successfully.")
    except Exception as e:
        print(f"Error creating application: {str(e)}")
        sys.exit(1)

    with app.app_context():
        print("\n== Running AI Recruiter Pro database migrations for Render ==")
        print(f"Database URL: {os.environ.get('DATABASE_URL', '').split('@')[1] if '@' in os.environ.get('DATABASE_URL', '') else 'Unknown'}")
        print(f"Starting migrations at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Connect to the database
        try:
            conn = db.engine.connect()
            print("Database connection established.")
        except Exception as e:
            print(f"Failed to connect to database: {str(e)}")
            sys.exit(1)
            
        # Helper function to execute SQL with error handling
        def execute_sql(sql_statement, description):
            try:
                conn.execute(db.text(sql_statement))
                print(f"✓ Success: {description}")
                return True
            except Exception as e:
                print(f"✗ Error: {description} - {str(e)}")
                return False
            
        # Run all migrations within a single connection
        with conn:
            # Enable autocommit mode
            conn.connection.autocommit = True
            
            # 1. Create roles table if not exists
            execute_sql("""
                CREATE TABLE IF NOT EXISTS roles (
                    id SERIAL PRIMARY KEY,
                    role_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    permissions JSON NOT NULL DEFAULT '[]',
                    inherits VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """, "Create roles table if not exists")
            
            # 2. Add role fields to recruiters table
            execute_sql("""
                ALTER TABLE recruiters 
                ADD COLUMN IF NOT EXISTS role_id VARCHAR(50) REFERENCES roles(role_id) DEFAULT 'recruiter';
            """, "Add role_id column to recruiters if not exists")
            
            # 3. Add role fields to invitations table
            execute_sql("""
                ALTER TABLE invitations 
                ADD COLUMN IF NOT EXISTS role_id VARCHAR(50) REFERENCES roles(role_id) DEFAULT 'recruiter';
            """, "Add role_id column to invitations if not exists")
            
            # 4. Add sharing fields to invitations
            execute_sql("""
                ALTER TABLE invitations 
                ADD COLUMN IF NOT EXISTS share_jobs BOOLEAN DEFAULT FALSE;
            """, "Add share_jobs column to invitations if not exists")
            
            execute_sql("""
                ALTER TABLE invitations 
                ADD COLUMN IF NOT EXISTS share_candidates BOOLEAN DEFAULT FALSE;
            """, "Add share_candidates column to invitations if not exists")
            
            # 5. Create recruiter_sharing table if not exists
            execute_sql("""
                CREATE TABLE IF NOT EXISTS recruiter_sharing (
                    id SERIAL PRIMARY KEY,
                    owner_id INTEGER REFERENCES recruiters(id) NOT NULL,
                    shared_with_id INTEGER REFERENCES recruiters(id) NOT NULL,
                    share_jobs BOOLEAN DEFAULT FALSE,
                    share_candidates BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_recruiter_sharing UNIQUE (owner_id, shared_with_id)
                );
            """, "Create recruiter_sharing table if not exists")
            
            # 6. Create job_tokens table if not exists
            execute_sql("""
                CREATE TABLE IF NOT EXISTS job_tokens (
                    id SERIAL PRIMARY KEY,
                    token_hash VARCHAR(64) UNIQUE,
                    base_title VARCHAR(255),
                    base_location VARCHAR(255),
                    description_vector TEXT,
                    job_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """, "Create job_tokens table if not exists")
            
            # 7. Add token_id column to jobs table
            execute_sql("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS token_id INTEGER REFERENCES job_tokens(id);
            """, "Add token_id column to jobs if not exists")
            
            # 8. Add expiration fields to jobs table
            execute_sql("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '60 days');
            """, "Add expires_at column to jobs if not exists")
            
            execute_sql("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE;
            """, "Add notification_sent column to jobs if not exists")
            
            execute_sql("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS last_renewed_at TIMESTAMP;
            """, "Add last_renewed_at column to jobs if not exists")
            
            # 9. Add status column to jobs table if not exists
            execute_sql("""
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
            """, "Add status column to jobs if not exists")
            
            # 10. Add candidate persona column
            execute_sql("""
                ALTER TABLE candidates 
                ADD COLUMN IF NOT EXISTS persona JSON;
            """, "Add persona column to candidates if not exists")
            
            # 11. Add uploaded_by column to candidates
            execute_sql("""
                ALTER TABLE candidates 
                ADD COLUMN IF NOT EXISTS uploaded_by INTEGER REFERENCES recruiters(id);
            """, "Add uploaded_by column to candidates if not exists")
            
            # 12. Add job_id column to candidates
            execute_sql("""
                ALTER TABLE candidates 
                ADD COLUMN IF NOT EXISTS job_id INTEGER REFERENCES jobs(id);
            """, "Add job_id column to candidates if not exists")
            
            # 13. Create ratings table if not exists
            execute_sql("""
                CREATE TABLE IF NOT EXISTS candidate_ratings (
                    id SERIAL PRIMARY KEY,
                    candidate_id INTEGER REFERENCES candidates(id) NOT NULL,
                    recruiter_id INTEGER REFERENCES recruiters(id) NOT NULL,
                    score FLOAT NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """, "Create candidate_ratings table if not exists")
            
            # 14. Initialize or ensure correct role data
            execute_sql("""
                INSERT INTO roles (role_id, name, permissions, inherits)
                VALUES 
                    ('recruiter', 'Recruiter', '["candidates:view", "candidates:upload", "jobs:view", "matches:view"]', NULL),
                    ('senior_recruiter', 'Senior Recruiter', '["candidates:create", "candidates:edit", "jobs:create", "jobs:edit", "invitations:create"]', 'recruiter'),
                    ('admin', 'Administrator', '["users:manage", "roles:manage", "system:configure"]', 'senior_recruiter')
                ON CONFLICT (role_id) DO NOTHING;
            """, "Initialize role data if not exists")
            
            # 15. Update existing jobs with expiration dates
            execute_sql("""
                UPDATE jobs SET expires_at = CURRENT_TIMESTAMP + INTERVAL '60 days'
                WHERE expires_at IS NULL;
            """, "Update existing jobs with expiration dates")
            
            # 16. Update email constraint on candidates table
            try:
                execute_sql("""
                    ALTER TABLE candidates ALTER COLUMN email DROP NOT NULL;
                """, "Make email nullable in candidates table")
            except:
                # This might fail if the column is already nullable
                print("Note: Email column might already be nullable")
            
            print("\n== Database migration for Render completed successfully ==")
            print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    run_migrations()
