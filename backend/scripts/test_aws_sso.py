#!/usr/bin/env python3
"""
Test script for AWS SSO login functionality.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth_service import AWSSSOService


async def test_aws_sso():
    """Test AWS SSO login functionality."""
    try:
        # Register client
        print("Registering client...")
        client_info = await AWSSSOService.register_client()
        print(f"Client registered: {json.dumps(client_info, indent=2)}")
        
        # Start device authorization
        print("\nStarting device authorization...")
        device_auth = await AWSSSOService.start_device_authorization(
            client_id=client_info["client_id"],
            client_secret=client_info["client_secret"]
        )
        print(f"Device authorization started: {json.dumps(device_auth, indent=2)}")
        
        # Print instructions for user
        print("\n" + "=" * 80)
        print(f"Please visit: {device_auth['verification_uri_complete']}")
        print(f"Or visit {device_auth['verification_uri']} and enter code: {device_auth['user_code']}")
        print("=" * 80 + "\n")
        
        # Wait for user to complete authorization
        print("Waiting for authorization...")
        print("Press Ctrl+C to cancel.")
        
        # This would normally be handled by the frontend
        # For testing purposes, we'll just wait for the user to manually complete the authorization
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_aws_sso()) 