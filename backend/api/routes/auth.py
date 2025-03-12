from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.auth import (
    Token, 
    DeviceAuthorizationRequest, 
    DeviceAuthorizationResponse, 
    CreateTokenRequest,
    UserResponse
)
from ...services.auth_service import AWSSSOService, get_current_user
from ...database import get_db
from ...models import User

router = APIRouter()


@router.post("/aws-login", response_model=Token)
async def aws_login(db: AsyncSession = Depends(get_db)):
    """Login with AWS credentials.
    
    This endpoint uses the AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, 
    and AWS_SESSION_TOKEN) configured in the application to authenticate the user.
    """
    return await AWSSSOService.login_with_aws_credentials(db)


@router.post("/register-client", response_model=dict)
async def register_client():
    """Register client with AWS SSO OIDC."""
    return await AWSSSOService.register_client()


@router.post("/device-authorization", response_model=DeviceAuthorizationResponse)
async def device_authorization(request: DeviceAuthorizationRequest):
    """Start device authorization flow."""
    return await AWSSSOService.start_device_authorization(
        client_id=request.client_id,
        client_secret=request.client_secret
    )


@router.post("/token", response_model=Token)
async def create_token(
    request: CreateTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create token from device code."""
    return await AWSSSOService.create_token_from_device_code(
        client_id=request.client_id,
        client_secret=request.client_secret,
        device_code=request.device_code,
        db=db
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user."""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh token."""
    from ...services.auth_service import create_token
    
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
            "full_name": current_user.full_name
        }
    } 