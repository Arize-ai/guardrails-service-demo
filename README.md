# Guardrails Service

A comprehensive AI safety platform that combines anomaly detection, malicious content filtering, and an intelligent chat agent with real-time guardrails. The platform uses vector similarity analysis to detect unusual requests and malicious patterns, with Phoenix integration for observability and dataset management.

## Architecture Overview

The platform consists of four integrated services:

1. **Guardrails Service** (Port 8000): Core detection engine with dual anomaly and malicious content detection
2. **Chat Agent Service** (Port 8001): LangGraph-powered chat agent with automatic guardrails checking
3. **UI Service** (Port 5000): Interactive web interface for chatting and dataset management
4. **Phoenix Dashboard** (Port 6006): Observability and tracing with Arize Phoenix

## Features

### Core Detection System
- **Dual Detection System**: Both anomaly detection and malicious content detection
- **Anomaly Detection**: Identifies unusual requests that differ from normal traffic patterns
- **Malicious Detection**: Identifies requests similar to known malicious patterns
- **Baseline Dataset Management**: Upload, add, retrieve, and clear baseline datasets with date filtering
- **Vector Database**: ChromaDB-powered storage with semantic embeddings using separate collections
- **Smart Detection Logic**: Uses median distance for anomaly detection, minimum distance for malicious detection

### AI Chat Agent
- **LangGraph-Powered Agent**: Intelligent chat agent with built-in guardrails workflow
- **Real-time Safety Checks**: Automatically screens all user inputs through both detection systems
- **Contextual Responses**: GPT-4o powered responses that adapt based on guardrail results
- **Blocked Request Handling**: Gracefully handles and explains blocked malicious or anomalous requests

### Observability & Management
- **Phoenix Integration**: Full observability with Arize Phoenix for tracing and monitoring
- **Dataset Synchronization**: Automatic sync between Phoenix datasets and vector store
- **Interactive UI**: Web-based interface for chatting with agent and managing datasets
- **Dynamic Dataset Updates**: Add new examples to baseline datasets in real-time from the UI

### Infrastructure
- **RESTful APIs**: Three FastAPI/Flask services working in concert
- **Docker Support**: Full containerized deployment with docker-compose
- **CORS Support**: Ready for cross-origin frontend integration

## Quick Start

### Prerequisites

- Python 3.11
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (optional, for containerized deployment)

### Local Development Setup

1. **Clone and setup environment**:
   ```bash
   ./bin/bootstrap.sh
   ```

2. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

3. **Run the service**:
   ```bash
   uv run uvicorn guardrails_service.server:app --reload
   ```

The service will be available at `http://localhost:8000`

### Docker Deployment

1. **Create a `.env` file from the example**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Build and run with docker-compose**:
   ```bash
   docker-compose up --build
   ```

   This will start all services:
   - **UI Service**: http://localhost:5000
   - **Phoenix Dashboard**: http://localhost:6006
   - **Agent API**: http://localhost:8001
   - **Guardrails API**: http://localhost:8000

3. **Production Docker build**:
   ```bash
   docker build -t guardrails-service .
   docker run -p 8000:8000 guardrails-service
   ```

## API Endpoints

The service provides two complete sets of endpoints for different detection types:

### Health Check

- **GET** `/health` - Service health status
- **GET** `/` - Root endpoint

## Anomaly Detection Endpoints

The anomaly detection system identifies requests that are **dissimilar** to normal traffic patterns.

### Anomaly Baseline Dataset Management

#### Upload Baseline Dataset
- **POST** `/anomaly/baseline/upload`
- Upload multiple requests to establish baseline patterns
- **Request Body**:
  ```json
  {
    "requests": [
      {
        "timestamp": "2025-08-12T10:00:00",
        "text": "The first of many normal requests"
      },
      ...
    ]
  }
  ```

#### Add Single Entry to Baseline
- **POST** `/anomaly/baseline/add`
- Add a single request to the baseline dataset
- **Request Body**:
  ```json
  {
    "timestamp": "2025-08-12T10:00:00",
    "text": "A new request to add to the baseline"
  }
  ```

#### Retrieve Baseline Entries
- **GET** `/anomaly/baseline`
- Retrieve baseline entries with optional date filtering
- **Query Parameters**:
  - `before` (optional): Get entries before this date (exclusive)
  - `after` (optional): Get entries after this date (inclusive)
