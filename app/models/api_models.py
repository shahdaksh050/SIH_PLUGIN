"""
API request and response models for the TM2 Healthcare Service.

This module defines Pydantic models for API endpoints including
request validation, response formatting, and error handling.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ProcessingStatus(str, Enum):
    """Status values for processing operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ServiceStatus(str, Enum):
    """Service health status values."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


# Request Models

class FileUploadRequest(BaseModel):
    """
    Request model for file upload validation.
    
    Note: The actual file is handled by FastAPI's UploadFile,
    this model is for additional metadata validation.
    """
    
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the file being uploaded",
        max_length=500
    )
    
    batch_name: Optional[str] = Field(
        default=None,
        description="Optional batch name for grouping related files",
        max_length=100
    )
    
    skip_duplicates: bool = Field(
        default=True,
        description="Whether to skip duplicate records during processing"
    )
    
    validate_only: bool = Field(
        default=False,
        description="If true, only validate the file without processing"
    )


# Response Models

class APIResponse(BaseModel):
    """
    Base response model for all API endpoints.
    
    Provides consistent structure for API responses including
    success/error status, timestamps, and metadata.
    """
    model_config = ConfigDict(use_enum_values=True)
    
    success: bool = Field(
        ...,
        description="Whether the operation was successful"
    )
    
    message: str = Field(
        ...,
        description="Human-readable response message"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp in UTC"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing"
    )


class ProcessingSummary(BaseModel):
    """
    Summary of file processing results.
    """
    
    total_records: int = Field(
        ...,
        description="Total number of records in the file",
        ge=0
    )
    
    processed_records: int = Field(
        ...,
        description="Number of successfully processed records",
        ge=0
    )
    
    validated_records: int = Field(
        ...,
        description="Number of records that passed validation",
        ge=0
    )
    
    stored_records: int = Field(
        ...,
        description="Number of records stored in database",
        ge=0
    )
    
    submitted_records: int = Field(
        ...,
        description="Number of records submitted to OpenMRS",
        ge=0
    )
    
    duplicate_records: int = Field(
        default=0,
        description="Number of duplicate records skipped",
        ge=0
    )
    
    validation_errors: int = Field(
        default=0,
        description="Number of validation errors",
        ge=0
    )
    
    storage_errors: int = Field(
        default=0,
        description="Number of storage errors",
        ge=0
    )
    
    submission_errors: int = Field(
        default=0,
        description="Number of submission errors",
        ge=0
    )
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages"
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate as percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.submitted_records / self.total_records) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate overall error rate as percentage."""
        if self.total_records == 0:
            return 0.0
        total_errors = self.validation_errors + self.storage_errors + self.submission_errors
        return (total_errors / self.total_records) * 100


class ProcessingResult(APIResponse):
    """
    Response model for file processing operations.
    """
    
    processing_id: str = Field(
        ...,
        description="Unique processing session identifier"
    )
    
    filename: str = Field(
        ...,
        description="Name of the processed file"
    )
    
    status: ProcessingStatus = Field(
        ...,
        description="Current processing status"
    )
    
    summary: Optional[ProcessingSummary] = Field(
        default=None,
        description="Processing results summary"
    )
    
    processing_time_seconds: Optional[float] = Field(
        default=None,
        description="Total processing time in seconds",
        ge=0
    )


class DatabaseStatistics(BaseModel):
    """
    MongoDB database statistics.
    """
    
    connection_status: str = Field(
        ...,
        description="Database connection status"
    )
    
    total_records: int = Field(
        ...,
        description="Total number of records in database",
        ge=0
    )
    
    submitted_records: int = Field(
        ...,
        description="Number of successfully submitted records",
        ge=0
    )
    
    failed_records: int = Field(
        ...,
        description="Number of failed records",
        ge=0
    )
    
    pending_records: int = Field(
        ...,
        description="Number of pending records",
        ge=0
    )
    
    collection_size: int = Field(
        ...,
        description="Size of the main collection",
        ge=0
    )
    
    status_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Breakdown of records by status"
    )
    
    last_updated: datetime = Field(
        ...,
        description="Last statistics update timestamp"
    )


