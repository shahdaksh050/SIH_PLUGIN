#!/usr/bin/env python3
"""
Test script to verify CSV reading fixes for the TM2 ingestion service.
This script tests the file pointer reset and encoding handling improvements.
"""

import asyncio
import io
from pathlib import Path

# Add the app directory to the path so we can import modules
import sys
sys.path.append('.')

from app.services.ingestion_service import TM2IngestionService
from app.services.mongo_service import MongoService
from app.services.openmrs_client import OpenMRSRestClient


class MockMongoService(MongoService):
    """Mock MongoDB service for testing."""

    def __init__(self):
        self.records = []
        self.connection_status = "connected"

    async def insert_record(self, record):
        self.records.append(record)
        return f"mock_id_{len(self.records)}"

    async def check_duplicate(self, record_hash):
        return False

    async def mark_as_submitted(self, record_id, submission_result):
        pass

    async def mark_as_failed(self, record_id, error):
        pass

    async def get_statistics(self):
        return {
            "connection_status": self.connection_status,
            "total_records": len(self.records),
            "submitted_records": len(self.records),
            "failed_records": 0,
            "pending_records": 0,
            "collection_size": len(self.records),
            "last_updated": "2023-01-01T00:00:00Z"
        }


class MockOpenMRSClient(OpenMRSRestClient):
    """Mock OpenMRS client for testing."""

    def __init__(self):
        self.initialized = True
        self.requests_made = 0
        self.successful_submissions = 0

    async def submit_tm2_record(self, record):
        self.requests_made += 1
        self.successful_submissions += 1
        return {
            "submission_id": f"mock_submission_{self.requests_made}",
            "status": "success"
        }

    async def get_statistics(self):
        return {
            "initialized": self.initialized,
            "base_url": "https://mock-openmrs.org",
            "username": "mock_user",
            "requests_made": self.requests_made,
            "successful_submissions": self.successful_submissions,
            "failed_submissions": 0,
            "patients_created": self.successful_submissions,
            "concepts_created": self.successful_submissions,
            "last_updated": "2023-01-01T00:00:00Z"
        }


async def test_csv_reading():
    """Test the CSV reading functionality with various scenarios."""

    print("🧪 Testing CSV reading fixes...")

    # Initialize mock services
    mongo_service = MockMongoService()
    openmrs_client = MockOpenMRSClient()
    ingestion_service = TM2IngestionService(mongo_service, openmrs_client)

    # Test data directory
    data_dir = Path("data")

    # Test 1: Normal CSV file
    print("\n📄 Test 1: Reading normal CSV file")
    csv_file_path = data_dir / "sample_tm2_dataset.csv"

    if csv_file_path.exists():
        with open(csv_file_path, 'rb') as f:
            file_content = io.BytesIO(f.read())

        # Simulate what happens in FastAPI (file already read once)
        file_content.read()  # This moves the pointer to the end

        try:
            records = await ingestion_service._read_csv_file(file_content)
            print(f"✅ Successfully read {len(records)} records")
            print(f"   First record: {records[0] if records else 'None'}")
        except Exception as e:
            print(f"❌ Failed to read CSV: {e}")
    else:
        print("⚠️  Sample CSV file not found")

    # Test 2: Empty file
    print("\n📄 Test 2: Reading empty file")
    empty_file = io.BytesIO(b"")
    try:
        records = await ingestion_service._read_csv_file(empty_file)
        print("❌ Should have failed for empty file")
    except ValueError as e:
        print(f"✅ Correctly rejected empty file: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for empty file: {e}")

    # Test 3: File with headers but no data
    print("\n📄 Test 3: Reading file with headers but no data")
    headers_only = io.BytesIO(b"patient_id,tm2_code,condition_name,system_type,severity,diagnosis_date,practitioner_id\n")
    try:
        records = await ingestion_service._read_csv_file(headers_only)
        print("❌ Should have failed for headers-only file")
    except ValueError as e:
        print(f"✅ Correctly rejected headers-only file: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for headers-only file: {e}")

    # Test 4: File with wrong encoding (simulate)
    print("\n📄 Test 4: Testing encoding fallback")
    # Create a file with UTF-8 BOM to test encoding detection
    utf8_bom_content = b'\xef\xbb\xbfpatient_id,tm2_code,condition_name,system_type,severity,diagnosis_date,practitioner_id\nP001,TM2.A01.01,Test,Ayurveda,Mild,2023-01-01,PRAC001\n'
    bom_file = io.BytesIO(utf8_bom_content)
    try:
        records = await ingestion_service._read_csv_file(bom_file)
        print(f"✅ Successfully handled UTF-8 BOM encoding, read {len(records)} records")
    except Exception as e:
        print(f"❌ Failed to handle UTF-8 BOM: {e}")

    print("\n🎉 CSV reading tests completed!")


if __name__ == "__main__":
    asyncio.run(test_csv_reading())
