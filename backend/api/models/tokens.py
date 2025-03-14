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


class UserResponse(BaseModel):
    """User data in token response."""
    username: str
    email: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    """Response model for token creation."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse 