# AWS Credentials Login Implementation

This document summarizes the changes made to implement direct AWS credentials login in the LLM Workflow Platform.

## Overview

The LLM Workflow Platform now supports two methods of AWS authentication:

1. **AWS SSO Device Authorization Flow** - The traditional SSO flow where users authenticate through a browser
2. **Direct AWS Credentials** - Using AWS access keys and session tokens directly

## Backend Changes

### Configuration

- Updated `config.py` to include `AWS_SESSION_TOKEN` in the settings
- Updated `.env.example` to include `AWS_SESSION_TOKEN` as a configurable environment variable

### Authentication Service

- Modified `services/auth_service.py` to:
  - Create a common `get_aws_client` function that handles session tokens
  - Add `get_aws_sts_client` function to interact with AWS STS
  - Add `get_aws_identity` method to retrieve AWS identity information
  - Add `login_with_aws_credentials` method to authenticate using AWS credentials
  - Keep legacy SSO methods for backward compatibility

### API Routes

- Added a new endpoint in `api/routes/auth.py`:
  - `POST /api/auth/aws-login` - Authenticates using AWS credentials configured on the server

### Documentation

- Updated `docs/auth_api.md` to document the new AWS login endpoint
- Updated `docs/aws_sso_setup.md` to include information about using AWS credentials directly
- Created a test script `scripts/test_aws_credentials.py` to demonstrate the AWS credentials login

## Frontend Changes

### Authentication Context

- Updated `contexts/AuthContext.js` to:
  - Add `loginWithAWS` method to call the new AWS login endpoint
  - Store and use JWT tokens for authenticated requests
  - Update the refresh token functionality to use the API

### Login Page

- Modified `pages/Login.js` to:
  - Add a new "Use AWS Credentials" button
  - Implement `handleAWSLogin` function to call the `loginWithAWS` method
  - Update the UI to accommodate both login methods

## How It Works

1. The user configures AWS credentials on the server:
   ```
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_SESSION_TOKEN=your-session-token
   AWS_REGION=us-east-1
   ```

2. When the user clicks "Use AWS Credentials" on the login page:
   - The frontend calls the `/api/auth/aws-login` endpoint
   - The backend uses the configured AWS credentials to get the caller's identity
   - The backend creates or updates a user record based on the AWS identity
   - The backend generates a JWT token and returns it to the frontend
   - The frontend stores the token and user information

3. The user is now authenticated and can use the application with the permissions associated with their AWS identity.

## Testing

You can test the AWS credentials login using the provided test script:

```bash
cd backend
./scripts/test_aws_credentials.py
```

This script will:
1. Check if AWS credentials are configured
2. Call the AWS login endpoint
3. Display the result of the authentication attempt 