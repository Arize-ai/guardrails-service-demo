# Guardrails Service

A comprehensive AI safety platform that combines anomaly detection, malicious content filtering, and an intelligent chat agent with real-time guardrails. The platform uses vector similarity analysis to detect unusual requests and malicious patterns, with Phoenix integration for observability and dataset management.

For a detailed walkthrough of the design and motivation, see the [Adaptive Guardrails for Agentic Applications](docs/guardrails-service-article.md) article.

## Quick Start

### Prerequisites

- Python 3.11
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key for LLM calls (Optional, canned response otherwise)
- Docker (optional, for containerized deployment)

### Environment Variables

Configure the services using a `.env` file in the root directory. Copy `.env.example` to `.env` and customize:

#### LLM
- `OPENAI_API_KEY`: Your OpenAI API key for the chat agent. If this is missing, you will always get a boilerplate response.

#### Anomaly Detection
- `ANOMALY_THRESHOLD`: Detection threshold (default: 0.7)
- `ANOMALY_COMPARE_TO`: Number of vectors to compare (default: 10)

#### Malicious Detection
- `MALICIOUS_THRESHOLD`: Detection threshold (default: 0.25)
- `MALICIOUS_COMPARE_TO`: Number of vectors to compare (default: 10)

#### Phoenix Tracing
- `PHOENIX_COLLECTOR_ENDPOINT`: Phoenix OTLP endpoint (automatically configured in docker-compose)
- `PHOENIX_GRPC_ENDPOINT`: Where to actually send the traces

