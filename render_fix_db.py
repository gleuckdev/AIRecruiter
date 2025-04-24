"""
Emergency database fix for Render deployment.
This script directly fixes the database schema using raw SQL commands
"""

import os
import sys
import time
from datetime import datetime, timedelta

def direct_db_fix():
    """Directly fix the database without using ORM"""
    # Get database URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable is not set")
        sys.exit(1)
        
    print(f"Connecting to database: {db_url.split('@')[1] if '@' in db_url else 'Unknown'}")
    
    try:
        import psycopg2
        
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to database successfully.")
        
        # Step 1: Get list of existing tables
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {', '.join(tables)}")
        
        # Step 2: Fix the jobs table
        print("\nFIXING JOBS TABLE")
        
        # Check if token_id column exists in jobs table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'token_id'
        """)
        
        if not cursor.fetchone():
            print("Adding token_id column to jobs table...")
            try:
                cursor.execute("""
                    ALTER TABLE jobs 
                    ADD COLUMN token_id INTEGER REFERENCES job_tokens(id);
                """)
                print("✓ Successfully added token_id column to jobs table")
            except Exception as e:
                print(f"✗ Error adding token_id column: {str(e)}")
                
        # Check if expires_at column exists in jobs table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'expires_at'
        """)
        
        if not cursor.fetchone():
            print("Adding expires_at column to jobs table...")
            try:
                cursor.execute("""
                    ALTER TABLE jobs 
                    ADD COLUMN expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '60 days');
                """)
                print("✓ Successfully added expires_at column to jobs table")
            except Exception as e:
                print(f"✗ Error adding expires_at column: {str(e)}")
                
        # Check if notification_sent column exists in jobs table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'notification_sent'
        """)
        
        if not cursor.fetchone():
            print("Adding notification_sent column to jobs table...")
            try:
                cursor.execute("""
                    ALTER TABLE jobs 
                    ADD COLUMN notification_sent BOOLEAN DEFAULT FALSE;
                """)
                print("✓ Successfully added notification_sent column to jobs table")
            except Exception as e:
                print(f"✗ Error adding notification_sent column: {str(e)}")
                
        # Check if last_renewed_at column exists in jobs table
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'last_renewed_at'
        """)
        
        if not cursor.fetchone():
            print("Adding last_renewed_at column to jobs table...")
            try:
                cursor.execute("""
                    ALTER TABLE jobs 
                    ADD COLUMN last_renewed_at TIMESTAMP;
                """)
                print("✓ Successfully added last_renewed_at column to jobs table")
            except Exception as e:
                print(f"✗ Error adding last_renewed_at column: {str(e)}")
        
        # Step 3: Create job_tokens table if it doesn't exist
        print("\nCHECKING JOB_TOKENS TABLE")
        
        if 'job_tokens' not in tables:
            print("Creating job_tokens table...")
            try:
                cursor.execute("""
                    CREATE TABLE job_tokens (
                        id SERIAL PRIMARY KEY,
                        token_hash VARCHAR(64) UNIQUE,
                        base_title VARCHAR(255),
                        base_location VARCHAR(255),
                        description_vector TEXT,
                        job_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                print("✓ Successfully created job_tokens table")
            except Exception as e:
                print(f"✗ Error creating job_tokens table: {str(e)}")
                
        # Step 4: Create or fix all tables - for full compatibility
        print("\nVERIFYING ALL REQUIRED TABLES AND COLUMNS")
        
        # Fix uploads directory
        try:
            if not os.path.exists('./static/uploads'):
                os.makedirs('./static/uploads')
                print("✓ Created static/uploads directory")
        except Exception as e:
            print(f"✗ Error creating uploads directory: {str(e)}")
        
        # Verify the database now has the correct schema
        print("\nDATABASE VERIFICATION")
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in database: {', '.join(tables)}")
        
        for table in tables:
            cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table}'
                ORDER BY column_name;
            """)
            columns = [row[0] for row in cursor.fetchall()]
            print(f"Columns in {table}: {', '.join(columns)}")
        
        # Step 5: Create monkey patched functions to bypass ORM
        print("\nCREATING OVERRIDE FUNCTIONS")
        
        # Write override file to handle ORM issues
        with open('override_orm.py', 'w') as f:
            f.write("""
# Override ORM functions that have issues on Render
import os
import logging
from datetime import datetime, timedelta
import psycopg2

logger = logging.getLogger(__name__)

# Monkey patch the job_expiration_service functions
def patch_job_expiration():
    try:
        from utils import job_expiration_service
        
        # Define new functions
        def direct_expire_jobs(days_threshold=0):
            try:
                expiration_date = datetime.utcnow() - timedelta(days=days_threshold)
                
                # Use direct psycopg2 connection
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Use basic SQL to update jobs
                cursor.execute(
                    "UPDATE jobs SET status = 'expired' WHERE status = 'active' AND expires_at < %s RETURNING id",
                    (expiration_date,)
                )
                
                # Get count of updated rows
                expired_ids = [row[0] for row in cursor.fetchall()]
                count = len(expired_ids)
                
                cursor.close()
                conn.close()
                
                logger.info(f"Marked {count} jobs as expired")
                return count
                
            except Exception as e:
                logger.error(f"Error in direct_expire_jobs: {str(e)}")
                return 0
                
        def direct_mark_expiring_soon_jobs(days_threshold=7):
            try:
                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=days_threshold)
                
                # Use direct psycopg2 connection
                conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Use basic SQL to update jobs
                cursor.execute(
                    "UPDATE jobs SET notification_sent = TRUE WHERE status = 'active' AND notification_sent = FALSE AND expires_at >= %s AND expires_at <= %s RETURNING id, title, recruiter_id, expires_at",
                    (start_date, end_date)
                )
                
                # Convert to list of dictionaries
                job_list = []
                for row in cursor.fetchall():
                    job_list.append({
                        'id': row[0],
                        'title': row[1],
                        'recruiter_id': row[2],
                        'expires_at': row[3].strftime('%Y-%m-%d') if row[3] else None
                    })
                
                cursor.close()
                conn.close()
                
                logger.info(f"Marked {len(job_list)} jobs for expiration notification")
                return job_list
                
            except Exception as e:
                logger.error(f"Error in direct_mark_expiring_soon_jobs: {str(e)}")
                return []
                
        def direct_run_expiration_check():
            expired_count = direct_expire_jobs()
            expiring_jobs = direct_mark_expiring_soon_jobs()
            return expired_count, expiring_jobs
            
        # Replace the original functions with our direct SQL versions
        job_expiration_service.expire_jobs = direct_expire_jobs
        job_expiration_service.mark_expiring_soon_jobs = direct_mark_expiring_soon_jobs
        job_expiration_service.run_expiration_check = direct_run_expiration_check
        
        logger.info("Patched job_expiration_service functions with direct SQL versions")
        return True
    except Exception as e:
        logger.error(f"Failed to patch job_expiration_service: {str(e)}")
        return False
""")
        print("✓ Created override_orm.py file")
            
        # Step 6: Create utility for importing the patch
        with open('patch_render.py', 'w') as f:
            f.write("""
# Patch for Render deployment
import sys
import logging

logger = logging.getLogger(__name__)

def apply_render_patch():
    logger.info("Applying Render-specific patches...")
    try:
        from override_orm import patch_job_expiration
        success = patch_job_expiration()
        logger.info(f"Applied job expiration patch: {'Success' if success else 'Failed'}")
        return success
    except Exception as e:
        logger.error(f"Failed to apply Render patch: {str(e)}")
        return False
        
if __name__ == '__main__':
    apply_render_patch()
""")
        print("✓ Created patch_render.py file")
        
        # Step 7: Clean up
        cursor.close()
        conn.close()
        
        print("\nDATABASE FIX COMPLETED")
        print("You should now use the build command: python render_fix_db.py && python patch_render.py && gunicorn main:app")
        
    except Exception as e:
        print(f"Error fixing database: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    direct_db_fix()
