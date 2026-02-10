from re import I
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from guardrails_service.models import (
    IncomingRequest,
    AnomalyDetectionResponse,
    AnomalyResult,
    BaselineUploadRequest,
    BaselineUploadResponse,
    BaselineClearRequest,
    BaselineClearResponse,
    BaselineGetResponse,
    TrafficRecord,
    MaliciousResult,
    MaliciousDetectionResponse,
)
from guardrails_service.vector_db import AnomalyVectorDatabase, MaliciousVectorDatabase
from guardrails_service.utils import DataLoader
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load datasets on startup"""
    logger.info("Starting up: Loading datasets from examples/data into Phoenix...")

    try:
        # Import here to avoid circular imports
        from dataset_manager import DatasetManager
        from constants import PHARMACY_ANOMALY_DATASET, PHARMACY_MALICIOUS_DATASET

        # Initialize dataset manager (we'll load directly to vector DBs, not via API)
        dataset_manager = DatasetManager()

        # Load or create anomaly dataset in Phoenix
        logger.info("Loading anomaly baseline dataset...")
        anomaly_exists = dataset_manager._check_dataset_exists(
            PHARMACY_ANOMALY_DATASET
        )

        if anomaly_exists:
            logger.info(f"Found existing dataset '{PHARMACY_ANOMALY_DATASET}' in Phoenix")
            anomaly_records = dataset_manager._load_dataset_from_phoenix(PHARMACY_ANOMALY_DATASET)
        else:
            logger.info(
                f"Creating new dataset '{PHARMACY_ANOMALY_DATASET}' from examples"
            )
            anomaly_records = dataset_manager._load_example_data("baseline.json")
            dataset_manager._create_phoenix_dataset(
                PHARMACY_ANOMALY_DATASET, anomaly_records
            )

        # Load directly into anomaly vector database
        logger.info(
            f"Loading {len(anomaly_records)} records into anomaly vector database..."
        )
        anomaly_count = anomaly_db.add_baseline_data(anomaly_records)
        logger.info(f"Loaded {anomaly_count} anomaly records into vector database")

        # Load or create malicious dataset in Phoenix
        logger.info("Loading malicious baseline dataset...")
        malicious_exists = dataset_manager._check_dataset_exists(
            PHARMACY_MALICIOUS_DATASET
        )

        if malicious_exists:
            logger.info(
                f"Found existing dataset '{PHARMACY_MALICIOUS_DATASET}' in Phoenix"
            )
            malicious_records = dataset_manager._load_dataset_from_phoenix(
                PHARMACY_MALICIOUS_DATASET
            )
        else:
            logger.info(
                f"Creating new dataset '{PHARMACY_MALICIOUS_DATASET}' from examples"
            )
            malicious_records = dataset_manager._load_example_data(
                "malicious_baseline.json"
            )
            dataset_manager._create_phoenix_dataset(
                PHARMACY_MALICIOUS_DATASET, malicious_records
            )

        # Load directly into malicious vector database
        logger.info(
            f"Loading {len(malicious_records)} records into malicious vector database..."
        )
        malicious_count = malicious_db.add_baseline_data(malicious_records)
        logger.info(f"Loaded {malicious_count} malicious records into vector database")

        logger.info(
            f"Startup complete: {anomaly_count} anomaly records, {malicious_count} malicious records loaded"
        )

    except Exception as e:
        logger.error(f"Failed to load datasets on startup: {e}")
        logger.exception(e)

    yield

    # Cleanup (if needed)
    logger.info("Shutting down...")


app = FastAPI(title="Guardrails Service", version="0.1.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anomaly_db = AnomalyVectorDatabase()
malicious_db = MaliciousVectorDatabase()
data_loader = DataLoader()


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Guardrails Anomaly Detection Service is running"}


@app.post("/anomaly/baseline/upload", response_model=BaselineUploadResponse)
async def upload_baseline_dataset(request: BaselineUploadRequest):
    """Upload a new baseline dataset via JSON payload"""
    try:
        # Convert the requests to the format expected by vector_db
        baseline_data = []
        for record in request.requests:
            baseline_data.append(
                {
                    "text": record.text,
                    "timestamp": (
                        record.timestamp.isoformat()
                        if record.timestamp
                        else datetime.now().isoformat()
                    ),
                }
            )

        # Add to vector database
        records_added = anomaly_db.add_baseline_data(baseline_data)

        return BaselineUploadResponse(
            message="Baseline dataset uploaded successfully",
            records_added=records_added,
            status="ready",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload baseline: {str(e)}"
        )


@app.post("/anomaly/baseline/add", response_model=BaselineUploadResponse)
async def add_to_baseline(request: TrafficRecord):
    """Add a new request to the baseline dataset"""
    try:
        # Convert the request to the format expected by vector_db
        baseline_data = {
            "text": request.text,
            "timestamp": request.timestamp.isoformat(),
        }

        # Add to vector database
        records_added = anomaly_db.add_entry(baseline_data)

        return BaselineUploadResponse(
            message="Request added to baseline successfully",
            records_added=records_added,
            status="ready",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add to baseline: {str(e)}"
        )


@app.get("/anomaly/baseline/stats")
async def get_baseline_stats():
    """Get statistics about the baseline dataset"""
    try:
        stats = anomaly_db.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/anomaly/baseline", response_model=BaselineGetResponse)
async def get_baseline_entries(
    before: Optional[datetime] = Query(
        None, description="Get entries before this date (exclusive)"
    ),
    after: Optional[datetime] = Query(
        None, description="Get entries after this date (inclusive)"
    ),
):
    """Get baseline dataset entries with optional date filtering"""
    try:
        entries_data = anomaly_db.get_baseline_entries(before=before, after=after)

        # Convert to TrafficRecord objects
        entries = [
            TrafficRecord(timestamp=entry["timestamp"], text=entry["text"])
            for entry in entries_data
        ]

        # Sort entries by timestamp
        entries.sort(key=lambda x: x.timestamp)

        return BaselineGetResponse(
            entries=entries,
            total_count=len(entries),
            filtered=before is not None or after is not None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get baseline entries: {str(e)}"
        )


@app.post("/anomaly/baseline/clear", response_model=BaselineClearResponse)
async def clear_baseline(request: BaselineClearRequest):
    """Clear baseline data with optional date filtering"""
    try:
        records_removed = anomaly_db.clear_baseline(
            before=request.before, after=request.after
        )

        if request.before is None and request.after is None:
            message = "All baseline data cleared successfully"
        elif request.before is not None and request.after is not None:
            message = f"Baseline data between {request.after.isoformat()} and {request.before.isoformat()} cleared successfully"
        elif request.before is not None:
            message = f"Baseline data before {request.before.isoformat()} cleared successfully"
        else:
            message = (
                f"Baseline data after {request.after.isoformat()} cleared successfully"
            )

        return BaselineClearResponse(
            message=message, records_removed=records_removed, status="success"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear baseline: {str(e)}"
        )


@app.post("/anomaly/detect", response_model=AnomalyDetectionResponse)
async def detect_anomaly(request: IncomingRequest):
    """Test an incoming request against the baseline to determine if it's an anomaly"""
    try:
        # Convert request to dict format expected by vector_db
        request_dict = {
            "text": request.text,
            "timestamp": (
                request.timestamp.isoformat()
                if request.timestamp
                else datetime.now().isoformat()
            ),
        }

        # Calculate anomaly score using vector similarity
        is_anomaly, anomaly_score, stats = anomaly_db.calculate_detection_score(
            request_dict,
            threshold=request.threshold,
            compare_to=request.compare_to,
        )

        # Determine risk level based on anomaly score
        if anomaly_score > 0.8:
            risk_level = "high"
        elif anomaly_score > 0.6:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate reasons based on analysis
        reasons = []
        if is_anomaly:
            if anomaly_score > 0.8:
                reasons.append(
                    "Request text significantly differs from baseline patterns"
                )
            elif stats.get("similar_records_count", 0) < 3:
                reasons.append("Very few similar requests found in baseline")
            else:
                reasons.append("Request appears unusual compared to baseline")

        result = AnomalyResult(
            is_anomaly=is_anomaly,
            confidence_score=anomaly_score,
            anomaly_reasons=reasons,
            risk_level=risk_level,
            similar_records_count=stats.get("similar_records_count", 0),
        )

        return AnomalyDetectionResponse(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            result=result,
            baseline_stats=stats,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Anomaly detection failed: {str(e)}"
        )


