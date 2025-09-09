"""
TM2 Healthcare Data Ingestion Service

A production-ready FastAPI application for processing TM2 dataset files
and integrating with OpenMRS healthcare systems.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.lifespan import lifespan
from app.api.endpoints import router
from app.models.api_models import ErrorResponse
from uuid import uuid4
from datetime import datetime
import logging

# Initialize settings
settings = get_settings()

# Create FastAPI application with lifespan management
app = FastAPI(
    title="TM2 Healthcare Data Ingestion Service",
    description="A production-ready service for processing TM2 dataset files and OpenMRS integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint providing service information.
    """
    return {
        "service": "TM2 Healthcare Data Ingestion Service",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "environment": settings.environment
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "service": "tm2-healthcare-service"
    }

# Exception handlers moved here from router

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTP exceptions to provide consistent error responses.
    """
    request_id = str(uuid4())
    logging.warning(
        f"HTTP exception occurred: status_code={exc.status_code}, detail={exc.detail}, request_id={request_id}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message="Request failed",
            error={
                "error_code": f"HTTP_{exc.status_code}",
                "error_type": "HTTPException",
                "message": str(exc.detail),
                "details": exc.detail if isinstance(exc.detail, dict) else None
            },
            request_id=request_id,
            timestamp=datetime.utcnow()
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handler for unexpected exceptions to provide consistent error responses.
    """
    request_id = str(uuid4())
    logging.error(
        f"Unexpected exception occurred: error_type={type(exc).__name__}, error_message={str(exc)}, request_id={request_id}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            message="An unexpected error occurred",
            error={
                "error_code": "INTERNAL_ERROR",
                "error_type": type(exc).__name__,
                "message": "An internal server error occurred. Please try again later.",
                "details": None  # Don't expose internal error details in production
            },
            request_id=request_id,
            timestamp=datetime.utcnow()
        ).model_dump()
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
