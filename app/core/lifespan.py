"""
FastAPI lifespan management for resource lifecycle control.

This module handles application startup and shutdown events,
managing database connections and other resources.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.services.mongo_service import MongoService
from app.services.openmrs_client import OpenMRSRestClient

# Initialize logging first
setup_logging()
logger = get_logger(__name__)

# Global service instances
_mongo_service: MongoService = None
_openmrs_client: OpenMRSRestClient = None

settings = get_settings()


async def startup_event() -> None:
    """
    Initialize services and resources during application startup.
    
    This function is called before the application starts accepting requests.
    It initializes database connections, external service clients, and other
    resources needed for the application to function properly.
    """
    global _mongo_service, _openmrs_client
    
    logger.info("Starting TM2 Healthcare Data Ingestion Service")
    
    try:
        # Initialize MongoDB service (mock for testing)
        logger.info("Initializing MongoDB service", database_name=settings.database_name)
        _mongo_service = MongoService()
        await _mongo_service.initialize()
        logger.info("MongoDB service initialized successfully")
        
        # Initialize OpenMRS client (mock for testing)
        logger.info(
            "Initializing OpenMRS client", 
            base_url=settings.openmrs_base_url,
            username=settings.openmrs_username
        )
        _openmrs_client = OpenMRSRestClient(
            base_url=settings.openmrs_base_url,
            username=settings.openmrs_username,
            password=settings.openmrs_password
        )
        await _openmrs_client.initialize()
        logger.info("OpenMRS client initialized successfully")
        
        # Log startup completion
        logger.info(
            "Service startup completed successfully",
            environment=settings.environment,
            log_level=settings.log_level,
            batch_size=settings.batch_size
        )
        
    except Exception as e:
        logger.error("Failed to start service", error=str(e), exc_info=True)
        raise


async def shutdown_event() -> None:
    """
    Clean up resources during application shutdown.
    
    This function is called when the application is shutting down.
    It properly closes database connections, cleans up resources,
    and logs the shutdown process.
    """
    global _mongo_service, _openmrs_client
    
    logger.info("Starting TM2 Healthcare Data Ingestion Service shutdown")
    
    try:
        # Cleanup OpenMRS client
        if _openmrs_client:
            logger.info("Closing OpenMRS client connection")
            await _openmrs_client.close()
            _openmrs_client = None
            logger.info("OpenMRS client connection closed")
        
        # Cleanup MongoDB service
        if _mongo_service:
            logger.info("Closing MongoDB service connection")
            await _mongo_service.close()
            _mongo_service = None
            logger.info("MongoDB service connection closed")
        
        logger.info("Service shutdown completed successfully")
        
    except Exception as e:
        logger.error("Error during service shutdown", error=str(e), exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    
    This async context manager handles the complete lifecycle of the FastAPI
    application, from startup to shutdown. It ensures proper resource
    initialization and cleanup.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control is yielded to the application runtime
    """
    # Startup
    await startup_event()
    
    try:
        # Application is running - yield control to FastAPI
        yield
    finally:
        # Shutdown
        await shutdown_event()


def get_mongo_service() -> MongoService:
    """
    Get the global MongoDB service instance.
    
    This function provides access to the MongoDB service initialized
    during application startup. It should be used as a dependency
    in FastAPI routes.
    
    Returns:
        MongoService: Initialized MongoDB service instance
        
    Raises:
        RuntimeError: If the service is not initialized
    """
    if _mongo_service is None:
        raise RuntimeError("MongoDB service not initialized. Check application startup.")
    
    return _mongo_service


def get_openmrs_client() -> OpenMRSRestClient:
    """
    Get the global OpenMRS client instance.
    
    This function provides access to the OpenMRS REST client initialized
    during application startup. It should be used as a dependency
    in FastAPI routes.
    
    Returns:
        OpenMRSRestClient: Initialized OpenMRS client instance
        
    Raises:
        RuntimeError: If the client is not initialized
    """
    if _openmrs_client is None:
        raise RuntimeError("OpenMRS client not initialized. Check application startup.")
    
    return _openmrs_client