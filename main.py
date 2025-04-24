# main.py
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure critical environment variables are set
if 'DEMO_PASSWORD' not in os.environ and os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if line.strip().startswith('DEMO_PASSWORD='):
                value = line.split('=', 1)[1].strip()
                os.environ['DEMO_PASSWORD'] = value
                print(f"Manually loaded DEMO_PASSWORD from .env file")
                break

# Import after environment variables are loaded
from app import create_app, db
from models import Recruiter

# Create the Flask application instance
app = create_app()

# Ensure ONLY the demo admin account has the correct password from environment variable
# Regular user accounts will continue to use standard password management
with app.app_context():
    try:
        demo_password = os.environ.get('DEMO_PASSWORD')
        if demo_password:
            # Only sync the demo@example.com admin account with the environment variable
            demo_admin = Recruiter.query.filter_by(email='demo@example.com').first()
            if demo_admin:
                # Check if we need to reset the password (first run after env var change)
                if not demo_admin.check_password(demo_password):
                    print(f"Updating demo admin password to match DEMO_PASSWORD environment variable")
                    demo_admin.set_password(demo_password)
                    db.session.commit()
    except Exception as e:
        print(f"Error checking demo admin password: {e}", file=sys.stderr)

# This file is used as the entry point for the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)