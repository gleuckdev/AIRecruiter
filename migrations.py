# Trigger migration re-run
from flask_migrate import Migrate
from app import create_app
from models import db

app = create_app()
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        import alembic.operations as ops
        from alembic.migration import MigrationContext
        from sqlalchemy import Column, Integer, JSON, ForeignKey, String, Text, Float, DateTime, Boolean
        from sqlalchemy.sql import func
        import psycopg2
        from datetime import datetime, timedelta

        # Separate transaction for each migration
        def run_migration(migration_fn, description):
            # Get a fresh connection for each migration
            with db.engine.connect() as conn:
                # Create a MigrationContext
                ctx = MigrationContext.configure(conn)
                # Create an operations object
                op = ops.Operations(ctx)
                
                try:
                    # Start transaction
                    conn.connection.connection.autocommit = False
                    # Run the migration
                    migration_fn(op, conn)
                    # Commit if successful
                    conn.connection.connection.commit()
                    print(f"Success: {description}")
                except Exception as e:
                    # Rollback on error
                    conn.connection.connection.rollback()
                    print(f"Error: {description} - {str(e)}")

        # Migration functions
        def add_persona_column(op, conn):
            op.add_column('candidates', Column('persona', JSON))
            
        def add_uploaded_by_column(op, conn):
            op.add_column('candidates', Column('uploaded_by', Integer, ForeignKey('recruiters.id')))
            
        def add_job_id_column(op, conn):
            op.add_column('candidates', Column('job_id', Integer, ForeignKey('jobs.id')))
            
        def create_ratings_table(op, conn):
            op.create_table(
                'candidate_ratings',
                Column('id', Integer, primary_key=True),
                Column('candidate_id', Integer, ForeignKey('candidates.id'), nullable=False),
                Column('recruiter_id', Integer, ForeignKey('recruiters.id'), nullable=False),
                Column('score', Float, nullable=False),  # Changed from Integer to Float for 0-1 scale
                Column('notes', Text),
                Column('created_at', DateTime, default=func.now()),
                Column('updated_at', DateTime, default=func.now(), onupdate=func.now())
            )
            
        def alter_score_column(op, conn):
            # Direct SQL execution because we need to handle existing tables
            from sqlalchemy.sql import text
            conn.execute(text("ALTER TABLE candidate_ratings ALTER COLUMN score TYPE FLOAT USING score::float"))
        
        # Role-based permission system migrations
        def create_roles_table(op, conn):
            import json
            op.create_table(
                'roles',
                Column('id', Integer, primary_key=True),
                Column('role_id', String(50), unique=True, nullable=False),
                Column('name', String(100), nullable=False),
                Column('permissions', JSON, nullable=False, server_default='[]'),
                Column('inherits', String(50), nullable=True),
                Column('created_at', DateTime, default=func.now())
            )
            
            # Insert default roles
            from sqlalchemy.sql import text
            # Admin role
            admin_permissions = [
                'users:create', 'users:view', 'users:edit', 'users:delete',
                'jobs:create', 'jobs:view', 'jobs:edit', 'jobs:delete', 'jobs:list', 'jobs:approve',
                'candidates:view', 'candidates:add', 'candidates:edit', 'candidates:delete', 'candidates:rate',
                'notes:create', 'notes:view', 'notes:edit', 'notes:delete', 'notes:delete_any',
                'audits:view', 'settings:edit'
            ]
            
            # Senior recruiter role
            senior_recruiter_permissions = [
                'jobs:create', 'jobs:view', 'jobs:edit', 'jobs:delete', 'jobs:list',
                'candidates:rate',
                'notes:delete_any'
            ]
            
            # Recruiter role
            recruiter_permissions = [
                'candidates:view', 'candidates:add',
                'notes:create', 'notes:view', 'notes:edit', 'notes:delete',
                'jobs:list', 'jobs:view'
            ]
            
            conn.execute(text(
                "INSERT INTO roles (role_id, name, permissions, inherits) VALUES ('admin', 'Administrator', :permissions, NULL)"
            ), {'permissions': json.dumps(admin_permissions)})
            
            conn.execute(text(
                "INSERT INTO roles (role_id, name, permissions, inherits) VALUES ('senior_recruiter', 'Senior Recruiter', :permissions, 'recruiter')"
            ), {'permissions': json.dumps(senior_recruiter_permissions)})
            
            conn.execute(text(
                "INSERT INTO roles (role_id, name, permissions, inherits) VALUES ('recruiter', 'Recruiter', :permissions, NULL)"
            ), {'permissions': json.dumps(recruiter_permissions)})
            
        def add_role_fields(op, conn):
            # Add role_id to recruiters
            op.add_column('recruiters', Column('role_id', String(50), ForeignKey('roles.role_id'), server_default="'recruiter'"))
            
            # Make sure role column exists
            try:
                op.add_column('recruiters', Column('role', String(20), server_default="'recruiter'"))
            except:
                # May already exist
                pass
                
            # Add role_id to invitations
            op.add_column('invitations', Column('role_id', String(50), ForeignKey('roles.role_id'), server_default="'recruiter'"))
            
            # Update existing admin recruiters
            from sqlalchemy.sql import text
            conn.execute(text("UPDATE recruiters SET role_id = 'admin' WHERE id = 1"))
        
        # Run each migration in separate transactions
        run_migration(add_persona_column, "Added persona column to candidates table")
        run_migration(add_uploaded_by_column, "Added uploaded_by column to candidates table")
        run_migration(add_job_id_column, "Added job_id column to candidates table")
        run_migration(create_ratings_table, "Created candidate_ratings table")
        run_migration(alter_score_column, "Altered score column type to FLOAT")
        run_migration(create_roles_table, "Created roles table with default roles")
        run_migration(add_role_fields, "Added role_id fields to recruiters and invitations")
        
        # Data sharing migrations
        def add_sharing_fields_to_invitation(op, conn):
            op.add_column('invitations', Column('share_jobs', Boolean, server_default="FALSE"))
            op.add_column('invitations', Column('share_candidates', Boolean, server_default="FALSE"))
            
        def create_recruiter_sharing_table(op, conn):
            op.create_table(
                'recruiter_sharing',
                Column('id', Integer, primary_key=True),
                Column('owner_id', Integer, ForeignKey('recruiters.id'), nullable=False),
                Column('shared_with_id', Integer, ForeignKey('recruiters.id'), nullable=False),
                Column('share_jobs', Boolean, default=False),
                Column('share_candidates', Boolean, default=False),
                Column('created_at', DateTime, default=func.now())
            )
            # Add unique constraint
            op.create_unique_constraint('uq_recruiter_sharing', 'recruiter_sharing', ['owner_id', 'shared_with_id'])
            
        # Job token related migrations
        def create_job_tokens_table(op, conn):
            op.create_table(
                'job_tokens',
                Column('id', Integer, primary_key=True),
                Column('token_hash', String(64), unique=True),
                Column('base_title', String(255)),
                Column('base_location', String(255)),
                Column('description_vector', Text),
                Column('job_count', Integer, server_default="1"),
                Column('created_at', DateTime, default=func.now())
            )
            # Add index for token_hash
            op.create_index('ix_job_tokens_token_hash', 'job_tokens', ['token_hash'])
            
        def add_token_id_to_jobs(op, conn):
            op.add_column('jobs', Column('token_id', Integer, ForeignKey('job_tokens.id')))
        
        # Email constraint migration
        def modify_candidate_email_constraint(op, conn):
            # First remove the unique constraint
            from sqlalchemy.sql import text
            conn.execute(text("ALTER TABLE candidates DROP CONSTRAINT IF EXISTS candidates_email_key"))
            
            # Then modify the column to allow NULL values
            conn.execute(text("ALTER TABLE candidates ALTER COLUMN email DROP NOT NULL"))
            
            # Add a conditional unique constraint that only applies when email is not null or empty
            conn.execute(text("CREATE UNIQUE INDEX candidates_email_unique_idx ON candidates (email) WHERE email IS NOT NULL AND email != ''"))
            
        # Run the new migrations
        run_migration(add_sharing_fields_to_invitation, "Added data sharing fields to invitations table")
        run_migration(create_recruiter_sharing_table, "Created recruiter sharing table")
        run_migration(create_job_tokens_table, "Created job_tokens table")
        run_migration(add_token_id_to_jobs, "Added token_id to jobs table")
        run_migration(modify_candidate_email_constraint, "Modified candidate email constraints to allow empty/null values")
        
        # Job expiration and renewal migrations
        def add_job_expiration_fields(op, conn):
            from sqlalchemy.sql import text as sql_text
            
            op.add_column('jobs', Column('expires_at', DateTime, 
                                         server_default=func.now() + sql_text("INTERVAL '60 days'")))
            op.add_column('jobs', Column('notification_sent', Boolean, server_default="FALSE"))
            op.add_column('jobs', Column('last_renewed_at', DateTime, nullable=True))
            
            # Update existing jobs to set expires_at to 60 days from today
            conn.execute(sql_text("UPDATE jobs SET expires_at = CURRENT_TIMESTAMP + INTERVAL '60 days' WHERE expires_at IS NULL"))
            
        # Run the job expiration migration
        run_migration(add_job_expiration_fields, "Added job expiration and renewal fields")
def add_token_id_column_to_jobs(op, conn):
    from sqlalchemy import inspect
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('jobs')]
    
    if 'token_id' not in columns:
        op.add_column('jobs', Column('token_id', String, unique=True))
    else:
        print("ℹ️ 'token_id' column already exists in jobs table.")
run_migration(add_token_id_column_to_jobs, "Added token_id column to jobs table")
