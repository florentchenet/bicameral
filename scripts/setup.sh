#!/bin/bash
# Bicameral Quick Install Script
# For new machines - installs bicameral and runs init
# Usage: curl -sSL <url> | bash  OR  ./scripts/setup.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ____  _                                   _ "
echo " | __ )(_) ___ __ _ _ __ ___   ___ _ __ __ _| |"
echo " |  _ \| |/ __/ _\` | '_ \` _ \ / _ \ '__/ _\` | |"
echo " | |_) | | (_| (_| | | | | | |  __/ | | (_| | |"
echo " |____/|_|\___\__,_|_| |_| |_|\___|_|  \__,_|_|"
echo -e "${NC}"
echo -e "${BLUE}AI Collaboration Infrastructure${NC}"
echo ""

# Get script directory (if run from repo)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" 2>/dev/null || echo "." )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR" 2>/dev/null || echo ".")"

# Check Python 3.10+
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 not found${NC}"
    echo "Install from: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}Python 3.10+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}Python $PYTHON_VERSION${NC}"

# Check if bicameral is already installed
if command -v bicameral &> /dev/null; then
    echo -e "${GREEN}Bicameral is already installed${NC}"
    BICAMERAL_VERSION=$(bicameral --version 2>/dev/null | head -1)
    echo -e "  Version: $BICAMERAL_VERSION"
    echo ""
    echo -e "${YELLOW}Run 'bicameral init' to configure${NC}"
    echo -e "${YELLOW}Run 'pip install --upgrade bicameral' to update${NC}"
    exit 0
fi

# Install bicameral
echo ""
echo -e "${YELLOW}Installing bicameral...${NC}"

# Check if we're in the repo directory
if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "Installing from local repository..."
    pip3 install -e "$PROJECT_ROOT" --quiet
else
    # Install from PyPI (when published)
    # For now, install from git
    echo "Installing from git repository..."
    pip3 install git+https://github.com/florentchenet/bicameral.git --quiet
fi

# Verify installation
if ! command -v bicameral &> /dev/null; then
    echo -e "${RED}Installation failed${NC}"
    echo "Try: pip3 install -e . --user"
    exit 1
fi

echo -e "${GREEN}Bicameral installed successfully!${NC}"
echo ""

# Run init
echo -e "${YELLOW}Starting setup wizard...${NC}"
echo ""

bicameral init

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Quick commands:"
echo "  bicameral status              # Check system health"
echo "  bicameral send claude message 'Hello!'  # Send a message"
echo "  bicameral monitor             # Visual monitor"
echo "  bicameral doctor              # Diagnose issues"
echo ""