- **Examples**:
  ```bash
  # Get all entries
  GET /anomaly/baseline
  
  # Get entries before August 1st
  GET /anomaly/baseline?before=2025-08-01T00:00:00
  
  # Get entries after July 31st
  GET /anomaly/baseline?after=2025-07-31T00:00:00
  
  # Get entries between dates
  GET /anomaly/baseline?after=2025-07-10T00:00:00&before=2025-08-05T00:00:00
  ```

#### Clear Baseline Data
- **POST** `/anomaly/baseline/clear`
- Remove baseline entries with optional date filtering
- **Request Body**:
  ```json
  {
    "before": "2025-08-01T00:00:00",  // optional
    "after": "2025-07-01T00:00:00"   // optional
  }
  ```
- **Filtering Logic**:
  - No dates: Remove all entries
  - `before` only: Remove entries before date (exclusive)
  - `after` only: Remove entries after date (inclusive)
  - Both dates: Remove entries between dates (after inclusive, before exclusive)

#### Baseline Statistics
- **GET** `/anomaly/baseline/stats`
- Get statistics about the baseline dataset
- **Response**:
  ```json
  {
    "total_records": 150,
    "collection_name": "traffic_baseline"
  }
  ```

### Anomaly Detection

#### Detect Anomaly
- **POST** `/anomaly/detect`
- Analyze incoming request against baseline patterns
- **Request Body**:
  ```json
  {
    "text": "Request text to analyze",
    "timestamp": "2025-08-12T10:00:00",  // optional
    "threshold": 0.7,                   // optional, defaults to env ANOMALY_THRESHOLD (0.7)
    "compare_to": 10                    // optional, defaults to env COMPARE_TO (10)
  }
  ```
- **Parameters**:
  - `threshold`: Similarity threshold for anomaly detection (0.0-1.0). Lower values are more sensitive.
  - `compare_to`: Number of similar baseline vectors to compare against (minimum 1).
- **Response**:
  ```json
  {
    "request_id": "uuid-string",
    "timestamp": "2025-08-12T10:00:00",
    "result": {
      "is_anomaly": false,
      "confidence_score": 0.65,
      "anomaly_reasons": [],
      "risk_level": "low",
      "similar_records_count": 8
    },
    "baseline_stats": {
      "median_distance": 0.65,
      "mean_distance": 0.62,
      "min_distance": 0.45,
      "max_distance": 0.85,
      "threshold": 0.7,
      "similar_records_count": 8
    }
  }
  ```

## Malicious Detection Endpoints

The malicious detection system identifies requests that are **similar** to known malicious patterns.

### Malicious Baseline Dataset Management

#### Upload Malicious Baseline Dataset
- **POST** `/malicious/baseline/upload`
- Upload multiple malicious requests to establish malicious patterns
- **Request Body**:
  ```json
  {
    "requests": [
      {
        "timestamp": "2025-08-12T10:00:00",
        "text": "'; DROP TABLE users; --"
      },
      ...
    ]
  }
  ```

#### Add Single Entry to Malicious Baseline
- **POST** `/malicious/baseline/add`
- Add a single malicious request to the baseline dataset
- **Request Body**:
  ```json
  {
    "timestamp": "2025-08-12T10:00:00",
    "text": "<script>alert('XSS attack')</script>"
  }
  ```

#### Retrieve Malicious Baseline Entries
- **GET** `/malicious/baseline`
- Retrieve malicious baseline entries with optional date filtering
- **Query Parameters**:
  - `before` (optional): Get entries before this date (exclusive)
  - `after` (optional): Get entries after this date (inclusive)
- **Examples**:
  ```bash
  # Get all malicious entries
  GET /malicious/baseline
  
  # Get entries before August 1st
  GET /malicious/baseline?before=2025-08-01T00:00:00
  
  # Get entries after July 31st
  GET /malicious/baseline?after=2025-07-31T00:00:00
  
  # Get entries between dates
  GET /malicious/baseline?after=2025-07-10T00:00:00&before=2025-08-05T00:00:00
  ```

#### Clear Malicious Baseline Data
- **POST** `/malicious/baseline/clear`
- Remove malicious baseline entries with optional date filtering
- **Request Body**:
  ```json
  {
    "before": "2025-08-01T00:00:00",  // optional
    "after": "2025-07-01T00:00:00"   // optional
  }
  ```
- **Filtering Logic**:
  - No dates: Remove all entries
  - `before` only: Remove entries before date (exclusive)
  - `after` only: Remove entries after date (inclusive)
  - Both dates: Remove entries between dates (after inclusive, before exclusive)

