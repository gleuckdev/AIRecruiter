#!/usr/bin/env python
"""
Script to create a backup of the AI Recruiter Pro project.
This script will copy all the important files to an export directory
and create a compressed archive for download.
"""

import os
import shutil
import datetime
import tarfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def backup_project():
    """Create a backup of the project files"""
    
    # Create a timestamp for the backup directory
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = f"./export/ai-recruiter-pro_{timestamp}"
    archive_path = "./export/ai-recruiter-pro.tar.gz"
    
    # Create the export directory structure
    os.makedirs(export_dir, exist_ok=True)
    os.makedirs(f"{export_dir}/static", exist_ok=True)
    os.makedirs(f"{export_dir}/templates", exist_ok=True)
    os.makedirs(f"{export_dir}/utils", exist_ok=True)
    
    # List of files to copy
    files_to_copy = [
        # Python files
        "main.py",
        "app.py",
        "models.py",
        "migrations.py",
        "load_env.py",
        "create_admin.py",
        "add_sample_job.py",
        "add_sample_candidates.py",
        "add_test_data.py",
        "promote_to_senior.py",
        "reset_password.py",
        "backup_project.py",
        
        # Documentation
        "README.md",
        "CONTRIBUTING.md",
        "CHANGES.md",
        "SETUP_INSTRUCTIONS.md",
        "LICENSE",
        
        # Configuration
        ".env.example",
        ".gitignore",
        "requirements-app.txt",
        "pyproject.toml",
        
        # Test files
        "test_system_e2e.py",
        "test_resume_system.py",
        "test_phone_matching.py",
        "test_openai_integration.py",
        "run_all_tests.sh",
    ]
    
    # Copy the files
    files_copied = []
    for file_name in files_to_copy:
        if os.path.exists(file_name):
            logger.info(f"Copying file: {file_name}")
            shutil.copy2(file_name, f"{export_dir}/{file_name}")
            files_copied.append(file_name)
    
    # Copy template files if they exist
    if os.path.exists("templates"):
        logger.info("Copying template files")
        template_files = os.listdir("templates")
        for file_name in template_files:
            if file_name.endswith(".html"):
                shutil.copy2(f"templates/{file_name}", f"{export_dir}/templates/{file_name}")
                files_copied.append(f"templates/{file_name}")
    
    # Copy static files if they exist
    if os.path.exists("static"):
        logger.info("Copying static files")
        # Copy CSS files
        if os.path.exists("static/styles.css"):
            shutil.copy2("static/styles.css", f"{export_dir}/static/styles.css")
            files_copied.append("static/styles.css")
        
        # Copy JS files
        if os.path.exists("static/js"):
            os.makedirs(f"{export_dir}/static/js", exist_ok=True)
            js_files = os.listdir("static/js")
            for file_name in js_files:
                if file_name.endswith(".js"):
                    shutil.copy2(f"static/js/{file_name}", f"{export_dir}/static/js/{file_name}")
                    files_copied.append(f"static/js/{file_name}")
    
    # Copy utility files if they exist
    if os.path.exists("utils"):
        logger.info("Copying utility files")
        util_files = os.listdir("utils")
        for file_name in util_files:
            if file_name.endswith(".py"):
                shutil.copy2(f"utils/{file_name}", f"{export_dir}/utils/{file_name}")
                files_copied.append(f"utils/{file_name}")
                
    # Copy the requirements.txt file from export directory if it exists
    if os.path.exists("export/requirements.txt"):
        logger.info("Adding requirements.txt to export")
        shutil.copy2("export/requirements.txt", f"{export_dir}/requirements.txt")
        files_copied.append("requirements.txt")
    
    # Create tar.gz archive
    logger.info(f"Creating archive at {archive_path}")
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(export_dir, arcname=os.path.basename(export_dir))
        
        # Get file size
        file_size_bytes = os.path.getsize(archive_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        logger.info(f"Archive created successfully: {archive_path} ({file_size_mb:.2f} MB)")
        
        # Print summary
        print(f"\nBackup completed successfully!")
        print(f"Files copied: {len(files_copied)}")
        print(f"Backup directory: {export_dir}")
        print(f"Archive file: {archive_path} ({file_size_mb:.2f} MB)")
        print(f"Archive date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return export_dir, archive_path, files_copied
        
    except Exception as e:
        logger.error(f"Error creating archive: {str(e)}")
        print(f"Error creating archive: {str(e)}")
        return export_dir, None, files_copied

if __name__ == "__main__":
    backup_project()