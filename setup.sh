#!/bin/bash
# Automated setup script - generates caiiclient from source and installs dependencies

set -e

echo "================================================"
echo "Model Traffic Generator - Automated Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
print_success "Python $PYTHON_VERSION detected"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo ""
echo "Checking for bundled caiiclient..."
if [ ! -f "$SCRIPT_DIR/vendor/caiiclient.tar.gz" ]; then
    print_error "caiiclient package not found in vendor/"
    echo ""
    echo "Expected location: $SCRIPT_DIR/vendor/caiiclient.tar.gz"
    echo ""
    echo "Please ensure the vendor directory contains caiiclient.tar.gz"
    exit 1
fi

print_success "Found bundled caiiclient package"

# Check if virtual environment exists or create one
echo ""
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"
print_success "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install -q --upgrade pip
print_success "pip upgraded"

# Install caiiclient from vendor directory
echo ""
echo "Installing caiiclient from bundled package..."
pip install "$SCRIPT_DIR/vendor/caiiclient.tar.gz"
print_success "caiiclient installed"

# Verify installation
if python3 -c "import caiiclient" 2>/dev/null; then
    print_success "caiiclient verified"
else
    print_error "caiiclient installation verification failed"
    exit 1
fi

# Install other dependencies
echo ""
echo "Installing other dependencies..."
pip install -q -r "$SCRIPT_DIR/requirements.txt"
print_success "Dependencies installed"

# Verify all imports
echo ""
echo "Verifying installation..."
python3 << 'EOF'
try:
    import caiiclient
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