#### Malicious Baseline Statistics
- **GET** `/malicious/baseline/stats`
- Get statistics about the malicious baseline dataset
- **Response**:
  ```json
  {
    "total_records": 50,
    "collection_name": "malicious_baseline"
  }
  ```

### Malicious Detection

#### Detect Malicious Content
- **POST** `/malicious/detect`
- Analyze incoming request against malicious patterns
- **Request Body**:
  ```json
  {
    "text": "Request text to analyze",
    "timestamp": "2025-08-12T10:00:00",  // optional
    "threshold": 0.25,                  // optional, defaults to env MALICIOUS_THRESHOLD (0.25)
    "compare_to": 10                    // optional, defaults to env MALICIOUS_COMPARE_TO (10)
  }
  ```
- **Parameters**:
  - `threshold`: Similarity threshold for malicious detection (0.0-1.0). Lower values are more sensitive.
  - `compare_to`: Number of similar malicious vectors to compare against (minimum 1).
- **Response**:
  ```json
  {
    "request_id": "uuid-string",
    "timestamp": "2025-08-12T10:00:00",
    "result": {
      "is_malicious": true,
      "confidence_score": 0.85,
      "malicious_reasons": ["Request text closely matches known malicious patterns"],
      "risk_level": "high",
      "similar_records_count": 3
    },
    "baseline_stats": {
      "median_distance": 0.15,
      "mean_distance": 0.18,
      "min_distance": 0.05,
      "max_distance": 0.35,
      "threshold": 0.25,
      "similar_records_count": 3,
      "detection_distance": 0.05,
      "detection_metric": "min_distance"
    }
  }
  ```

## Detection Logic Comparison

| Aspect | Anomaly Detection | Malicious Detection |
|--------|------------------|-------------------|
| **Purpose** | Find unusual requests | Find known attack patterns |
| **Logic** | High dissimilarity = anomaly | High similarity = malicious |
| **Metric Used** | Median distance (robust) | Minimum distance (sensitive) |
| **Threshold Logic** | `median_distance > threshold` | `min_distance < threshold` |
| **Default Threshold** | 0.7 | 0.25 |
| **When No Data** | Assume anomaly | Assume benign |
| **Use Case** | Novel/unknown threats | Known attack variations |

## Chat Agent API

The Chat Agent Service provides an intelligent conversational interface with built-in guardrails.

### Chat Endpoint

- **POST** `/chat` - Send a message to the chat agent with guardrails
- **Request Body**:
  ```json
  {
    "message": "What medications do you have available?",
    "anomaly_threshold": 0.7,      // optional, defaults to env variable
    "malicious_threshold": 0.25    // optional, defaults to env variable
  }
  ```
- **Response**:
  ```json
  {
    "response": "I can help you with information about our medications...",
    "timestamp": "2025-10-16T10:00:00",
    "anomaly_details": {
      "is_anomaly": false,
      "confidence_score": 0.65,
      "risk_level": "low",
      "baseline_stats": { ... }
    },
    "malicious_details": {
      "is_malicious": false,
      "confidence_score": 0.05,
      "risk_level": "low",
      "baseline_stats": { ... }
    }
  }
  ```

### Health Check
- **GET** `/health` - Chat agent service health status

## UI Service API

The UI Service provides dataset management capabilities via Phoenix integration.

### Dataset Management Endpoints

#### Get Dataset Information
- **GET** `/datasets/info` - Get information about Phoenix datasets
- **Response**:
  ```json
  {
    "pharmacy-anomaly-baseline": {
      "exists": true,
      "name": "pharmacy-anomaly-baseline",
      "created_at": "2025-10-15T10:00:00"
    },
    "pharmacy-malicious-baseline": {
      "exists": true,
      "name": "pharmacy-malicious-baseline",
      "created_at": "2025-10-15T10:00:00"
    }
  }
  ```

#### Sync Datasets
- **POST** `/datasets/sync` - Manually sync Phoenix datasets to vector store
- **Response**:
  ```json
  {
    "status": "success",
    "results": {
      "anomaly": "Loaded from Phoenix (100 records)",
      "malicious": "Loaded from Phoenix (50 records)"
    }
  }
  ```

#### Add to Dataset
- **POST** `/datasets/add` - Add an entry to a Phoenix dataset
- **Request Body**:
  ```json
  {
    "dataset_type": "anomaly",  // or "malicious"
    "text": "What are your hours?",
    "timestamp": "2025-10-16T10:00:00"
  }
  ```

### Web Interface

Access the interactive UI at `http://localhost:5000` to:
- Chat with the AI agent with real-time guardrails
- View detection scores for anomaly and malicious content
- Add examples to datasets directly from the conversation
- Sync Phoenix datasets with the vector store
- Monitor guardrail effectiveness in real-time

