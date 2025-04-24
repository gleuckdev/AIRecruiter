"""
Job Expiration Service - Manages job expiration and notifications.

This module provides functions to:
1. Check for expired jobs and mark them as expired
2. Check for jobs that will expire soon and mark them for notification
3. Handle job renewal
"""

import logging
from datetime import datetime, timedelta
from models import db, Job

logger = logging.getLogger(__name__)

def expire_jobs(days_threshold=0):
    """
    Mark jobs as expired if they have passed their expiration date.
    
    Args:
        days_threshold: Days threshold for expiration (0 = today)
        
    Returns:
        int: Number of jobs marked as expired
    """
    try:
        expiration_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Find jobs that have expired but still marked as active
        expired_jobs = Job.query.filter(
            Job.status == 'active',
            Job.expires_at < expiration_date
        ).all()
        
        count = 0
        for job in expired_jobs:
            job.status = 'expired'
            count += 1
            
        db.session.commit()
        logger.info(f"Marked {count} jobs as expired")
        return count
    
    except Exception as e:
        logger.error(f"Error in expire_jobs: {str(e)}")
        db.session.rollback()
        return 0

def mark_expiring_soon_jobs(days_threshold=7):
    """
    Mark jobs that will expire soon for notification.
    
    Args:
        days_threshold: Days threshold for notification (7 = notify for jobs expiring in 7 days)
        
    Returns:
        list: List of jobs marked for notification
    """
    try:
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_threshold)
        
        # Find active jobs that will expire soon and haven't been notified yet
        expiring_jobs = Job.query.filter(
            Job.status == 'active',
            Job.notification_sent == False,
            Job.expires_at >= start_date,
            Job.expires_at <= end_date
        ).all()
        
        job_list = []
        for job in expiring_jobs:
            job.notification_sent = True
            job_list.append({
                'id': job.id,
                'title': job.title,
                'recruiter_id': job.recruiter_id,
                'expires_at': job.expires_at.strftime('%Y-%m-%d')
            })
            
        db.session.commit()
        logger.info(f"Marked {len(job_list)} jobs for expiration notification")
        return job_list
    
    except Exception as e:
        logger.error(f"Error in mark_expiring_soon_jobs: {str(e)}")
        db.session.rollback()
        return []

def renew_job(job_id, days=60):
    """
    Renew a job for the specified number of days.
    
    Args:
        job_id: The ID of the job to renew
        days: Number of days to extend the job
        
    Returns:
        bool: True if renewal was successful, False otherwise
    """
    try:
        job = Job.query.get(job_id)
        if not job:
            logger.error(f"Job not found: {job_id}")
            return False
            
        job.renew(days)
        db.session.commit()
        logger.info(f"Job {job_id} renewed for {days} days")
        return True
    
    except Exception as e:
        logger.error(f"Error in renew_job: {str(e)}")
        db.session.rollback()
        return False

def get_expiring_jobs_by_recruiter(recruiter_id, days_threshold=7):
    """
    Get all jobs for a specific recruiter that are expiring within the threshold.
    
    Args:
        recruiter_id: The recruiter's ID
        days_threshold: Days threshold (jobs expiring within this many days)
        
    Returns:
        list: List of jobs expiring soon
    """
    try:
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_threshold)
        
        expiring_jobs = Job.query.filter(
            Job.recruiter_id == recruiter_id,
            Job.status == 'active',
            Job.expires_at >= start_date,
            Job.expires_at <= end_date
        ).all()
        
        return [{
            'id': job.id,
            'title': job.title,
            'expires_at': job.expires_at.strftime('%Y-%m-%d'),
            'days_left': (job.expires_at - start_date).days
        } for job in expiring_jobs]
    
    except Exception as e:
        logger.error(f"Error in get_expiring_jobs_by_recruiter: {str(e)}")
        return []

def run_expiration_check():
    """
    Run both expiration and notification checks.
    
    Returns:
        tuple: (expired_count, expiring_jobs)
    """
    expired_count = expire_jobs()
    expiring_jobs = mark_expiring_soon_jobs()
    return expired_count, expiring_jobs