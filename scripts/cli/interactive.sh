#!/bin/bash
# Start Bicameral System
# Launches sync daemon and monitor in one command

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Bicameral System..."
echo ""

# Check if local Redis is running
echo "📡 Checking local Redis..."
if ! docker ps | grep -q "redis"; then
    echo "⚠️  Local Redis not running. Starting..."
    cd "$PROJECT_ROOT"
    docker compose up -d redis 2>/dev/null || docker compose -f deploy/minimal/docker-compose.yml up -d redis
    sleep 2
fi
echo "✅ Local Redis ready"
echo ""

# Start sync daemon in background
echo "🔄 Starting sync daemon..."
if pgrep -f "redis_sync_daemon.py" > /dev/null; then
    echo "✅ Sync daemon already running (PID: $(pgrep -f redis_sync_daemon.py))"
else
    python3 "$SCRIPT_DIR/redis_sync_daemon.py" > /dev/null 2>&1 &
    DAEMON_PID=$!
    sleep 2

    if ps -p $DAEMON_PID > /dev/null; then
        echo "✅ Sync daemon started (PID: $DAEMON_PID)"
    else
        echo "⚠️  Sync daemon failed to start (check logs: ~/.bicameral/sync_daemon.log)"
    fi
fi
echo ""

# Show status
echo "📊 System Status:"
echo "   Local Redis:  $(docker ps | grep redis | wc -l | xargs) containers running"
echo "   Sync Daemon:  $(pgrep -f redis_sync_daemon.py | wc -l | xargs) processes"
echo "   Logs:         ~/.bicameral/sync_daemon.log"
echo ""

# Ask user what to do next
echo "What would you like to do?"
echo ""
echo "  1) Monitor collaboration (visual)"
echo "  2) View sync daemon logs (live)"
echo "  3) Send test message"
echo "  4) View message history"
echo "  5) Stop sync daemon"
echo "  6) Exit"
echo ""
read -p "Choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "📺 Starting collaboration monitor..."
        echo "   Press Ctrl+C to exit"
        echo ""
        sleep 1
        python3 "$SCRIPT_DIR/monitor_collab_v2.py"
        ;;
    2)
        echo ""
        echo "📋 Showing sync daemon logs (Ctrl+C to exit)..."
        echo ""
        tail -f ~/.bicameral/sync_daemon.log
        ;;
    3)
        echo ""
        read -p "Agent name (claude/gemini): " agent
        read -p "Message: " message
        python3 "$SCRIPT_DIR/bicameral_client.py" "$agent" test "$message"
        ;;
    4)
        echo ""
        echo "📜 Recent message history:"
        echo ""
        python3 << EOF
from scripts.bicameral_client import BicameralClient
c = BicameralClient('viewer')
for msg in c.get_history(20):
    print(f"[{msg['timestamp'][11:19]}] {msg['from']:8} → {msg['type']:10} | {msg['message'][:60]}")
EOF
        ;;
    5)
        echo ""
        echo "🛑 Stopping sync daemon..."
        pkill -f redis_sync_daemon.py
        echo "✅ Daemon stopped"
        ;;
    6)
        echo ""
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
