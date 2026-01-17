#!/bin/bash
# Bicameral Setup Wizard
# One-command setup for new machines
# Usage: ./scripts/setup_bicameral.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🦏 BICAMERAL SETUP WIZARD              ║${NC}"
echo -e "${BLUE}║   Claude ↔ Gemini Collaboration System  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: Check prerequisites
echo -e "${YELLOW}📋 Step 1/7: Checking prerequisites...${NC}"

# Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "   Install: https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✅ Python ${PYTHON_VERSION}${NC}"

# Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo "   Install: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✅ Docker $(docker --version | awk '{print $3}' | tr -d ',')${NC}"

# Tailscale (optional)
if command -v tailscale &> /dev/null; then
    echo -e "${GREEN}✅ Tailscale $(tailscale version | head -1)${NC}"
else
    echo -e "${YELLOW}⚠️  Tailscale not found (optional for VPS sync)${NC}"
    echo "   Install: https://tailscale.com/download"
fi

# Git
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}⚠️  Git not found (recommended)${NC}"
else
    echo -e "${GREEN}✅ Git $(git --version | awk '{print $3}')${NC}"
fi

echo ""

# Step 2: Install Python dependencies
echo -e "${YELLOW}📦 Step 2/7: Installing Python packages...${NC}"

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Not in virtual environment${NC}"
    read -p "   Create venv? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m venv "$PROJECT_ROOT/venv"
        source "$PROJECT_ROOT/venv/bin/activate"
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    fi
fi

pip3 install -q redis python-dotenv rich 2>&1 | grep -v "already satisfied" || true
echo -e "${GREEN}✅ Packages installed: redis, python-dotenv, rich${NC}"
echo ""

# Step 3: Create directory structure
echo -e "${YELLOW}📁 Step 3/7: Creating directories...${NC}"
mkdir -p ~/.bicameral/{bin,config,logs,notifications}
echo -e "${GREEN}✅ Created ~/.bicameral/{bin,config,logs,notifications}${NC}"
echo ""

# Step 4: Generate passwords
echo -e "${YELLOW}🔐 Step 4/7: Generating secure passwords...${NC}"

# Check if config exists
if [ -f ~/.bicameral/.env ]; then
    echo -e "${YELLOW}⚠️  Configuration already exists${NC}"
    read -p "   Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}ℹ️  Using existing configuration${NC}"
        source ~/.bicameral/.env
        SKIP_CONFIG=true
    fi
fi

