"""
FastAPI endpoints for the TM2 Healthcare Data Ingestion Service.

This module defines the REST API routes for file upload, processing,
and status monitoring.
"""

import time
from datetime import datetime
from typing import Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, RequestIDContext, HealthcareOperationContext
from app.core.lifespan import get_mongo_service, get_openmrs_client
from app.services.mongo_service import MongoService
from app.services.openmrs_client import OpenMRSRestClient
from app.services.ingestion_service import TM2IngestionService
from app.models.api_models import (
    ProcessingResult, SystemStatus, ErrorResponse, HealthCheckResponse,
    ProcessingStatus, ServiceStatus, ComponentHealth, ServiceStatistics,
    DatabaseStatistics, OpenMRSStatistics
)

# Initialize router and dependencies
router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)

# Service startup time for uptime calculation
SERVICE_START_TIME = time.time()


def get_ingestion_service(
    mongo_service: MongoService = Depends(get_mongo_service),
    openmrs_client: OpenMRSRestClient = Depends(get_openmrs_client)
) -> TM2IngestionService:
    """
    Dependency to get TM2 ingestion service instance.
    
    Args:
        mongo_service: MongoDB service dependency
        openmrs_client: OpenMRS client dependency
        
    Returns:
        TM2IngestionService: Configured ingestion service
    """
    return TM2IngestionService(mongo_service, openmrs_client)


@router.post(
    "/ingest/trigger",
    response_model=ProcessingResult,
    summary="Upload and process TM2 dataset file",
    description="Upload a CSV file containing TM2 dataset records for processing and OpenMRS submission",
    responses={
        200: {"description": "File processed successfully"},
        400: {"description": "Invalid file format or validation errors"},
        422: {"description": "Request validation errors"},
        500: {"description": "Internal server error"}
    }
)
async def trigger_ingestion(
    file: UploadFile = File(..., description="CSV file containing TM2 dataset records"),
    ingestion_service: TM2IngestionService = Depends(get_ingestion_service)
) -> ProcessingResult:
    """
    Upload and process a TM2 dataset file.
    
    This endpoint accepts CSV files containing TM2 (Traditional Medicine Module 2)
    records, validates the data, stores it in MongoDB, and submits it to OpenMRS.
    
    **Expected CSV Format:**
    - patient_id: Unique patient identifier
    - tm2_code: Traditional medicine code (e.g., TM2.A01.01)
    - condition_name: Medical condition name
    - system_type: Medicine system (Ayurveda, Siddha, Unani, etc.)
    - severity: Condition severity (Mild, Moderate, Severe, Critical)
    - diagnosis_date: Date of diagnosis
    - practitioner_id: Healthcare provider identifier
    
    **Processing Steps:**
    1. File validation and CSV parsing
    2. Record-by-record data validation
    3. Duplicate detection and filtering
    4. Storage in MongoDB database
    5. Submission to OpenMRS via REST API
    6. Status tracking and error handling
    """
    request_id = str(uuid4())
    
    with RequestIDContext(request_id):
        logger.info(
            "File upload initiated",
            filename=file.filename,
            content_type=file.content_type,
            file_size=file.size if hasattr(file, 'size') else 'unknown'
        )
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            logger.warning("Invalid file type uploaded", filename=file.filename)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_FILE_TYPE",
                    "message": "Only CSV files are supported",
                    "supported_types": [".csv"]
                }
            )
        
        # Validate file size (optional)
        max_size_mb = settings.max_file_size_mb
        if hasattr(file, 'size') and file.size:
            if file.size > max_size_mb * 1024 * 1024:
                logger.warning(
                    "File size exceeds limit",
                    filename=file.filename,
                    file_size=file.size,
                    max_size_mb=max_size_mb
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail={
                        "error_code": "FILE_TOO_LARGE",
                        "message": f"File size exceeds {max_size_mb}MB limit",
                        "max_size_mb": max_size_mb
                    }
                )
        
        try:
            # Process the file
            with HealthcareOperationContext("file_ingestion", record_count=None):
                processing_start = time.time()

                # Log file details before processing
                logger.info(
                    "Starting file processing",
                    processing_id=request_id,
                    filename=file.filename,
                    file_size=getattr(file, 'size', 'unknown'),
                    content_type=file.content_type
                )

                result = await ingestion_service.process_tm2_file(
                    file_content=file.file,
                    filename=file.filename
                )

                processing_time = time.time() - processing_start

                # Determine overall status
                if result["status"] == "completed":
                    summary = result.get("summary", {})
                    if summary.get("submission_errors", 0) > 0:
                        overall_status = ProcessingStatus.PARTIAL
                    else:
                        overall_status = ProcessingStatus.COMPLETED
                else:
                    overall_status = ProcessingStatus.FAILED

                # Build response
                response = ProcessingResult(
                    success=result["status"] in ["completed", "partial"],
                    message=f"File processing {result['status']}",
                    processing_id=result["processing_id"],
                    filename=result["filename"],
                    status=overall_status,
                    summary=result.get("summary"),
                    processing_time_seconds=processing_time,
                    request_id=request_id
                )

                # Enhanced logging with detailed statistics
                summary_info = result.get("summary", {})
                logger.info(
                    "File processing completed",
                    processing_id=result["processing_id"],
                    status=result["status"],
                    processing_time_seconds=round(processing_time, 2),
                    total_records=summary_info.get("total_records", 0),
                    processed_records=summary_info.get("processed_records", 0),
                    validated_records=summary_info.get("validated_records", 0),
                    stored_records=summary_info.get("stored_records", 0),
                    submitted_records=summary_info.get("submitted_records", 0),
                    duplicate_records=summary_info.get("duplicate_records", 0),
                    validation_errors=summary_info.get("validation_errors", 0),
                    storage_errors=summary_info.get("storage_errors", 0),
                    submission_errors=summary_info.get("submission_errors", 0)
                )

                return response
        
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during file processing",
                filename=file.filename,
                error=str(e),
                exc_info=True
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "PROCESSING_ERROR",
                    "message": "An unexpected error occurred during file processing",
                    "details": str(e)
                }
            )


