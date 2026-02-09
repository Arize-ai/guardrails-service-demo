from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class ChatRequestHeaders(BaseModel):
    space_id: Optional[str] = None
    project_id: Optional[str] = None

    class Config:
        extra = "allow"
        ignore_extra = True


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    anomaly_threshold: float = 0.8
    malicious_threshold: float = 0.1


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime
    anomaly_details: Dict[str, Any]
    malicious_details: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    version: str
