from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_workflow")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    
    def model_post_init(self, __context) -> None:
        """Validate settings after initialization."""
        # Only validate SECRET_KEY if it's explicitly set to the default placeholder
        if self.SECRET_KEY == "your-secret-key-for-jwt":
            raise ValueError("SECRET_KEY must be set to a secure random value")
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: Optional[str] = os.getenv("AWS_SESSION_TOKEN")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # AWS SSO
    AWS_SSO_START_URL: str = os.getenv("AWS_SSO_START_URL", "https://d-xxxxxxxxxx.awsapps.com/start")
    AWS_SSO_REGION: str = os.getenv("AWS_SSO_REGION", "us-east-1")
    AWS_SSO_ACCOUNT_ID: str = os.getenv("AWS_SSO_ACCOUNT_ID", "123456789012")
    AWS_SSO_ROLE_NAME: str = os.getenv("AWS_SSO_ROLE_NAME", "AdministratorAccess")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings() 