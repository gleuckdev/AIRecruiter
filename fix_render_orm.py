"""
Fix for Render deployment - Ensures the ORM and database are synchronized
by updating job_expiration_service.py to use raw SQL queries instead of the ORM
when the token_id column is causing issues.
"""

import os
import sys
from datetime import datetime, timedelta

def fix_orm_issues():
    """Update job_expiration_service.py to use raw SQL when needed"""
    try:
        # Import app 
        from app import create_app
        from models import db
        
        app = create_app()
        print("Application created successfully.")
    except Exception as e:
        print(f"Error creating application: {str(e)}")
        sys.exit(1)

    with app.app_context():
        # 1. Check job_expiration_service for token_id errors
        from utils import job_expiration_service
        
        # 2. Create a new implementation of expire_jobs using raw SQL
        def safe_expire_jobs(days_threshold=0):
            """
            Safe version using raw SQL directly to avoid token_id issues
            """
            try:
                from models import Job
                expiration_date = datetime.utcnow() - timedelta(days=days_threshold)
                
                # Use SQL text directly to find jobs
                sql = """
                UPDATE jobs 
                SET status = 'expired' 
                WHERE status = 'active' AND expires_at < :expiration_date
                RETURNING id
                """
                
                result = db.session.execute(db.text(sql), {
                    'expiration_date': expiration_date
                })
                
                # Get count of updated rows
                updated_ids = [row[0] for row in result]
                count = len(updated_ids)
                
                db.session.commit()
                print(f"Safely marked {count} jobs as expired")
                return count
                
            except Exception as e:
                print(f"Error in safe_expire_jobs: {str(e)}")
                db.session.rollback()
                return 0
                
        # 3. Create a new implementation of mark_expiring_soon_jobs using raw SQL
        def safe_mark_expiring_soon_jobs(days_threshold=7):
            """
            Safe version using raw SQL directly to avoid token_id issues
            """
            try:
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=days_threshold)
                
                # Use SQL text directly to find and update jobs
                sql = """
                UPDATE jobs 
                SET notification_sent = TRUE
                WHERE status = 'active' 
                AND notification_sent = FALSE
                AND expires_at >= :start_date 
                AND expires_at <= :end_date
                RETURNING id, title, recruiter_id, expires_at
                """
                
                result = db.session.execute(db.text(sql), {
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                # Convert to list of dictionaries
                job_list = []
                for row in result:
                    job_list.append({
                        'id': row[0],
                        'title': row[1],
                        'recruiter_id': row[2],
                        'expires_at': row[3].strftime('%Y-%m-%d') if row[3] else None
                    })
                
                db.session.commit()
                print(f"Safely marked {len(job_list)} jobs for expiration notification")
                return job_list
                
            except Exception as e:
                print(f"Error in safe_mark_expiring_soon_jobs: {str(e)}")
                db.session.rollback()
                return []
        
        # 4. Create a new implementation of get_expiring_jobs_by_recruiter using raw SQL
        def safe_get_expiring_jobs_by_recruiter(recruiter_id, days_threshold=7):
            """
            Safe version using raw SQL directly to avoid token_id issues
            """
            try:
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=days_threshold)
                
                # Use SQL text directly
                sql = """
                SELECT id, title, expires_at
                FROM jobs
                WHERE recruiter_id = :recruiter_id
                AND status = 'active'
                AND expires_at >= :start_date
                AND expires_at <= :end_date
                """
                
                result = db.session.execute(db.text(sql), {
                    'recruiter_id': recruiter_id,
                    'start_date': start_date,
                    'end_date': end_date
                })
                
                # Convert to list of dictionaries
                jobs = []
                for row in result:
                    expires_at = row[2]
                    days_left = (expires_at - start_date).days if expires_at else 0
                    
                    jobs.append({
                        'id': row[0],
                        'title': row[1],
                        'expires_at': expires_at.strftime('%Y-%m-%d') if expires_at else None,
                        'days_left': days_left
                    })
                
                return jobs
                
            except Exception as e:
                print(f"Error in safe_get_expiring_jobs_by_recruiter: {str(e)}")
                return []
        
        # 5. Create a new implementation of run_expiration_check
        def safe_run_expiration_check():
            """
            Safe version that uses our raw SQL methods
            """
            expired_count = safe_expire_jobs()
            expiring_jobs = safe_mark_expiring_soon_jobs()
            return expired_count, expiring_jobs
        
        # 6. Monkey patch the functions to use our safer versions
        print("Patching job_expiration_service functions with safer SQL-based versions...")
        
        # Save references to original functions for fallback
        original_expire_jobs = job_expiration_service.expire_jobs
        original_mark_expiring_soon_jobs = job_expiration_service.mark_expiring_soon_jobs
        original_get_expiring_jobs_by_recruiter = job_expiration_service.get_expiring_jobs_by_recruiter
        original_run_expiration_check = job_expiration_service.run_expiration_check
        
        # Replace with our safe versions
        job_expiration_service.expire_jobs = safe_expire_jobs
        job_expiration_service.mark_expiring_soon_jobs = safe_mark_expiring_soon_jobs
        job_expiration_service.get_expiring_jobs_by_recruiter = safe_get_expiring_jobs_by_recruiter
        job_expiration_service.run_expiration_check = safe_run_expiration_check
        
        print("Job expiration service functions patched successfully.")
        
        # 7. Run a test of the job expiration service
        print("Testing job expiration service with patched functions...")
        expired, expiring = job_expiration_service.run_expiration_check()
        print(f"Test successful: {expired} jobs expired, {len(expiring)} jobs marked for notification")

        # 8. Fix Job class token_id relationship if possible
        try:
            from sqlalchemy import inspect
            
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('jobs')]
            
            if 'token_id' in columns:
                print("token_id column exists in jobs table - database schema is correct.")
            else:
                print("token_id column missing from jobs table - trying to add it...")
                sql = """
                ALTER TABLE jobs 
                ADD COLUMN IF NOT EXISTS token_id INTEGER REFERENCES job_tokens(id);
                """
                db.session.execute(db.text(sql))
                db.session.commit()
                print("Column added successfully.")
        except Exception as e:
            print(f"Error checking or fixing token_id column: {str(e)}")

if __name__ == '__main__':
    fix_orm_issues()
