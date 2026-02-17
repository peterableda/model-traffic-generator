#!/bin/bash
# Quick start script for Model Traffic Generator

set -e

echo "================================================"
echo "Model Traffic Generator - Quick Start"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $PYTHON_VERSION detected"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Check if caiiclient is installed
echo ""
echo "Checking for caiiclient..."
if ! python3 -c "import caiiclient" 2>/dev/null; then
    echo "⚠️  caiiclient is not installed"
    echo ""
    echo "caiiclient must be installed before running this application."
    echo ""
    echo "Run the automated setup script first:"
    echo "  ./setup.sh"
    echo ""
    echo "Or install manually:"
    echo "  Option 1: Download from cluster"
    echo "    curl -k https://\$CML_DOMAIN/api/v1alpha1/client/python --output caiiclient.tar.gz"
    echo "    pip install caiiclient.tar.gz"
    echo ""
    echo "  Option 2: Generate locally"
    echo "    cd ../../../"
    echo "    make build-api-pythonlib"
    echo "    pip install build/python-clients/out/caiiclient.tar.gz"
    echo ""
    exit 1
else
    echo "✓ caiiclient is installed"
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found"
    echo ""
    echo "Please create a .env file with your credentials:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your CDP_TOKEN and CML_DOMAIN"
    echo ""
    
    # Check for environment variables
    if [ -z "$CDP_TOKEN" ] || [ -z "$CML_DOMAIN" ]; then
        echo "Or set environment variables:"
        echo "  export CDP_TOKEN=your-token"
        echo "  export CML_DOMAIN=your-domain.com"
        echo ""
        echo "Then run: python traffic_generator.py"
        exit 1
    fi
fi

# Run the application
echo ""
echo "================================================"
echo "Starting Traffic Generator..."
echo "================================================"
echo ""

# Load .env if it exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the application
python traffic_generator.py "$@"
