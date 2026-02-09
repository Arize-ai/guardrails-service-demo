from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from src.agent.models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from src.agent.chat_service import ChatService
import os

from arize.otel import register

# Configure the Arize tracer
# Reads ARIZE_SPACE_ID, ARIZE_API_KEY, and ARIZE_PROJECT_NAME from environment variables
tracer_provider = register(
    space_id=os.getenv("ARIZE_SPACE_ID"),
    api_key=os.getenv("ARIZE_API_KEY"),
    project_name=os.getenv("ARIZE_PROJECT_NAME", "Guardrails Project"),
)

chat_service = ChatService()
app = FastAPI(title="Guardrails Agent Service", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", version="0.1.0")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Extract headers if available
        response, anomaly_details, malicious_details = await chat_service.chat(
            message=request.message,
            anomaly_threshold=request.anomaly_threshold,
            malicious_threshold=request.malicious_threshold,
        )

        return ChatResponse(
            response=response,
            timestamp=datetime.now(),
            anomaly_details=anomaly_details,
            malicious_details=malicious_details,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