class OpenMRSStatistics(BaseModel):
    """
    OpenMRS client statistics.
    """
    
    initialized: bool = Field(
        ...,
        description="Whether the client is initialized"
    )
    
    base_url: str = Field(
        ...,
        description="OpenMRS server base URL"
    )
    
    username: str = Field(
        ...,
        description="API username"
    )
    
    requests_made: int = Field(
        ...,
        description="Total number of API requests made",
        ge=0
    )
    
    successful_submissions: int = Field(
        ...,
        description="Number of successful submissions",
        ge=0
    )
    
    failed_submissions: int = Field(
        ...,
        description="Number of failed submissions",
        ge=0
    )
    
    patients_created: int = Field(
        ...,
        description="Number of patients created",
        ge=0
    )
    
    concepts_created: int = Field(
        ...,
        description="Number of concepts created",
        ge=0
    )
    
    mock_entities: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of mock entities (for testing)"
    )
    
    last_updated: str = Field(
        ...,
        description="Last statistics update timestamp"
    )


class ServiceStatistics(BaseModel):
    """
    Overall service statistics.
    """
    
    files_processed: int = Field(
        ...,
        description="Total number of files processed",
        ge=0
    )
    
    records_processed: int = Field(
        ...,
        description="Total number of records processed",
        ge=0
    )
    
    records_validated: int = Field(
        ...,
        description="Total number of records validated",
        ge=0
    )
    
    records_stored: int = Field(
        ...,
        description="Total number of records stored",
        ge=0
    )
    
    records_submitted: int = Field(
        ...,
        description="Total number of records submitted",
        ge=0
    )
    
    validation_errors: int = Field(
        ...,
        description="Total validation errors",
        ge=0
    )
    
    storage_errors: int = Field(
        ...,
        description="Total storage errors",
        ge=0
    )
    
    submission_errors: int = Field(
        ...,
        description="Total submission errors",
        ge=0
    )
    
    duplicate_records: int = Field(
        ...,
        description="Total duplicate records encountered",
        ge=0
    )


class SystemStatus(APIResponse):
    """
    Response model for system status endpoint.
    """
    
    service_status: ServiceStatus = Field(
        ...,
        description="Overall service health status"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    
    environment: str = Field(
        ...,
        description="Deployment environment"
    )
    
    uptime_seconds: Optional[float] = Field(
        default=None,
        description="Service uptime in seconds",
        ge=0
    )
    
    processing_statistics: ServiceStatistics = Field(
        ...,
        description="Processing statistics"
    )
    
    database_statistics: DatabaseStatistics = Field(
        ...,
        description="Database statistics"
    )
    
    openmrs_statistics: OpenMRSStatistics = Field(
        ...,
        description="OpenMRS client statistics"
    )


# Error Response Models

class ValidationError(BaseModel):
    """
    Individual validation error details.
    """
    
    field: str = Field(
        ...,
        description="Field name that failed validation"
    )
    
    message: str = Field(
        ...,
        description="Validation error message"
    )
    
    invalid_value: Optional[Union[str, int, float, bool]] = Field(
        default=None,
        description="The invalid value that caused the error"
    )


class ErrorDetail(BaseModel):
    """
    Detailed error information.
    """
    
    error_code: str = Field(
        ...,
        description="Unique error code for categorization"
    )
    
    error_type: str = Field(
        ...,
        description="Error type classification"
    )
    
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    validation_errors: Optional[List[ValidationError]] = Field(
        default=None,
        description="Field-specific validation errors"
    )


class ErrorResponse(APIResponse):
    """
    Response model for API errors.
    """
    
    error: ErrorDetail = Field(
        ...,
        description="Detailed error information"
    )
    
    # Override success to always be False for error responses
    success: bool = Field(
        default=False,
        description="Always false for error responses"
    )


# Health Check Models

class ComponentHealth(BaseModel):
    """
    Health status of individual service components.
    """
    
    name: str = Field(
        ...,
        description="Component name"
    )
    
    status: ServiceStatus = Field(
        ...,
        description="Component health status"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional component details"
    )
    
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp"
    )


class HealthCheckResponse(APIResponse):
    """
    Response model for health check endpoint.
    """
    
    overall_status: ServiceStatus = Field(
        ...,
        description="Overall service health status"
    )
    
    components: List[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health status"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Service version"
    )
    
    environment: str = Field(
        ...,
        description="Deployment environment"
    )