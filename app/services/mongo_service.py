"""
Mock MongoDB service for development and testing.

This module provides an in-memory implementation of MongoDB operations
that simulates the behavior of a real MongoDB database for testing
and development purposes.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class MongoService:
    """
    Mock MongoDB service using in-memory dictionary storage.
    
    This class simulates MongoDB operations for development and testing
    without requiring an actual MongoDB connection. It maintains data
    consistency during the application lifecycle and provides realistic
    MongoDB-like behavior.
    """
    
    def __init__(self):
        """Initialize the mock MongoDB service."""
        self._data: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._connection_status = "disconnected"
        
        # Statistics tracking
        self._stats = {
            "total_records": 0,
            "submitted_records": 0,
            "failed_records": 0,
            "pending_records": 0
        }
    
    async def initialize(self) -> None:
        """
        Initialize the mock MongoDB connection.
        
        This method simulates the connection establishment to MongoDB
        and sets up the required collections and indexes.
        """
        try:
            logger.info("Establishing mock MongoDB connection")
            
            # Simulate connection delay
            await asyncio.sleep(0.1)
            
            # Initialize mock database structure
            self._data = {
                settings.collection_name: {},
                "metadata": {},
                "processing_status": {}
            }
            
            self._connection_status = "connected"
            self._initialized = True
            
            logger.info(
                "Mock MongoDB service initialized successfully",
                database_name=settings.database_name,
                collection_name=settings.collection_name,
                connection_status=self._connection_status
            )
            
        except Exception as e:
            logger.error("Failed to initialize MongoDB service", error=str(e))
            self._connection_status = "error"
            raise
    
    async def insert_record(self, record: Dict[str, Any]) -> str:
        """
        Insert a new record into the mock database.
        
        Args:
            record: Dictionary containing the record data
            
        Returns:
            str: Unique record ID
            
        Raises:
            RuntimeError: If service is not initialized
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        # Generate unique record ID
        record_id = str(uuid4())
        
        # Add metadata
        enhanced_record = {
            **record,
            "_id": record_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "pending",
            "submission_attempts": 0,
            "submitted_to_openmrs": False
        }
        
        # Store in mock database
        self._data[settings.collection_name][record_id] = enhanced_record
        
        # Update statistics
        self._stats["total_records"] += 1
        self._stats["pending_records"] += 1
        
        logger.info(
            "Record inserted successfully",
            record_id=record_id,
            patient_id=record.get("patient_id"),
            tm2_code=record.get("tm2_code")
        )
        
        return record_id
    
    async def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a record by ID from the mock database.
        
        Args:
            record_id: Unique record identifier
            
        Returns:
            Optional[Dict]: Record data if found, None otherwise
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        record = self._data[settings.collection_name].get(record_id)
        
        if record:
            logger.debug("Record retrieved successfully", record_id=record_id)
        else:
            logger.warning("Record not found", record_id=record_id)
        
        return record
    
    async def update_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing record in the mock database.
        
        Args:
            record_id: Unique record identifier
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if record was updated, False if not found
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        if record_id not in self._data[settings.collection_name]:
            logger.warning("Cannot update record - not found", record_id=record_id)
            return False
        
        # Apply updates
        record = self._data[settings.collection_name][record_id]
        record.update(updates)
        record["updated_at"] = datetime.utcnow()
        
        logger.info(
            "Record updated successfully",
            record_id=record_id,
            updated_fields=list(updates.keys())
        )
        
        return True
    
    async def mark_as_submitted(self, record_id: str, submission_result: Dict[str, Any]) -> bool:
        """
        Mark a record as successfully submitted to OpenMRS.
        
        Args:
            record_id: Unique record identifier
            submission_result: Result data from OpenMRS submission
            
        Returns:
            bool: True if record was updated, False if not found
        """
        updates = {
            "status": "submitted",
            "submitted_to_openmrs": True,
            "openmrs_submission_result": submission_result,
            "submission_timestamp": datetime.utcnow()
        }
        
        success = await self.update_record(record_id, updates)
        
        if success:
            # Update statistics
            self._stats["submitted_records"] += 1
            self._stats["pending_records"] -= 1
            
            logger.info(
                "Record marked as submitted",
                record_id=record_id,
                openmrs_id=submission_result.get("id")
            )
        
        return success
    
    async def mark_as_failed(self, record_id: str, error_message: str) -> bool:
        """
        Mark a record as failed during processing.
        
        Args:
            record_id: Unique record identifier
            error_message: Error description
            
        Returns:
            bool: True if record was updated, False if not found
        """
        updates = {
            "status": "failed",
            "error_message": error_message,
            "failure_timestamp": datetime.utcnow()
        }
        
        success = await self.update_record(record_id, updates)
        
        if success:
            # Update statistics
            self._stats["failed_records"] += 1
            self._stats["pending_records"] -= 1
            
            logger.warning(
                "Record marked as failed",
                record_id=record_id,
                error_message=error_message
            )
        
        return success
    
    async def get_pending_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve pending records for processing.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List[Dict]: List of pending records
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        pending_records = [
            record for record in self._data[settings.collection_name].values()
            if record.get("status") == "pending"
        ]
        
        # Sort by creation date and limit results
        pending_records.sort(key=lambda x: x["created_at"])
        limited_records = pending_records[:limit]
        
        logger.info(
            "Retrieved pending records",
            total_pending=len(pending_records),
            returned_count=len(limited_records)
        )
        
        return limited_records
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics and metrics.
        
        Returns:
            Dict: Statistics including record counts and status
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        # Recalculate statistics to ensure accuracy
        collection = self._data[settings.collection_name]
        
        status_counts = {}
        for record in collection.values():
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        stats = {
            **self._stats,
            "connection_status": self._connection_status,
            "collection_size": len(collection),
            "status_breakdown": status_counts,
            "last_updated": datetime.utcnow()
        }
        
        logger.debug("Database statistics retrieved", **stats)
        
        return stats
    
    async def check_duplicate(self, record_hash: str) -> bool:
        """
        Check if a record with the given hash already exists.
        
        Args:
            record_hash: Normalized hash of the record
            
        Returns:
            bool: True if duplicate exists, False otherwise
        """
        if not self._initialized:
            raise RuntimeError("MongoDB service not initialized")
        
        collection = self._data[settings.collection_name]
        
        for record in collection.values():
            if record.get("record_hash") == record_hash:
                logger.info(
                    "Duplicate record detected",
                    record_hash=record_hash,
                    existing_id=record["_id"]
                )
                return True
        
        return False
    
    async def close(self) -> None:
        """
        Close the mock MongoDB connection and cleanup resources.
        
        This method simulates the connection cleanup process and
        clears the in-memory data storage.
        """
        logger.info("Closing mock MongoDB connection")
        
        try:
            # Log final statistics
            final_stats = await self.get_statistics()
            logger.info("Final database statistics", **final_stats)
            
            # Clear data
            self._data.clear()
            self._initialized = False
            self._connection_status = "disconnected"
            
            # Reset statistics
            self._stats = {
                "total_records": 0,
                "submitted_records": 0,
                "failed_records": 0,
                "pending_records": 0
            }
            
            logger.info("Mock MongoDB connection closed successfully")
            
        except Exception as e:
            logger.error("Error closing MongoDB connection", error=str(e))
            raise