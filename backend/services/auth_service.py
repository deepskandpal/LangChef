import boto3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Union
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import uuid4

from backend.config import settings
from backend.models import User
from backend.database import get_db
from backend.core.logging import get_logger

# Configure logging
logger = get_logger(__name__)

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
    
    # Check if AWS session token is expired
    if user.aws_token_expiry:
        try:
            # Make sure both datetimes are timezone naive for comparison
            now = datetime.utcnow()
            # If aws_token_expiry is timezone aware, convert it to naive
            token_expiry = user.aws_token_expiry
            if hasattr(token_expiry, 'tzinfo') and token_expiry.tzinfo:
                # Convert to naive UTC datetime
                token_expiry = token_expiry.replace(tzinfo=None)
            
            if now > token_expiry:
                logger.warning(f"AWS session token expired for user {user.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="AWS session expired, please log in again",
                    headers={"X-AWS-Session-Expired": "true"}
                )
        except TypeError as type_error:
            # If there's a TypeError (likely due to datetime comparison), consider the token expired
            logger.error(f"Error comparing token expiry times: {type_error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Error validating AWS token expiry, please log in again",
                headers={"X-AWS-Session-Expired": "true"}
            )
    
    return user

# Add a new function to validate AWS credentials
async def validate_aws_credentials(user: User) -> bool:
    """Validate AWS credentials by making a test call to AWS."""
    logger.info(f"Validating AWS credentials for user: {user.username}")
    
    if not user.aws_access_key_id or not user.aws_secret_access_key:
        logger.warning(f"Missing AWS credentials for user {user.username} - access_key: {bool(user.aws_access_key_id)}, secret_key: {bool(user.aws_secret_access_key)}")
        return False
        
    # Check if AWS token is expired
    if user.aws_token_expiry:
        try:
            # Make sure both datetimes are timezone naive for comparison
            now = datetime.utcnow()
            # If aws_token_expiry is timezone aware, convert it to naive
            token_expiry = user.aws_token_expiry
            if hasattr(token_expiry, 'tzinfo') and token_expiry.tzinfo:
                # Convert to naive UTC datetime
                token_expiry = token_expiry.replace(tzinfo=None)
            
            if now > token_expiry:
                logger.warning(f"AWS token expired for user {user.username} - expiry: {token_expiry}, now: {now}")
                return False
        except Exception as e:
            logger.error(f"Error comparing token expiry times: {e}")
            return False
        
    try:
        # Try to create a boto3 session with user credentials
        boto3_session = boto3.Session(
            aws_access_key_id=user.aws_access_key_id,
            aws_secret_access_key=user.aws_secret_access_key,
            aws_session_token=user.aws_session_token,
            region_name=settings.AWS_REGION
        )
        
        # Try a simple API call to verify credentials
        sts_client = boto3_session.client('sts')
        identity = sts_client.get_caller_identity()
        
        logger.info(f"AWS credentials valid for user {user.username} - identity: {identity.get('Arn')}")
        # If we get here, credentials are valid
        return True
    except Exception as e:
        logger.error(f"Error validating AWS credentials for user {user.username}: {e}")
        return False

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
                    "full_name": user.full_name,
                    "id": user.id,
                    "is_active": user.is_active
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
            logger.info(f"Creating token from device code: {device_code[:5]}...")
            
            # Try to get token from AWS SSO OIDC
            client = get_aws_sso_oidc_client()
            
            try:
                # Create token from device code
                token_response = client.create_token(
                    clientId=client_id,
                    clientSecret=client_secret,
                    deviceCode=device_code,
                    grantType="urn:ietf:params:oauth:grant-type:device_code"
                )
                
                logger.info("Successfully created token from device code")
                access_token = token_response["accessToken"]
                
                # Get AWS SSO client
                sso_client = get_aws_sso_client()
                
                # Get user info
                try:
                    # The AWS SSO client doesn't have a get_profile method
                    # We need to use the account list to get user information
                    username = f"user_{int(time.time())}"
                    email = f"{username}@example.com"
                    full_name = f"User {int(time.time())}"
                    user_id = ""
                    
                    # Try to get AWS account list to extract user information
                    try:
                        logger.info("Retrieving account list to get user information")
                        account_info = sso_client.list_accounts(accessToken=access_token)
                        
                        if account_info and 'accountList' in account_info and account_info['accountList']:
                            # Found accounts, try to extract email/username from the first account
                            first_account = account_info['accountList'][0]
                            logger.info(f"Found account: {first_account.get('accountName', 'Unknown')}")
                            
                            # Try to get email
                            if first_account.get('emailAddress'):
                                email = first_account.get('emailAddress')
                                # Extract username from email
                                email_parts = email.split('@')
                                if len(email_parts) > 0 and email_parts[0]:
                                    username = email_parts[0]
                                    full_name = username.replace(".", " ").title()
                    except Exception as account_error:
                        logger.warning(f"Could not retrieve account list: {account_error}")
                    
                    # Try to get role credentials to get additional identity information
                    try:
                        # Check if we have the needed settings
                        if settings.AWS_SSO_ACCOUNT_ID and settings.AWS_SSO_ROLE_NAME:
                            logger.info(f"Getting role credentials for {settings.AWS_SSO_ACCOUNT_ID}/{settings.AWS_SSO_ROLE_NAME}")
                            role_credentials = sso_client.get_role_credentials(
                                accessToken=access_token,
                                accountId=settings.AWS_SSO_ACCOUNT_ID,
                                roleName=settings.AWS_SSO_ROLE_NAME
                            )
                            # Successfully got role credentials, which confirms user's identity
                            logger.info("Successfully got role credentials")
                            
                            # Extract AWS credentials
                            aws_access_key_id = role_credentials.get('roleCredentials', {}).get('accessKeyId')
                            aws_secret_access_key = role_credentials.get('roleCredentials', {}).get('secretAccessKey')
                            aws_session_token = role_credentials.get('roleCredentials', {}).get('sessionToken')
                            aws_token_expiry = role_credentials.get('roleCredentials', {}).get('expiration')
                            
                            if aws_token_expiry:
                                # Convert from milliseconds to datetime
                                aws_token_expiry = datetime.fromtimestamp(aws_token_expiry / 1000)
                            
                            logger.info("Extracted AWS credentials from role credentials")
                    except Exception as role_error:
                        logger.warning(f"Could not get role credentials: {role_error}")
                        # We'll continue without role credentials, but set defaults
                        aws_access_key_id = None
                        aws_secret_access_key = None
                        aws_session_token = None
                        aws_token_expiry = None
                    
                    # Put together user info
                    user_info = {
                        "username": username,
                        "email": email,
                        "name": full_name,
                        "userId": user_id
                    }
                    
                    logger.info(f"User info: {user_info}")
                    
                    # Check if user exists
                    result = await db.execute(select(User).filter(User.username == username))
                    user = result.scalars().first()
                    
                    if user is None:
                        # Create new user
                        logger.info(f"Creating new user: {user_info.get('username')}")
                        user = User(
                            id=str(uuid4()),  # Explicitly set a UUID for the user id
                            username=user_info.get("username"),
                            email=user_info.get("email", f"{user_info.get('username')}@example.com"),
                            full_name=user_info.get("name", user_info.get("username")),
                            aws_identity_id=user_info.get("userId", ""),
                            aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key,
                            aws_session_token=aws_session_token,
                            aws_token_expiry=aws_token_expiry,
                            is_active=True
                        )
                        db.add(user)
                    else:
                        # Update existing user
                        logger.info(f"Updating existing user: {user.username}")
                        user.aws_access_key_id = aws_access_key_id
                        user.aws_secret_access_key = aws_secret_access_key
                        user.aws_session_token = aws_session_token
                        user.aws_token_expiry = aws_token_expiry
                        user.is_active = True
                    
                    await db.commit()
                    logger.info(f"User {user.username} successfully saved to database")
                    
                    # Create JWT token
                    token_data = {
                        "sub": user.username,
                        "email": user.email
                    }
                    jwt_token = create_token(token_data)
                    logger.info("JWT token successfully created")
                    
                    return {
                        "access_token": jwt_token,
                        "token_type": "bearer",
                        "user": {
                            "username": user.username,
                            "email": user.email,
                            "full_name": user.full_name,
                            "id": user.id,  # This should now be a valid string
                            "is_active": user.is_active
                        }
                    }
                except Exception as user_info_error:
                    logger.error(f"Error creating user profile: {user_info_error}")
                    raise
            except Exception as token_error:
                # Check for specific AWS errors to map to appropriate HTTP responses
                error_message = str(token_error)
                
                # Handle various AWS SSO error cases
                if "ExpiredTokenException" in error_message:
                    logger.info("Device code has expired")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="expired_token"
                    )
                
                if "SlowDownException" in error_message:
                    logger.info("Polling too frequently, slow down")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="slow_down"
                    )
                
                if "AccessDeniedException" in error_message:
                    logger.info("Access denied by user")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="access_denied"
                    )
                
                if "InvalidGrantException" in error_message:
                    logger.info("Invalid grant - treating as authorization pending")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="authorization_pending"
                    )
                
                # Re-raise any other errors
                raise token_error
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error in create_token_from_device_code: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create token from device code: {str(e)}"
            ) 
    