## How It Works

### LangGraph Guardrails Workflow

The Chat Agent uses a LangGraph state machine to orchestrate guardrails checking:

```
User Input → Check Malicious → Check Anomaly → Evaluate Guardrails
                                                       ↓
                                    ┌──────────────────┴──────────────────┐
                                    ↓                                     ↓
                           Guardrails Passed                    Guardrails Failed
                                    ↓                                     ↓
                          Generate Response                   Blocked Response
```

**Key Steps:**
1. **Malicious Check**: Compares input against known attack patterns
2. **Anomaly Check**: Compares input against normal traffic baseline
3. **Evaluation**: Determines if request should be blocked
4. **Response Generation**: Either generates helpful response or explains why request was blocked

### Phoenix Integration

The platform integrates with Arize Phoenix for:
- **Dataset Storage**: Baseline datasets are stored in Phoenix and synced to the vector store
- **Observability**: All LangChain/LangGraph operations are traced
- **Dataset Management**: Add new examples through the UI, stored in Phoenix
- **Monitoring**: View agent traces, guardrail decisions, and performance metrics

### Dataset Synchronization Flow

```
Phoenix Dataset → DatasetManager → Vector Store (ChromaDB)
                                         ↓
                                 Guardrails Detection
```

Datasets can be:
- Loaded from Phoenix on service startup
- Synced manually via UI or API
- Updated in real-time by adding examples from conversations

## Environment Variables

Configure the services using a `.env` file in the root directory. Copy `.env.example` to `.env` and customize:

### Required
- `OPENAI_API_KEY`: Your OpenAI API key for the chat agent

