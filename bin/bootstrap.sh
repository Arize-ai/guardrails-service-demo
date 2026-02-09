#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_NAME=".venv"
VENV_PATH="$PROJECT_ROOT/$VENV_NAME"

echo "🚀 Bootstrapping Guardrails Service..."
echo "Project root: $PROJECT_ROOT"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found: $(uv --version)"

# Navigate to project root
cd "$PROJECT_ROOT"

# Remove existing virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    echo "🧹 Removing existing virtual environment at $VENV_PATH"
    rm -rf "$VENV_PATH"
fi

# Create virtual environment with specific name
echo "📦 Creating virtual environment: $VENV_NAME"
uv venv "$VENV_NAME" --python 3.11
source "$VENV_NAME/bin/activate"

# Install dependencies
echo "📥 Installing dependencies..."
uv sync --dev

echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "To activate the virtual environment:"
echo "   source $VENV_NAME/bin/activate"
echo ""
echo "To run the service:"
echo "   uv run uvicorn guardrails_service.server:app --reload"
echo ""
echo "To run tests:"
echo "   uv run pytest"