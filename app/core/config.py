"""
Configuration management using Pydantic Settings.

This module provides centralized configuration management with 
environment variable loading and validation.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic Settings for automatic validation and type conversion.
    """
    
    # Database Configuration
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/tm2_healthcare",
        description="MongoDB connection URI"
    )
    database_name: str = Field(
        default="tm2_healthcare",
        description="MongoDB database name"
    )
    collection_name: str = Field(
        default="tm2_records",
        description="MongoDB collection name"
    )
    
    # OpenMRS Configuration
    openmrs_base_url: str = Field(
        default="http://localhost:8080/openmrs",
        description="OpenMRS base URL"
    )
    openmrs_username: str = Field(
        default="admin",
        description="OpenMRS API username"
    )
    openmrs_password: str = Field(
        default="Admin123",
        description="OpenMRS API password"
    )
    
    # Application Configuration
    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Security Configuration
    jwt_secret_key: Optional[str] = Field(
        default=None,
        description="JWT secret key for token generation"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key for external service authentication"
    )
    
    # Processing Configuration
    batch_size: int = Field(
        default=100,
        description="Batch size for processing records"
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB"
    )
    processing_timeout_seconds: int = Field(
        default=300,
        description="Processing timeout in seconds"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses lru_cache to ensure settings are loaded only once
    and reused across the application lifecycle.
    
    Returns:
        Settings: Application configuration object
    """
    return Settings()