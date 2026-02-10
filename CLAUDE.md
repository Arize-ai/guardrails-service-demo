# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a collection of project prototypes with the main project being a Python-based Guardrails Service located in `guardrails_service/`.

## Guardrails Service

### Architecture
- FastAPI-based REST API service in `guardrails_service/`
- Docker containerized with development support via docker-compose
- Self-hosted Phoenix for dataset management and OpenTelemetry tracing (port 6006 UI, port 4317 gRPC)

### Common Commands

#### Development Setup
```bash
cd guardrails_service
# Bootstrap the project (creates .venv and installs dependencies)
./bin/bootstrap.sh

# Or manually:
uv venv .venv --python 3.11
uv sync --dev
source .venv/bin/activate
```

#### Running the Service
```bash
# Local development (uses uv to run in virtual environment)
uv run uvicorn guardrails_service.main:app --reload

# Docker development
docker-compose up --build

# Production Docker
docker build -t guardrails-service .
docker run -p 8000:8000 guardrails-service
```

#### Code Quality
```bash
# Format code
uv run black guardrails_service/

# Sort imports
uv run isort

# Type checking
uv run mypy
```

### Key Files
- `guardrails_service/server.py` - FastAPI application entry point
- `guardrails_service/vector_db.py` - Handles embedding and comparisons of text
- `guardrails_service/models.py` - Schema definitions for requests and responses
- `examples/` - example notebooks and tutorials
- `pyproject.toml` - Project configuration and dependencies
- `bin/bootstrap.sh` - Development environment setup script
- `Dockerfile` - Production container configuration using uv
- `docker-compose.yml` - Development environment setup
- `.venv/` - Virtual environment directory (created by bootstrap)