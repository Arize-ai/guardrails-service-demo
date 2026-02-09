from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrafficRecord(BaseModel):
    timestamp: Optional[datetime] = Field(
        datetime.now(), description="Request timestamp"
    )
    text: str = Field(..., description="Text content of the request")


class BaselineDataset(BaseModel):
    records: List[TrafficRecord]
    start_date: datetime
    end_date: datetime
    total_records: int = Field(..., description="Total number of records")

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days


class IncomingRequest(BaseModel):
    text: str = Field(..., description="Text content of the request")
    timestamp: Optional[datetime] = Field(
        datetime.now(), description="Request timestamp"
    )
    threshold: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Threshold for anomaly detection (0-1)"
    )
    compare_to: Optional[int] = Field(
        None, ge=1, description="Number of nearest vectors to compare"
    )


class AnomalyResult(BaseModel):
    is_anomaly: bool
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    anomaly_reasons: List[str] = Field(
        default=[], description="Reasons why flagged as anomaly"
    )
    risk_level: str = Field(..., description="Risk level: low, medium, high")
    similar_records_count: int = Field(
        ..., ge=0, description="Number of similar records in baseline"
    )


class MaliciousResult(BaseModel):
    is_malicious: bool
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    malicious_reasons: List[str] = Field(
        default=[], description="Reasons why flagged as malicious"
    )
    risk_level: str = Field(..., description="Risk level: low, medium, high")
    similar_records_count: int = Field(
        ..., ge=0, description="Number of similar records in baseline"
    )


class BaselineUploadRequest(BaseModel):
    requests: List[TrafficRecord] = Field(
        ..., description="List of baseline requests with timestamps"
    )


class BaselineUploadResponse(BaseModel):
    message: str
    records_added: int
    status: str


class BaselineClearRequest(BaseModel):
    before: Optional[datetime] = Field(
        None, description="Remove entries before this date (exclusive)"
    )
    after: Optional[datetime] = Field(
        None, description="Remove entries after this date (inclusive)"
    )


class BaselineClearResponse(BaseModel):
    message: str
    records_removed: int
    status: str


class BaselineGetRequest(BaseModel):
    before: Optional[datetime] = Field(
        None, description="Get entries before this date (exclusive)"
    )
    after: Optional[datetime] = Field(
        None, description="Get entries after this date (inclusive)"
    )


class BaselineGetResponse(BaseModel):
    entries: List[TrafficRecord] = Field(description="List of baseline entries")
    total_count: int = Field(description="Total number of entries returned")
    filtered: bool = Field(description="Whether date filtering was applied")


class AnomalyDetectionResponse(BaseModel):
    request_id: str
    timestamp: datetime
    result: AnomalyResult
    baseline_stats: Dict[str, Any] = Field(
        default={}, description="Baseline statistics used"
    )


class MaliciousDetectionResponse(BaseModel):
    request_id: str
    timestamp: datetime
    result: MaliciousResult
    baseline_stats: Dict[str, Any] = Field(
        default={}, description="Baseline statistics used"
    )
