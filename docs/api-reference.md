# API Reference

The platform exposes three services, each with its own set of endpoints:

| Service | Base URL | Description |
|---------|----------|-------------|
| **Guardrails Service** | `http://localhost:8000` | Core anomaly and malicious content detection |
| **Chat Agent Service** | `http://localhost:8001` | LangGraph-powered chat agent with guardrails |
| **UI Service** | `http://localhost:5000` | Dataset management via Phoenix integration |

## Quick Reference

| Method | Endpoint | Service | Description |
|--------|----------|---------|-------------|
| POST | `/anomaly/baseline/upload` | Guardrails | Upload baseline dataset |
| POST | `/anomaly/baseline/add` | Guardrails | Add single entry to baseline |
| GET | `/anomaly/baseline` | Guardrails | Retrieve baseline entries |
| POST | `/anomaly/baseline/clear` | Guardrails | Clear baseline data |
| GET | `/anomaly/baseline/stats` | Guardrails | Get baseline statistics |
| POST | `/anomaly/detect` | Guardrails | Detect anomalous requests |
| POST | `/malicious/baseline/upload` | Guardrails | Upload malicious baseline dataset |
| POST | `/malicious/baseline/add` | Guardrails | Add single entry to malicious baseline |
| GET | `/malicious/baseline` | Guardrails | Retrieve malicious baseline entries |
| POST | `/malicious/baseline/clear` | Guardrails | Clear malicious baseline data |
| GET | `/malicious/baseline/stats` | Guardrails | Get malicious baseline statistics |
| POST | `/malicious/detect` | Guardrails | Detect malicious content |
| POST | `/chat` | Chat Agent | Send a message with guardrails |
| GET | `/datasets/info` | UI | Get Phoenix dataset information |
| POST | `/datasets/sync` | UI | Sync Phoenix datasets to vector store |
| POST | `/datasets/add` | UI | Add an entry to a Phoenix dataset |

---

## Guardrails Service (Port 8000)

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

---

## Chat Agent Service (Port 8001)

The Chat Agent Service provides an intelligent conversational interface with built-in guardrails.

### Chat Endpoint

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

---

## UI Service (Port 5000)

The UI Service provides dataset management capabilities via Phoenix integration.

### Dataset Management Endpoints

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