# Malicious Detection Endpoints


@app.post("/malicious/baseline/upload", response_model=BaselineUploadResponse)
async def upload_malicious_baseline_dataset(request: BaselineUploadRequest):
    """Upload a new malicious baseline dataset via JSON payload"""
    try:
        # Convert the requests to the format expected by malicious_db
        baseline_data = []
        for record in request.requests:
            baseline_data.append(
                {"text": record.text, "timestamp": record.timestamp.isoformat()}
            )

        # Add to malicious vector database
        records_added = malicious_db.add_baseline_data(baseline_data)

        return BaselineUploadResponse(
            message="Malicious baseline dataset uploaded successfully",
            records_added=records_added,
            status="ready",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to upload malicious baseline: {str(e)}"
        )


@app.post("/malicious/baseline/add", response_model=BaselineUploadResponse)
async def add_to_malicious_baseline(request: TrafficRecord):
    """Add a new request to the malicious baseline dataset"""
    try:
        # Convert the request to the format expected by malicious_db
        baseline_data = {
            "text": request.text,
            "timestamp": request.timestamp.isoformat(),
        }

        # Add to malicious vector database
        records_added = malicious_db.add_entry(baseline_data)

        return BaselineUploadResponse(
            message="Request added to malicious baseline successfully",
            records_added=records_added,
            status="ready",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add to malicious baseline: {str(e)}"
        )