if [ -z "$SKIP_CONFIG" ]; then
    # Generate secure passwords
    LOCAL_PASS=$(openssl rand -base64 32)
    VPS_PASS=$(openssl rand -hex 16)
    GATEWAY_TOKEN=$(openssl rand -hex 32)

    echo -e "${GREEN}✅ Generated secure passwords${NC}"
    echo ""

    # Step 5: Create configuration
    echo -e "${YELLOW}⚙️  Step 5/7: Creating configuration...${NC}"

    # Ask for VPS details
    echo "VPS Configuration (press Enter for defaults):"
    read -p "   VPS IP [100.111.230.6]: " VPS_IP
    VPS_IP=${VPS_IP:-100.111.230.6}

    read -p "   VPS Redis password [auto-generated]: " USER_VPS_PASS
    VPS_PASS=${USER_VPS_PASS:-$VPS_PASS}

    read -p "   Gateway API URL [https://api.rhncrs.com]: " GATEWAY_URL
    GATEWAY_URL=${GATEWAY_URL:-https://api.rhncrs.com}

    # Create config file
    cat > ~/.bicameral/.env << EOF
# Bicameral Unified Configuration
# Generated: $(date)

# Local Redis (PRIMARY - work here, always fast)
LOCAL_REDIS_HOST=localhost
LOCAL_REDIS_PORT=6379
LOCAL_REDIS_PASSWORD=$LOCAL_PASS

# VPS Redis (SYNC TARGET - for remote access, iOS, etc)
REDIS_HOST=$VPS_IP
REDIS_PORT=6379
REDIS_PASSWORD=$VPS_PASS

# Gateway API (production)
GATEWAY_API=$GATEWAY_URL
GATEWAY_TOKEN=$GATEWAY_TOKEN

# Stream configuration
STREAM_KEY=bicameral:stream:collab
EOF

    chmod 600 ~/.bicameral/.env
    echo -e "${GREEN}✅ Configuration saved to ~/.bicameral/.env${NC}"
    echo ""
else
    echo ""
fi

# Source config for next steps
source ~/.bicameral/.env

# Step 6: Start local Redis
echo -e "${YELLOW}🚀 Step 6/7: Starting local Redis...${NC}"

# Check if Redis is already running
if docker ps | grep -q bicameral-redis; then
    echo -e "${GREEN}✅ Redis already running${NC}"
elif docker ps -a | grep -q bicameral-redis; then
    echo -e "${YELLOW}⚠️  Redis container exists but stopped${NC}"
    docker start bicameral-redis
    echo -e "${GREEN}✅ Redis started${NC}"
else
    # Start new Redis container
    docker run -d \
        --name bicameral-redis \
        --restart unless-stopped \
        -p 6379:6379 \
        redis:7-alpine \
        redis-server --appendonly yes --requirepass "$LOCAL_REDIS_PASSWORD" \
        > /dev/null 2>&1

    # Wait for Redis to be ready
    echo -n "   Waiting for Redis..."
    for i in {1..10}; do
        if docker exec bicameral-redis redis-cli -a "$LOCAL_REDIS_PASSWORD" ping > /dev/null 2>&1; then
            echo " ready!"
            break
        fi
        sleep 1
        echo -n "."
    done

    echo -e "${GREEN}✅ Redis started (container: bicameral-redis)${NC}"
fi
echo ""

# Step 7: Test connection
echo -e "${YELLOW}🧪 Step 7/7: Testing system...${NC}"

# Test Python client
cd "$PROJECT_ROOT"
if python3 scripts/bicameral_client.py system test "Setup complete!" 2>&1 | grep -q "Message sent"; then
    echo -e "${GREEN}✅ Message send: WORKING${NC}"
else
    echo -e "${RED}❌ Message send: FAILED${NC}"
    echo "   Check logs: ~/.bicameral/client.log"
    exit 1
fi

# Check message in Redis
MSG_COUNT=$(redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" \
    XLEN bicameral:stream:collab 2>/dev/null)
echo -e "${GREEN}✅ Messages in stream: $MSG_COUNT${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✅ SETUP COMPLETE!                     ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Show next steps
echo -e "${BLUE}📚 Next Steps:${NC}"
echo ""
echo -e "  ${YELLOW}1. Start sync daemon (for VPS sync):${NC}"
echo "     python3 scripts/redis_sync_daemon.py &"
echo ""
echo -e "  ${YELLOW}2. Start visual monitor:${NC}"
echo "     python3 scripts/monitor_collab_v2.py"
echo ""
echo -e "  ${YELLOW}3. Send a message:${NC}"
echo "     python3 scripts/bicameral_client.py claude test 'Hello Gemini!'"
echo ""
echo -e "  ${YELLOW}4. Install auto-start service (optional):${NC}"
echo "     ./scripts/install_sync_service.sh"
echo ""
echo -e "  ${YELLOW}5. Interactive menu:${NC}"
echo "     ./scripts/start_bicameral.sh"
echo ""

# Show configuration summary
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo "   Config file: ~/.bicameral/.env"
echo "   Local Redis: localhost:6379"
echo "   VPS Redis: $REDIS_HOST:6379"
echo "   Gateway API: $GATEWAY_API"
echo "   Logs: ~/.bicameral/logs/"
echo ""

# Show documentation
echo -e "${BLUE}📖 Documentation:${NC}"
echo "   Quick reference: $PROJECT_ROOT/QUICK-REFERENCE.md"
echo "   Full audit: $PROJECT_ROOT/BICAMERAL-INFRASTRUCTURE-AUDIT-2026-01-17.md"
echo "   Architecture: $PROJECT_ROOT/LOCAL-FIRST-ARCHITECTURE.md"
echo ""

# Ask if user wants to start interactive menu
read -p "Start interactive menu now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ./scripts/start_bicameral.sh
fi

echo ""
echo -e "${GREEN}🎉 Welcome to Bicameral! 🦏${NC}"
