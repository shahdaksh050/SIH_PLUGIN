"""
Mock OpenMRS REST client for development and testing.

This module provides a mock implementation of the OpenMRS REST API client
that simulates HTTP requests and responses without making actual external calls.
"""

import asyncio
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()


class OpenMRSRestClient:
    """
    Mock OpenMRS REST API client.
    
    This class simulates HTTP requests to OpenMRS REST endpoints
    without making actual network calls. It provides realistic
    responses for testing and development purposes.
    """
    
    def __init__(self, base_url: str, username: str, password: str):
        """
        Initialize the OpenMRS REST client.
        
        Args:
            base_url: OpenMRS base URL
            username: API username
            password: API password
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self._session: Optional[httpx.AsyncClient] = None
        self._initialized = False
        self._auth_header = None
        
        # Mock data storage for simulating OpenMRS entities
        self._mock_patients = {}
        self._mock_concepts = {}
        self._mock_encounters = {}
        self._mock_observations = {}
        
        # Statistics
        self._stats = {
            "requests_made": 0,
            "successful_submissions": 0,
            "failed_submissions": 0,
            "patients_created": 0,
            "concepts_created": 0
        }
    
    async def initialize(self) -> None:
        """
        Initialize the OpenMRS client connection.
        
        This method sets up the HTTP client session and authenticates
        with the OpenMRS server (simulated for mock client).
        """
        try:
            logger.info(
                "Initializing OpenMRS REST client",
                base_url=self.base_url,
                username=self.username
            )
            
            # Create basic auth header
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self._auth_header = f"Basic {auth_b64}"
            
            # Simulate HTTP client creation (not actually making requests)
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "Authorization": self._auth_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            # Simulate connection test
            await asyncio.sleep(0.1)
            await self._mock_authentication_check()
            
            self._initialized = True
            
            logger.info("OpenMRS REST client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize OpenMRS client", error=str(e))
            raise
    
    async def _mock_authentication_check(self) -> bool:
        """
        Mock authentication check with OpenMRS server.
        
        Returns:
            bool: True if authentication successful
        """
        logger.info("Performing mock authentication check")
        
        # Simulate different authentication scenarios
        if self.username == "invalid_user":
            raise Exception("Authentication failed: Invalid credentials")
        
        if self.base_url.startswith("https://invalid-server"):
            raise Exception("Connection failed: Server unreachable")
        
        logger.info("Mock authentication successful")
        return True
    
    async def create_patient(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new patient in OpenMRS (mock implementation).
        
        Args:
            patient_data: Patient information dictionary
            
        Returns:
            Dict: Mock OpenMRS patient response
        """
        if not self._initialized:
            raise RuntimeError("OpenMRS client not initialized")
        
        # Generate mock patient ID
        patient_uuid = str(uuid4())
        
        # Create mock patient record
        mock_patient = {
            "uuid": patient_uuid,
            "display": f"{patient_data.get('givenName', 'Unknown')} {patient_data.get('familyName', 'Patient')}",
            "identifiers": [
                {
                    "uuid": str(uuid4()),
                    "identifier": patient_data.get("identifier", f"PAT{len(self._mock_patients) + 1:06d}"),
                    "identifierType": {
                        "uuid": str(uuid4()),
                        "display": "OpenMRS ID"
                    }
                }
            ],
            "person": {
                "uuid": patient_uuid,
                "gender": patient_data.get("gender", "U"),
                "birthdate": patient_data.get("birthdate"),
                "names": [
                    {
                        "uuid": str(uuid4()),
                        "givenName": patient_data.get("givenName"),
                        "familyName": patient_data.get("familyName")
                    }
                ]
            },
            "voided": False,
            "dateCreated": datetime.utcnow().isoformat(),
            "links": [
                {
                    "rel": "self",
                    "uri": f"{self.base_url}/ws/rest/v1/patient/{patient_uuid}"
                }
            ]
        }
        
        # Store in mock database
        self._mock_patients[patient_uuid] = mock_patient
        
        # Update statistics
        self._stats["requests_made"] += 1
        self._stats["patients_created"] += 1
        
        logger.info(
            "Mock patient created successfully",
            patient_uuid=patient_uuid,
            identifier=mock_patient["identifiers"][0]["identifier"],
            display_name=mock_patient["display"]
        )
        
        return mock_patient
    
    async def create_concept(self, concept_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new concept in OpenMRS (mock implementation).
        
        Args:
            concept_data: Concept information dictionary
            
        Returns:
            Dict: Mock OpenMRS concept response
        """
        if not self._initialized:
            raise RuntimeError("OpenMRS client not initialized")
        
        concept_uuid = str(uuid4())
        
        mock_concept = {
            "uuid": concept_uuid,
            "display": concept_data.get("display", "Unknown Concept"),
            "names": [
                {
                    "uuid": str(uuid4()),
                    "name": concept_data.get("name", "Unknown"),
                    "conceptNameType": "FULLY_SPECIFIED"
                }
            ],
            "descriptions": [
                {
                    "uuid": str(uuid4()),
                    "description": concept_data.get("description", "No description available")
                }
            ],
            "conceptClass": {
                "uuid": str(uuid4()),
                "display": concept_data.get("conceptClass", "Misc")
            },
            "datatype": {
                "uuid": str(uuid4()),
                "display": concept_data.get("datatype", "Text")
            },
            "retired": False,
            "dateCreated": datetime.utcnow().isoformat(),
            "links": [
                {
                    "rel": "self",
                    "uri": f"{self.base_url}/ws/rest/v1/concept/{concept_uuid}"
                }
            ]
        }
        
        self._mock_concepts[concept_uuid] = mock_concept
        
        self._stats["requests_made"] += 1
        self._stats["concepts_created"] += 1
        
        logger.info(
            "Mock concept created successfully",
            concept_uuid=concept_uuid,
            display_name=mock_concept["display"]
        )
        
        return mock_concept
    
    async def submit_observation(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit an observation to OpenMRS (mock implementation).
        
        Args:
            observation_data: Observation data dictionary
            
        Returns:
            Dict: Mock OpenMRS observation response
        """
        if not self._initialized:
            raise RuntimeError("OpenMRS client not initialized")
        
        observation_uuid = str(uuid4())
        
        # Simulate validation errors occasionally
        if observation_data.get("concept") is None:
            self._stats["requests_made"] += 1
            self._stats["failed_submissions"] += 1
            raise Exception("Concept is required for observation")
        
        mock_observation = {
            "uuid": observation_uuid,
            "display": f"Observation: {observation_data.get('concept', 'Unknown')}",
            "concept": {
                "uuid": observation_data.get("concept"),
                "display": observation_data.get("conceptName", "Unknown Concept")
            },
            "person": {
                "uuid": observation_data.get("person"),
                "display": observation_data.get("personName", "Unknown Patient")
            },
            "value": observation_data.get("value"),
            "obsDatetime": observation_data.get("obsDatetime", datetime.utcnow().isoformat()),
            "encounter": {
                "uuid": observation_data.get("encounter"),
                "display": "TM2 Data Ingestion Encounter"
            },
            "voided": False,
            "dateCreated": datetime.utcnow().isoformat(),
            "links": [
                {
                    "rel": "self",
                    "uri": f"{self.base_url}/ws/rest/v1/obs/{observation_uuid}"
                }
            ]
        }
        
        self._mock_observations[observation_uuid] = mock_observation
        
        self._stats["requests_made"] += 1
        self._stats["successful_submissions"] += 1
        
        logger.info(
            "Mock observation submitted successfully",
            observation_uuid=observation_uuid,
            concept=observation_data.get("concept"),
            patient=observation_data.get("person")
        )
        
        return mock_observation
    
    async def submit_tm2_record(self, tm2_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a complete TM2 record to OpenMRS (mock implementation).
        
        This method orchestrates the submission of patient data, concepts,
        and observations in the correct sequence.
        
        Args:
            tm2_record: Complete TM2 record data
            
        Returns:
            Dict: Submission result with all created entities
        """
        if not self._initialized:
            raise RuntimeError("OpenMRS client not initialized")
        
        logger.info(
            "Starting TM2 record submission",
            patient_id=tm2_record.get("patient_id"),
            tm2_code=tm2_record.get("tm2_code")
        )
        
        try:
            # Create or retrieve patient
            patient_data = {
                "identifier": tm2_record.get("patient_id"),
                "givenName": f"Patient",
                "familyName": tm2_record.get("patient_id", "Unknown"),
                "gender": "U"  # Unknown gender as default
            }
            patient_response = await self.create_patient(patient_data)
            
            # Create concept for TM2 code if needed
            concept_data = {
                "name": tm2_record.get("condition_name", "Unknown Condition"),
                "display": tm2_record.get("condition_name", "Unknown Condition"),
                "description": f"TM2 Code: {tm2_record.get('tm2_code')} - {tm2_record.get('system_type', 'Traditional Medicine')}",
                "conceptClass": "Diagnosis",
                "datatype": "Coded"
            }
            concept_response = await self.create_concept(concept_data)
            
            # Submit observation
            observation_data = {
                "concept": concept_response["uuid"],
                "conceptName": concept_response["display"],
                "person": patient_response["uuid"],
                "personName": patient_response["display"],
                "value": tm2_record.get("severity", "Unknown"),
                "obsDatetime": tm2_record.get("diagnosis_date", datetime.utcnow().isoformat()),
                "encounter": str(uuid4())  # Mock encounter
            }
            observation_response = await self.submit_observation(observation_data)
            
            # Compile submission result
            submission_result = {
                "success": True,
                "patient": patient_response,
                "concept": concept_response,
                "observation": observation_response,
                "submission_id": str(uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "tm2_code": tm2_record.get("tm2_code"),
                "patient_id": tm2_record.get("patient_id")
            }
            
            logger.info(
                "TM2 record submitted successfully",
                submission_id=submission_result["submission_id"],
                patient_uuid=patient_response["uuid"],
                concept_uuid=concept_response["uuid"],
                observation_uuid=observation_response["uuid"]
            )
            
            return submission_result
            
        except Exception as e:
            self._stats["failed_submissions"] += 1
            
            logger.error(
                "Failed to submit TM2 record",
                patient_id=tm2_record.get("patient_id"),
                tm2_code=tm2_record.get("tm2_code"),
                error=str(e)
            )
            
            raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get client statistics and metrics.
        
        Returns:
            Dict: Statistics including request counts and entity counts
        """
        stats = {
            **self._stats,
            "initialized": self._initialized,
            "base_url": self.base_url,
            "username": self.username,
            "mock_entities": {
                "patients": len(self._mock_patients),
                "concepts": len(self._mock_concepts),
                "observations": len(self._mock_observations)
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
        logger.debug("OpenMRS client statistics retrieved", **stats)
        
        return stats
    
    async def close(self) -> None:
        """
        Close the OpenMRS client connection and cleanup resources.
        """
        logger.info("Closing OpenMRS REST client")
        
        try:
            # Log final statistics
            final_stats = await self.get_statistics()
            logger.info("Final OpenMRS client statistics", **final_stats)
            
            # Close HTTP session if it exists
            if self._session:
                await self._session.aclose()
                self._session = None
            
            # Clear mock data
            self._mock_patients.clear()
            self._mock_concepts.clear()
            self._mock_encounters.clear()
            self._mock_observations.clear()
            
            self._initialized = False
            
            logger.info("OpenMRS REST client closed successfully")
            
        except Exception as e:
            logger.error("Error closing OpenMRS client", error=str(e))
            raise