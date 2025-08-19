from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class Token(BaseModel):
    """Token schema."""
    access_token: str
    token_type: str
    user: Dict[str, Any]


class TokenData(BaseModel):
    """Token data schema."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    aws_identity_id: Optional[str] = None


class UserBase(BaseModel):
    """User base schema."""
    username: str
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User create schema."""
    aws_identity_id: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""
    id: str
    is_active: bool

    class Config:
        from_attributes = True


class DeviceAuthorizationRequest(BaseModel):
    """Device authorization request schema."""
    client_id: str
    client_secret: str


class DeviceAuthorizationResponse(BaseModel):
    """Device authorization response schema."""
    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int


class CreateTokenRequest(BaseModel):
    """Create token request schema."""
    client_id: str
    client_secret: str
    device_code: str 