from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.auth import (
    Token, 
    UserResponse
)
from backend.services.auth_service import AWSSSOService, get_current_user
from backend.database import get_db
from backend.models import User
# Import directly from the tokens.py file to avoid using the models directory
from pydantic import BaseModel
from typing import Dict, Optional, List


class AuthClientResponse(BaseModel):
    """Response model for client registration."""
    client_id: str
    client_secret: str


class DeviceAuthorizationRequest(BaseModel):
    """Request model for device authorization."""
    client_id: str
    client_secret: str


class DeviceAuthorizationResponse(BaseModel):
    """Response model for device authorization."""
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: Optional[int] = 5


class TokenRequest(BaseModel):
    """Request model for token creation."""
    client_id: str
    client_secret: str
    device_code: str


class TokenResponse(BaseModel):
    """Response model for token creation."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

from backend.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/aws-login", response_model=Token)
async def aws_login(db: AsyncSession = Depends(get_db)):
    """Login with AWS credentials.
    
    This endpoint uses the AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, 
    and AWS_SESSION_TOKEN) configured in the application to authenticate the user.
    """
    return await AWSSSOService.login_with_aws_credentials(db)


@router.post("/register-client", response_model=AuthClientResponse)
async def register_client():
    """Register client with AWS SSO OIDC."""
    try:
        logger.info("Registering client with AWS SSO OIDC")
        client = await AWSSSOService.register_client()
        return client
    except Exception as e:
        logger.error(f"Error registering client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register client: {str(e)}"
        )


@router.post("/device-authorization", response_model=DeviceAuthorizationResponse)
async def start_device_authorization(
    request: DeviceAuthorizationRequest
):
    """Start device authorization flow with AWS SSO."""
    try:
        logger.info("Starting device authorization flow")
        authorization = await AWSSSOService.start_device_authorization(
            client_id=request.client_id,
            client_secret=request.client_secret
        )
        return authorization
    except Exception as e:
        logger.error(f"Error starting device authorization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start device authorization: {str(e)}"
        )


@router.post("/token", response_model=TokenResponse)
async def create_token(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create token from device code."""
    try:
        # Try to create token from device code
        logger.info(f"Creating token from device code")
        response = await AWSSSOService.create_token_from_device_code(
            request.client_id,
            request.client_secret,
            request.device_code,
            db
        )
        
        if response:
            logger.info(f"Successfully created token for user: {response.get('user', {}).get('username')}")
            logger.info(f"User AWS credentials obtained: access_key={bool(response.get('user', {}).get('aws_access_key_id'))}, secret_key={bool(response.get('user', {}).get('aws_secret_access_key'))}, token={bool(response.get('user', {}).get('aws_session_token'))}")
            return response
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create token"
            )
    except HTTPException as http_exc:
        # Log the exception
        logger.warning(f"HTTP exception in token creation: {http_exc.detail}")
        # Re-raise the exception
        raise http_exc
    except Exception as e:
        # Log the exception
        logger.error(f"Error creating token: {str(e)}")
        
        # Return a proper error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create token: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh token."""
    from backend.services.auth_service import create_token
    
    # Create new token
    token_data = {
        "sub": current_user.username,
        "email": current_user.email,
        "aws_identity_id": current_user.aws_identity_id
    }
    jwt_token = create_token(token_data)
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "id": current_user.id,
            "is_active": current_user.is_active
        }
    } 