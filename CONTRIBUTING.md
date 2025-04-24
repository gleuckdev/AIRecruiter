# Contributing to AI Recruiter Pro

First off, thank you for considering contributing to AI Recruiter Pro! It's people like you that make this project such a great tool.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible.
* **Provide specific examples to demonstrate the steps**. Include links to files or GitHub projects, or copy/pasteable snippets, which you use in those examples.
* **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
* **Explain which behavior you expected to see instead and why.**
* **Include screenshots and animated GIFs** which show you following the described steps and clearly demonstrate the problem.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
* **Provide specific examples to demonstrate the steps**. Include copy/pasteable snippets which you use in those examples.
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why.
* **Include screenshots and animated GIFs** which help you demonstrate the steps or point out the part of the project which the suggestion is related to.
* **Explain why this enhancement would be useful** to most users.
* **List some other text editors or applications where this enhancement exists.**
* **Specify which version of the project you're using.**

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Include screenshots and animated GIFs in your pull request whenever possible.
* Follow the Python [PEP 8](https://www.python.org/dev/peps/pep-0008/) styleguide.
* Document new code based on the [Google Python Style Guide](http://google.github.io/styleguide/pyguide.html)
* End all files with a newline
* Avoid platform-dependent code

## Development Environment Setup

1. Fork the repository
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/ai-recruiter-pro.git
   cd ai-recruiter-pro
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements-app.txt
   ```
5. Set up your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
6. Run the migrations:
   ```bash
   python migrations.py
   ```
7. Run the app:
   ```bash
   python main.py
   ```

## Style Guidelines

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python Style Guide

* Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
* Use consistent indentation (4 spaces, not tabs)
* Maximum line length of 88 characters
* Use docstrings to document functions and classes

### JavaScript Style Guide

* Use 2 spaces for indentation
* Prefer single quotes for strings
* End statements with semicolons
* Add space after keywords and function names
* No trailing whitespace
* Naming conventions:
  * Use camelCase for variables and functions
  * Use PascalCase for classes and React components

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Thank You!

Thank you for your contributions - you help make this project better for everyone!