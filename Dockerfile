FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY examples/ ./examples/

# Install dependencies with uv
RUN uv sync --frozen

# Pre-download HuggingFace model to cache it in the image
# This prevents download failures at runtime and improves startup time
RUN uv run python -c "from transformers import AutoTokenizer, AutoModel; \
    model_name = 'sentence-transformers/all-MiniLM-L6-v2'; \
    AutoTokenizer.from_pretrained(model_name); \
    AutoModel.from_pretrained(model_name); \
    print('Model cached successfully')"

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "guardrails_service.server:app", "--host", "0.0.0.0", "--port", "8000"]