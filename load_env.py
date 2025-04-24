import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if GCP credentials were loaded
if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
    print(f"GCP credentials file path: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"GCS bucket name: {os.environ.get('GCS_BUCKET_NAME', 'ai-recruiter-resumes')}")
else:
    print("GCP credentials not found in environment variables")