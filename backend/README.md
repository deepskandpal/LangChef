# LLM Workflow Platform Backend

This is the backend service for the LLM Workflow Platform, built with FastAPI and SQLAlchemy.

## Development Setup

### Using uv Package Manager

This project uses [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver.

#### Installation

1. Install uv:

```bash
pip install uv
```

2. Install dependencies:

```bash
# Create a virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

#### Managing Dependencies

- Add a new dependency:

```bash
uv pip add package_name
```

- Update the lock file after modifying pyproject.toml:

```bash
uv pip compile pyproject.toml -o uv.lock
```

### Running the Application

#### Using Docker

```bash
docker-compose up -d
```

#### Locally

```bash
uvicorn main:app --reload
```

### Running Tests

```bash
pytest
```

## Authentication

The LLM Workflow Platform supports two methods of AWS authentication:

1. **AWS SSO Device Authorization Flow** - The traditional SSO flow where users authenticate through a browser
2. **Direct AWS Credentials** - Using AWS access keys and session tokens directly

### Using AWS Credentials

To use AWS credentials directly:

1. Set the following environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN` (optional)
   - `AWS_REGION`

2. Test the AWS credentials login:

```bash
./scripts/test_aws_credentials.py
```

For more details, see the [AWS SSO Setup Guide](docs/aws_sso_setup.md).

## Project Structure

- `api/`: API routes and endpoints
- `models/`: SQLAlchemy models
- `services/`: Business logic
- `utils/`: Utility functions
- `migrations/`: Alembic migrations
- `scripts/`: Utility scripts
- `docs/`: Documentation

## Environment Variables

Copy `.env.example` to `.env` and update the values as needed. 