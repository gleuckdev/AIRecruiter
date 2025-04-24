# AI Recruiter Pro

<p align="center">
  <img src="static/images/logo.svg" alt="AI Recruiter Pro Logo" width="200"/>
</p>

AI-powered recruitment platform that intelligently matches candidates with job opportunities through advanced natural language processing and AI algorithms.

## 🚀 Features

- **AI-Powered Matching**: Uses OpenAI embedding models to match candidates with suitable job openings
- **Smart Resume Processing**: Automatically extracts skills, experience, and qualifications from resumes
- **Candidate Persona Generation**: Creates detailed candidate profiles using AI
- **Recruiter Collaboration**: Share candidates and jobs with team members
- **Advanced Role-Based Access Control**: Granular permission system with administrator, senior recruiter, and recruiter roles
- **Cloud Storage Integration**: Store candidate resumes in Google Cloud Storage
- **Responsive Design**: Modern Material Design-inspired UI
- **Bulk Resume Upload**: Process multiple candidate resumes at once
- **Job Token System**: Intelligently groups similar job postings for improved analytics
- **Candidate Rating System**: Collect and manage recruiter feedback on candidates

## 📸 Screenshots

<p align="center">
  <img src="static/images/screenshots/dashboard.png" alt="Dashboard" width="400"/>
  <img src="static/images/screenshots/candidate-matching.png" alt="Candidate Matching" width="400"/>
</p>

## 🔄 Data Sharing System

The platform includes a sophisticated data sharing system that allows recruiters to collaborate effectively:

- **Sharing During Invitation**: Administrators and Senior Recruiters can enable data sharing when inviting new team members
- **Granular Permissions**: Choose to share job listings, candidates, or both
- **Visual Indicators**: Shared resources display "Shared by [Name]" to clearly indicate ownership
- **Filtering Options**: Dedicated tabs for filtering between owned and shared resources
- **Dynamic Updates**: Changes to shared resources are instantly visible to all team members with access

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Google Cloud Storage account (optional, falls back to local storage)
- OpenAI API key

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-recruiter-pro.git
   cd ai-recruiter-pro
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt  # For exact versions
   # OR
   pip install -r requirements-app.txt  # For minimum versions
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up the database**
   ```bash
   python migrations.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Access the application**
   Open your browser and go to: http://localhost:5000

## ⚙️ Configuration

### Environment Variables

See `.env.example` for a complete list of configuration options. The most important ones are:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL database connection string |
| `OPENAI_API_KEY` | Your OpenAI API key for AI features |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account credentials file |
| `GCS_BUCKET_NAME` | Google Cloud Storage bucket name for resume storage |
| `SECRET_KEY` | Secret key for session encryption |
| `DEMO_PASSWORD` | Password for the demo admin account (improves security) |

## 🔒 Google Cloud Storage Setup

This application can use Google Cloud Storage to store candidate resumes, making them accessible from anywhere and reducing local storage needs:

1. Create a Google Cloud Project
2. Create a service account with Storage Admin permissions
3. Download the service account credentials JSON file
4. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of this file
5. Create a bucket and set the `GCS_BUCKET_NAME` environment variable

The application will automatically fall back to local storage if GCS credentials are not provided.

## 📋 Admin Guide

### Initial Setup

After installation, create an admin account:
```bash
python create_admin.py --email admin@example.com --password SecurePassword123
```

### Adding Sample Data

You can add sample data to test the application:
```bash
python add_test_data.py
```

## 🔐 Security Best Practices

- Keep your `.env` file secure and never commit it to version control
- Store the Google Cloud credentials file securely
- Regularly rotate your API keys and credentials
- Use strong passwords for database and admin accounts
- Always set the `DEMO_PASSWORD` environment variable to a secure value
- Never expose login credentials in UI elements or public-facing pages
- Set up proper HTTPS in production

### Role-Based Access Control System

The application implements a three-tier role hierarchy:

- **Administrator**: Full system access with user management capabilities
- **Senior Recruiter**: Enhanced permissions for team management, with ability to invite users and share data
- **Recruiter**: Standard permissions for candidate and job management

Each role has specific permissions:

| Feature | Recruiter | Senior Recruiter | Administrator |
|---------|-----------|-----------------|---------------|
| View Candidates | ✓ | ✓ | ✓ |
| Rate Candidates | ✓ | ✓ | ✓ |
| Manage Jobs | ✓ | ✓ | ✓ |
| Bulk Upload | ✗ | ✓ | ✓ |
| Invite Users | ✗ | ✓ | ✓ |
| Manage Teams | ✗ | ✓ | ✓ |
| System Config | ✗ | ✗ | ✓ |
| Data Analytics | ✗ | ✓ | ✓ |

### Demo Admin Account Security

The application uses a special security mechanism for the demo admin account:

- The password for the demo admin account (`demo@example.com`) is controlled by the `DEMO_PASSWORD` environment variable
- This variable is loaded from the `.env` file at startup
- The application automatically synchronizes the demo account password with this environment variable
- Regular user accounts (non-demo) continue to use standard password management
- This approach ensures that demo credentials can be centrally managed without hardcoding 
- The demo account password is automatically reset to match the environment variable upon application startup

## 🚀 Deployment

For production deployment:

1. Set `FLASK_ENV=production` and `DEBUG=False`
2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn --bind 0.0.0.0:5000 main:app
   ```
3. Set up proper HTTPS with a valid SSL certificate
4. Configure database connection pooling
5. Consider using a reverse proxy like Nginx

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/yourusername/ai-recruiter-pro/issues).