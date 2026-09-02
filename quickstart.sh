#!/bin/bash
# Quick start script for Model Traffic Generator

set -e

echo "================================================"
echo "Model Traffic Generator - Quick Start"
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $PYTHON_VERSION detected"

# Create or reuse virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"

# Check for credentials
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found"
    echo ""
    echo "Please create a .env file with your credentials:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env with your CDP_TOKEN and CML_DOMAIN"
    echo ""

    if [ -z "$CDP_TOKEN" ] || [ -z "$CML_DOMAIN" ]; then
        echo "Or set environment variables:"
        echo "  export CDP_TOKEN=your-token"
        echo "  export CML_DOMAIN=your-domain.com"
        echo ""
        echo "Then run: python traffic_generator.py"
        exit 1
    fi
fi

# Run
echo ""
echo "================================================"
echo "Starting Traffic Generator..."
echo "================================================"
echo ""

if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

python traffic_generator.py "$@"
