#!/usr/bin/env python3
"""
Test script for AWS credentials login.

This script demonstrates how to use the AWS credentials login endpoint
to authenticate with the LLM Workflow Platform.
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Import settings
from config import settings

def test_aws_credentials_login():
    """Test AWS credentials login."""
    
    # Check if AWS credentials are set
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        print("AWS credentials not set. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
        return False
    
    # Print AWS credentials info (without revealing secrets)
    print(f"Using AWS credentials:")
    print(f"  AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID[:4]}...{settings.AWS_ACCESS_KEY_ID[-4:]}")
    print(f"  AWS_SECRET_ACCESS_KEY: {settings.AWS_SECRET_ACCESS_KEY[:4]}...{settings.AWS_SECRET_ACCESS_KEY[-4:]}")
    print(f"  AWS_SESSION_TOKEN: {'Set' if settings.AWS_SESSION_TOKEN else 'Not set'}")
    print(f"  AWS_REGION: {settings.AWS_REGION}")
    
    # Get the API URL
    api_url = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/api/auth/aws-login"
    print(f"\nAttempting to login using AWS credentials at: {api_url}")
    
    try:
        # Make the request
        response = requests.post(api_url)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            print("\nLogin successful!")
            print(f"Access token: {data['access_token'][:20]}...")
            print(f"User: {data['user']['username']} ({data['user']['email']})")
            return True
        else:
            print(f"\nLogin failed with status code: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"\nError making request: {e}")
        return False

if __name__ == "__main__":
    # Run the test
    success = test_aws_credentials_login()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 