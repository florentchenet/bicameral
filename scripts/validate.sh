#!/bin/bash
# Bicameral Deployment Validation Script
# Verifies that the system is correctly set up and operational
# Usage: ./scripts/validate_deployment.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🔍 BICAMERAL DEPLOYMENT VALIDATOR      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Load configuration
if [ -f ~/.bicameral/.env ]; then
    source ~/.bicameral/.env
    echo -e "${GREEN}✅ Configuration found${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "${RED}❌ Configuration missing: ~/.bicameral/.env${NC}"
    echo "   Run: ./scripts/setup_bicameral.sh"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    exit 1
fi
echo ""

# Test 1: Python Dependencies
echo -e "${BLUE}[1/10] Python Dependencies${NC}"
MISSING_DEPS=""
for pkg in redis python-dotenv rich; do
    if python3 -c "import ${pkg//-/_}" 2>/dev/null; then
        echo -e "  ${GREEN}✅ $pkg${NC}"
    else
        echo -e "  ${RED}❌ $pkg (missing)${NC}"
        MISSING_DEPS="$MISSING_DEPS $pkg"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done
if [ -z "$MISSING_DEPS" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}Fix: pip install$MISSING_DEPS${NC}"
fi
echo ""

# Test 2: Local Redis
echo -e "${BLUE}[2/10] Local Redis${NC}"
if redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" PING > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Local Redis: ONLINE${NC}"

    # Check Redis version
    REDIS_VERSION=$(redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" INFO server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r')
    echo -e "  ${GREEN}   Version: $REDIS_VERSION${NC}"

    # Check memory
    REDIS_MEM=$(redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    echo -e "  ${GREEN}   Memory: $REDIS_MEM${NC}"

    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${RED}❌ Local Redis: OFFLINE${NC}"
    echo -e "  ${YELLOW}Fix: docker run -d --name bicameral-redis -p 6379:6379 redis:7-alpine redis-server --requirepass \"$LOCAL_REDIS_PASSWORD\"${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 3: VPS Redis
echo -e "${BLUE}[3/10] VPS Redis${NC}"
if redis-cli -h "$REDIS_HOST" -p 6379 -a "$REDIS_PASSWORD" PING > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ VPS Redis: ONLINE${NC}"
    echo -e "  ${GREEN}   Host: $REDIS_HOST:6379${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}⚠️  VPS Redis: OFFLINE${NC}"
    echo -e "  ${YELLOW}   Note: VPS sync disabled (local-only mode)${NC}"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
echo ""

# Test 4: Stream Exists
echo -e "${BLUE}[4/10] Redis Stream${NC}"
STREAM_LEN=$(redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" \
    XLEN "$STREAM_KEY" 2>/dev/null || echo "0")
if [ "$STREAM_LEN" != "0" ]; then
    echo -e "  ${GREEN}✅ Stream exists: $STREAM_LEN messages${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}⚠️  Stream empty (no messages yet)${NC}"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
echo ""

# Test 5: Message Send
echo -e "${BLUE}[5/10] Message Send${NC}"
cd "$(dirname "$0")/.."
if python3 scripts/bicameral_client.py validator test "Validation test message" 2>&1 | grep -q "Message sent"; then
    echo -e "  ${GREEN}✅ Message send: WORKING${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${RED}❌ Message send: FAILED${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 6: Pub/Sub Channel
echo -e "${BLUE}[6/10] Pub/Sub Channels${NC}"
CHANNELS=$(redis-cli -h localhost -p 6379 -a "$LOCAL_REDIS_PASSWORD" \
    PUBSUB CHANNELS 2>/dev/null | wc -l | xargs)
if [ "$CHANNELS" != "0" ]; then
    echo -e "  ${GREEN}✅ Active channels: $CHANNELS${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}⚠️  No active subscribers${NC}"
    echo -e "  ${YELLOW}   Note: Start listener to activate Pub/Sub${NC}"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
echo ""

# Test 7: Sync Daemon
echo -e "${BLUE}[7/10] Sync Daemon${NC}"
if pgrep -f redis_sync_daemon.py > /dev/null; then
    DAEMON_PID=$(pgrep -f redis_sync_daemon.py)
    echo -e "  ${GREEN}✅ Sync daemon: RUNNING (PID: $DAEMON_PID)${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}⚠️  Sync daemon: NOT RUNNING${NC}"
    echo -e "  ${YELLOW}   Fix: python3 scripts/redis_sync_daemon.py &${NC}"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
echo ""

# Test 8: Directory Structure
echo -e "${BLUE}[8/10] Directory Structure${NC}"
ALL_DIRS_OK=true
for dir in bin config logs notifications; do
    if [ -d ~/.bicameral/$dir ]; then
        echo -e "  ${GREEN}✅ ~/.bicameral/$dir${NC}"
    else
        echo -e "  ${RED}❌ ~/.bicameral/$dir (missing)${NC}"
        ALL_DIRS_OK=false
    fi
done
if $ALL_DIRS_OK; then
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}Fix: mkdir -p ~/.bicameral/{bin,config,logs,notifications}${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Test 9: Log Files
echo -e "${BLUE}[9/10] Log Files${NC}"
LOG_COUNT=0
for log in client.log sync_daemon.log; do
    if [ -f ~/.bicameral/$log ]; then
        LOG_SIZE=$(du -h ~/.bicameral/$log 2>/dev/null | cut -f1)
        echo -e "  ${GREEN}✅ $log ($LOG_SIZE)${NC}"
        LOG_COUNT=$((LOG_COUNT + 1))
    fi
done
if [ $LOG_COUNT -gt 0 ]; then
    echo -e "  ${GREEN}✅ Found $LOG_COUNT log files${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}⚠️  No log files yet (system not used)${NC}"
    WARN_COUNT=$((WARN_COUNT + 1))
fi
echo ""

# Test 10: Scripts Executable
echo -e "${BLUE}[10/10] Script Permissions${NC}"
EXEC_COUNT=0
for script in bicameral_client.py redis_sync_daemon.py start_bicameral.sh; do
    if [ -x "scripts/$script" ]; then
        echo -e "  ${GREEN}✅ $script${NC}"
        EXEC_COUNT=$((EXEC_COUNT + 1))
    else
        echo -e "  ${RED}❌ $script (not executable)${NC}"
    fi
done
if [ $EXEC_COUNT -eq 3 ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo -e "  ${YELLOW}Fix: chmod +x scripts/*.sh scripts/*.py${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
echo ""

# Summary
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   📊 VALIDATION SUMMARY                  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}✅ Passed: $PASS_COUNT/10${NC}"
echo -e "  ${YELLOW}⚠️  Warnings: $WARN_COUNT/10${NC}"
echo -e "  ${RED}❌ Failed: $FAIL_COUNT/10${NC}"
echo ""

# Overall status
if [ $FAIL_COUNT -eq 0 ]; then
    if [ $WARN_COUNT -eq 0 ]; then
        echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║   ✅ ALL TESTS PASSED!                   ║${NC}"
        echo -e "${GREEN}║   System is fully operational            ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${YELLOW}╔═══════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║   ⚠️  SYSTEM OPERATIONAL WITH WARNINGS   ║${NC}"
        echo -e "${YELLOW}║   Core features working, optional items  ║${NC}"
        echo -e "${YELLOW}║   disabled or not configured             ║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════╝${NC}"
        exit 0
    fi
else
    echo -e "${RED}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ❌ VALIDATION FAILED                   ║${NC}"
    echo -e "${RED}║   Fix critical issues above              ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Run setup: ./scripts/setup_bicameral.sh${NC}"
    exit 1
fi