@app.get("/malicious/baseline/stats")
async def get_malicious_baseline_stats():
    """Get statistics about the malicious baseline dataset"""
    try:
        stats = malicious_db.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get malicious stats: {str(e)}"
        )


@app.get("/malicious/baseline", response_model=BaselineGetResponse)
async def get_malicious_baseline_entries(
    before: Optional[datetime] = Query(
        None, description="Get entries before this date (exclusive)"
    ),
    after: Optional[datetime] = Query(
        None, description="Get entries after this date (inclusive)"
    ),
):
    """Get malicious baseline dataset entries with optional date filtering"""
    try:
        entries_data = malicious_db.get_baseline_entries(before=before, after=after)

        # Convert to TrafficRecord objects
        entries = [
            TrafficRecord(timestamp=entry["timestamp"], text=entry["text"])
            for entry in entries_data
        ]

        # Sort entries by timestamp
        entries.sort(key=lambda x: x.timestamp)

        return BaselineGetResponse(
            entries=entries,
            total_count=len(entries),
            filtered=before is not None or after is not None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get malicious baseline entries: {str(e)}",
        )


@app.post("/malicious/baseline/clear", response_model=BaselineClearResponse)
async def clear_malicious_baseline(request: BaselineClearRequest):
    """Clear malicious baseline data with optional date filtering"""
    try:
        records_removed = malicious_db.clear_baseline(
            before=request.before, after=request.after
        )

        if request.before is None and request.after is None:
            message = "All malicious baseline data cleared successfully"
        elif request.before is not None and request.after is not None:
            message = f"Malicious baseline data between {request.after.isoformat()} and {request.before.isoformat()} cleared successfully"
        elif request.before is not None:
            message = f"Malicious baseline data before {request.before.isoformat()} cleared successfully"
        else:
            message = f"Malicious baseline data after {request.after.isoformat()} cleared successfully"

        return BaselineClearResponse(
            message=message, records_removed=records_removed, status="success"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to clear malicious baseline: {str(e)}"
        )


@app.post("/malicious/detect", response_model=MaliciousDetectionResponse)
async def detect_malicious(request: IncomingRequest):
    """Test an incoming request against the malicious baseline to determine if it's malicious"""
    try:
        # Convert request to dict format expected by malicious_db
        request_dict = {
            "text": request.text,
            "timestamp": (
                request.timestamp.isoformat()
                if request.timestamp
                else datetime.now().isoformat()
            ),
        }

        # Calculate malicious score using vector similarity
        is_malicious, malicious_score, stats = malicious_db.calculate_detection_score(
            request_dict,
            threshold=request.threshold,
            compare_to=request.compare_to,
        )

        # Determine risk level based on malicious score
        if malicious_score > 0.8:
            risk_level = "high"
        elif malicious_score > 0.6:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate reasons based on analysis
        reasons = []
        if is_malicious:
            if malicious_score > 0.8:
                reasons.append("Request text closely matches known malicious patterns")
            elif stats.get("similar_records_count", 0) >= 3:
                reasons.append("Multiple similar malicious requests found in baseline")
            else:
                reasons.append("Request appears similar to known malicious content")

        result = MaliciousResult(
            is_malicious=is_malicious,  # Using same model structure
            confidence_score=max(malicious_score, 0.01),
            malicious_reasons=reasons,  # Will contain malicious reasons
            risk_level=risk_level,
            similar_records_count=stats.get("similar_records_count", 0),
        )

        return MaliciousDetectionResponse(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            result=result,
            baseline_stats=stats,
        )
    except Exception as e:
        import traceback

        error_detail = f"Malicious detection failed: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=500, detail=f"Malicious detection failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