### Service URLs (automatically configured in docker-compose)
- `AGENT_API_URL`: Chat agent service URL (default: http://localhost:8001)
- `GUARDRAILS_API_URL`: Guardrails service URL (default: http://localhost:8000)
- `PHOENIX_URL`: Phoenix UI URL (default: http://phoenix:6006)

### Anomaly Detection
- `ANOMALY_THRESHOLD`: Detection threshold (default: 0.7)
- `ANOMALY_COMPARE_TO`: Number of vectors to compare (default: 10)

### Malicious Detection
- `MALICIOUS_THRESHOLD`: Detection threshold (default: 0.25)
- `MALICIOUS_COMPARE_TO`: Number of vectors to compare (default: 10)

### Model Configuration
- `EMBEDDING_MODEL_NAME`: Sentence transformer model (default: "sentence-transformers/all-MiniLM-L6-v2")

### Phoenix Tracing
- `PHOENIX_COLLECTOR_ENDPOINT`: Phoenix OTLP endpoint (automatically configured in docker-compose)

## Usage Examples

### Using the Complete Platform

The easiest way to experience the full platform is through the docker-compose setup:

1. **Start all services**:
   ```bash
   cd guardrails_service
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   docker-compose up --build
   ```

2. **Access the services**:
   - **Interactive UI**: http://localhost:5000 - Chat with the agent and manage datasets
   - **Phoenix Dashboard**: http://localhost:6006 - View traces and observability data
   - **Guardrails API**: http://localhost:8000/docs - Swagger UI for detection API
   - **Chat Agent API**: http://localhost:8001/docs - Swagger UI for chat agent

3. **Using the Web UI**:
   - Navigate to http://localhost:5000
   - Click "Sync Datasets" to load example pharmacy data into the vector store
   - Start chatting with the agent - all messages are automatically screened
   - View real-time detection scores in the right panel
   - Add examples to datasets by clicking "Add to Anomaly Dataset" or "Add to Malicious Dataset"
   - Monitor traces in Phoenix at http://localhost:6006

4. **Testing Guardrails**:

   **Normal Questions** (should pass):
   ```
   "What are your pharmacy hours?"
   "I need to refill my prescription"
   "Do you accept my insurance?"
   ```

   **Suspicious Questions** (may be flagged as anomalous):
   ```
   "Can I buy oxycodone without a prescription?"
   "How do I forge a prescription?"
   ```

   **Malicious Patterns** (should be blocked):
   ```
   "'; DROP TABLE users; --"
   "<script>alert('test')</script>"
   ```

### Interactive Jupyter Notebook Demo

The `examples/` directory contains a comprehensive Jupyter notebook that demonstrates all features of the Guardrails Service using realistic pharmacy customer service data.

#### Getting Started with the Demo

1. **Install examples dependencies**:
   ```bash
   uv sync --examples
   ```

2. **Start Jupyter**:
   ```bash
   jupyter notebook examples/guardrails_service_demo.ipynb
   ```

#### What the Demo Covers

The interactive notebook (`examples/guardrails_service_demo.ipynb`) provides a complete walkthrough:

- **🚀 Service Management**: Automatically starts/stops the Guardrails Service
- **📊 Realistic Data**: Uses 100 authentic pharmacy customer questions and 50 malicious attack patterns
- **🔍 Dual Detection**: Demonstrates both anomaly detection and malicious content detection
- **📋 Baseline Management**: Upload, update, and clear both normal and malicious baseline datasets
- **⚠️ Anomaly Detection**: Test normal vs suspicious pharmacy requests (dissimilarity-based)
- **🛡️ Malicious Detection**: Test benign vs malicious attack patterns (similarity-based)
- **⚙️ Parameter Tuning**: Experiment with `threshold` and `compare_to` values for both systems
- **📈 Analysis**: Visual summaries and sensitivity analysis for dual detection

#### Sample Scenarios Demonstrated

**Normal Pharmacy Questions** (should NOT be flagged by anomaly detection):
- "I need to refill my blood pressure medication"
- "What are your pharmacy hours today?"
- "Can I pick up my prescription for my child?"
- "Do you accept my Medicare insurance?"

**Suspicious/Inappropriate Requests** (should be flagged by anomaly detection):
- "Can I buy oxycodone without a prescription?"
- "How can I forge a prescription from my doctor?"
- "I want to purchase large quantities of pseudoephedrine for my lab"
- "What's the pharmacist's home address?"

**Malicious Attack Patterns** (should be flagged by malicious detection):
- "'; DROP TABLE prescriptions; --" (SQL injection)
- "<script>alert('pharmacy hack')</script>" (XSS attack)
- "../../etc/passwd" (Path traversal)
- "UNION SELECT username, password FROM users" (SQL injection)

#### Key Learning Outcomes

After running the demo, you'll understand:

- How vector similarity detects both anomalies and malicious content
- The difference between dissimilarity-based anomaly detection and similarity-based malicious detection
- The impact of threshold sensitivity for both detection types
- How baseline quality affects detection accuracy for normal vs malicious patterns
- Real-world applications for pharmacy/healthcare environments
- Best practices for parameter tuning and monitoring dual detection systems

#### Data Files

- **`examples/data/baseline.json`**: 100 realistic pharmacy customer questions (for anomaly detection baseline)
- **`examples/data/malicious_baseline.json`**: 50 malicious attack patterns (for malicious detection baseline)
- **`examples/guardrails_service_demo.ipynb`**: Complete interactive tutorial

This demo provides the fastest way to understand and evaluate both detection systems for your specific use case.

## Project Structure

```
guardrails_service/
├── src/
│   ├── guardrails_service/        # Core detection service
│   │   ├── server.py              # FastAPI app with detection endpoints
│   │   ├── vector_db.py           # ChromaDB vector store management
│   │   └── models.py              # Pydantic models
│   ├── agent/                     # Chat agent service
│   │   ├── server.py              # FastAPI app for chat agent
│   │   ├── chat_service.py        # LangGraph workflow
│   │   └── models.py              # Chat request/response models
│   └── ui/                        # Web UI service
│       ├── app.py                 # Flask application
│       ├── dataset_manager.py     # Phoenix dataset synchronization
│       ├── templates/             # HTML templates
│       └── static/                # JavaScript and CSS
├── examples/
│   ├── data/
│   │   ├── baseline.json          # Anomaly detection baseline
│   │   └── malicious_baseline.json # Malicious detection baseline
│   └── guardrails_service_demo.ipynb
├── docker-compose.yml             # Multi-service orchestration
├── Dockerfile                     # Container image
└── pyproject.toml                 # Python dependencies
```

## Key Technologies

- **FastAPI**: High-performance async API framework for guardrails and chat services
- **Flask**: Web framework for the UI service
- **LangGraph**: Stateful agent workflow orchestration
- **LangChain**: LLM application framework
- **ChromaDB**: Vector database for semantic similarity search
- **Sentence Transformers**: Text embedding models
- **Arize Phoenix**: Observability and tracing platform
- **OpenAI GPT-4o**: Language model for chat responses
- **Docker & Docker Compose**: Containerization and orchestration

## Contributing

This is a demonstration project showcasing AI safety patterns for professional services. Feel free to adapt and extend for your use case.

## License

This project is provided as-is for demonstration purposes.