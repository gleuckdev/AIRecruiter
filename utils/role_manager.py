"""
Role management utilities for AI Recruiter Pro.
These functions handle role assignments, permissions and user role changes.
"""
import logging
from models import db, Recruiter, Role

# Configure logging
logger = logging.getLogger(__name__)

def get_all_recruiters():
    """
    Get all recruiters sorted by creation date (newest first)
    
    Returns:
        list: List of Recruiter objects
    """
    return Recruiter.query.order_by(Recruiter.created_at.desc()).all()

def get_all_roles():
    """
    Get all available roles in the system
    
    Returns:
        list: List of Role objects
    """
    return Role.query.all()

def can_change_role(current_recruiter, target_recruiter, new_role_id):
    """
    Check if the current recruiter can change the target recruiter's role
    
    Args:
        current_recruiter: The Recruiter object making the change
        target_recruiter: The Recruiter object being changed
        new_role_id: The new role ID to assign
        
    Returns:
        tuple: (bool, str) - Whether the change is allowed and reason if not
    """
    # Cannot change own role
    if current_recruiter.id == target_recruiter.id:
        return False, "You cannot change your own role"
        
    # Only admins can promote/demote other admins
    if target_recruiter.is_admin() and not current_recruiter.is_admin():
        return False, "Only administrators can change the role of an administrator"
        
    # Only admins can promote to admin
    if new_role_id == 'admin' and not current_recruiter.is_admin():
        return False, "Only administrators can promote users to administrator"
        
    # Senior recruiters can only promote to recruiter
    if not current_recruiter.is_admin() and new_role_id not in ['recruiter']:
        return False, "You can only assign the recruiter role"
        
    return True, "Role change allowed"

def change_recruiter_role(recruiter_id, new_role_id, changed_by_id=None):
    """
    Change a recruiter's role
    
    Args:
        recruiter_id: The ID of the recruiter to change
        new_role_id: The new role ID to assign
        changed_by_id: The ID of the recruiter making the change
        
    Returns:
        tuple: (bool, str) - Whether the change was successful and a message
    """
    try:
        recruiter = Recruiter.query.get(recruiter_id)
        if not recruiter:
            return False, "Recruiter not found"
            
        # Get the role
        role = Role.query.filter_by(role_id=new_role_id).first()
        if not role:
            return False, f"Role '{new_role_id}' not found"
            
        # Update the recruiter's role
        old_role = recruiter.role_id
        recruiter.role_id = new_role_id
        recruiter.role = new_role_id  # For backward compatibility
        
        db.session.commit()
        
        # Log the change
        changed_by = "System"
        if changed_by_id:
            changed_by_user = Recruiter.query.get(changed_by_id)
            if changed_by_user:
                changed_by = changed_by_user.email
                
        logger.info(f"Recruiter {recruiter.email} role changed from {old_role} to {new_role_id} by {changed_by}")
        
        return True, f"Role successfully updated to {role.name}"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing role: {str(e)}")
        return False, str(e)