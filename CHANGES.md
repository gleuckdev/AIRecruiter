# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-04-23

### Added
- AI-powered candidate matching with jobs
- Resume processing and skill extraction
- Candidate persona generation with OpenAI
- Recruiter collaboration with sharing options
- Administrative role management
- Google Cloud Storage integration for resume storage
- Rating system for candidates (0-1 scale aligned with OpenAI metrics)
- Job token system for detecting similar job postings
- Bulk resume upload feature with progress tracking
- Role-based access control with granular permissions
- Responsive Material Design-inspired UI

### Changed
- Enhanced invitation system (removed email dependency, now uses shareable links)
- Improved button labels with action-oriented text
- Updated dashboard layout with card-based design
- Enhanced candidate details view with tabbed interface

### Fixed
- Proper environment variable management through .env
- Secure GCP credentials handling
- Fixed permission checks for shared resources
- Improved error handling for API requests
- Enhanced security by removing hardcoded credentials from UI
- Implemented environment-variable based password handling with DEMO_PASSWORD
- Added secure password synchronization for demo admin account
- Improved startup code to ensure demo account security across all environments

## [0.9.0] - 2025-03-15

### Added
- Initial beta release
- Basic candidate and job management
- Simple matching algorithm
- User authentication system
- Initial UI design