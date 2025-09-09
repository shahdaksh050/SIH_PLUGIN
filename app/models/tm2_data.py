"""
Pydantic models for TM2 healthcare data validation and serialization.

This module defines the data models for TM2 (Traditional Medicine Module 2) 
records, including validation rules and transformation logic.
"""

from datetime import datetime
from typing import Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict


class SystemType(str, Enum):
    """Traditional medicine system types supported by TM2."""
    AYURVEDA = "Ayurveda"
    SIDDHA = "Siddha"
    UNANI = "Unani"
    HOMEOPATHY = "Homeopathy"
    TRADITIONAL_CHINESE_MEDICINE = "Traditional Chinese Medicine"
    NATUROPATHY = "Naturopathy"
    YOGA = "Yoga"
    OTHER = "Other"


class SeverityLevel(str, Enum):
    """Condition severity levels."""
    MILD = "Mild"
    MODERATE = "Moderate"
    SEVERE = "Severe"
    CRITICAL = "Critical"
    UNKNOWN = "Unknown"


class TM2RawRecord(BaseModel):
    """
    Raw TM2 record as received from CSV file input.
    
    This model validates the basic structure and data types
    of incoming TM2 records before processing.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
        max_length=50,
        example="PAT001"
    )
    
    tm2_code: str = Field(
        ...,
        description="Traditional Medicine Module 2 code from ICD-11",
        min_length=1,
        max_length=20,
        example="TM2.A01.01"
    )
    
    condition_name: str = Field(
        ...,
        description="Name of the medical condition",
        min_length=1,
        max_length=200,
        example="Chronic Insomnia"
    )
    
    system_type: str = Field(
        ...,
        description="Traditional medicine system",
        example="Ayurveda"
    )
    
    severity: str = Field(
        ...,
        description="Condition severity level",
        example="Moderate"
    )
    
    diagnosis_date: str = Field(
        ...,
        description="Date of diagnosis (various formats accepted)",
        example="2024-01-15"
    )
    
    practitioner_id: str = Field(
        ...,
        description="Healthcare practitioner identifier",
        min_length=1,
        max_length=50,
        example="DOC001"
    )
    
    @validator('tm2_code')
    def validate_tm2_code(cls, v):
        """Validate TM2 code format."""
        if not v.startswith('TM2.'):
            raise ValueError('TM2 code must start with "TM2."')
        return v.upper()
    
    @validator('patient_id', 'practitioner_id')
    def validate_id_format(cls, v):
        """Validate ID format (alphanumeric and underscores only)."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('ID must contain only alphanumeric characters, hyphens, and underscores')
        return v.upper()