#### Service URLs (automatically configured in docker-compose)
- `AGENT_API_URL`: Chat agent service URL (default: http://localhost:8001)
- `GUARDRAILS_API_URL`: Guardrails service URL (default: http://localhost:8000)
- `PHOENIX_URL`: Phoenix UI URL (default: http://phoenix:6006)

### Docker Deployment

The docker deployed platform consists of four integrated services:

1. **UI Service** (Port 5000): Interactive web interface for chatting and dataset management
2. **Phoenix Dashboard** (Port 6006): Observability and tracing with Arize Phoenix
3. **Chat Agent Service** (Port 8001): LangGraph-powered chat agent with automatic guardrails checking
4. **Guardrails Service** (Port 8000): Core detection engine with dual anomaly and malicious content detection

#### Setup

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

#### Web Interface

Access the interactive UI at `http://localhost:5000` to:
- Chat with the AI agent with real-time guardrails
- View detection scores for anomaly and malicious content
- Add examples to datasets directly from the conversation
- Sync Phoenix datasets with the vector store
- Monitor guardrail effectiveness in real-time

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

### Features

#### Core Detection System
- **Dual Detection System**: Both anomaly detection and malicious content detection
- **Anomaly Detection**: Identifies unusual requests that differ from normal traffic patterns
- **Malicious Detection**: Identifies requests similar to known malicious patterns
- **Baseline Dataset Management**: Upload, add, retrieve, and clear baseline datasets with date filtering
- **Vector Database**: ChromaDB-powered storage with semantic embeddings using separate collections
- **Smart Detection Logic**: Uses median distance for anomaly detection, minimum distance for malicious detection

#### AI Chat Agent
- **LangGraph-Powered Agent**: Intelligent chat agent with built-in guardrails workflow
- **Real-time Safety Checks**: Automatically screens all user inputs through both detection systems
- **Contextual Responses**: GPT-4o powered responses that adapt based on guardrail results
- **Blocked Request Handling**: Gracefully handles and explains blocked malicious or anomalous requests

#### Observability & Management
- **Phoenix Integration**: Full observability with Arize Phoenix for tracing and monitoring
- **Dataset Synchronization**: Automatic sync between Phoenix datasets and vector store
- **Interactive UI**: Web-based interface for chatting with agent and managing datasets
- **Dynamic Dataset Updates**: Add new examples to baseline datasets in real-time from the UI



## API Endpoints

The service provides two complete sets of endpoints for different detection types:

### Anomaly Detection Endpoints

The anomaly detection system identifies requests that are **dissimilar** to normal traffic patterns.

#### Anomaly Baseline Dataset Management

##### Upload Baseline Dataset
- **POST** `/anomaly/baseline/upload`
- Upload multiple requests to establish baseline patterns
- **Request Body**:
  ```json
  {
    "requests": [
      {
        "timestamp": "2025-08-12T10:00:00",
        "text": "The first of many normal requests"
      }
    ]
  }
  ```
- **Parameters**:
  - `requests` *(array, required)*: List of baseline records, each containing:
    - `text` *(string, required)*: Text content of the request.
    - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.

##### Add Single Entry to Baseline
- **POST** `/anomaly/baseline/add`
- Add a single request to the baseline dataset
- **Request Body**:
  ```json
  {
    "timestamp": "2025-08-12T10:00:00",
    "text": "A new request to add to the baseline"
  }
  ```
- **Parameters**:
  - `text` *(string, required)*: Text content of the request.
  - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.

##### Retrieve Baseline Entries
- **GET** `/anomaly/baseline`
- Retrieve baseline entries with optional date filtering
- **Parameters**:
  - `before` *(datetime, optional)*: Get entries before this date (exclusive). Query parameter.
  - `after` *(datetime, optional)*: Get entries after this date (inclusive). Query parameter.
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

##### Clear Baseline Data
- **POST** `/anomaly/baseline/clear`
- Remove baseline entries with optional date filtering
- **Request Body**:
  ```json
  {
    "before": "2025-08-01T00:00:00",
    "after": "2025-07-01T00:00:00"
  }
  ```
- **Parameters**:
  - `before` *(datetime, optional)*: Remove entries before this date (exclusive).
  - `after` *(datetime, optional)*: Remove entries after this date (inclusive).
  - If no dates provided, all entries are removed. If both provided, removes entries between the dates.

##### Baseline Statistics
- **GET** `/anomaly/baseline/stats`
- Get statistics about the baseline dataset
- **Parameters**: None.
- **Response**:
  ```json
  {
    "total_records": 150,
    "collection_name": "traffic_baseline"
  }
  ```

#### Anomaly Detection

##### Detect Anomaly
- **POST** `/anomaly/detect`
- Analyze incoming request against baseline patterns
- **Request Body**:
  ```json
  {
    "text": "Request text to analyze",
    "timestamp": "2025-08-12T10:00:00",
    "threshold": 0.7,
    "compare_to": 10
  }
  ```
- **Parameters**:
  - `text` *(string, required)*: Text content of the request to analyze.
  - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.
  - `threshold` *(float, optional)*: Similarity threshold for anomaly detection (0.0-1.0). Lower values are more sensitive. Defaults to env `ANOMALY_THRESHOLD` (`0.7`).
  - `compare_to` *(int, optional)*: Number of similar baseline vectors to compare against (minimum 1). Defaults to env `ANOMALY_COMPARE_TO` (`10`).
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

### Malicious Detection Endpoints

The malicious detection system identifies requests that are **similar** to known malicious patterns.

#### Malicious Baseline Dataset Management

##### Upload Malicious Baseline Dataset
- **POST** `/malicious/baseline/upload`
- Upload multiple malicious requests to establish malicious patterns
- **Request Body**:
  ```json
  {
    "requests": [
      {
        "timestamp": "2025-08-12T10:00:00",
        "text": "'; DROP TABLE users; --"
      }
    ]
  }
  ```
- **Parameters**:
  - `requests` *(array, required)*: List of malicious baseline records, each containing:
    - `text` *(string, required)*: Text content of the malicious request.
    - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.

##### Add Single Entry to Malicious Baseline
- **POST** `/malicious/baseline/add`
- Add a single malicious request to the baseline dataset
- **Request Body**:
  ```json
  {
    "timestamp": "2025-08-12T10:00:00",
    "text": "<script>alert('XSS attack')</script>"
  }
  ```
- **Parameters**:
  - `text` *(string, required)*: Text content of the malicious request.
  - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.

##### Retrieve Malicious Baseline Entries
- **GET** `/malicious/baseline`
- Retrieve malicious baseline entries with optional date filtering
- **Parameters**:
  - `before` *(datetime, optional)*: Get entries before this date (exclusive). Query parameter.
  - `after` *(datetime, optional)*: Get entries after this date (inclusive). Query parameter.
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

##### Clear Malicious Baseline Data
- **POST** `/malicious/baseline/clear`
- Remove malicious baseline entries with optional date filtering
- **Request Body**:
  ```json
  {
    "before": "2025-08-01T00:00:00",
    "after": "2025-07-01T00:00:00"
  }
  ```
- **Parameters**:
  - `before` *(datetime, optional)*: Remove entries before this date (exclusive).
  - `after` *(datetime, optional)*: Remove entries after this date (inclusive).
  - If no dates provided, all entries are removed. If both provided, removes entries between the dates.

##### Malicious Baseline Statistics
- **GET** `/malicious/baseline/stats`
- Get statistics about the malicious baseline dataset
- **Parameters**: None.
- **Response**:
  ```json
  {
    "total_records": 50,
    "collection_name": "malicious_baseline"
  }
  ```

#### Malicious Detection

##### Detect Malicious Content
- **POST** `/malicious/detect`
- Analyze incoming request against malicious patterns
- **Request Body**:
  ```json
  {
    "text": "Request text to analyze",
    "timestamp": "2025-08-12T10:00:00",
    "threshold": 0.25,
    "compare_to": 10
  }
  ```
- **Parameters**:
  - `text` *(string, required)*: Text content of the request to analyze.
  - `timestamp` *(datetime, optional)*: Request timestamp. Defaults to current time.
  - `threshold` *(float, optional)*: Similarity threshold for malicious detection (0.0-1.0). Lower values are more sensitive. Defaults to env `MALICIOUS_THRESHOLD` (`0.25`).
  - `compare_to` *(int, optional)*: Number of similar malicious vectors to compare against (minimum 1). Defaults to env `MALICIOUS_COMPARE_TO` (`10`).
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

### Detection Logic Comparison

| Aspect | Anomaly Detection | Malicious Detection |
|--------|------------------|-------------------|
| **Purpose** | Find unusual requests | Find known attack patterns |
| **Logic** | High dissimilarity = anomaly | High similarity = malicious |
| **Metric Used** | Median distance (robust) | Minimum distance (sensitive) |
| **Threshold Logic** | `median_distance > threshold` | `min_distance < threshold` |
| **Default Threshold** | 0.7 | 0.25 |
| **When No Data** | Assume anomaly | Assume benign |
| **Use Case** | Novel/unknown threats | Known attack variations |

### Chat Agent API

The Chat Agent Service provides an intelligent conversational interface with built-in guardrails.

#### Chat Endpoint

- **POST** `/chat` - Send a message to the chat agent with guardrails
- **Request Body**:
  ```json
  {
    "message": "What medications do you have available?",
    "system_prompt": null,
    "anomaly_threshold": 0.8,
    "malicious_threshold": 0.1
  }
  ```
- **Parameters**:
  - `message` *(string, required)*: The user message to send to the chat agent.
  - `system_prompt` *(string, optional)*: Custom system prompt to guide the agent's behavior. Defaults to `null`.
  - `anomaly_threshold` *(float, optional)*: Similarity threshold for anomaly detection (0.0-1.0). Higher values are more permissive. Defaults to `0.8`.
  - `malicious_threshold` *(float, optional)*: Similarity threshold for malicious content detection (0.0-1.0). Lower values are more sensitive. Defaults to `0.1`.

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

### UI Service API

The UI Service provides dataset management capabilities via Phoenix integration.

#### Dataset Management Endpoints

##### Get Dataset Information
- **GET** `/datasets/info` - Get information about Phoenix datasets
- **Parameters**: None. Returns info for the configured `pharmacy-anomaly-baseline` and `pharmacy-malicious-baseline` datasets.
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

##### Sync Datasets
- **POST** `/datasets/sync` - Manually sync Phoenix datasets to vector store
- **Parameters**: None. Syncs both the anomaly and malicious datasets from Phoenix to the vector store.
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

##### Add to Dataset
- **POST** `/datasets/add` - Add an entry to a Phoenix dataset
- **Request Body**:
  ```json
  {
    "dataset_type": "anomaly",
    "text": "What are your hours?",
    "timestamp": "2025-10-16T10:00:00"
  }
  ```
- **Parameters**:
  - `dataset_type` *(string, required)*: The type of dataset to add to. Must be `"anomaly"` or `"malicious"`.
  - `text` *(string, required)*: The text content to add to the dataset.
  - `timestamp` *(string, required)*: ISO 8601 timestamp for the entry.