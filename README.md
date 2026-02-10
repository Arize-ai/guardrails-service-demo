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
- `PHOENIX_GRPC_ENDPOINT`: Where to actually send the traces (automatically configured in docker-compose)

### Docker Deployment

The docker deployed platform consists of four integrated services:

1. **UI Service**: Interactive web interface for chatting and dataset management
2. **Phoenix Dashboard**: Observability and tracing with Arize Phoenix
3. **Chat Agent Service**: LangGraph-powered chat agent with automatic guardrails checking
4. **Guardrails Service**: Core detection engine with dual anomaly and malicious content detection

#### Setup

1. **Create a `.env` file from the example**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY if you have one
   # You can also update any of the defaults (listed above)
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

   See the [API reference](docs/api-reference.md) for endpoint documentation.

#### Web Interface

Access the interactive UI at `http://localhost:5000` to:
- Chat with the AI agent with real-time guardrails
- View detection scores for anomaly and malicious content
- Add examples to datasets directly from the conversation
- Sync Phoenix datasets with the vector store
- Monitor guardrail effectiveness in real-time

### Local Development Setup

1. **Setup environment**:
   ```bash
   ./bin/bootstrap.sh
   source .venv/bin/activate
   ```

2. **Run the service**:
   ```bash
   uv run uvicorn guardrails_service.server:app --reload
   ```

The service will be available at `http://localhost:8000`. See the [API reference](docs/api-reference.md) for endpoint documentation.

### Interactive Jupyter Notebook Demo

The `examples/` directory contains a comprehensive Jupyter notebook that demonstrates all features of the Guardrails Service using realistic pharmacy customer service data.

#### Getting Started with the Demo

1. **Install examples dependencies**:
   ```bash
   uv sync --extra examples
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

The platform exposes 16 endpoints across three services. See the [full API reference](docs/api-reference.md) for detailed request/response documentation.

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