class TM2ProcessedRecord(BaseModel):
    """
    Processed TM2 record after validation and transformation.
    
    This model represents the cleaned and validated data that will be
    stored in MongoDB and submitted to OpenMRS.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    patient_id: str = Field(
        ...,
        description="Unique patient identifier",
        min_length=1,
        max_length=50,
        example="PAT001"
    )
    
    tm2_code: str = Field(
        ...,
        description="Traditional Medicine Module 2 code from ICD-11",
        min_length=1,
        max_length=20,
        example="TM2.A01.01"
    )
    
    condition_name: str = Field(
        ...,
        description="Name of the medical condition",
        min_length=1,
        max_length=200,
        example="Chronic Insomnia"
    )
    
    system_type: SystemType = Field(
        ...,
        description="Traditional medicine system (validated enum)"
    )
    
    severity: SeverityLevel = Field(
        ...,
        description="Condition severity level (validated enum)"
    )
    
    diagnosis_date: datetime = Field(
        ...,
        description="Date of diagnosis (parsed datetime)"
    )
    
    practitioner_id: str = Field(
        ...,
        description="Healthcare practitioner identifier",
        min_length=1,
        max_length=50,
        example="DOC001"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp"
    )
    
    source_file: Optional[str] = Field(
        default=None,
        description="Source filename for audit trail",
        max_length=255
    )
    
    # Additional processed fields
    icd11_category: Optional[str] = Field(
        default=None,
        description="ICD-11 category derived from TM2 code",
        max_length=100
    )
    
    traditional_diagnosis: Optional[str] = Field(
        default=None,
        description="Traditional medicine diagnosis in native terminology",
        max_length=500
    )
    
    @validator('system_type', pre=True)
    def normalize_system_type(cls, v):
        """Normalize system type to enum value."""
        if isinstance(v, str):
            # Try to match common variations
            v_lower = v.lower().strip()
            
            if v_lower in ['ayurveda', 'ayurved']:
                return SystemType.AYURVEDA
            elif v_lower in ['siddha', 'siddh']:
                return SystemType.SIDDHA
            elif v_lower in ['unani', 'yunani']:
                return SystemType.UNANI
            elif v_lower in ['homeopathy', 'homoeopathy', 'homeo']:
                return SystemType.HOMEOPATHY
            elif v_lower in ['tcm', 'traditional chinese medicine', 'chinese medicine']:
                return SystemType.TRADITIONAL_CHINESE_MEDICINE
            elif v_lower in ['naturopathy', 'naturo']:
                return SystemType.NATUROPATHY
            elif v_lower in ['yoga']:
                return SystemType.YOGA
            else:
                return SystemType.OTHER
        
        return v
    
    @validator('severity', pre=True)
    def normalize_severity(cls, v):
        """Normalize severity level to enum value."""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            
            if v_lower in ['mild', 'light', 'low']:
                return SeverityLevel.MILD
            elif v_lower in ['moderate', 'medium', 'moderate']:
                return SeverityLevel.MODERATE
            elif v_lower in ['severe', 'high', 'serious']:
                return SeverityLevel.SEVERE
            elif v_lower in ['critical', 'very severe', 'life threatening']:
                return SeverityLevel.CRITICAL
            else:
                return SeverityLevel.UNKNOWN
        
        return v


class TM2ValidationResult(BaseModel):
    """
    Result of TM2 record validation.
    
    This model contains the validation outcome and any error messages
    for a processed TM2 record.
    """
    
    is_valid: bool = Field(
        ...,
        description="Whether the record passed validation"
    )
    
    record: Optional[TM2ProcessedRecord] = Field(
        default=None,
        description="Validated record (if validation passed)"
    )
    
    errors: list[str] = Field(
        default_factory=list,
        description="List of validation error messages"
    )
    
    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings"
    )


class TM2ConceptMapping(BaseModel):
    """
    Mapping between TM2 codes and OpenMRS concepts.
    
    This model represents the relationship between traditional medicine
    codes and their corresponding OpenMRS concept representations.
    """
    
    tm2_code: str = Field(
        ...,
        description="TM2 code from ICD-11",
        example="TM2.A01.01"
    )
    
    openmrs_concept_uuid: Optional[str] = Field(
        default=None,
        description="OpenMRS concept UUID if mapping exists",
        example="5089AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    )
    
    concept_name: str = Field(
        ...,
        description="Human-readable concept name",
        example="Chronic Insomnia"
    )
    
    concept_description: Optional[str] = Field(
        default=None,
        description="Detailed concept description",
        max_length=1000
    )
    
    system_specific_names: dict[str, str] = Field(
        default_factory=dict,
        description="Traditional names in different systems",
        example={
            "ayurveda": "Nidranasha",
            "siddha": "Thookammai",
            "unani": "Qillat-un-Naum"
        }
    )
    
    icd11_foundation_id: Optional[str] = Field(
        default=None,
        description="ICD-11 Foundation ID for cross-referencing"
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Mapping creation timestamp"
    )
    
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )


class TM2ProcessingMetadata(BaseModel):
    """
    Metadata for TM2 processing operations.
    
    This model tracks processing information for audit and monitoring purposes.
    """
    
    processing_id: str = Field(
        ...,
        description="Unique processing session identifier"
    )
    
    filename: str = Field(
        ...,
        description="Original filename"
    )
    
    file_size_bytes: int = Field(
        ...,
        description="File size in bytes",
        ge=0
    )
    
    total_records: int = Field(
        ...,
        description="Total records in file",
        ge=0
    )
    
    processed_records: int = Field(
        default=0,
        description="Number of successfully processed records",
        ge=0
    )
    
    failed_records: int = Field(
        default=0,
        description="Number of failed records",
        ge=0
    )
    
    processing_start: datetime = Field(
        default_factory=datetime.utcnow,
        description="Processing start time"
    )
    
    processing_end: Optional[datetime] = Field(
        default=None,
        description="Processing completion time"
    )
    
    status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending",
        description="Current processing status"
    )
    
    error_summary: Optional[str] = Field(
        default=None,
        description="Summary of processing errors if any"
    )
    
    @property
    def processing_duration_seconds(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if self.processing_end:
            return (self.processing_end - self.processing_start).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100