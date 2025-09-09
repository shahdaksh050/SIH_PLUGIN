<<<<<<< HEAD
# TM2 Healthcare Data Ingestion Service

A production-ready FastAPI service for automating the ingestion of TM2 (Traditional Medicine Module 2) dataset files, processing and storing data in MongoDB Atlas, and submitting validated information to OpenMRS REST API endpoints.

## Project Overview

This service implements a robust, production-grade data pipeline that:
- Ingests TM2 dataset files (CSV format) containing traditional medicine codes
- Validates and transforms healthcare data according to ICD-11 TM2 standards
- Stores processed data securely in MongoDB Atlas (with in-memory mock for testing)
- Submits validated data to OpenMRS REST API endpoints (with mock client for testing)
- Provides comprehensive logging, error handling, and status monitoring

## Architecture

The application follows a layered architecture with clear separation of concerns:

```
├── app/
│   ├── core/           # Configuration, logging, lifespan management
│   ├── services/       # Business logic and external integrations
│   ├── models/         # Data models and API schemas
│   └── api/           # REST API endpoints
├── data/              # Sample data and mappings
├── requirements.txt   # Python dependencies
├── .env.example      # Environment template
└── main.py           # Application entry point
```

## Features

- **Production-Ready**: Structured logging, error handling, lifespan management
- **Security**: Environment-based configuration, no hardcoded secrets
- **Resilience**: Idempotent operations using normalized hash keys
- **Scalability**: Async/await patterns, efficient data processing
- **Healthcare Compliance**: TM2/ICD-11 compatible data validation
- **Testing**: Mock services for MongoDB and OpenMRS integration

## Setup Instructions

### 1. Environment Setup

Create a virtual environment and install dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your specific credentials:

```env
# MongoDB Atlas Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/tm2_healthcare?retryWrites=true&w=majority

# OpenMRS Configuration
OPENMRS_BASE_URL=https://your-openmrs-instance.org/openmrs
OPENMRS_USERNAME=your_openmrs_username
OPENMRS_PASSWORD=your_openmrs_password

# Application Configuration
ENVIRONMENT=development
```

### 3. Run the Application

Start the FastAPI development server:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at:
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### POST /ingest/trigger
Upload and process TM2 dataset files.

**Request**: Multipart form data with CSV file
**Response**: Processing status and summary

```bash
curl -X POST "http://localhost:8000/ingest/trigger" \
     -F "file=@data/tm2_sample.csv"
```

### GET /status
Get current ingestion pipeline status.

**Response**: System status and processing metrics

```bash
curl "http://localhost:8000/status"
```

## Data Format


| Column | Description | Example |
|--------|-------------|---------|
| `patient_id` | Unique patient identifier | PAT001 |
| `tm2_code` | Traditional medicine code | TM2.A01.01 |
| `condition_name` | Medical condition name | Chronic Insomnia |
| `system_type` | Medicine system | Ayurveda |
| `severity` | Condition severity | Moderate |
| `diagnosis_date` | Date of diagnosis | 2024-01-15 |
| `practitioner_id` | Healthcare provider ID | DOC001 |

### Sample Data

See `data/tm2_sample.csv` for example data format.

## Configuration

### Core Settings (app/core/config.py)

The application uses Pydantic Settings for configuration management:

```python
class Settings(BaseSettings):
    # Database
    mongodb_uri: str = "mongodb://localhost:27017/tm2_healthcare"
    
    # OpenMRS
    openmrs_base_url: str = "http://localhost:8080/openmrs"
    openmrs_username: str = "admin"
    openmrs_password: str = "Admin123"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
```

### Logging

Structured JSON logging with contextual fields:
- Request IDs for tracing
- User actions and system events
- Error details and stack traces
- Performance metrics

## Development

### Project Structure

```
tm2-healthcare-service/
├── main.py                 # FastAPI application entry point
├── README.md              # This documentation
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── app/
│   ├── core/
│   │   ├── config.py      # Pydantic settings
│   │   ├── logging.py     # Logging configuration
│   │   └── lifespan.py    # App lifecycle management
│   ├── services/
│   │   ├── mongo_service.py      # Mock MongoDB service
│   │   ├── openmrs_client.py     # Mock OpenMRS client
│   │   └── ingestion_service.py  # Data pipeline orchestration
│   ├── models/
│   │   ├── tm2_data.py           # TM2 data models
│   │   └── api_models.py         # API request/response models
│   └── api/
│       └── endpoints.py          # REST API routes
└── data/
    ├── tm2_sample.csv           # Sample TM2 dataset
    └── tm2_mappings.json        # Code mappings
```

### Testing

Run the application with sample data:

1. Start the service: `uvicorn main:app --reload`
2. Upload sample data via API docs at http://localhost:8000/docs
3. Check processing status at `/status` endpoint
4. Review logs for detailed processing information

### Mock Services

For development and testing, the application includes:

**Mock MongoDB Service**: In-memory dictionary-based storage
- Simulates MongoDB operations (insert, find, update)
- Maintains data consistency during application lifecycle
- Provides status reporting and metrics

**Mock OpenMRS Client**: HTTP client simulator
- Logs intended API calls without external requests
- Returns realistic HTTP responses for testing
- Supports authentication and error simulation

## Production Deployment

### Required Credentials

For production deployment, provide these environment variables:

1. **MONGODB_URI**: Your MongoDB Atlas connection string
2. **OPENMRS_BASE_URL**: Your OpenMRS instance URL
3. **OPENMRS_USERNAME**: OpenMRS API username
4. **OPENMRS_PASSWORD**: OpenMRS API password

### Deployment Considerations

- Use proper secret management (AWS Secrets Manager, Azure Key Vault)
- Enable SSL/TLS for database and API connections
- Implement proper monitoring and alerting
- Set up log aggregation and analysis
- Configure backup and disaster recovery

## Troubleshooting

### Common Issues

**Connection Errors**: Verify environment variables and network connectivity
**Import Errors**: Ensure all dependencies are installed via requirements.txt
**Data Validation**: Check CSV format matches expected TM2 structure
**Performance**: Monitor memory usage with large datasets

### Support

For technical support:
1. Check application logs for error details
2. Verify environment configuration
3. Test with sample data first
4. Review API documentation at `/docs`

## License

This project is designed for healthcare data processing and should comply with relevant healthcare regulations (HIPAA, GDPR) in your jurisdiction.
=======
