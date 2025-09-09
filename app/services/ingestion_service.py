"""
TM2 data ingestion service orchestrating the complete data pipeline.

This module implements the core business logic for processing TM2 dataset files,
validating data, storing in MongoDB, and submitting to OpenMRS.
"""

import asyncio
import hashlib
import io
from datetime import datetime
from typing import Dict, List, Any, Optional, BinaryIO
from uuid import uuid4

import pandas as pd
from dateutil import parser as date_parser

from app.core.logging import get_logger, HealthcareOperationContext
from app.core.config import get_settings
from app.services.mongo_service import MongoService
from app.services.openmrs_client import OpenMRSRestClient
from app.models.tm2_data import TM2RawRecord, TM2ProcessedRecord

logger = get_logger(__name__)
settings = get_settings()


class TM2IngestionService:
    """
    Service for orchestrating TM2 data ingestion pipeline.
    
    This service handles the complete data processing workflow:
    1. File validation and parsing
    2. Data transformation and validation
    3. Storage in MongoDB
    4. Submission to OpenMRS
    5. Error handling and recovery
    """
    
    def __init__(self, mongo_service: MongoService, openmrs_client: OpenMRSRestClient):
        """
        Initialize the ingestion service.
        
        Args:
            mongo_service: MongoDB service instance
            openmrs_client: OpenMRS client instance
        """
        self.mongo_service = mongo_service
        self.openmrs_client = openmrs_client
        
        # Processing statistics
        self.processing_stats = {
            "files_processed": 0,
            "records_processed": 0,
            "records_validated": 0,
            "records_stored": 0,
            "records_submitted": 0,
            "validation_errors": 0,
            "storage_errors": 0,
            "submission_errors": 0,
            "duplicate_records": 0
        }
    
    async def process_tm2_file(self, file_content: BinaryIO, filename: str) -> Dict[str, Any]:
        """
        Process a complete TM2 dataset file.
        
        Args:
            file_content: File content as binary stream
            filename: Original filename
            
        Returns:
            Dict: Processing results and statistics
        """
        processing_id = str(uuid4())
        
        with HealthcareOperationContext("tm2_file_processing"):
            logger.info(
                "Starting TM2 file processing",
                processing_id=processing_id,
                filename=filename
            )
            
            try:
                # Read and parse CSV file
                raw_data = await self._read_csv_file(file_content)
                logger.info(
                    "CSV file parsed successfully",
                    processing_id=processing_id,
                    raw_record_count=len(raw_data)
                )
                
                # Process records in batches
                processing_results = await self._process_records_batch(
                    raw_data, processing_id
                )
                
                # Update global statistics
                self._update_processing_stats(processing_results)
                
                # Prepare final result
                result = {
                    "processing_id": processing_id,
                    "filename": filename,
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "summary": processing_results,
                    "statistics": self.processing_stats.copy()
                }
                
                logger.info(
                    "TM2 file processing completed",
                    processing_id=processing_id,
                    **processing_results
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Failed to process TM2 file",
                    processing_id=processing_id,
                    filename=filename,
                    error=str(e),
                    exc_info=True
                )
                
                return {
                    "processing_id": processing_id,
                    "filename": filename,
                    "status": "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "statistics": self.processing_stats.copy()
                }
    
    async def _read_csv_file(self, file_content: BinaryIO) -> List[Dict[str, Any]]:
        """
        Read and parse CSV file content with robust error handling.

        Args:
            file_content: Binary file content

        Returns:
            List[Dict]: Parsed CSV data as list of dictionaries

        Raises:
            ValueError: If file format is invalid
        """
        try:
            # Reset file pointer to beginning (critical fix for UploadFile)
            file_content.seek(0)

            # Read raw content for validation
            raw_content = file_content.read()

            # Check if file is empty
            if not raw_content or len(raw_content.strip()) == 0:
                raise ValueError("File is empty or contains no data")

            # Try different encodings if UTF-8 fails
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            df = None
            successful_encoding = None

            for encoding in encodings_to_try:
                try:
                    file_content.seek(0)  # Reset pointer for each attempt
                    df = pd.read_csv(io.BytesIO(file_content.read()), encoding=encoding)
                    successful_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue
                except pd.errors.EmptyDataError:
                    raise ValueError("CSV file contains no data rows")
                except Exception as e:
                    if encoding == encodings_to_try[-1]:  # Last encoding attempted
                        raise ValueError(f"Failed to parse CSV with any supported encoding: {str(e)}")
                    continue

            if df is None or df.empty:
                raise ValueError("No valid data found in CSV file")

            logger.info(
                "CSV file read successfully",
                encoding=successful_encoding,
                raw_content_size=len(raw_content),
                dataframe_shape=df.shape,
                columns=list(df.columns)
            )

            # Validate required columns
            required_columns = {
                'patient_id', 'tm2_code', 'condition_name', 'system_type',
                'severity', 'diagnosis_date', 'practitioner_id'
            }

            missing_columns = required_columns - set(df.columns)
            if missing_columns:
                logger.error(
                    "Missing required columns in CSV",
                    missing_columns=list(missing_columns),
                    available_columns=list(df.columns)
                )
                raise ValueError(f"Missing required columns: {missing_columns}")

            # Check for empty headers
            empty_headers = [col for col in df.columns if not col or str(col).strip() == '']
            if empty_headers:
                logger.warning("CSV contains empty column headers", empty_headers=empty_headers)

            # Validate that we have actual data rows (not just headers)
            if len(df) == 0:
                raise ValueError("CSV file contains headers but no data rows")

            # Check for completely empty rows
            non_empty_rows = len(df.dropna(how='all'))
            if non_empty_rows == 0:
                raise ValueError("CSV file contains no non-empty data rows")

            # Convert to list of dictionaries, filtering out empty rows
            records = []
            for idx, row in df.iterrows():
                # Skip rows where all values are NaN or empty
                if row.dropna().empty:
                    logger.warning(f"Skipping empty row at index {idx}")
                    continue

                # Convert row to dict and clean up
                record = {}
                for col in df.columns:
                    value = row[col]
                    # Handle NaN values
                    if pd.isna(value):
                        record[col] = None
                    else:
                        record[col] = str(value).strip() if isinstance(value, str) else value

                records.append(record)

            logger.info(
                "CSV parsing completed successfully",
                total_records=len(records),
                non_empty_rows=non_empty_rows,
                empty_rows_filtered=len(df) - len(records),
                columns=list(df.columns),
                encoding=successful_encoding
            )

            return records

        except ValueError:
            # Re-raise ValueError as-is (our custom validation errors)
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during CSV parsing",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    async def _process_records_batch(
        self, 
        raw_records: List[Dict[str, Any]], 
        processing_id: str
    ) -> Dict[str, Any]:
        """
        Process a batch of raw records through the complete pipeline.
        
        Args:
            raw_records: List of raw record dictionaries
            processing_id: Unique processing session ID
            
        Returns:
            Dict: Batch processing results
        """
        batch_results = {
            "total_records": len(raw_records),
            "processed_records": 0,
            "validated_records": 0,
            "stored_records": 0,
            "submitted_records": 0,
            "validation_errors": 0,
            "storage_errors": 0,
            "submission_errors": 0,
            "duplicate_records": 0,
            "errors": []
        }
        
        logger.info(
            "Starting batch processing",
            processing_id=processing_id,
            batch_size=len(raw_records)
        )
        
        # Process records in chunks for better performance
        chunk_size = settings.batch_size
        for i in range(0, len(raw_records), chunk_size):
            chunk = raw_records[i:i + chunk_size]
            
            logger.info(
                "Processing chunk",
                processing_id=processing_id,
                chunk_start=i,
                chunk_size=len(chunk)
            )
            
            # Process chunk concurrently
            chunk_tasks = [
                self._process_single_record(record, processing_id)
                for record in chunk
            ]
            
            chunk_results = await asyncio.gather(
                *chunk_tasks, 
                return_exceptions=True
            )
            
            # Aggregate chunk results
            for result in chunk_results:
                if isinstance(result, Exception):
                    batch_results["errors"].append(str(result))
                    continue
                
                batch_results["processed_records"] += 1
                
                if result["status"] == "validated":
                    batch_results["validated_records"] += 1
                elif result["status"] == "duplicate":
                    batch_results["duplicate_records"] += 1
                elif result["status"] == "validation_error":
                    batch_results["validation_errors"] += 1
                    batch_results["errors"].append(result.get("error", "Unknown validation error"))
                elif result["status"] == "stored":
                    batch_results["stored_records"] += 1
                elif result["status"] == "submitted":
                    batch_results["submitted_records"] += 1
                elif result["status"] == "storage_error":
                    batch_results["storage_errors"] += 1
                    batch_results["errors"].append(result.get("error", "Unknown storage error"))
                elif result["status"] == "submission_error":
                    batch_results["submission_errors"] += 1
                    batch_results["errors"].append(result.get("error", "Unknown submission error"))
        
        logger.info(
            "Batch processing completed",
            processing_id=processing_id,
            **batch_results
        )
        
        return batch_results
    
    async def _process_single_record(
        self, 
        raw_record: Dict[str, Any], 
        processing_id: str
    ) -> Dict[str, Any]:
        """
        Process a single TM2 record through the complete pipeline.
        
        Args:
            raw_record: Raw record dictionary
            processing_id: Processing session ID
            
        Returns:
            Dict: Processing result for the record
        """
        record_id = str(uuid4())
        
        try:
            # Step 1: Validate and transform raw data
            validated_record = await self._validate_and_transform_record(raw_record)
            if not validated_record:
                return {
                    "record_id": record_id,
                    "status": "validation_error",
                    "error": "Data validation failed"
                }
            
            # Step 2: Check for duplicates
            record_hash = self._generate_record_hash(validated_record)
            is_duplicate = await self.mongo_service.check_duplicate(record_hash)
            
            if is_duplicate:
                logger.info(
                    "Duplicate record detected, skipping",
                    record_id=record_id,
                    patient_id=validated_record.get("patient_id"),
                    record_hash=record_hash
                )
                return {
                    "record_id": record_id,
                    "status": "duplicate",
                    "record_hash": record_hash
                }
            
            # Step 3: Store in MongoDB
            try:
                stored_id = await self.mongo_service.insert_record({
                    **validated_record,
                    "record_hash": record_hash,
                    "processing_id": processing_id
                })
                
                logger.info(
                    "Record stored successfully",
                    record_id=record_id,
                    stored_id=stored_id,
                    patient_id=validated_record.get("patient_id")
                )
                
            except Exception as storage_error:
                logger.error(
                    "Failed to store record",
                    record_id=record_id,
                    error=str(storage_error)
                )
                return {
                    "record_id": record_id,
                    "status": "storage_error",
                    "error": str(storage_error)
                }
            
            # Step 4: Submit to OpenMRS
            try:
                submission_result = await self.openmrs_client.submit_tm2_record(validated_record)
                
                # Update record status in MongoDB
                await self.mongo_service.mark_as_submitted(stored_id, submission_result)
                
                logger.info(
                    "Record submitted successfully",
                    record_id=record_id,
                    stored_id=stored_id,
                    submission_id=submission_result.get("submission_id"),
                    patient_id=validated_record.get("patient_id")
                )
                
                return {
                    "record_id": record_id,
                    "status": "submitted",
                    "stored_id": stored_id,
                    "submission_id": submission_result.get("submission_id")
                }
                
            except Exception as submission_error:
                # Mark as failed in MongoDB
                await self.mongo_service.mark_as_failed(stored_id, str(submission_error))
                
                logger.error(
                    "Failed to submit record to OpenMRS",
                    record_id=record_id,
                    stored_id=stored_id,
                    error=str(submission_error)
                )
                
                return {
                    "record_id": record_id,
                    "status": "submission_error",
                    "stored_id": stored_id,
                    "error": str(submission_error)
                }
        
        except Exception as e:
            logger.error(
                "Unexpected error processing record",
                record_id=record_id,
                error=str(e),
                exc_info=True
            )
            return {
                "record_id": record_id,
                "status": "processing_error",
                "error": str(e)
            }
    
    async def _validate_and_transform_record(
        self, 
        raw_record: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate and transform a raw TM2 record.
        
        Args:
            raw_record: Raw record dictionary
            
        Returns:
            Optional[Dict]: Validated and transformed record, or None if invalid
        """
        try:
            # Create and validate raw record model
            raw_model = TM2RawRecord(**raw_record)
            
            # Transform to processed record
            processed_data = {
                "patient_id": raw_model.patient_id,
                "tm2_code": raw_model.tm2_code,
                "condition_name": raw_model.condition_name,
                "system_type": raw_model.system_type,
                "severity": raw_model.severity,
                "practitioner_id": raw_model.practitioner_id,
                "diagnosis_date": self._parse_date(raw_model.diagnosis_date),
                "created_at": datetime.utcnow(),
                "source_file": "uploaded_file"
            }
            
            # Validate processed record
            processed_model = TM2ProcessedRecord(**processed_data)
            
            logger.debug(
                "Record validated successfully",
                patient_id=processed_model.patient_id,
                tm2_code=processed_model.tm2_code
            )
            
            return processed_model.model_dump()
            
        except Exception as e:
            logger.warning(
                "Record validation failed",
                patient_id=raw_record.get("patient_id"),
                error=str(e)
            )
            return None
    
    def _parse_date(self, date_string: str) -> datetime:
        """
        Parse date string into datetime object.
        
        Args:
            date_string: Date string in various formats
            
        Returns:
            datetime: Parsed datetime object
        """
        try:
            return date_parser.parse(date_string)
        except Exception:
            # Return current date if parsing fails
            logger.warning(f"Failed to parse date: {date_string}, using current date")
            return datetime.utcnow()
    
    def _generate_record_hash(self, record: Dict[str, Any]) -> str:
        """
        Generate a normalized hash for duplicate detection.
        
        Args:
            record: Record dictionary
            
        Returns:
            str: SHA-256 hash of normalized record
        """
        # Create normalized string from key fields
        normalized_data = f"{record['patient_id']}|{record['tm2_code']}|{record['diagnosis_date']}"
        
        # Generate hash
        record_hash = hashlib.sha256(normalized_data.encode()).hexdigest()
        
        logger.debug(
            "Record hash generated",
            normalized_data=normalized_data,
            record_hash=record_hash[:16]  # Log first 16 characters
        )
        
        return record_hash
    
    def _update_processing_stats(self, batch_results: Dict[str, Any]) -> None:
        """
        Update global processing statistics.
        
        Args:
            batch_results: Batch processing results
        """
        self.processing_stats["files_processed"] += 1
        self.processing_stats["records_processed"] += batch_results["processed_records"]
        self.processing_stats["records_validated"] += batch_results["validated_records"]
        self.processing_stats["records_stored"] += batch_results["stored_records"]
        self.processing_stats["records_submitted"] += batch_results["submitted_records"]
        self.processing_stats["validation_errors"] += batch_results["validation_errors"]
        self.processing_stats["storage_errors"] += batch_results["storage_errors"]
        self.processing_stats["submission_errors"] += batch_results["submission_errors"]
        self.processing_stats["duplicate_records"] += batch_results["duplicate_records"]
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status and statistics.
        
        Returns:
            Dict: Current processing status
        """
        mongo_stats = await self.mongo_service.get_statistics()
        openmrs_stats = await self.openmrs_client.get_statistics()
        
        status = {
            "service_status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "processing_statistics": self.processing_stats,
            "mongodb_statistics": mongo_stats,
            "openmrs_statistics": openmrs_stats
        }
        
        return status