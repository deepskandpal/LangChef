import boto3
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..config import settings
from ..models import User
from ..database import get_db

# Configure logging
logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

# AWS clients
def get_aws_client(service_name):
    """Get AWS client with session token if available."""
    if settings.AWS_SESSION_TOKEN:
        return boto3.client(
            service_name,
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN
        )
    else:
        return boto3.client(
            service_name,
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

def get_aws_sso_client():
    """Get AWS SSO client."""
    return get_aws_client('sso')

def get_aws_sso_oidc_client():
    """Get AWS SSO OIDC client."""
    return get_aws_client('sso-oidc')

def get_aws_sts_client():
    """Get AWS STS client."""
    return get_aws_client('sts')

def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user

class AWSSSOService:
    """AWS SSO authentication service."""
    
    @staticmethod
    async def get_aws_identity() -> Dict[str, Any]:
        """Get AWS identity using the provided AWS credentials."""
        try:
            # Check if we have AWS credentials
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="AWS credentials not provided"
                )
            
            # Get AWS identity
            sts_client = get_aws_sts_client()
            identity = sts_client.get_caller_identity()
            
            return {
                "account_id": identity["Account"],
                "user_id": identity["UserId"],
                "arn": identity["Arn"]
            }
        except Exception as e:
            logger.error(f"Error getting AWS identity: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get AWS identity: {str(e)}"
            )
    
    @staticmethod
    async def login_with_aws_credentials(db: AsyncSession) -> Dict[str, Any]:
        """Login with AWS credentials."""
        try:
            # Get AWS identity
            identity = await AWSSSOService.get_aws_identity()
            
            # Extract username from ARN
            arn_parts = identity["arn"].split("/")
            username = arn_parts[-1] if len(arn_parts) > 1 else arn_parts[0]
            
            # Create or update user
            result = await db.execute(select(User).filter(User.aws_identity_id == identity["user_id"]))
            user = result.scalars().first()
            
            if user is None:
                # Try to get user info from AWS
                email = f"{username}@example.com"  # Default email if we can't get it
                full_name = username  # Default name if we can't get it
                
                # Create new user
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    aws_identity_id=identity["user_id"]
                )
                db.add(user)
            else:
                # Update user
                user.is_active = True
            
            await db.commit()
            
            # Create JWT token
            token_data = {
                "sub": user.username,
                "email": user.email,
                "aws_identity_id": user.aws_identity_id
            }
            jwt_token = create_token(token_data)
            
            return {
                "access_token": jwt_token,
                "token_type": "bearer",
                "user": {
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name
                }
            }
        except Exception as e:
            logger.error(f"Error logging in with AWS credentials: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to login with AWS credentials: {str(e)}"
            )
    
    # Legacy SSO methods - kept for backward compatibility
    @staticmethod
    async def register_client() -> Dict[str, str]:
        """Register client with AWS SSO OIDC."""
        try:
            client = get_aws_sso_oidc_client()
            response = client.register_client(
                clientName="LLM Workflow Platform",
                clientType="public",
                scopes=["openid"]
            )
            
            return {
                "client_id": response["clientId"],
                "client_secret": response["clientSecret"],
                "expiration": str(response["clientSecretExpiresAt"])
            }
        except Exception as e:
            logger.error(f"Error registering client with AWS SSO OIDC: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register with AWS SSO"
            )
    
    @staticmethod
    async def start_device_authorization(client_id: str, client_secret: str) -> Dict[str, str]:
        """Start device authorization flow."""
        try:
            client = get_aws_sso_oidc_client()
            response = client.start_device_authorization(
                clientId=client_id,
                clientSecret=client_secret,
                startUrl=settings.AWS_SSO_START_URL
            )
            
            return {
                "device_code": response["deviceCode"],
                "user_code": response["userCode"],
                "verification_uri": response["verificationUri"],
                "verification_uri_complete": response["verificationUriComplete"],
                "expires_in": response["expiresIn"],
                "interval": response["interval"]
            }
        except Exception as e:
            logger.error(f"Error starting device authorization: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start device authorization"
            )
    
    @staticmethod
    async def create_token_from_device_code(
        client_id: str,
        client_secret: str,
        device_code: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """Create token from device code."""
        try:
            client = get_aws_sso_oidc_client()
            
            # Poll for token
            max_attempts = 60  # 5 minutes with 5-second interval
            for _ in range(max_attempts):
                try:
                    response = client.create_token(
                        clientId=client_id,
                        clientSecret=client_secret,
                        deviceCode=device_code,
                        grantType="urn:ietf:params:oauth:grant-type:device_code"
                    )
                    
                    # Get access token
                    access_token = response["accessToken"]
                    
                    # Get user info
                    sso_client = get_aws_sso_client()
                    user_info = sso_client.get_profile(accessToken=access_token)
                    
                    # Create or update user
                    result = await db.execute(
                        select(User).filter(User.email == user_info["email"])
                    )
                    user = result.scalars().first()
                    
                    if user is None:
                        user = User(
                            username=user_info["username"],
                            email=user_info["email"],
                            full_name=user_info.get("name"),
                            aws_identity_id=user_info.get("id")
                        )
                        db.add(user)
                    else:
                        user.username = user_info["username"]
                        user.full_name = user_info.get("name")
                        user.aws_identity_id = user_info.get("id")
                        user.is_active = True
                    
                    await db.commit()
                    
                    # Create JWT token
                    token_data = {
                        "sub": user.username,
                        "email": user.email,
                        "aws_identity_id": user.aws_identity_id
                    }
                    jwt_token = create_token(token_data)
                    
                    return {
                        "access_token": jwt_token,
                        "token_type": "bearer",
                        "user": {
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name
                        }
                    }
                except client.exceptions.AuthorizationPendingException:
                    # User hasn't authorized yet, wait and retry
                    time.sleep(5)
                    continue
                except Exception as e:
                    logger.error(f"Error creating token: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create token"
                    )
            
            # If we get here, authorization timed out
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Authorization timed out"
            )
        except Exception as e:
            logger.error(f"Error in create_token_from_device_code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create token from device code"
            ) 