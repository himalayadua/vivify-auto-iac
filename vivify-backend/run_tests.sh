#!/bin/bash
# Run all backend tests

echo "🧪 Running Vivify Backend Tests"
echo "================================"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# Install test dependencies if needed
pip install pytest pytest-asyncio pytest-cov httpx -q

# Run tests with coverage
echo ""
echo "📊 Running tests with coverage..."
pytest tests/ -v --cov=services --cov=api --cov-report=term-missing --cov-report=html

# Summary
echo ""
echo "================================"
echo "✅ Tests complete!"
echo "📁 Coverage report: htmlcov/index.html"

