#!/bin/bash
# Setup script - installs dependencies into a virtual environment

set -e

echo "================================================"
echo "Model Traffic Generator - Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error()   { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_success "Python $PYTHON_VERSION detected"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create or reuse virtual environment
echo ""
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate
echo ""
echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"
print_success "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install -q --upgrade pip
print_success "pip upgraded"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
print_success "Dependencies installed"

# Verify imports
echo ""
echo "Verifying installation..."
python3 << 'EOF'
try:
    from cloudera.ai.inference import create_client, ServingListEndpointsRequest
    import httpx
    import openai
    print("✓ All packages imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)
EOF

print_success "All dependencies verified"

echo ""
echo "================================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Set your credentials:"
echo "     export CDP_TOKEN=your-token"
echo "     export CML_DOMAIN=your-domain.com"
echo ""
echo "  2. Or create a .env file:"
echo "     echo 'CDP_TOKEN=your-token' > .env"
echo "     echo 'CML_DOMAIN=your-domain.com' >> .env"
echo ""
echo "  3. Run the traffic generator:"
echo "     python traffic_generator.py --help"
echo "     python traffic_generator.py --once --debug"
echo ""
echo "  4. Or run continuously:"
echo "     python traffic_generator.py"
echo ""
