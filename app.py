# app.py
import os
import bcrypt
import jwt
import json
import logging
import threading
import time
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from io import BytesIO
import openai
from google.cloud import storage

from models import db, Recruiter, Job, Candidate, JobCandidateMatch, Session, Invitation, CandidateRating, Role, RecruiterSharing
from utils.roles import initialize_roles
from utils.role_manager import get_all_roles, get_all_recruiters, change_recruiter_role, can_change_role
from utils.job_expiration_service import expire_jobs, mark_expiring_soon_jobs, renew_job, get_expiring_jobs_by_recruiter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", os.environ.get('SECRET_KEY', 'fallback-dev-key'))
    app.config.update({
        'MAX_CONTENT_LENGTH': 5 * 1024 * 1024,
        'ALLOWED_EXTENSIONS': {'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg'},
        'RATE_LIMITS': {'auth': '5/minute', 'jobs': '10/minute', 'uploads': '10/minute'},
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_pre_ping': True,
            'pool_recycle': 280,
            'connect_args': {
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5
            }
        }
    })
    
    # Initialize services
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    
    # Initialize GCS client only if credentials are available and valid
    gcs_client = None
    try:
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            gcs_client = storage.Client()
            logger.info("Google Cloud Storage client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize GCS client: {str(e)}")
        logger.error("Will fall back to local storage for file uploads")
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        
        # Initialize roles
        initialize_roles(db.session)
        
        # Create a demo recruiter account if none exists
        if not Recruiter.query.filter_by(email='demo@example.com').first():
            demo_recruiter = Recruiter(
                name='Demo Recruiter',
                email='demo@example.com',
                role='admin',
                role_id='admin'
            )
            demo_recruiter.set_password('password123')
            db.session.add(demo_recruiter)
            db.session.commit()
        
        # Schedule job expiration check to run daily
        def run_scheduled_job_expiration_check():
            with app.app_context():
                try:
                    logger.info("Running scheduled job expiration check")
                    expired_count = expire_jobs()
                    expiring_jobs = mark_expiring_soon_jobs()
                    logger.info(f"Scheduled task completed: {expired_count} jobs expired, {len(expiring_jobs)} jobs marked for notification")
                except Exception as e:
                    logger.error(f"Error in scheduled job expiration check: {str(e)}")
                    
        # Run the expiration check immediately on startup
        threading.Thread(target=run_scheduled_job_expiration_check).start()
        
        # Set up a scheduler for daily checks
        def schedule_daily_expiration_check():
            while True:
                # Sleep until next day at 1 AM
                now = datetime.now()
                next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)
                    
                sleep_seconds = (next_run - now).total_seconds()
                logger.info(f"Job expiration checker scheduled to run in {sleep_seconds/3600:.1f} hours")
                time.sleep(sleep_seconds)
                
                # Run the check
                run_scheduled_job_expiration_check()
                
        # Start the scheduler in a background thread
        threading.Thread(target=schedule_daily_expiration_check, daemon=True).start()
    
    # Rate Limiter
    class RateLimiter:
        def __init__(self):
            self.windows = {}
            
        def hit(self, key, limit, window):
            now = datetime.now().timestamp()
            window_key = f"{key}_{window}"
            
            if window_key not in self.windows:
                self.windows[window_key] = []
                
            timestamps = [t for t in self.windows[window_key] if t > now - window]
            
            if len(timestamps) >= limit:
                return False
                
            timestamps.append(now)
            self.windows[window_key] = timestamps
            return True
    
    limiter = RateLimiter()
    
    # Decorators
    def rate_limited(endpoint):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                limit, window = parse_rate_limit(app.config['RATE_LIMITS'].get(endpoint, '10/hour'))
                key = f"{endpoint}_{request.remote_addr}"
                
                if not limiter.hit(key, limit, window):
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def recruiter_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.cookies.get('access_token')
            if not token:
                return redirect(url_for('recruiter_login'))
                
            try:
                payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
                session = Session.query.get(payload['session_id'])
                
                if not session or session.expires_at < datetime.utcnow():
                    raise jwt.InvalidTokenError
                    
                # Add recruiter info to kwargs
                recruiter = Recruiter.query.get(session.recruiter_id)
                if not recruiter:
                    raise jwt.InvalidTokenError
                    
                kwargs['recruiter'] = recruiter
                    
            except jwt.ExpiredSignatureError:
                return redirect(url_for('recruiter_login'))
            except jwt.InvalidTokenError:
                return redirect(url_for('recruiter_login'))
                
            return f(*args, **kwargs)
        return decorated
    
    def requires_permission(permission):
        """
        Decorator that checks if the current recruiter has the specified permission.
        Must be used after @recruiter_required to ensure the recruiter object is available.
        
        Args:
            permission: The permission string to check (e.g., 'jobs:create')
            
        Returns:
            Decorated function
        """
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                recruiter = kwargs.get('recruiter')
                
                if not recruiter:
                    logger.error("requires_permission used without recruiter_required")
                    return jsonify({'error': 'Server configuration error'}), 500
                
                if not recruiter.has_permission(permission):
                    logger.warning(f"Permission denied: {recruiter.email} attempted to access {permission}")
                    
                    # For API requests, return a JSON response
                    if request.path.startswith('/api/'):
                        return jsonify({
                            'error': 'Permission denied',
                            'details': f'This action requires the {permission} permission',
                            'required_role': 'Senior Recruiter or Administrator',
                            'current_role': recruiter.role_id,
                            'code': 'permission_denied'
                        }), 403
                    
                    # For regular requests, use flash message and redirect
                    flash("You don't have permission to access this resource", "error")
                    return redirect(url_for('dashboard'))
                
                return f(*args, **kwargs)
            return decorated
        return decorator
    
    # File handling
    def upload_to_gcs(content, filename):
        """
        Upload a file to Google Cloud Storage or fall back to local storage
        """
        # Try to use GCS if client is available
        if gcs_client:
            try:
                bucket_name = os.environ.get('GCS_BUCKET_NAME')
                if not bucket_name:
                    logger.warning("GCS_BUCKET_NAME environment variable not set")
                else:
                    bucket = gcs_client.bucket(bucket_name)
                    blob = bucket.blob(f"resumes/{filename}")
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    blob.upload_from_string(content)
                    # Make blob publicly accessible
                    blob.make_public()
                    logger.info(f"Successfully uploaded file to GCS: {blob.public_url}")
                    return blob.public_url
            except Exception as e:
                logger.error(f"GCS upload failed: {str(e)}")
                # Continue to local storage fallback
        
        # Fallback to local storage
        logger.info(f"Falling back to local storage for file: {filename}")
        try:
            # Ensure the uploads directory exists
            upload_dir = os.path.join('static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save file locally
            local_path = os.path.join(upload_dir, filename)
            if isinstance(content, str):
                with open(local_path, 'w') as f:
                    f.write(content)
            else:
                with open(local_path, 'wb') as f:
                    f.write(content)
            
            # Return the relative URL path for the file
            url_path = f"/static/uploads/{filename}"
            logger.info(f"File saved locally at: {url_path}")
            return url_path
        except Exception as e:
            logger.error(f"Local storage fallback failed: {str(e)}")
            return None
            
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    # Routes
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/recruiter/login')
    def recruiter_login():
        token = request.cookies.get('access_token')
        if token:
            try:
                payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
                session = Session.query.get(payload['session_id'])
                if session and session.expires_at > datetime.utcnow():
                    return redirect(url_for('dashboard'))
            except:
                pass
        return render_template('recruiter_login.html')
    
    @app.route('/sharing')
    @recruiter_required
    def manage_sharing(recruiter):
        try:
            # Get sharing relationships where current recruiter is the owner
            shared_with = RecruiterSharing.query.filter_by(owner_id=recruiter.id).all()
            
            # Get sharing relationships where current recruiter has access to others' data
            shared_by = RecruiterSharing.query.filter_by(shared_with_id=recruiter.id).all()
            
            # Get recruiters not already in a sharing relationship with the current user
            subquery = db.session.query(RecruiterSharing.shared_with_id).filter_by(owner_id=recruiter.id)
            available_recruiters = Recruiter.query.filter(
                Recruiter.id != recruiter.id,
                ~Recruiter.id.in_(subquery)
            ).all()
            
            return render_template(
                'sharing.html',
                current_user=recruiter,
                shared_with=shared_with,
                shared_by=shared_by,
                available_recruiters=available_recruiters
            )
        except Exception as e:
            logger.error(f"Manage sharing error: {str(e)}")
            flash(f"An error occurred while loading sharing data: {str(e)}", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/dashboard')
    @recruiter_required
    def dashboard(recruiter):
        try:
            logger.debug(f"Dashboard accessed by recruiter ID: {recruiter.id}")
            # Get jobs created by this recruiter
            recruiter_jobs = Job.query.filter_by(recruiter_id=recruiter.id).all()
            logger.debug(f"Found {len(recruiter_jobs)} jobs for recruiter")
            
            # Add match info and expiration data to each job
            for job in recruiter_jobs:
                matches = JobCandidateMatch.query.filter_by(job_id=job.id).all()
                job.match_score = round(sum([m.score for m in matches]) / max(1, len(matches)) * 100) if matches else 0
                
                # Add expiration information
                if job.expires_at:
                    days_until_expiry = (job.expires_at - datetime.utcnow()).days
                    job.days_until_expiry = days_until_expiry
                    job.is_expiring_soon = job.is_expiring_soon(7)  # Check if job is expiring within 7 days
            
            # Calculate statistics
            # 1. Total candidates in the system
            total_candidates = Candidate.query.count()
            
            # 2. Job statistics - applications per job
            job_stats = []
            for job in recruiter_jobs:
                applications = JobCandidateMatch.query.filter_by(job_id=job.id).count()
                job_stats.append({
                    'id': job.id,
                    'title': job.title,
                    'applications': applications
                })
            
            return render_template(
                'dashboard.html', 
                jobs=recruiter_jobs, 
                current_user=recruiter,
                total_candidates=total_candidates,
                job_stats=job_stats
            )
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return render_template('error.html', error=str(e))
    
    @app.route('/apply')
    def apply():
        return render_template('candidate_apply.html')
    
    @app.route('/logout')
    def logout():
        response = make_response(redirect(url_for('home')))
        response.delete_cookie('access_token')
        return response
        

        
    @app.route('/download-resume/<int:candidate_id>')
    @recruiter_required
    def download_resume(recruiter, candidate_id):
        """
        Download a candidate's resume with proper headers for browser handling
        
        Args:
            recruiter: The authenticated recruiter (from decorator)
            candidate_id: The ID of the candidate whose resume to download
            
        Returns:
            The resume file as a downloadable attachment
        """
        try:
            candidate = Candidate.query.get_or_404(candidate_id)
            
            # Check if recruiter can access this candidate
            if not recruiter.can_access_candidate(candidate):
                logger.warning(f"Unauthorized resume download attempt: recruiter {recruiter.id} for candidate {candidate_id}")
                flash("You don't have permission to download this resume", "error")
                return redirect(url_for('view_candidates'))
            
            # Check if resume file exists
            if not candidate.resume_file or not candidate.gcs_url:
                logger.error(f"Resume file missing for candidate {candidate_id}")
                flash("No resume file available for this candidate", "error")
                return redirect(url_for('view_candidate_detail', candidate_id=candidate_id))
            
            # Get the file path or URL
            file_path = candidate.gcs_url
            
            # For local files (URL starts with /static)
            if file_path.startswith('/static'):
                local_path = os.path.join(os.getcwd(), file_path.lstrip('/'))
                
                if not os.path.exists(local_path):
                    logger.error(f"Resume file not found at {local_path}")
                    flash("Resume file could not be found", "error")
                    return redirect(url_for('view_candidate_detail', candidate_id=candidate_id))
                
                # Get file extension to set correct MIME type
                file_ext = os.path.splitext(local_path)[1].lower()
                mime_type = 'application/pdf'  # Default to PDF
                
                if file_ext == '.docx':
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif file_ext == '.doc':
                    mime_type = 'application/msword'
                elif file_ext == '.txt':
                    mime_type = 'text/plain'
                
                # Return the file with proper headers
                return send_file(
                    local_path,
                    mimetype=mime_type,
                    as_attachment=True,
                    download_name=candidate.resume_file
                )
                
            # For GCS files (full URL)
            elif file_path.startswith('http'):
                # Redirect to the GCS URL (which should be publicly accessible)
                return redirect(file_path)
            
            # For other cases, return an error
            logger.error(f"Unrecognized file path format: {file_path}")
            flash("Could not download resume due to an invalid file path", "error")
            return redirect(url_for('view_candidate_detail', candidate_id=candidate_id))
                
        except Exception as e:
            logger.error(f"Error downloading resume: {str(e)}")
            flash(f"An error occurred while downloading the resume: {str(e)}", "error")
            return redirect(url_for('view_candidate_detail', candidate_id=candidate_id))
    
    # Unified User Management Routes
    @app.route('/user-management')
    @recruiter_required
    @requires_permission('users:view')
    def user_management(recruiter):
        try:
            # Fetch all recruiters and roles
            recruiters = get_all_recruiters()
            roles = get_all_roles()
            
            # Fetch pending invitations
            invitations = Invitation.query.filter_by(used=False).all()
            
            return render_template(
                'user_management.html',
                current_user=recruiter,
                recruiters=recruiters,
                roles=roles,
                invitations=invitations
            )
        except Exception as e:
            logger.error(f"User management error: {str(e)}")
            flash(f"An error occurred while loading user management: {str(e)}", "error")
            return redirect(url_for('dashboard'))
    
    @app.route('/api/roles', methods=['GET'])
    @recruiter_required
    @requires_permission('users:view')
    def get_roles(recruiter):
        try:
            roles = get_all_roles()
            roles_data = []
            
            for role in roles:
                roles_data.append({
                    'id': role.role_id,
                    'name': role.name,
                    'permissions': role.permissions,
                    'inherits': role.inherits
                })
                
            return jsonify({'roles': roles_data})
        except Exception as e:
            logger.error(f"Get roles error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/recruiters', methods=['GET'])
    @recruiter_required
    @requires_permission('users:view')
    def get_recruiters(recruiter):
        try:
            recruiters = get_all_recruiters()
            recruiters_data = []
            
            for rec in recruiters:
                recruiters_data.append({
                    'id': rec.id,
                    'name': rec.name,
                    'email': rec.email,
                    'role': rec.role_id,
                    'created_at': rec.created_at.isoformat()
                })
                
            return jsonify({'recruiters': recruiters_data})
        except Exception as e:
            logger.error(f"Get recruiters error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/recruiters/<int:recruiter_id>/role', methods=['PUT'])
    @recruiter_required
    def update_recruiter_role(recruiter, recruiter_id):
        try:
            logger.debug(f"Role update request received for recruiter ID: {recruiter_id}")
            logger.debug(f"Request data: {request.data}")
            
            # Don't allow changing your own role
            if recruiter_id == recruiter.id:
                logger.warning(f"Self role change attempt by {recruiter.email}")
                return jsonify({
                    'error': 'You cannot change your own role',
                    'code': 'self_change_not_allowed'
                }), 403
                
            # Get the target recruiter
            target_recruiter = Recruiter.query.get(recruiter_id)
            if not target_recruiter:
                logger.error(f"Target recruiter {recruiter_id} not found")
                return jsonify({'error': 'Recruiter not found'}), 404
                
            # Get request data - try multiple approaches due to potential Content-Type issues
            data = None
            if request.is_json:
                data = request.get_json()
                logger.debug("Request is JSON format")
            elif request.form:
                data = request.form.to_dict()
                logger.debug("Request is form data format")
            elif request.data:
                try:
                    data = json.loads(request.data)
                    logger.debug("Parsed data from request.data")
                except:
                    logger.error(f"Failed to parse JSON from request.data: {request.data}")
            
            logger.debug(f"Processed request data: {data}")
            
            if not data or 'role_id' not in data:
                logger.error("Missing role_id in request data")
                return jsonify({'error': 'Missing role_id in request'}), 400
            
            new_role_id = data['role_id']
            logger.debug(f"Requested new role: {new_role_id}")
                
            # Check permissions
            logger.debug(f"Checking if {recruiter.email} can change {target_recruiter.email} to role {new_role_id}")
            allowed, reason = can_change_role(recruiter, target_recruiter, new_role_id)
            if not allowed:
                logger.warning(f"Role change permission denied: {reason}")
                return jsonify({
                    'error': reason,
                    'code': 'permission_denied',
                    'details': reason
                }), 403
                
            # Update the role
            logger.debug(f"Changing role for {target_recruiter.email} from {target_recruiter.role_id} to {new_role_id}")
            success, message = change_recruiter_role(
                recruiter_id,
                new_role_id,
                changed_by_id=recruiter.id
            )
            
            if success:
                logger.info(f"Role updated successfully for {target_recruiter.email} to {new_role_id}")
                return jsonify({
                    'success': True,
                    'message': message,
                    'recruiter': {
                        'id': target_recruiter.id,
                        'name': target_recruiter.name,
                        'email': target_recruiter.email,
                        'role': new_role_id
                    }
                })
            else:
                logger.error(f"Role update failed: {message}")
                return jsonify({'error': message}), 400
                
        except Exception as e:
            logger.error(f"Update recruiter role error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/recruiters/<int:recruiter_id>', methods=['DELETE'])
    @recruiter_required
    @requires_permission('users:admin')
    def delete_recruiter(recruiter, recruiter_id):
        try:
            if recruiter_id == recruiter.id:
                logger.warning(f"Recruiter {recruiter.email} attempted to delete themselves")
                return jsonify({
                    'error': 'You cannot delete your own account',
                    'code': 'self_delete_not_allowed'
                }), 403
                
            target_recruiter = Recruiter.query.get(recruiter_id)
            if not target_recruiter:
                return jsonify({'error': 'User not found'}), 404
                
            # Don't allow deleting another admin unless you're an admin
            if target_recruiter.is_admin() and not recruiter.is_admin():
                logger.warning(f"Non-admin {recruiter.email} tried to delete admin {target_recruiter.email}")
                return jsonify({
                    'error': 'Permission denied',
                    'details': 'Only administrators can remove other administrators',
                    'code': 'permission_denied'
                }), 403
                
            # Store the name for the response
            deleted_name = target_recruiter.name
            deleted_email = target_recruiter.email
            
            # Delete the user's sessions
            Session.query.filter_by(recruiter_id=recruiter_id).delete()
            
            # Delete the user's ratings
            CandidateRating.query.filter_by(recruiter_id=recruiter_id).delete()
            
            # Delete sharing relations
            RecruiterSharing.query.filter(
                (RecruiterSharing.owner_id == recruiter_id) | 
                (RecruiterSharing.shared_with_id == recruiter_id)
            ).delete()
            
            # Delete the user
            db.session.delete(target_recruiter)
            db.session.commit()
            
            logger.info(f"Recruiter {deleted_email} ({recruiter_id}) was deleted by {recruiter.email}")
            
            return jsonify({
                'success': True,
                'message': f"User {deleted_name} has been permanently removed",
                'deleted_id': recruiter_id
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Delete recruiter error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/invites/<int:invitation_id>', methods=['DELETE'])
    @recruiter_required
    @requires_permission('users:invite')
    def cancel_invitation(recruiter, invitation_id):
        try:
            invitation = Invitation.query.get(invitation_id)
            
            if not invitation:
                return jsonify({'error': 'Invitation not found'}), 404
                
            # Only admins can delete any invitation
            if invitation.created_by != recruiter.id and not recruiter.is_admin():
                logger.warning(f"Permission denied: {recruiter.email} attempted to delete invitation created by another user")
                return jsonify({
                    'error': 'Permission denied',
                    'details': 'You can only delete invitations that you created',
                    'code': 'permission_denied'
                }), 403
                
            email = invitation.email
            db.session.delete(invitation)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Invitation for {email} has been cancelled',
                'deleted_id': invitation_id
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Delete invitation error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Route moved to avoid duplicate function name
    
    # Invitation Routes
    @app.route('/join/<token>', methods=['GET'])
    def join_with_invitation(token):
        try:
            # Find invitation by token
            invitation = Invitation.query.filter_by(token=token, used=False).first()
            
            if not invitation:
                flash('Invalid or expired invitation link.', 'error')
                return redirect(url_for('home'))
                
            # Check if invitation is expired
            if invitation.expires_at < datetime.utcnow():
                flash('This invitation has expired.', 'error')
                return redirect(url_for('home'))
                
            # Pass invitation data to template
            return render_template('join.html', invitation=invitation, token=token)
        except Exception as e:
            logger.error(f"Join invitation error: {str(e)}")
            flash('An error occurred while processing your invitation.', 'error')
            return redirect(url_for('home'))
            
    @app.route('/api/join', methods=['POST'])
    def process_invitation():
        try:
            data = request.get_json()
            
            if not data or not all(key in data for key in ['token', 'name', 'email', 'password']):
                return jsonify({'error': 'Missing required fields'}), 400
                
            # Find invitation by token
            invitation = Invitation.query.filter_by(token=data['token'], used=False).first()
            
            if not invitation:
                return jsonify({'error': 'Invalid or expired invitation'}), 400
                
            if invitation.expires_at < datetime.utcnow():
                return jsonify({'error': 'This invitation has expired'}), 400
                
            # Check if email matches the invited email
            if invitation.email.lower() != data['email'].lower():
                return jsonify({'error': 'The email does not match the invited email'}), 400
                
            # Check if email is already in use by another recruiter
            if Recruiter.query.filter_by(email=data['email']).first():
                return jsonify({'error': 'Email is already registered'}), 400
                
            # Create new recruiter
            recruiter = Recruiter(
                name=data['name'],
                email=data['email']
            )
            # Set role based on invitation
            recruiter.role = invitation.role
            recruiter.role_id = invitation.role_id
            recruiter.set_password(data['password'])
            
            # Mark invitation as used
            invitation.used = True
            
            db.session.add(recruiter)
            db.session.commit()
            
            # Create data sharing relationship if sharing options were enabled
            inviter = Recruiter.query.get(invitation.created_by)
            if inviter and (invitation.share_jobs or invitation.share_candidates):
                # Create sharing relationship from inviter to new recruiter
                sharing = RecruiterSharing(
                    owner_id=inviter.id,
                    shared_with_id=recruiter.id,
                    share_jobs=invitation.share_jobs,
                    share_candidates=invitation.share_candidates
                )
                
                db.session.add(sharing)
                db.session.commit()
                
                logger.info(f"Created data sharing relationship: {inviter.name} → {recruiter.name} (jobs: {invitation.share_jobs}, candidates: {invitation.share_candidates})")
            
            # Create session and JWT for auto-login
            session_id = os.urandom(16).hex()
            expires_at = datetime.utcnow() + timedelta(hours=4)
            
            # Create JWT token
            access_token = jwt.encode({
                'session_id': session_id,
                'exp': expires_at
            }, app.secret_key, algorithm='HS256')
            
            # Create session record
            session = Session(
                id=session_id,
                recruiter_id=recruiter.id,
                expires_at=expires_at
            )
            db.session.add(session)
            db.session.commit()
            
            response = jsonify({'message': 'Account created successfully', 'redirect': '/dashboard'})
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=False,  # Set to False for local development
                samesite='Lax',
                max_age=14400
            )
            return response
            
        except Exception as e:
            logger.error(f"Process invitation error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/invites', methods=['GET'])
    @recruiter_required
    @requires_permission('users:view')
    def list_invitations(recruiter):
        try:
                
            # Get all unused invitations
            invitations = Invitation.query.filter_by(used=False).all()
            
            invites_data = []
            for invite in invitations:
                invites_data.append({
                    'id': invite.id,
                    'email': invite.email,
                    'token': invite.token,
                    'role': invite.role,
                    'created_at': invite.created_at.isoformat(),
                    'expires_at': invite.expires_at.isoformat(),
                    'share_jobs': invite.share_jobs,
                    'share_candidates': invite.share_candidates
                })
                
            return jsonify({'invites': invites_data})
        except Exception as e:
            logger.error(f"List invitations error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/invites', methods=['POST'])
    @recruiter_required
    @requires_permission('users:invite')
    def create_invitation(recruiter):
        try:
                
            data = request.get_json()
            
            if not data or 'email' not in data:
                return jsonify({'error': 'Email is required'}), 400
                
            email = data.get('email')
            role = data.get('role', 'recruiter')
            role_id = data.get('role_id', 'recruiter')
            share_jobs = data.get('share_jobs', False)
            share_candidates = data.get('share_candidates', False)
            
            # Only admins can send admin invites
            if (role == 'admin' or role_id == 'admin') and not recruiter.has_permission('users:admin'):
                logger.warning(f"Non-admin user {recruiter.email} attempted to create admin invitation")
                role = 'recruiter'
                role_id = 'recruiter'
                flash("Only administrators can create admin invites. Your invitation has been sent as a recruiter invite.", "warning")
            
            # Validate email
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                return jsonify({'error': 'Invalid email format'}), 400
                
            # Check if email already exists
            if Recruiter.query.filter_by(email=email).first():
                return jsonify({'error': 'A recruiter with this email already exists'}), 400
                
            # Check if there's already an active invitation for this email
            existing_invite = Invitation.query.filter_by(email=email, used=False).first()
            if existing_invite:
                return jsonify({'error': 'An invitation for this email already exists'}), 400
                
            # Generate unique token
            token = os.urandom(16).hex()
            
            # Set expiration to 7 days from now
            expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Create invitation with data sharing options
            invitation = Invitation(
                email=email,
                token=token,
                role=role,
                role_id=role_id,
                created_by=recruiter.id,
                expires_at=expires_at,
                share_jobs=share_jobs,
                share_candidates=share_candidates
            )
            
            db.session.add(invitation)
            db.session.commit()
            
            # Generate invitation link
            invitation_link = f"{request.host_url.rstrip('/')}/join/{token}"
            
            # Import email sender
            from utils.email_sender import send_invitation_email
            
            # Send invitation email
            email_result = send_invitation_email(
                email, 
                invitation_link, 
                inviter_name=recruiter.name
            )
            
            return jsonify({
                'message': 'Invitation created successfully',
                'invite_link': invitation_link,
                'email_status': email_result
            })
        except Exception as e:
            logger.error(f"Create invitation error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/invites/<token>', methods=['DELETE'])
    @recruiter_required
    @requires_permission('users:delete')
    def delete_token_invitation(recruiter, token):
        try:
                
            # Find invitation by token
            invitation = Invitation.query.filter_by(token=token, used=False).first()
            
            if not invitation:
                return jsonify({'error': 'Invitation not found'}), 404
                
            # Delete invitation
            db.session.delete(invitation)
            db.session.commit()
            
            return jsonify({'message': 'Invitation deleted successfully'})
        except Exception as e:
            logger.error(f"Delete invitation error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # API Routes
    @app.route('/api/auth/login', methods=['POST'])
    @rate_limited('auth')
    def login():
        try:
            logger.debug("Login attempt received")
            data = request.get_json()
            logger.debug(f"Login data: {data}")
            
            if not data or 'email' not in data or 'password' not in data:
                logger.error("Login missing email or password")
                return jsonify({'error': 'Invalid request'}), 400
                
            recruiter = Recruiter.query.filter_by(email=data['email']).first()
            logger.debug(f"Found recruiter: {recruiter is not None}")
            
            if recruiter and recruiter.check_password(data['password']):
                logger.debug("Password check successful")
                session_id = os.urandom(16).hex()
                expires_at = datetime.utcnow() + timedelta(hours=4)
                
                # Create JWT token
                access_token = jwt.encode({
                    'session_id': session_id,
                    'exp': expires_at
                }, app.secret_key, algorithm='HS256')
                
                # Create session record
                session = Session(
                    id=session_id,
                    recruiter_id=recruiter.id,
                    expires_at=expires_at
                )
                db.session.add(session)
                db.session.commit()
                
                response = jsonify({'message': 'Login successful', 'redirect': '/dashboard'})
                response.set_cookie(
                    'access_token',
                    access_token,
                    httponly=True,
                    secure=False,  # Set to False for local development
                    samesite='Lax',
                    max_age=14400
                )
                logger.debug("Login successful, returning response with redirect")
                return response
            
            logger.error("Invalid credentials")
            return jsonify({'error': 'Invalid credentials'}), 401
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/jobs', methods=['POST'])
    @recruiter_required
    @rate_limited('jobs')
    @requires_permission('jobs:create')
    def create_job(recruiter):
        try:
            logger.debug("Job creation started")
            data = request.get_json()
            logger.debug(f"Job data: {data}")
            
            if not data or not data.get('description'):
                logger.error("Job description is required")
                return jsonify({'error': 'Job description is required'}), 400
                
            description = data['description']
            logger.debug(f"Processing job description: {description[:50]}...")
            
            try:
                # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                logger.debug("Calling OpenAI for job analysis")
                analysis = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "system",
                        "content": "You are a job analyst. Analyze the job description and extract the following information: title, location, experience (in years), required skills (list), preferred skills (list), education requirements, job type (full-time, part-time, contract, etc.), salary range (if mentioned), and company name (if mentioned). Return the data as a structured JSON object."
                    }, {
                        "role": "user",
                        "content": description
                    }],
                    response_format={"type": "json_object"}
                )
                
                logger.debug("OpenAI analysis complete")
                job_details = json.loads(analysis.choices[0].message.content)
                logger.debug(f"Job details extracted: {job_details}")
                
                # Generate embeddings for matching
                logger.debug("Generating embeddings")
                embedding_response = openai.embeddings.create(
                    input=description,
                    model="text-embedding-3-small"
                )
                logger.debug("Embeddings generated")
                
                # Create job record - use manually provided values if available, fall back to AI-analyzed values
                job = Job(
                    title=job_details.get('title', 'Untitled Position'),
                    description=description,
                    location=data.get('location') if data.get('location') else job_details.get('location'),
                    experience=data.get('experience') if data.get('experience') else job_details.get('experience'),
                    education=job_details.get('education'),
                    job_type=job_details.get('job_type'),
                    salary_range=job_details.get('salary_range'),
                    company=job_details.get('company'),
                    required_skills=job_details.get('required_skills', []),
                    preferred_skills=job_details.get('preferred_skills', []),
                    embedding=embedding_response.data[0].embedding,
                    recruiter_id=recruiter.id,
                    status='active'
                )
                
                logger.debug("Adding job to database")
                # Start a new session to ensure connection is fresh
                db.session.add(job)
                db.session.commit()
                logger.debug(f"Job created with ID: {job.id}")
                
                # Find matching candidates
                try:
                    logger.debug("Finding matching candidates")
                    candidates = Candidate.query.all()
                    logger.debug(f"Found {len(candidates)} candidates to match")
                    
                    for candidate in candidates:
                        score = calculate_match_score(candidate, job)
                        if score > 0.3:  # Reduced threshold from 0.6 to 0.3 (30%)
                            match = JobCandidateMatch(
                                job_id=job.id,
                                candidate_id=candidate.id,
                                score=score
                            )
                            db.session.add(match)
                    
                    db.session.commit()
                    logger.debug("Candidate matching complete")
                except Exception as match_error:
                    logger.error(f"Error during candidate matching: {str(match_error)}")
                    # Continue even if matching fails - the job is still created
                
                # Return job details in the response
                return jsonify({
                    'status': 'success', 
                    'job_id': job.id,
                    'title': job.title,
                    'location': job.location,
                    'experience': job.experience,
                    'required_skills': job.required_skills,
                    'preferred_skills': job.preferred_skills
                }), 201
                
            except openai.error.OpenAIError as openai_error:
                logger.error(f"OpenAI API error: {str(openai_error)}")
                return jsonify({'error': f'AI processing error: {str(openai_error)}'}), 500
                
        except Exception as e:
            logger.error(f"Job creation failed: {str(e)}")
            return jsonify({'error': 'Internal server error occurred while processing your job posting. Please try again later.'}), 500
    
    # Sharing Management API Routes
    @app.route('/api/sharing', methods=['POST'])
    @recruiter_required
    def create_sharing_relationship(recruiter):
        try:
            data = request.get_json()
            
            if not data or 'shared_with_id' not in data:
                return jsonify({'error': 'Missing required fields'}), 400
                
            shared_with_id = data.get('shared_with_id')
            share_jobs = data.get('share_jobs', False)
            share_candidates = data.get('share_candidates', False)
            
            # Validate recruiter exists
            shared_with = Recruiter.query.get(shared_with_id)
            if not shared_with:
                return jsonify({'error': 'Recruiter not found'}), 404
                
            # Check if sharing relationship already exists
            existing = RecruiterSharing.query.filter_by(
                owner_id=recruiter.id,
                shared_with_id=shared_with_id
            ).first()
            
            if existing:
                return jsonify({'error': 'A sharing relationship with this recruiter already exists'}), 400
                
            # Create new sharing relationship
            sharing = RecruiterSharing(
                owner_id=recruiter.id,
                shared_with_id=shared_with_id,
                share_jobs=share_jobs,
                share_candidates=share_candidates
            )
            
            db.session.add(sharing)
            db.session.commit()
            
            logger.info(f"Created sharing relationship: {recruiter.name} → {shared_with.name}")
            return jsonify({'success': True, 'id': sharing.id})
        except Exception as e:
            logger.error(f"Create sharing error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/sharing/<int:sharing_id>/jobs', methods=['PUT'])
    @recruiter_required
    def update_job_sharing(recruiter, sharing_id):
        try:
            data = request.get_json()
            
            if not data or 'enabled' not in data:
                return jsonify({'error': 'Missing required fields'}), 400
                
            enabled = data.get('enabled')
            
            # Find sharing relationship
            sharing = RecruiterSharing.query.get(sharing_id)
            
            if not sharing:
                return jsonify({'error': 'Sharing relationship not found'}), 404
                
            # Verify ownership
            if sharing.owner_id != recruiter.id:
                return jsonify({'error': 'You do not have permission to modify this sharing relationship'}), 403
                
            # Update sharing setting
            sharing.share_jobs = enabled
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Update job sharing error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/sharing/<int:sharing_id>/candidates', methods=['PUT'])
    @recruiter_required
    def update_candidate_sharing(recruiter, sharing_id):
        try:
            data = request.get_json()
            
            if not data or 'enabled' not in data:
                return jsonify({'error': 'Missing required fields'}), 400
                
            enabled = data.get('enabled')
            
            # Find sharing relationship
            sharing = RecruiterSharing.query.get(sharing_id)
            
            if not sharing:
                return jsonify({'error': 'Sharing relationship not found'}), 404
                
            # Verify ownership
            if sharing.owner_id != recruiter.id:
                return jsonify({'error': 'You do not have permission to modify this sharing relationship'}), 403
                
            # Update sharing setting
            sharing.share_candidates = enabled
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Update candidate sharing error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/api/sharing/<int:sharing_id>', methods=['DELETE'])
    @recruiter_required
    def delete_sharing_relationship(recruiter, sharing_id):
        try:
            # Find sharing relationship
            sharing = RecruiterSharing.query.get(sharing_id)
            
            if not sharing:
                return jsonify({'error': 'Sharing relationship not found'}), 404
                
            # Verify ownership
            if sharing.owner_id != recruiter.id:
                return jsonify({'error': 'You do not have permission to delete this sharing relationship'}), 403
                
            # Delete sharing relationship
            db.session.delete(sharing)
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Delete sharing error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/candidates', methods=['POST'])
    @rate_limited('uploads')
    def upload_resume():
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
            
        try:
            logger.debug("Resume upload started")
            content = file.read()
            filename = secure_filename(file.filename)
            logger.debug(f"Processing file: {filename}")
            
            # For a temporary upload without GCS
            local_path = os.path.join('static', 'uploads', filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(content)
            
            logger.debug(f"File saved locally at: {local_path}")
            
            # Extract text from content based on file type
            text = ""
            if isinstance(content, bytes):
                try:
                    img = Image.open(BytesIO(content))
                    text = pytesseract.image_to_string(img)
                    logger.debug("Extracted text from image")
                except Exception as img_error:
                    logger.error(f"Image processing failed: {str(img_error)}")
                    # Assume it's raw text
                    text = content.decode('utf-8', errors='ignore')
                    logger.debug("Decoded text from bytes")
            else:
                text = str(content)
                logger.debug("Converted content to string")
            
            # Limit text size to avoid rate limits
            if len(text) > 10000:
                logger.debug(f"Text is too large ({len(text)} chars), truncating...")
                text = text[:10000]
                
            # Simple parsing if OpenAI fails
            basic_resume_data = {
                "skills": extract_skills_from_text(text),
                "experience": [],
                "education": [],
                "summary": text[:500] + "..."
            }
            
            try:
                # Use OpenAI to analyze the resume
                # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                # do not change this unless explicitly requested by the user
                logger.debug("Calling OpenAI for resume analysis")
                analysis = openai.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use cheaper model to avoid rate limits
                    messages=[{
                        "role": "system",
                        "content": "You are a resume parser. Extract the following information from the resume text and return it as JSON: skills (list), experience (list of jobs with company, title, years), education (list of degrees with school, degree, field, year), summary (brief overview). Format all text properly and ensure lists are well-structured."
                    }, {
                        "role": "user",
                        "content": text
                    }],
                    response_format={"type": "json_object"},
                    max_tokens=500
                )
                
                resume_data = json.loads(analysis.choices[0].message.content)
                logger.debug("OpenAI resume analysis complete")
            except Exception as openai_error:
                logger.error(f"OpenAI resume analysis failed: {str(openai_error)}")
                resume_data = basic_resume_data
                logger.debug("Using basic resume data as fallback")
            
            try:
                # Generate embeddings for matching
                logger.debug("Generating embeddings")
                embedding_response = openai.embeddings.create(
                    input=text[:1000],  # Use shorter text for embeddings
                    model="text-embedding-3-small"
                )
                embedding_vector = embedding_response.data[0].embedding
                logger.debug("Embeddings generated")
            except Exception as embed_error:
                logger.error(f"Embedding generation failed: {str(embed_error)}")
                # Use a dummy embedding of correct size if OpenAI fails
                embedding_vector = [0.0] * 1536
                logger.debug("Using dummy embedding as fallback")
            
            # Handle candidate record creation or update
            try:
                email = request.form.get('email', '')
                logger.debug(f"Processing candidate with email: {email}")
                
                # Check if candidate with this email already exists
                existing_candidate = None
                if email:
                    try:
                        existing_candidate = Candidate.query.filter_by(email=email).first()
                        if existing_candidate:
                            logger.debug(f"Found existing candidate with ID: {existing_candidate.id}")
                    except Exception as query_error:
                        logger.error(f"Error querying for existing candidate: {str(query_error)}")
                
                if existing_candidate:
                    # Update existing candidate
                    logger.debug("Updating existing candidate record")
                    
                    # Update candidate fields
                    existing_candidate.name = request.form.get('name', existing_candidate.name)
                    existing_candidate.phone = request.form.get('phone', existing_candidate.phone)
                    existing_candidate.resume_file = filename
                    existing_candidate.gcs_url = '/static/uploads/' + filename
                    existing_candidate.parsed_data = resume_data
                    existing_candidate.embedding = embedding_vector
                    
                    candidate = existing_candidate
                    db.session.commit()
                    logger.debug(f"Candidate record updated with ID: {candidate.id}")
                    
                    # Delete old matches for this candidate to re-calculate
                    try:
                        JobCandidateMatch.query.filter_by(candidate_id=candidate.id).delete()
                        db.session.commit()
                        logger.debug("Old job matches deleted for re-calculation")
                    except Exception as delete_error:
                        logger.error(f"Error deleting old matches: {str(delete_error)}")
                        db.session.rollback()
                    
                else:
                    # Create new candidate
                    logger.debug("Creating new candidate record")
                    candidate = Candidate(
                        name=request.form.get('name', 'Anonymous'),
                        email=email,
                        phone=request.form.get('phone', ''),
                        resume_file=filename,
                        gcs_url='/static/uploads/' + filename,
                        parsed_data=resume_data,
                        embedding=embedding_vector
                    )
                    
                    db.session.add(candidate)
                    db.session.commit()
                    logger.debug(f"New candidate record created with ID: {candidate.id}")
                
                # Find matching jobs
                try:
                    logger.debug("Finding matching jobs")
                    jobs = Job.query.filter_by(status='active').all()
                    logger.debug(f"Found {len(jobs)} active jobs")
                    
                    for job in jobs:
                        score = calculate_match_score(candidate, job)
                        if score > 0.3:  # Reduced threshold from 0.6 to 0.3 (30%)
                            match = JobCandidateMatch(
                                job_id=job.id,
                                candidate_id=candidate.id,
                                score=score
                            )
                            db.session.add(match)
                    
                    db.session.commit()
                    logger.debug("Job matching complete")
                except Exception as match_error:
                    logger.error(f"Job matching failed: {str(match_error)}")
                    # Continue even if matching fails
                
                return jsonify({
                    'status': 'success', 
                    'message': 'Your resume has been processed. We will email you when matches are found.',
                    'candidate_id': candidate.id
                }), 201
                
            except Exception as db_error:
                logger.error(f"Database operation failed: {str(db_error)}")
                db.session.rollback()  # Ensure we rollback any failed transaction
                return jsonify({'error': 'Database connection error. Please try again later.'}), 500
            
        except Exception as e:
            logger.error(f"Resume upload failed: {str(e)}")
            return jsonify({'error': 'Upload failed: ' + str(e)}), 500
            
    # Helper function to extract skills from text without OpenAI
    def extract_skills_from_text(text):
        # Common programming languages and technologies
        tech_skills = [
            "Python", "Java", "JavaScript", "HTML", "CSS", "SQL", "C++", "C#", "Ruby",
            "PHP", "Swift", "Go", "Rust", "TypeScript", "React", "Angular", "Vue", 
            "Node.js", "Django", "Flask", "Rails", "Spring", "ASP.NET", "Laravel",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "GitHub", "CI/CD",
            "TensorFlow", "PyTorch", "Machine Learning", "AI", "Data Science",
            "Agile", "Scrum", "DevOps", "Microservices", "RESTful API", "GraphQL"
        ]
        
        # Soft skills
        soft_skills = [
            "Communication", "Teamwork", "Leadership", "Problem Solving", 
            "Critical Thinking", "Time Management", "Adaptability", "Creativity",
            "Project Management", "Customer Service", "Presentation", "Negotiation"
        ]
        
        # Combine all skills
        all_skills = tech_skills + soft_skills
        
        # Extract skills that appear in the text
        found_skills = []
        for skill in all_skills:
            if skill.lower() in text.lower():
                found_skills.append(skill)
                
        return found_skills
    
    @app.route('/api/resume/text', methods=['POST'])
    @rate_limited('uploads')
    @recruiter_required
    @requires_permission('candidates:add')
    def upload_resume_text(recruiter):
        try:
            logger.debug("Resume text upload started")
            data = request.get_json()
            
            if not data:
                logger.error("No data provided")
                return jsonify({'error': 'No data provided'}), 400
            
            name = data.get('name', '')
            email = data.get('email', '')
            phone = data.get('phone', '')
            resume_text = data.get('resume_text', '')
            
            if not name or not resume_text:
                logger.error("Name and resume text are required")
                return jsonify({'error': 'Name and resume text are required'}), 400
            
            logger.debug(f"Processing resume for {name}")
            
            # Save the text as a file
            timestamp = int(time.time())
            filename = f"{name.lower().replace(' ', '_')}_{timestamp}.txt"
            
            # Make sure the directory exists
            os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
            local_path = os.path.join('static', 'uploads', filename)
            
            with open(local_path, 'w') as f:
                f.write(resume_text)
            
            logger.debug(f"Resume text saved locally at: {local_path}")
            
            # Check for exact duplicate by email
            duplicate_candidate = None
            is_update = False
            message = 'Resume uploaded successfully!'
            
            if email:
                logger.debug(f"Checking for duplicate by email: {email}")
                duplicate_candidate = Candidate.query.filter_by(email=email).first()
                if duplicate_candidate:
                    logger.debug(f"Found duplicate by email: {duplicate_candidate.id}")
                    is_update = True
                    message = 'Your resume has been updated!'
            
            # If no email match, check by phone number if provided
            if not duplicate_candidate and phone:
                logger.debug(f"Checking for duplicate by phone: {phone}")
                
                # Normalize phone numbers for comparison (remove all non-digit characters)
                normalized_phone = re.sub(r'\D', '', phone)
                
                if normalized_phone:
                    # Get all candidates to check normalized phone numbers
                    candidates = Candidate.query.all()
                    for candidate in candidates:
                        if candidate.phone:
                            candidate_phone = re.sub(r'\D', '', candidate.phone)
                            if normalized_phone == candidate_phone:
                                logger.debug(f"Found duplicate by phone: {candidate.id}")
                                duplicate_candidate = candidate
                                is_update = True
                                message = 'Your resume has been updated based on matching phone number!'
                                break
            
            # Parse the resume text to extract structured data
            # Simple parsing if OpenAI fails
            basic_resume_data = {
                "skills": extract_skills_from_text(resume_text),
                "experience": [],
                "education": [],
                "summary": resume_text[:500] + "..."
            }
            
            try:
                # Use OpenAI to analyze the resume
                logger.debug("Calling OpenAI for resume analysis")
                analysis = openai.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use cheaper model to avoid rate limits
                    messages=[{
                        "role": "system",
                        "content": "You are a resume parser. Extract the following information from the resume text and return it as JSON: skills (list), experience (list of jobs with company, title, years), education (list of degrees with school, degree, field, year), summary (brief overview). Format all text properly and ensure lists are well-structured."
                    }, {
                        "role": "user",
                        "content": resume_text
                    }],
                    response_format={"type": "json_object"},
                    max_tokens=500
                )
                
                resume_data = json.loads(analysis.choices[0].message.content)
                logger.debug("OpenAI resume analysis complete")
            except Exception as openai_error:
                logger.error(f"OpenAI resume analysis failed: {str(openai_error)}")
                resume_data = basic_resume_data
                logger.debug("Using basic resume data as fallback")
            
            try:
                # Generate embeddings for matching
                logger.debug("Generating embeddings")
                embedding_response = openai.embeddings.create(
                    input=resume_text[:1000],  # Use shorter text for embeddings
                    model="text-embedding-3-small"
                )
                embedding_vector = embedding_response.data[0].embedding
                logger.debug("Embeddings generated")
            except Exception as embed_error:
                logger.error(f"Embedding generation failed: {str(embed_error)}")
                # Use a dummy embedding of correct size if OpenAI fails
                embedding_vector = [0.0] * 1536
                logger.debug("Using dummy embedding as fallback")
            
            # Update or create candidate
            if duplicate_candidate:
                candidate_id = duplicate_candidate.id
                
                # Update the candidate's information
                duplicate_candidate.name = name
                if email:
                    duplicate_candidate.email = email
                if phone:
                    duplicate_candidate.phone = phone
                duplicate_candidate.resume_file = filename
                duplicate_candidate.parsed_data = resume_data
                duplicate_candidate.embedding = embedding_vector
                duplicate_candidate.updated_at = datetime.utcnow()
                
                db.session.commit()
                logger.debug(f"Updated candidate ID: {candidate_id}")
            else:
                # Create a new candidate
                candidate = Candidate(
                    name=name,
                    email=email,
                    phone=phone,
                    resume_file=filename,
                    parsed_data=resume_data,
                    embedding=embedding_vector,
                    uploaded_by=recruiter.id
                )
                
                db.session.add(candidate)
                db.session.commit()
                candidate_id = candidate.id
                logger.debug(f"Created new candidate ID: {candidate_id}")
            
            # Return success response
            return jsonify({
                'message': message,
                'candidate_id': candidate_id,
                'is_update': is_update
            }), 200
            
        except Exception as e:
            logger.error(f"Resume text upload error: {str(e)}")
            return jsonify({'error': f'Resume upload failed: {str(e)}'}), 500
    
    @app.route('/api/candidates/bulk', methods=['POST'])
    @recruiter_required
    @rate_limited('uploads')
    @requires_permission('candidates:bulk_add')
    def bulk_upload_resumes(recruiter):
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
            
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'Empty upload'}), 400
        
        # Limit to 10 files
        files = files[:10]
            
        try:
            logger.debug(f"Bulk upload started with {len(files)} files")
            results = []
            processed_count = 0
            
            # Create a task queue to track processing
            if not hasattr(app, 'task_queue'):
                app.task_queue = []
                
            for file in files:
                if file.filename == '':
                    results.append({'filename': 'unknown', 'status': 'error', 'message': 'Empty filename'})
                    continue
                    
                if not allowed_file(file.filename):
                    results.append({'filename': file.filename, 'status': 'error', 'message': 'Invalid file type'})
                    continue
                    
                try:
                    # Read file content
                    content = file.read()
                    filename = secure_filename(file.filename)
                    logger.debug(f"Processing file: {filename}")
                    
                    # Save file locally
                    local_path = os.path.join('static', 'uploads', filename)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, 'wb') as f:
                        f.write(content)
                    
                    # Add to processing queue
                    app.task_queue.append({
                        'type': 'resume_processing',
                        'filename': filename,
                        'local_path': local_path,
                        'recruiter_id': recruiter.id,
                        'created_at': datetime.utcnow().isoformat()
                    })
                    
                    processed_count += 1
                    results.append({
                        'filename': filename, 
                        'status': 'queued', 
                        'message': 'Added to processing queue'
                    })
                    
                    # Process first file immediately if there's only a few
                    if processed_count <= 3:
                        # Start background thread for processing
                        threading.Thread(
                            target=process_resume_in_background,
                            args=(app, local_path, filename, recruiter.id),
                            daemon=True
                        ).start()
                        
                except Exception as file_error:
                    logger.error(f"Error processing file {file.filename}: {str(file_error)}")
                    results.append({
                        'filename': file.filename, 
                        'status': 'error', 
                        'message': f'Processing error: {str(file_error)}'
                    })
                    
            logger.debug(f"Bulk upload completed. Processed: {processed_count}, Total results: {len(results)}")
            return jsonify({
                'results': results,
                'message': f"Successfully queued {processed_count} files for processing.",
                'queued_files': processed_count
            }), 202
            
        except Exception as e:
            logger.error(f"Bulk upload failed: {str(e)}")
            return jsonify({'error': 'Bulk processing failed: ' + str(e)}), 500
            
    # Background processing function
    def process_resume_in_background(app, file_path, filename, recruiter_id):
        try:
            with app.app_context():
                logger.debug(f"Background processing started for {filename}")
                
                # Read file content
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # Extract text
                text = ""
                try:
                    img = Image.open(BytesIO(content))
                    text = pytesseract.image_to_string(img)
                    logger.debug("Extracted text from image")
                except Exception:
                    # Assume it's raw text
                    text = content.decode('utf-8', errors='ignore')
                    logger.debug("Decoded text from bytes")
                
                # Limit text size
                if len(text) > 10000:
                    text = text[:10000]
                    
                # Basic parsing
                basic_resume_data = {
                    "skills": extract_skills_from_text(text),
                    "experience": [],
                    "education": [],
                    "summary": text[:500] + "..."
                }
                
                # Try OpenAI analysis
                try:
                    logger.debug("Calling OpenAI for resume analysis")
                    analysis = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{
                            "role": "system",
                            "content": "You are a resume parser. Extract the following information from the resume text and return it as JSON: skills (list), experience (list of jobs with company, title, years), education (list of degrees with school, degree, field, year), summary (brief overview). Format all text properly and ensure lists are well-structured."
                        }, {
                            "role": "user",
                            "content": text
                        }],
                        response_format={"type": "json_object"},
                        max_tokens=500
                    )
                    resume_data = json.loads(analysis.choices[0].message.content)
                    logger.debug("OpenAI resume analysis complete")
                except Exception as openai_error:
                    logger.error(f"OpenAI resume analysis failed: {str(openai_error)}")
                    resume_data = basic_resume_data
                
                # Generate embeddings
                try:
                    logger.debug("Generating embeddings")
                    embedding_response = openai.embeddings.create(
                        input=text[:1000],
                        model="text-embedding-3-small"
                    )
                    embedding_vector = embedding_response.data[0].embedding
                    logger.debug("Embeddings generated")
                except Exception:
                    embedding_vector = [0.0] * 1536
                
                # Extract email from resume if possible
                extracted_email = None
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_matches = re.findall(email_pattern, text)
                if email_matches:
                    extracted_email = email_matches[0]
                    logger.debug(f"Extracted email: {extracted_email}")
                
                # Generate a unique name based on filename
                name_from_file = os.path.splitext(filename)[0].replace('_', ' ').title()
                
                # Check for existing candidate with this email
                existing_candidate = None
                if extracted_email:
                    existing_candidate = Candidate.query.filter_by(email=extracted_email).first()
                
                if existing_candidate:
                    logger.debug(f"Updating existing candidate: {existing_candidate.id}")
                    # Update fields
                    existing_candidate.resume_file = filename
                    existing_candidate.gcs_url = '/static/uploads/' + filename
                    existing_candidate.parsed_data = resume_data
                    existing_candidate.embedding = embedding_vector
                    
                    candidate = existing_candidate
                    db.session.commit()
                    
                    # Delete old matches
                    JobCandidateMatch.query.filter_by(candidate_id=candidate.id).delete()
                    db.session.commit()
                else:
                    logger.debug("Creating new candidate from bulk upload")
                    # Create new candidate
                    candidate = Candidate(
                        name=name_from_file,
                        email=extracted_email if extracted_email else "",
                        phone="",
                        resume_file=filename,
                        gcs_url='/static/uploads/' + filename,
                        parsed_data=resume_data,
                        embedding=embedding_vector
                    )
                    db.session.add(candidate)
                    db.session.commit()
                
                # Find matching jobs
                logger.debug("Finding job matches")
                jobs = Job.query.filter_by(status='active').all()
                
                for job in jobs:
                    score = calculate_match_score(candidate, job)
                    if score > 0.3:  # Reduced threshold from 0.6 to 0.3 (30%)
                        match = JobCandidateMatch(
                            job_id=job.id,
                            candidate_id=candidate.id,
                            score=score
                        )
                        db.session.add(match)
                
                db.session.commit()
                logger.debug(f"Background processing completed for {filename}")
                
        except Exception as process_error:
            logger.error(f"Background processing failed: {str(process_error)}")
            
    @app.route('/api/candidates/<job_id>', methods=['GET'])
    @recruiter_required
    @requires_permission('candidates:view')
    def get_candidates_for_job(recruiter, job_id):
        # Find the job
        job = Job.query.filter_by(id=job_id, recruiter_id=recruiter.id).first()
        
        if not job:
            return jsonify({'error': 'Job not found'}), 404
            
        # Get matches
        matches = JobCandidateMatch.query.filter_by(job_id=job.id).order_by(JobCandidateMatch.score.desc()).all()
        
        candidates_list = []
        for match in matches:
            candidate = Candidate.query.get(match.candidate_id)
            if candidate:
                candidates_list.append({
                    'id': candidate.id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'phone': candidate.phone,
                    'score': match.score,
                    'skills': candidate.parsed_data.get('skills', []) if candidate.parsed_data else [],
                    'experience': candidate.parsed_data.get('experience', []) if candidate.parsed_data else [],
                    'resume_url': candidate.gcs_url
                })
        
        return render_template('candidate_matches.html', matches=candidates_list, job=job)
    
    @app.route('/api/matches/refresh', methods=['POST'])
    @recruiter_required
    @requires_permission('matches:refresh')
    def refresh_matches(recruiter):
        try:
            # Delete existing matches
            JobCandidateMatch.query.delete()
            db.session.commit()
            
            # Get all active jobs
            jobs = Job.query.filter_by(status='active').all()
            
            # Get all candidates
            candidates = Candidate.query.all()
            
            match_count = 0
            
            # Generate new matches with updated threshold
            for candidate in candidates:
                for job in jobs:
                    score = calculate_match_score(candidate, job)
                    if score > 0.3:  # Using same threshold as in background processing
                        match = JobCandidateMatch(
                            job_id=job.id,
                            candidate_id=candidate.id,
                            score=score
                        )
                        db.session.add(match)
                        match_count += 1
            
            db.session.commit()
            logger.debug(f"Refreshed matches: {match_count} new matches created")
            
            return jsonify({
                'success': True,
                'message': f'Successfully refreshed matches. {match_count} new matches created.'
            })
            
        except Exception as e:
            logger.error(f"Match refresh failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Failed to refresh matches: {str(e)}'
            }), 500
    
    # Additional Routes for Candidate and Job Management
    @app.route('/my-candidates')
    @recruiter_required
    @requires_permission('candidates:view')
    def view_candidates(recruiter):
        try:
            logger.debug(f"My Candidates page accessed by recruiter ID: {recruiter.id}")
            
            # Get candidates uploaded by this recruiter
            own_candidates = Candidate.query.filter_by(uploaded_by=recruiter.id).all()
            
            # For admin users, show all candidates in the system
            if recruiter.has_permission('candidates:view_all'):
                logger.debug("Admin user accessing all candidates")
                shared_candidates = Candidate.query.filter(
                    Candidate.uploaded_by != recruiter.id
                ).all()
                is_admin_view = True
            else:
                # Get candidates shared with this recruiter through sharing relationships
                logger.debug("Regular user accessing shared candidates")
                shared_candidates = []
                
                # Get sharing relationships where this recruiter has access to candidates
                sharing_relationships = RecruiterSharing.query.filter_by(
                    shared_with_id=recruiter.id,
                    share_candidates=True
                ).all()
                
                # Get candidates from those relationships
                for relationship in sharing_relationships:
                    owner_candidates = Candidate.query.filter_by(uploaded_by=relationship.owner_id).all()
                    shared_candidates.extend(owner_candidates)
                    
                is_admin_view = False
            
            # Combine own and shared candidates
            candidates = own_candidates + shared_candidates
                
            logger.debug(f"Found {len(candidates)} candidates for display ({len(own_candidates)} own, {len(shared_candidates)} shared)")
            
            # Get recruiter names for displaying who uploaded each candidate
            recruiter_ids = set(c.uploaded_by for c in candidates if c.uploaded_by is not None)
            recruiters = {r.id: r for r in Recruiter.query.filter(Recruiter.id.in_(recruiter_ids)).all()}
                
            return render_template('candidates.html', 
                                  candidates=candidates, 
                                  current_user=recruiter, 
                                  is_admin_view=is_admin_view,
                                  recruiters=recruiters)
        except Exception as e:
            logger.error(f"View candidates error: {str(e)}")
            return render_template('error.html', error=str(e))
            
    @app.route('/candidates/<int:candidate_id>')
    @recruiter_required
    @requires_permission('candidates:view')
    def view_candidate_detail(recruiter, candidate_id):
        try:
            candidate = Candidate.query.get_or_404(candidate_id)
            
            # Check if recruiter has permission to view this candidate
            can_view = False
            
            # Admin can view all
            if recruiter.has_permission('candidates:view_all'):
                can_view = True
            # Uploaded by the current recruiter
            elif candidate.uploaded_by == recruiter.id:
                can_view = True
            # Shared via sharing relationships
            else:
                sharing = RecruiterSharing.query.filter_by(
                    owner_id=candidate.uploaded_by,
                    shared_with_id=recruiter.id,
                    share_candidates=True
                ).first()
                
                if sharing:
                    can_view = True
            
            if not can_view:
                flash('You do not have permission to view this candidate.', 'error')
                return redirect(url_for('view_candidates'))
            
            # Get all matches for this candidate
            matches = JobCandidateMatch.query.filter_by(candidate_id=candidate.id).all()
            
            # Get the jobs this candidate matches with
            matched_jobs = []
            for match in matches:
                job = Job.query.get(match.job_id)
                # Check if recruiter can view this job
                if job and recruiter.can_access_job(job):
                    job.match_score = round(match.score * 100)
                    matched_jobs.append(job)
            
            # Sort by match score (descending)
            matched_jobs.sort(key=lambda x: x.match_score, reverse=True)
            
            # Get candidate ratings
            candidate_ratings = CandidateRating.query.filter_by(candidate_id=candidate.id).order_by(CandidateRating.created_at.desc()).all()
            
            # Get current recruiter's rating if it exists
            candidate_rating = CandidateRating.query.filter_by(
                candidate_id=candidate.id,
                recruiter_id=recruiter.id
            ).first()
            
            return render_template(
                'candidate_detail.html', 
                candidate=candidate, 
                matched_jobs=matched_jobs,
                candidate_ratings=candidate_ratings,
                candidate_rating=candidate_rating,
                current_user=recruiter
            )
        except Exception as e:
            logger.error(f"View candidate detail error: {str(e)}")
            return render_template('error.html', error=str(e))
            
    @app.route('/api/candidates/<int:candidate_id>', methods=['GET'])
    @recruiter_required
    @requires_permission('candidates:view')
    def get_candidate_api(recruiter, candidate_id):
        try:
            # Check if the request is coming from an XHR/AJAX call or direct browser access
            is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            accept_header = request.headers.get('Accept', '')
            
            # If it's a direct browser access (not AJAX) or HTML is explicitly requested,
            # redirect to the candidate details page
            if not is_xhr and ('text/html' in accept_header or '*/*' in accept_header):
                return redirect(url_for('view_candidate_detail', candidate_id=candidate_id))
            
            # Otherwise proceed with API response for programmatic access
            candidate = Candidate.query.get_or_404(candidate_id)
            
            # Check if recruiter has permission to view this candidate
            can_view = False
            
            # Admin can view all
            if recruiter.has_permission('candidates:view_all'):
                can_view = True
            # Uploaded by the current recruiter
            elif candidate.uploaded_by == recruiter.id:
                can_view = True
            # Shared via sharing relationships
            else:
                sharing = RecruiterSharing.query.filter_by(
                    owner_id=candidate.uploaded_by,
                    shared_with_id=recruiter.id,
                    share_candidates=True
                ).first()
                
                if sharing:
                    can_view = True
            
            if not can_view:
                return jsonify({
                    'error': 'You do not have permission to view this candidate.'
                }), 403
            
            # Get job matches
            matches = JobCandidateMatch.query.filter_by(candidate_id=candidate.id).all()
            
            # Format matches data
            matches_data = []
            for match in matches:
                job = Job.query.get(match.job_id)
                # For admin users, show all job matches, not just their own
                if job and (recruiter.has_permission('jobs:view_all') or job.recruiter_id == recruiter.id):
                    # For non-recruiter jobs, indicate the owner
                    job_recruiter = None
                    if job.recruiter_id != recruiter.id:
                        job_recruiter = Recruiter.query.get(job.recruiter_id)
                        
                    matches_data.append({
                        'job_id': job.id,
                        'job_title': job.title,
                        'company': job.company,
                        'score': round(match.score * 100),
                        'created_at': match.created_at.isoformat(),
                        'owned_by_current_user': (job.recruiter_id == recruiter.id),
                        'owner_name': job_recruiter.name if job_recruiter else None
                    })
            
            # Get ratings for this candidate
            ratings = CandidateRating.query.filter_by(candidate_id=candidate.id).all()
            ratings_data = []
            for rating in ratings:
                rater = Recruiter.query.get(rating.recruiter_id)
                ratings_data.append({
                    'id': rating.id,
                    'recruiter_id': rating.recruiter_id,
                    'recruiter_name': rater.name if rater else 'Unknown',
                    'score': rating.score,
                    'notes': rating.notes,
                    'created_at': rating.created_at.isoformat(),
                    'updated_at': rating.updated_at.isoformat()
                })
            
            # Check if candidate has a persona, if not generate one
            if not candidate.persona:
                try:
                    from utils.persona_generator import generate_candidate_persona
                    candidate.persona = generate_candidate_persona(candidate.parsed_data)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Error generating persona: {str(e)}")
                    candidate.persona = {
                        "ideal_roles": [],
                        "key_strengths": [],
                        "growth_areas": [],
                        "team_fit": "Not analyzed"
                    }
            
            # Format candidate data
            candidate_data = {
                'id': candidate.id,
                'name': candidate.name,
                'email': candidate.email,
                'phone': candidate.phone,
                'resume_url': candidate.gcs_url,
                'parsed_data': candidate.parsed_data,
                'created_at': candidate.created_at.isoformat(),
                'matches': matches_data,
                'ratings': ratings_data,
                'persona': candidate.persona,
                'uploaded_by': candidate.uploaded_by,
                'job_id': candidate.job_id
            }
            
            return jsonify(candidate_data)
        except Exception as e:
            logger.error(f"API get candidate error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    # Ratings API endpoints
    @app.route('/api/candidates/<int:candidate_id>/rate', methods=['POST'])
    @recruiter_required
    @requires_permission('candidates:rate')
    def rate_candidate(recruiter, candidate_id):
        try:
            # Verify candidate exists
            candidate = Candidate.query.get_or_404(candidate_id)
            
            # Parse request data - support both JSON and form data for HTMX
            if request.is_json:
                data = request.get_json()
                if not data or 'score' not in data:
                    return jsonify({'error': 'Rating score is required'}), 400
                score = data.get('score')
                notes = data.get('notes', '')
            else:
                # Form data from HTMX request
                if 'score' not in request.form:
                    return '<div class="alert alert-danger">Rating score is required</div>', 400
                score = request.form.get('score')
                notes = request.form.get('notes', '')
            
            # Validate score (0-1)
            try:
                score = float(score)
                if score < 0 or score > 1:
                    return jsonify({'error': 'Score must be between 0 and 1'}), 400
            except ValueError:
                return jsonify({'error': 'Score must be a number between 0 and 1'}), 400
                
            # Check if recruiter already rated this candidate
            existing_rating = CandidateRating.query.filter_by(
                candidate_id=candidate_id,
                recruiter_id=recruiter.id
            ).first()
            
            if existing_rating:
                # Update existing rating
                existing_rating.score = score
                existing_rating.notes = notes
                existing_rating.updated_at = datetime.utcnow()
                db.session.commit()
                
                # Check if this is a HTMX request
                if request.headers.get('HX-Request'):
                    return f'''
                    <div class="alert alert-success">
                        <i class="material-icons">check_circle</i>
                        Rating updated successfully!
                    </div>
                    '''
                else:
                    return jsonify({
                        'message': 'Rating updated successfully',
                        'rating': {
                            'id': existing_rating.id,
                            'score': existing_rating.score,
                            'notes': existing_rating.notes,
                            'updated_at': existing_rating.updated_at.isoformat()
                        }
                    })
            else:
                # Create new rating
                rating = CandidateRating(
                    candidate_id=candidate_id,
                    recruiter_id=recruiter.id,
                    score=score,
                    notes=notes
                )
                
                db.session.add(rating)
                db.session.commit()
                
                # Check if this is a HTMX request
                if request.headers.get('HX-Request'):
                    return f'''
                    <div class="alert alert-success">
                        <i class="material-icons">check_circle</i>
                        Rating added successfully!
                    </div>
                    '''
                else:
                    return jsonify({
                        'message': 'Rating added successfully',
                        'rating': {
                            'id': rating.id,
                            'score': rating.score,
                            'notes': rating.notes,
                            'created_at': rating.created_at.isoformat()
                        }
                    }), 201
                
        except Exception as e:
            logger.error(f"Rate candidate error: {str(e)}")
            if request.headers.get('HX-Request'):
                return f'''
                <div class="alert alert-danger">
                    <i class="material-icons">error</i>
                    Error: {str(e)}
                </div>
                ''', 500
            else:
                return jsonify({'error': str(e)}), 500
            
    @app.route('/api/candidates/<int:candidate_id>/ratings/<int:rating_id>', methods=['DELETE'])
    @recruiter_required
    @requires_permission('candidates:rate')
    def delete_rating(recruiter, candidate_id, rating_id):
        try:
            # Find the rating
            rating = CandidateRating.query.get_or_404(rating_id)
            
            # Verify ownership
            if rating.recruiter_id != recruiter.id and not recruiter.is_admin():
                return jsonify({'error': 'Unauthorized to delete this rating'}), 403
                
            # Delete the rating
            db.session.delete(rating)
            db.session.commit()
            
            # Check if this is a HTMX request
            if request.headers.get('HX-Request'):
                return '''
                <div class="alert alert-success">
                    <i class="material-icons">check_circle</i>
                    Rating deleted successfully!
                </div>
                '''
            else:
                return jsonify({'message': 'Rating deleted successfully'})
            
        except Exception as e:
            logger.error(f"Delete rating error: {str(e)}")
            if request.headers.get('HX-Request'):
                return f'''
                <div class="alert alert-danger">
                    <i class="material-icons">error</i>
                    Error: {str(e)}
                </div>
                ''', 500
            else:
                return jsonify({'error': str(e)}), 500
    
    @app.route('/api/candidates/<int:candidate_id>/generate-persona', methods=['POST'])
    @recruiter_required
    @requires_permission('candidates:generate_persona')
    def generate_candidate_persona_api(recruiter, candidate_id):
        try:
            # Verify candidate exists
            candidate = Candidate.query.get_or_404(candidate_id)
            
            # Generate persona
            from utils.persona_generator import generate_candidate_persona
            persona = generate_candidate_persona(candidate.parsed_data)
            
            # Update candidate
            candidate.persona = persona
            db.session.commit()
            
            return jsonify({
                'message': 'Persona generated successfully',
                'persona': persona
            })
            
        except Exception as e:
            logger.error(f"Generate persona error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    @app.route('/my-jobs')
    @recruiter_required
    @requires_permission('jobs:view')
    def view_jobs(recruiter):
        try:
            logger.debug(f"My Jobs page accessed by recruiter ID: {recruiter.id}")
            
            # Get jobs created by this recruiter
            own_jobs = Job.query.filter_by(recruiter_id=recruiter.id).all()
            
            # For admin users, show all jobs in the system
            if recruiter.has_permission('jobs:view_all'):
                logger.debug("Admin user accessing all jobs")
                shared_jobs = Job.query.filter(Job.recruiter_id != recruiter.id).all()
                is_admin_view = True
            else:
                # Get jobs shared with this recruiter through sharing relationships
                logger.debug("Regular user accessing shared jobs")
                shared_jobs = []
                
                # Get sharing relationships where this recruiter has access to jobs
                sharing_relationships = RecruiterSharing.query.filter_by(
                    shared_with_id=recruiter.id,
                    share_jobs=True
                ).all()
                
                # Get jobs from those relationships
                for relationship in sharing_relationships:
                    owner_jobs = Job.query.filter_by(recruiter_id=relationship.owner_id).all()
                    shared_jobs.extend(owner_jobs)
                    
                is_admin_view = False
            
            # Combine own and shared jobs
            jobs = own_jobs + shared_jobs
                
            logger.debug(f"Found {len(jobs)} jobs for display ({len(own_jobs)} own, {len(shared_jobs)} shared)")
            
            # Get recruiter names for displaying who owns each job
            recruiter_ids = set(job.recruiter_id for job in jobs)
            recruiters = {r.id: r for r in Recruiter.query.filter(Recruiter.id.in_(recruiter_ids)).all()}
            
            # Add match info and application count to each job
            for job in jobs:
                matches = JobCandidateMatch.query.filter_by(job_id=job.id).all()
                job.matches = matches
                job.match_score = round(sum([m.score for m in matches]) / max(1, len(matches)) * 100) if matches else 0
            
            # If admin view, get all recruiters for displaying owner info
            recruiters = {}
            if is_admin_view:
                all_recruiters = Recruiter.query.all()
                recruiters = {r.id: r for r in all_recruiters}
            
            return render_template('jobs.html', 
                                  jobs=jobs, 
                                  current_user=recruiter,
                                  is_admin_view=is_admin_view,
                                  recruiters=recruiters)
        except Exception as e:
            logger.error(f"View jobs error: {str(e)}")
            return render_template('error.html', error=str(e))
    
    # Job renewal and expiration endpoints
    @app.route('/api/jobs/<int:job_id>/renew', methods=['POST'])
    @recruiter_required
    @requires_permission('jobs:edit')
    def renew_job_api(recruiter, job_id):
        """
        Renew a job for another 60 days
        """
        try:
            # Check the job exists and belongs to this recruiter or is shared with them
            job = Job.query.get(job_id)
            
            if not job:
                return jsonify({'error': 'Job not found'}), 404
                
            if not recruiter.can_access_job(job):
                return jsonify({'error': 'You don\'t have permission to renew this job'}), 403
                
            # Only the owner can renew the job
            if job.recruiter_id != recruiter.id:
                return jsonify({'error': 'Only the job owner can renew it'}), 403
                
            # Default renewal period is 60 days
            days = request.json.get('days', 60) if request.is_json else 60
            
            # Limit renewal period
            if days < 1:
                days = 1
            elif days > 365:
                days = 365
                
            result = renew_job(job_id, days)
            
            if not result:
                return jsonify({'error': 'Failed to renew job'}), 500
                
            return jsonify({
                'success': True, 
                'message': f'Job renewed successfully for {days} days',
                'job': {
                    'id': job.id,
                    'title': job.title,
                    'status': job.status,
                    'expires_at': job.expires_at.strftime('%Y-%m-%d'),
                    'days_left': (job.expires_at - datetime.utcnow()).days
                }
            })
            
        except Exception as e:
            logger.error(f"Error renewing job: {str(e)}")
            return jsonify({'error': f"Failed to renew job: {str(e)}"}), 500
            
    @app.route('/api/jobs/expiring', methods=['GET'])
    @recruiter_required
    def get_expiring_jobs_api(recruiter):
        """
        Get list of jobs expiring soon for this recruiter
        """
        try:
            # Default threshold is 7 days
            days_threshold = request.args.get('days', 7, type=int)
            
            # Limit threshold
            if days_threshold < 1:
                days_threshold = 1
            elif days_threshold > 30:
                days_threshold = 30
                
            expiring_jobs = get_expiring_jobs_by_recruiter(recruiter.id, days_threshold)
            
            return jsonify({
                'success': True,
                'expiring_jobs': expiring_jobs,
                'count': len(expiring_jobs)
            })
            
        except Exception as e:
            logger.error(f"Error getting expiring jobs: {str(e)}")
            return jsonify({'error': f"Failed to get expiring jobs: {str(e)}"}), 500
    
    # Template filters
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%b %d, %Y'):
        """Convert a datetime to a different format."""
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return value
        return value.strftime(format)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # Helper functions
    def calculate_match_score(candidate, job):
        try:
            # Get embeddings similarity using dot product
            candidate_embedding = candidate.embedding
            job_embedding = job.embedding
            
            if not candidate_embedding or not job_embedding:
                return 0.0
                
            embedding_similarity = sum(a * b for a, b in zip(candidate_embedding, job_embedding))
            
            # Get skills match
            candidate_skills = candidate.parsed_data.get('skills', []) if candidate.parsed_data else []
            required_skills = job.required_skills or []
            preferred_skills = job.preferred_skills or []
            
            # Normalize skills to lowercase for comparison
            candidate_skills_norm = set(s.lower() for s in candidate_skills)
            required_skills_norm = set(s.lower() for s in required_skills)
            preferred_skills_norm = set(s.lower() for s in preferred_skills)
            
            # Calculate match percentages
            if required_skills_norm:
                required_match = len(candidate_skills_norm.intersection(required_skills_norm)) / len(required_skills_norm)
            else:
                required_match = 1.0  # Full match if no required skills
                
            if preferred_skills_norm:
                preferred_match = len(candidate_skills_norm.intersection(preferred_skills_norm)) / len(preferred_skills_norm)
            else:
                preferred_match = 0.5  # Neutral score if no preferred skills
                
            # Weight required skills higher than preferred
            skills_match = (required_match * 0.7) + (preferred_match * 0.3)
            
            # Calculate combined score (60% embedding, 40% skills)
            combined_score = (embedding_similarity * 0.6) + (skills_match * 0.4)
            
            # Normalize to 0-1 range
            normalized_score = max(0.0, min(1.0, combined_score))
            return normalized_score
            
        except Exception as e:
            logger.error(f"Match score calculation failed: {str(e)}")
            return 0.0
    
    def parse_rate_limit(limit_str):
        limit, _, window = limit_str.partition('/')
        return int(limit), {'minute': 60, 'hour': 3600}.get(window, 60)
    
    return app

# The create_app function will be imported by main.py