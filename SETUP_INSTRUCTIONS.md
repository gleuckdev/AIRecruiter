# AI Recruiter Pro Setup Instructions

This document provides detailed instructions for setting up and deploying the AI Recruiter Pro application in various environments.

## Local Development Setup

### Prerequisites

1. Python 3.9+ installed
2. PostgreSQL database server installed and running
3. Google Cloud Platform account (optional, for resume storage)
4. OpenAI API key

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ai-recruiter-pro.git
cd ai-recruiter-pro
```

### Step 2: Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-app.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file to include:

```
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/ai_recruiter

# Application Settings
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your_secure_random_key
SESSION_SECRET=another_secure_random_key
# The password for the built-in demo admin account (demo@example.com)
DEMO_PASSWORD=a_very_secure_password_for_demo_admin

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Google Cloud Storage (optional)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your-service-account-credentials.json
GCS_BUCKET_NAME=your-gcs-bucket-name
```

### Step 4: Initialize the Database

Run the database migrations:

```bash
python migrations.py
```

### Step 5: Create an Admin User

```bash
python create_admin.py --email admin@example.com --password SecurePassword123 --name "Admin User"
```

### Step 6: Run the Development Server

```bash
python main.py
```

The application will be available at http://localhost:5000

## Production Deployment

### Option 1: Traditional Server Deployment

#### Prerequisites

1. Linux server with Python 3.9+
2. Nginx or Apache web server
3. PostgreSQL database
4. SSL certificate (Let's Encrypt recommended)

#### Step 1: Clone and Set Up the Application

```bash
git clone https://github.com/yourusername/ai-recruiter-pro.git
cd ai-recruiter-pro
python -m venv venv
source venv/bin/activate
pip install -r requirements-app.txt
```

#### Step 2: Configure Environment Variables

Create a `.env` file with production settings:

```
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/ai_recruiter_prod

# Application Settings
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your_very_secure_random_key
SESSION_SECRET=another_very_secure_random_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=path/to/your-service-account-credentials.json
GCS_BUCKET_NAME=your-gcs-bucket-name
```

#### Step 3: Set Up Nginx Configuration

Create an Nginx configuration file:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Step 4: Set Up Systemd Service

Create a systemd service file:

```ini
[Unit]
Description=AI Recruiter Pro
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/ai-recruiter-pro
Environment="PATH=/path/to/ai-recruiter-pro/venv/bin"
EnvironmentFile=/path/to/ai-recruiter-pro/.env
ExecStart=/path/to/ai-recruiter-pro/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable ai-recruiter
sudo systemctl start ai-recruiter
```

### Option 2: Docker Deployment

#### Prerequisites

1. Docker and Docker Compose installed
2. SSL certificate (for production)

#### Step 1: Create a Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt

COPY . .

ENV FLASK_ENV=production
ENV DEBUG=False

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

#### Step 2: Create a docker-compose.yml file

```yaml
version: '3'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads
      - ./credentials:/app/credentials
    restart: always

  db:
    image: postgres:13
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${PGUSER}
      - POSTGRES_PASSWORD=${PGPASSWORD}
      - POSTGRES_DB=${PGDATABASE}
    restart: always

volumes:
  postgres_data:
```

#### Step 3: Configure Environment Variables

Create a `.env` file for Docker:

```
# Database Configuration
PGUSER=postgres
PGPASSWORD=your_secure_password
PGDATABASE=ai_recruiter
DATABASE_URL=postgresql://postgres:your_secure_password@db:5432/ai_recruiter

# Application Settings
SECRET_KEY=your_very_secure_random_key
SESSION_SECRET=another_very_secure_random_key
# Secure password for the demo admin account
DEMO_PASSWORD=strong_password_for_demo_user

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Google Cloud Storage
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/your-service-account-credentials.json
GCS_BUCKET_NAME=your-gcs-bucket-name
```

#### Step 4: Run Docker Compose

```bash
docker-compose up -d
```

#### Step 5: Initialize the Database and Create Admin

```bash
docker-compose exec web python migrations.py
docker-compose exec web python create_admin.py --email admin@example.com --password SecurePassword123
```

## Database Backup and Restore

### Backup

```bash
pg_dump -U username -d ai_recruiter -h localhost -F c -f backup.dump
```

### Restore

```bash
pg_restore -U username -d ai_recruiter -h localhost -c backup.dump
```

## Security Best Practices

1. Regularly update dependencies
2. Rotate API keys and secrets periodically
3. Enable HTTPS with proper SSL certificate
4. Use strong passwords for all accounts
5. Implement IP whitelisting for admin access
6. Set up proper firewall rules
7. Enable database encryption at rest
8. Regularly back up the database
9. Monitor application logs for suspicious activity
10. Implement rate limiting for API endpoints

## Troubleshooting

### Database Connection Issues

1. Check the `DATABASE_URL` in your `.env` file
2. Ensure the database server is running
3. Verify database user permissions

### OpenAI API Issues

1. Check the `OPENAI_API_KEY` in your `.env` file
2. Verify the OpenAI API key is active and has sufficient credits
3. Check the application logs for specific error messages

### Google Cloud Storage Issues

1. Verify the path to your Google Cloud credentials file
2. Ensure the service account has Storage Admin permissions
3. Check that the specified GCS bucket exists and is accessible

### Application Not Starting

1. Check the application logs for error messages
2. Verify all required environment variables are set
3. Ensure all dependencies are installed
4. Check if the port is already in use by another application