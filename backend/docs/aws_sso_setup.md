# AWS SSO Setup Guide

This guide explains how to set up AWS SSO for the LLM Workflow Platform.

## Prerequisites

1. An AWS account with administrative access
2. AWS CLI installed and configured
3. Access to AWS SSO service

## Authentication Options

The LLM Workflow Platform supports two methods of AWS authentication:

1. **AWS SSO Device Authorization Flow** - The traditional SSO flow where users authenticate through a browser
2. **Direct AWS Credentials** - Using AWS access keys and session tokens directly

## Using Direct AWS Credentials

If you already have AWS credentials (access key, secret key, and session token), you can configure the application to use these directly:

1. Update your `.env` file with the following settings:

```
# AWS Credentials
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token
AWS_REGION=us-east-1
```

2. To authenticate, simply call the `/api/auth/aws-login` endpoint:

```bash
curl -X POST http://localhost:8000/api/auth/aws-login
```

This will return a JWT token that you can use for subsequent API calls.

## Setting up AWS SSO

### 1. Enable AWS SSO

1. Sign in to the AWS Management Console
2. Navigate to the AWS SSO service
3. Click "Enable AWS SSO"
4. Choose your identity source (AWS SSO, Active Directory, or External Identity Provider)
5. Follow the prompts to complete the setup

### 2. Create a Permission Set

1. In the AWS SSO console, navigate to "Permission sets"
2. Click "Create permission set"
3. Choose "Create a custom permission set"
4. Enter a name (e.g., "LLMWorkflowAccess")
5. Add the necessary permissions:
   - AmazonBedrockFullAccess
   - AmazonS3FullAccess
   - Any other services your application needs
6. Click "Create"

### 3. Assign Users

1. In the AWS SSO console, navigate to "AWS accounts"
2. Select your AWS account
3. Click "Assign users"
4. Select the users or groups you want to grant access to
5. Choose the permission set you created
6. Click "Assign users"

### 4. Configure the Application

1. Update your `.env` file with the following settings:

```
# AWS SSO
AWS_SSO_START_URL=https://d-xxxxxxxxxx.awsapps.com/start
AWS_SSO_REGION=us-east-1
AWS_SSO_ACCOUNT_ID=123456789012
AWS_SSO_ROLE_NAME=LLMWorkflowAccess
```

Replace the values with your actual AWS SSO configuration.

## Testing AWS SSO Login

You can test the AWS SSO login functionality using the provided test script:

```bash
cd backend
python scripts/test_aws_sso.py
```

This script will:
1. Register a client with AWS SSO
2. Start the device authorization flow
3. Provide a URL and code for you to complete the authorization
4. Wait for the authorization to complete

## Integrating with the Frontend

The frontend should implement the following flow:

1. Call the `/api/auth/register-client` endpoint to get a client ID and secret
2. Call the `/api/auth/device-authorization` endpoint with the client ID and secret
3. Display the verification URI and user code to the user
4. Poll the `/api/auth/token` endpoint with the client ID, secret, and device code until the user completes the authorization
5. Store the returned JWT token and use it for subsequent API calls

## Troubleshooting

### Common Issues

1. **"Failed to register with AWS SSO"**: Ensure your AWS credentials have the necessary permissions to access AWS SSO.

2. **"Authorization timed out"**: The user didn't complete the authorization within the time limit. Try again.

3. **"Could not validate credentials"**: The JWT token is invalid or expired. Refresh the token or log in again.

### Debugging

Enable debug logging by setting `DEBUG=true` in your `.env` file. This will provide more detailed logs about the AWS SSO authentication process. 