@router.get(
    "/status",
    response_model=SystemStatus,
    summary="Get system status and statistics",
    description="Retrieve current system status, processing statistics, and service health information"
)
async def get_system_status(
    ingestion_service: TM2IngestionService = Depends(get_ingestion_service)
) -> SystemStatus:
    """
    Get comprehensive system status and statistics.
    
    This endpoint provides detailed information about:
    - Service health and operational status
    - Processing statistics and metrics
    - Database connection and record counts  
    - OpenMRS client status and submission metrics
    - Service uptime and performance data
    """
    request_id = str(uuid4())
    
    with RequestIDContext(request_id):
        logger.info("System status requested")
        
        try:
            # Get processing status from ingestion service
            status_data = await ingestion_service.get_processing_status()
            
            # Calculate uptime
            uptime_seconds = time.time() - SERVICE_START_TIME
            
            # Build comprehensive status response
            response = SystemStatus(
                success=True,
                message="System status retrieved successfully",
                service_status=ServiceStatus.OPERATIONAL,
                version="1.0.0",
                environment=settings.environment,
                uptime_seconds=uptime_seconds,
                processing_statistics=ServiceStatistics(**status_data["processing_statistics"]),
                database_statistics=DatabaseStatistics(**status_data["mongodb_statistics"]),
                openmrs_statistics=OpenMRSStatistics(**status_data["openmrs_statistics"]),
                request_id=request_id
            )
            
            logger.info("System status retrieved successfully")
            
            return response
        
        except Exception as e:
            logger.error(
                "Failed to retrieve system status",
                error=str(e),
                exc_info=True
            )
            
            # Return degraded status with partial information
            return SystemStatus(
                success=False,
                message="System status retrieval partially failed",
                service_status=ServiceStatus.DEGRADED,
                version="1.0.0",
                environment=settings.environment,
                uptime_seconds=time.time() - SERVICE_START_TIME,
                processing_statistics=ServiceStatistics(
                    files_processed=0,
                    records_processed=0,
                    records_validated=0,
                    records_stored=0,
                    records_submitted=0,
                    validation_errors=0,
                    storage_errors=0,
                    submission_errors=0,
                    duplicate_records=0
                ),
                database_statistics=DatabaseStatistics(
                    connection_status="error",
                    total_records=0,
                    submitted_records=0,
                    failed_records=0,
                    pending_records=0,
                    collection_size=0,
                    last_updated=datetime.utcnow()
                ),
                openmrs_statistics=OpenMRSStatistics(
                    initialized=False,
                    base_url=settings.openmrs_base_url,
                    username=settings.openmrs_username,
                    requests_made=0,
                    successful_submissions=0,
                    failed_submissions=0,
                    patients_created=0,
                    concepts_created=0,
                    last_updated=datetime.utcnow().isoformat()
                ),
                request_id=request_id
            )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check endpoint",
    description="Simple health check for monitoring and load balancer integration"
)
async def health_check(
    mongo_service: MongoService = Depends(get_mongo_service),
    openmrs_client: OpenMRSRestClient = Depends(get_openmrs_client)
) -> HealthCheckResponse:
    """
    Perform health check of service components.
    
    This endpoint is designed for:
    - Load balancer health checks
    - Monitoring system integration
    - Quick service availability verification
    
    It checks the status of critical components and returns
    an overall health assessment.
    """
    request_id = str(uuid4())
    components = []
    overall_status = ServiceStatus.OPERATIONAL
    
    with RequestIDContext(request_id):
        logger.debug("Health check initiated")
        
        # Check MongoDB service
        try:
            mongo_stats = await mongo_service.get_statistics()
            mongo_status = (
                ServiceStatus.OPERATIONAL 
                if mongo_stats["connection_status"] == "connected" 
                else ServiceStatus.DOWN
            )
            
            components.append(ComponentHealth(
                name="mongodb",
                status=mongo_status,
                details={
                    "connection_status": mongo_stats["connection_status"],
                    "total_records": mongo_stats["total_records"]
                }
            ))
            
            if mongo_status != ServiceStatus.OPERATIONAL:
                overall_status = ServiceStatus.DEGRADED
                
        except Exception as e:
            logger.error("MongoDB health check failed", error=str(e))
            components.append(ComponentHealth(
                name="mongodb",
                status=ServiceStatus.DOWN,
                details={"error": str(e)}
            ))
            overall_status = ServiceStatus.DEGRADED
        
        # Check OpenMRS client
        try:
            openmrs_stats = await openmrs_client.get_statistics()
            openmrs_status = (
                ServiceStatus.OPERATIONAL 
                if openmrs_stats["initialized"] 
                else ServiceStatus.DOWN
            )
            
            components.append(ComponentHealth(
                name="openmrs_client",
                status=openmrs_status,
                details={
                    "initialized": openmrs_stats["initialized"],
                    "base_url": openmrs_stats["base_url"],
                    "successful_submissions": openmrs_stats["successful_submissions"]
                }
            ))
            
            if openmrs_status != ServiceStatus.OPERATIONAL:
                overall_status = ServiceStatus.DEGRADED
                
        except Exception as e:
            logger.error("OpenMRS client health check failed", error=str(e))
            components.append(ComponentHealth(
                name="openmrs_client",
                status=ServiceStatus.DOWN,
                details={"error": str(e)}
            ))
            overall_status = ServiceStatus.DEGRADED
        
        response = HealthCheckResponse(
            success=overall_status in [ServiceStatus.OPERATIONAL, ServiceStatus.DEGRADED],
            message=f"Health check completed - status: {overall_status.value}",
            overall_status=overall_status,
            components=components,
            version="1.0.0",
            environment=settings.environment,
            request_id=request_id
        )
        
        logger.info(
            "Health check completed",
            overall_status=overall_status.value,
            component_count=len(components)
        )
        
        return response


